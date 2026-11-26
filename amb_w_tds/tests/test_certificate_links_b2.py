"""TASKS-384 B2 (tds half), DB-free: the certificate's Work Order, the type by product, creation from a lot with the
customers filled on the server, and the two repairs on the form (the lot-change handler, the Client Script that
emptied the series).

The classification table ships EMPTY (no rule separating finished from semi-finished products could be read from the
code); these tests fill it for their own run to prove the mechanism around it."""

import json
import os
import types
import unittest
from contextlib import ExitStack, contextmanager
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.doctype.coa_amb import coa_amb as amb
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2
from amb_w_tds.api import certificate as api

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLASSES = {"COA AMB": amb.COAAMB, "COA AMB2": amb2.COAAMB2}
TABLE = {"Finished": "COA AMB", "Semi": "COA AMB2"}
# item -> its Item Group; Item Group -> its parent
ITEMS = {"MIX-1": "Finished Mixes", "POWDER-1": "Semi Powders", "PACK-1": "Packaging", "ODD-1": "Loop A"}
GROUPS = {
	"Finished Mixes": "Finished",
	"Finished": "All Item Groups",
	"Semi Powders": "Semi",
	"Semi": "All Item Groups",
	"Packaging": "All Item Groups",
	"All Item Groups": None,
	"Loop A": "Loop B",
	"Loop B": "Loop A",
}


def _throw(msg, *a, **k):
	raise frappe.ValidationError(msg)


class Db:
	"""Items, Item Groups, lots and specifications, as the code reads them."""

	def __init__(self, lots=None, specs=None):
		self.lots, self.specs, self.asked = lots or {}, specs or {}, []

	def get_value(self, doctype, name, fields, as_dict=False):
		self.asked.append((doctype, name))
		if doctype == "Item":
			return ITEMS.get(name)
		if doctype == "Item Group":
			return GROUPS.get(name)
		if doctype == "Batch AMB":
			return frappe._dict(self.lots[name]) if name in self.lots else None
		if doctype == "TDS Product Specification":
			return (self.specs.get(name) or {}).get("product_item")
		return None

	def exists(self, doctype, name=None):
		return name in {"Item": ITEMS, "TDS Product Specification": self.specs}.get(doctype, {})


@contextmanager
def site(db=None, table=TABLE, docs=None):
	db = db or Db()
	fake = types.SimpleNamespace(
		session=frappe._dict(user="maker"),
		throw=_throw,
		msgprint=mock.Mock(),
		db=db,
		get_doc=lambda doctype, name: (docs or {})[(doctype, name)],
		new_doc=mock.Mock(),
		whitelist=frappe.whitelist,
	)
	with ExitStack() as stack:
		for module in (rules, api):
			stack.enter_context(mock.patch.object(module, "frappe", fake))
			stack.enter_context(mock.patch.object(module, "_", lambda s: s))
		stack.enter_context(mock.patch.object(frappe, "throw", _throw))
		stack.enter_context(mock.patch.object(api, "CERTIFICATE_TYPE_BY_ITEM_GROUP", dict(table)))
		yield fake


def cert(doctype="COA AMB", product="MIX-1", before=None, new=True, **kw):
	d = object.__new__(CLASSES[doctype])
	d.__dict__.update(
		doctype=doctype,
		name="COA-1",
		docstatus=0,
		linked_tds=None,
		batch_reference=None,
		product_item=product,
		work_order=None,
		coa_quality_test_parameter=[],
		custom_coa_customers=[],
		filled_by=None,
		approved_by=None,
		approval_date=None,
	)
	d.__dict__[rules.STATE_FIELD[doctype]] = "Draft"
	d.__dict__.update(kw)
	if new:
		d.__dict__["__islocal"] = 1
		d._doc_before_save = None
	else:
		stored = frappe._dict(
			doctype=doctype,
			docstatus=0,
			product_item=product,
			batch_reference=d.batch_reference,
			coa_quality_test_parameter=[],
			filled_by=None,
			approved_by=None,
			approval_date=None,
		)
		stored[rules.STATE_FIELD[doctype]] = "Draft"
		stored.update(before or {})
		d._doc_before_save = stored
	for name in ("validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link"):
		setattr(d, name, lambda: None)
	return d


def save(doc, **kw):
	with site(**kw) as fake:
		try:
			doc.validate()
		except frappe.ValidationError as e:
			return str(e), fake
	return None, fake


class TestTypeByProduct(unittest.TestCase):
	def classed(self, item, table=TABLE):
		with site(table=table) as fake:
			return api.certificate_type_for_item(item), fake.db.asked

	def test_the_table_ships_empty_so_every_item_is_unclassed_and_nothing_is_read(self):
		self.assertEqual(api.CERTIFICATE_TYPE_BY_ITEM_GROUP, {})
		self.assertEqual(self.classed("MIX-1", table={}), (None, []))

	def test_an_item_is_classed_by_the_nearest_group_of_its_ancestry_named_in_the_table(self):
		self.assertEqual(self.classed("MIX-1")[0], "COA AMB")
		self.assertEqual(self.classed("POWDER-1")[0], "COA AMB2")
		# the item's own group wins over an ancestor
		self.assertEqual(
			self.classed("MIX-1", table={"Finished": "COA AMB", "Finished Mixes": "COA AMB2"})[0], "COA AMB2"
		)

	def test_an_item_outside_the_table_an_unknown_item_and_no_item_are_unclassed(self):
		for item in ("PACK-1", "NOT-AN-ITEM", None, ""):
			self.assertIsNone(self.classed(item)[0], item)
		self.assertIsNone(self.classed("ODD-1")[0])  # a loop in the tree ends

	def test_the_wrong_type_for_a_classed_product_is_refused_when_the_certificate_is_made(self):
		refusal, _ = save(cert("COA AMB", "POWDER-1"))
		self.assertIn("takes a COA AMB2, not a COA AMB", refusal or "")
		refusal, _ = save(cert("COA AMB2", "MIX-1"))
		self.assertIn("takes a COA AMB, not a COA AMB2", refusal or "")

	def test_the_right_type_and_an_unclassed_product_pass(self):
		for doctype, product in (
			("COA AMB", "MIX-1"),
			("COA AMB2", "POWDER-1"),
			("COA AMB", "PACK-1"),
			("COA AMB2", "PACK-1"),
			("COA AMB", None),
		):
			self.assertIsNone(save(cert(doctype, product))[0], (doctype, product))
		# with the table as shipped nothing is refused
		self.assertIsNone(save(cert("COA AMB", "POWDER-1"), table={})[0])

	def test_a_stored_certificate_is_judged_again_only_when_its_product_changes(self):
		unchanged = cert("COA AMB", "POWDER-1", new=False)
		self.assertIsNone(save(unchanged)[0])
		changed = cert("COA AMB", "POWDER-1", new=False, before={"product_item": "MIX-1"})
		self.assertIn("takes a COA AMB2, not a COA AMB", save(changed)[0] or "")


class TestWorkOrderFollowsTheLot(unittest.TestCase):
	LOT = (("LOTE-1", {"work_order_ref": "WO-1", "item_to_manufacture": "MIX-1"}),)

	def test_the_server_writes_the_lots_work_order_on_both_types(self):
		for doctype, product in (("COA AMB", "MIX-1"), ("COA AMB2", "POWDER-1")):
			d = cert(doctype, product, batch_reference="LOTE-1", work_order="TYPED")
			self.assertIsNone(
				save(d, db=Db(lots={"LOTE-1": {"work_order_ref": "WO-1", "item_to_manufacture": product}}))[0]
			)
			self.assertEqual(d.work_order, "WO-1", doctype)

	def test_a_lot_without_a_work_order_no_lot_and_a_missing_lot_leave_the_field(self):
		for lots, lot in (
			({"LOTE-1": {"work_order_ref": None, "item_to_manufacture": "MIX-1"}}, "LOTE-1"),
			({}, None),
			({}, "GONE"),
		):
			d = cert(batch_reference=lot, work_order="TYPED")
			self.assertIsNone(save(d, db=Db(lots=lots))[0])
			self.assertEqual(d.work_order, "TYPED")

	def test_a_different_item_on_the_lot_is_shown_not_refused_and_the_product_stays(self):
		d = cert("COA AMB", "MIX-1", batch_reference="LOTE-1")
		refusal, fake = save(
			d, db=Db(lots={"LOTE-1": {"work_order_ref": "WO-1", "item_to_manufacture": "POWDER-1"}})
		)
		self.assertIsNone(refusal)
		self.assertEqual(d.product_item, "MIX-1")
		self.assertEqual(fake.msgprint.call_count, 1)
		self.assertIn("The product was not changed", fake.msgprint.call_args.args[0])

	def test_the_message_comes_once_not_on_every_save(self):
		lots = {"LOTE-1": {"work_order_ref": "WO-1", "item_to_manufacture": "POWDER-1"}}
		same = cert("COA AMB", "MIX-1", new=False, batch_reference="LOTE-1")
		self.assertEqual(save(same, db=Db(lots=lots))[1].msgprint.call_count, 0)
		lot_changed = cert(
			"COA AMB", "MIX-1", new=False, batch_reference="LOTE-1", before={"batch_reference": "LOTE-0"}
		)
		self.assertEqual(save(lot_changed, db=Db(lots=lots))[1].msgprint.call_count, 1)
		# the same item on both: nothing to say
		equal = cert("COA AMB", "MIX-1", batch_reference="LOTE-1")
		self.assertEqual(save(equal, db=Db(lots=dict(self.LOT)))[1].msgprint.call_count, 0)


def _customer(name, **kw):
	return frappe._dict(
		customer=name, custom_customer_name=name + " name", custom_customer_part_number=None, **kw
	)


class TestCustomersFilledOnTheServer(unittest.TestCase):
	def fill(
		self,
		spec_rows=None,
		item_rows=None,
		doctype="COA AMB",
		existing=None,
		has_field=True,
		linked_tds="TDS-1",
	):
		d = cert(doctype, "MIX-1", linked_tds=linked_tds, custom_coa_customers=list(existing or []))
		d.__dict__["meta"] = types.SimpleNamespace(has_field=lambda f: has_field)
		d.append = lambda table, values: d.__dict__[table].append(dict(values))
		docs = {
			("TDS Product Specification", "TDS-1"): frappe._dict(custom_tds_customers=spec_rows),
			("Item", "MIX-1"): frappe._dict(custom_amb_customer_items=item_rows),
		}
		with site(db=Db(specs={"TDS-1": {"product_item": "MIX-1"}}), docs=docs):
			rules.fill_customers(d)
		return d.custom_coa_customers

	def test_the_specifications_customers_come_first(self):
		rows = self.fill(spec_rows=[_customer("C-1"), _customer("C-2")], item_rows=[_customer("C-9")])
		self.assertEqual([r["customer"] for r in rows], ["C-1", "C-2"])
		self.assertEqual(sorted(rows[0]), sorted(rules.CUSTOMER_ROW_FIELDS))
		self.assertEqual(rows[0]["custom_customer_name"], "C-1 name")

	def test_else_the_items(self):
		for spec_rows in (None, [], [frappe._dict(customer=None)]):
			rows = self.fill(spec_rows=spec_rows, item_rows=[_customer("C-9")])
			self.assertEqual([r["customer"] for r in rows], ["C-9"], spec_rows)
		self.assertEqual(
			[r["customer"] for r in self.fill(item_rows=[_customer("C-9")], linked_tds=None)], ["C-9"]
		)

	def test_no_customers_anywhere_leaves_the_list_empty(self):
		self.assertEqual(self.fill(), [])

	def test_a_list_that_has_rows_and_a_type_without_the_table_are_left_alone(self):
		existing = [frappe._dict(customer="C-0")]
		self.assertEqual(self.fill(spec_rows=[_customer("C-1")], existing=existing), existing)
		self.assertEqual(self.fill(spec_rows=[_customer("C-1")], doctype="COA AMB2", has_field=False), [])

	def test_a_new_coa_amb_is_filled_in_before_insert_after_the_specification_was_read(self):
		calls = []
		d = cert("COA AMB", "MIX-1", linked_tds="TDS-1", naming_series="COA-.YY.-.####")
		d.sync_from_tds = lambda: calls.append("sync")
		with mock.patch.object(rules, "fill_customers", lambda doc: calls.append("customers")):
			d.before_insert()
		self.assertEqual(calls, ["sync", "customers"])


class Lot:
	def __init__(self, **kw):
		self.name = "LOTE-1"
		self._d = dict(tds_link=None, item_to_manufacture=None, work_order_ref="WO-1")
		self._d.update(kw)
		self.check_permission = mock.Mock()

	def get(self, key):
		return self._d.get(key)


class TestMakeCertificateForLot(unittest.TestCase):
	def make(self, lot, specs=None, table=TABLE):
		made = types.SimpleNamespace(insert=mock.Mock(), name="NEW-1", doctype=None)

		def new_doc(doctype):
			made.doctype = doctype
			return made

		with site(db=Db(specs=specs or {}), table=table, docs={("Batch AMB", "LOTE-1"): lot}) as fake:
			fake.new_doc = new_doc
			try:
				return api.make_certificate_for_lot("LOTE-1"), made
			except frappe.ValidationError as e:
				return str(e), made

	def test_a_lot_of_each_class_gets_the_certificate_of_its_type_with_everything_filled(self):
		for item, doctype in (("MIX-1", "COA AMB"), ("POWDER-1", "COA AMB2")):
			lot = Lot(tds_link="TDS-1")
			out, made = self.make(lot, specs={"TDS-1": {"product_item": item}})
			self.assertEqual(out, {"doctype": doctype, "name": "NEW-1"})
			self.assertEqual(
				(made.batch_reference, made.work_order, made.product_item, made.linked_tds),
				("LOTE-1", "WO-1", item, "TDS-1"),
			)
			made.insert.assert_called_once_with()  # the caller's own right to create is checked by the insert
			lot.check_permission.assert_called_once_with("read")

	def test_without_a_specification_the_lots_item_is_the_product(self):
		out, made = self.make(Lot(item_to_manufacture="POWDER-1"))
		self.assertEqual((out["doctype"], made.product_item, made.linked_tds), ("COA AMB2", "POWDER-1", None))

	def test_a_lot_with_no_specification_and_no_real_item_is_refused(self):
		for lot in (Lot(), Lot(item_to_manufacture="NOT-AN-ITEM")):
			out, made = self.make(lot)
			self.assertIn("names no specification and no item", out)
			made.insert.assert_not_called()

	def test_an_unclassed_product_is_refused_with_its_own_message_and_nothing_is_inserted(self):
		for table, item in ((TABLE, "PACK-1"), ({}, "MIX-1")):
			out, made = self.make(Lot(item_to_manufacture=item), table=table)
			self.assertIn("is not classed", out)
			made.insert.assert_not_called()

	def test_it_is_whitelisted_under_the_name_the_other_apps_call(self):
		self.assertIn(api.make_certificate_for_lot, frappe.whitelisted)
		self.assertEqual(
			api.__name__ + "." + api.make_certificate_for_lot.__name__,
			"amb_w_tds.api.certificate.make_certificate_for_lot",
		)


class TestFormAndFixture(unittest.TestCase):
	def test_work_order_is_a_link_on_both_certificates(self):
		for doctype in ("coa_amb", "coa_amb2"):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", doctype, doctype + ".json"), encoding="utf-8"
			) as f:
				d = json.load(f)
			(field,) = [x for x in d["fields"] if x["fieldname"] == "work_order"]
			self.assertEqual((field["fieldtype"], field["options"]), ("Link", "Work Order"))
			self.assertEqual(field["read_only_depends_on"], "eval:doc.work_order")
			self.assertEqual(d["field_order"][d["field_order"].index("batch_reference") + 1], "work_order")

	def test_the_lot_change_handler_sets_no_missing_field_and_keeps_the_product(self):
		for doctype in ("coa_amb", "coa_amb2"):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", doctype, doctype + ".js"), encoding="utf-8"
			) as f:
				text = f.read()
			start = text.index("    batch_reference: function(frm) {")
			block = text[start : text.index("\n    },\n", start)]
			for gone in ("set_value('production_date'", "set_value('batch_quantity'", "frappe.client.get"):
				self.assertNotIn(gone, block, (doctype, gone))
			self.assertEqual(block.count("set_value('product_item'"), 1)
			self.assertIn("r.item_to_manufacture && !frm.doc.product_item", block)
			self.assertIn("set_value('work_order', r.work_order_ref)", block)

	def test_the_client_script_no_longer_empties_the_series(self):
		with open(os.path.join(PKG, "fixtures", "client_script.json"), encoding="utf-8") as f:
			(script,) = [d for d in json.load(f) if d["name"] == "custom_naming_series"]
		self.assertEqual(script["enabled"], 0)
		self.assertNotIn("set_value", script["script"])
		self.assertGreater(
			script["modified"], "2025-08-30 18:06:56.227479"
		)  # a later stamp, so the import takes it


if __name__ == "__main__":
	unittest.main()
