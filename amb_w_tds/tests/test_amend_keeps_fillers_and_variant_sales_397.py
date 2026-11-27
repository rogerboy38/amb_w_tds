"""TASKS-397 (tds), DB-free: decisions 349 and 350.

- 349: a certificate made by Amend (`amended_from` set; COA AMB and COA AMB2) starts with its original's stored
  `fillers_since_draft`, with the original's stored `filled_by` added, read from the database (not from the form);
  then its maker is added if the insert fills it. Whoever filled the original stays barred from approving the
  amendment. An original that cannot be read refuses the save. A Duplicate (no `amended_from`) starts empty.
- 350: a new Item variant (`variant_of` set) takes its template's stored `is_sales_item` once, on insert only
  (`amb_w_tds.item_variant_sales`, the Item's `before_insert` doc_event), whether or not the field is on Item
  Variant Settings' copy list. ERPNext 16.17.0's own `create_variant` / `copy_attributes_to_variant` run here as
  shipped, with the framework calls they make stood in for.

A certificate save is run as the framework runs it before the write (`before_validate`, then `validate`), on
documents built without a database, as in `test_filler_list_and_share_391`."""

import json
import os
import unittest
from contextlib import contextmanager
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds import hooks
from amb_w_tds import item_variant_sales as ivs
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2
from amb_w_tds.tests.test_certificate_rules_b1 import cert, row, stored
from amb_w_tds.tests.test_filler_list_and_share_391 import (
	IN_THE_LIST,
	LAST_FILLER,
	change_and_set_back,
	save,
	signed_by,
)
from amb_w_tds.tests.test_identity_share_freeze_387 import as_sent, run, site387

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOTH = ("COA AMB", "COA AMB2")
A, B, C, D = "first.a", "second.b", "third.c", "amender.d"
FIELDS = ["filled_by", rules.FILLERS_FIELD]
NOT_READ = "which cannot be read, so it is not known who filled it"


@contextmanager
def originals_site(user, originals):
	"""The 387 site, plus the stored certificates an amendment may name (`originals`: name -> stored fields)."""
	with site387(user=user) as fake:
		plain = fake.db.get_value

		def get_value(doctype, name=None, fields=None, *a, **k):
			if doctype in rules.STATE_FIELD and fields == FIELDS and name in originals:
				return frappe._dict(originals[name])
			return plain(doctype, name, fields, *a, **k)

		fake.db.get_value = mock.Mock(side_effect=get_value)
		yield fake


def insert(doc, user, originals):
	"""The insert of a new certificate as `user` (`before_validate`, then `validate`). Returns (refusal, site)."""
	with originals_site(user, originals) as fake:
		try:
			with mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
				doc.before_validate()
			doc.validate()
		except frappe.ValidationError as e:
			return str(e), fake
	return None, fake


def amendment(doctype, **kw):
	"""What the form's Amend sends: a new draft naming its cancelled original, the rows copied (values filled), and
	whatever else the copy carried."""
	values = dict(amended_from="COA-0", rows=[row("r1", "5"), row("r2", "6")], batch_reference="LOT-1")
	values.update(kw)
	return cert(doctype, new=True, **values)


def stored_after_insert(doctype, d):
	"""The amendment as the database holds it after its insert."""
	s = stored(doctype, "Draft", [row("r1", "5"), row("r2", "6")], filled_by=d.filled_by, signed_by=None)
	s.update(batch_reference="LOT-1", amended_from=d.amended_from)
	s[rules.FILLERS_FIELD] = d.fillers_since_draft
	return s


def to_review_and_ask(doctype, s, approver, by=None):
	"""The amendment is sent for review by `by`, `approver` signs it and approves. Returns the refusal, or None."""
	_d, s = save(doctype, s, by or approver, state="Pending Supervisor")
	s = signed_by(doctype, s, approver)
	return run(as_sent(doctype, s, state="Approved"), user=approver)


class TestAnAmendKeepsTheFillerList(unittest.TestCase):
	"""Decision 349."""

	def test_amend_then_a_filler_of_the_original_tries_to_approve_refused(self):
		"""The original was filled by A then B (B last). B amends it (the copied rows make B its filler). A, who is
		not the amendment's last filler, signs and approves: refused, because the list kept A."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = amendment(doctype)
				refusal, _site = insert(d, B, {"COA-0": {"filled_by": B, rules.FILLERS_FIELD: f"{A}\n{B}"}})
				self.assertIsNone(refusal)
				self.assertEqual((d.filled_by, d.fillers_since_draft), (B, f"{A}\n{B}"))
				refusal = to_review_and_ask(doctype, stored_after_insert(doctype, d), A, by=B)
				self.assertIn(IN_THE_LIST, refusal or "")
				self.assertNotIn(LAST_FILLER, refusal)

	def test_amend_by_someone_who_never_filled_then_the_original_filler_approves_refused(self):
		"""The original was filled by A alone. D, who never filled it, amends it; A approves: refused."""
		for doctype in BOTH:
			for original in (
				{"filled_by": A, rules.FILLERS_FIELD: A},
				{"filled_by": A, rules.FILLERS_FIELD: None},
			):
				with self.subTest(doctype=doctype, original=original):
					d = amendment(doctype)
					self.assertIsNone(insert(d, D, {"COA-0": original})[0])
					self.assertEqual((d.filled_by, d.fillers_since_draft), (D, f"{A}\n{D}"))
					refusal = to_review_and_ask(doctype, stored_after_insert(doctype, d), A, by=D)
					self.assertIn(IN_THE_LIST, refusal or "")

	def test_a_third_person_approves_the_amendment(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = amendment(doctype)
				insert(d, D, {"COA-0": {"filled_by": B, rules.FILLERS_FIELD: f"{A}\n{B}"}})
				s = stored_after_insert(doctype, d)
				self.assertIsNone(to_review_and_ask(doctype, s, C, by=D))
				for user in (A, B):
					self.assertIn(IN_THE_LIST, to_review_and_ask(doctype, s, user, by=C) or "", user)
				self.assertIn(LAST_FILLER, to_review_and_ask(doctype, s, D, by=C) or "")

	def test_the_list_keeps_growing_after_the_amend(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = amendment(doctype)
				insert(d, D, {"COA-0": {"filled_by": A, rules.FILLERS_FIELD: A}})
				s = change_and_set_back(doctype, stored_after_insert(doctype, d), B)
				self.assertEqual((s.filled_by, s[rules.FILLERS_FIELD]), (B, f"{A}\n{D}\n{B}"))

	def test_the_original_is_read_from_the_database_not_from_the_form(self):
		"""The form's Amend may carry a copied `fillers_since_draft` / `filled_by` (or a caller may type them): both
		are replaced by what the original stores. The read names this doctype, the original and the two fields."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = amendment(doctype, filled_by=C, **{rules.FILLERS_FIELD: f"{C}\nsomeone"})
				refusal, fake = insert(d, D, {"COA-0": {"filled_by": A, rules.FILLERS_FIELD: B}})
				self.assertIsNone(refusal)
				self.assertEqual((d.filled_by, d.fillers_since_draft), (D, f"{B}\n{A}\n{D}"))
				fake.db.get_value.assert_any_call(doctype, "COA-0", FIELDS, as_dict=True)

	def test_the_maker_is_added_only_if_the_insert_fills(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = cert(doctype, new=True, amended_from="COA-0", rows=[])
				self.assertIsNone(insert(d, D, {"COA-0": {"filled_by": A, rules.FILLERS_FIELD: A}})[0])
				self.assertEqual((d.filled_by, d.fillers_since_draft), (None, A))

	def test_an_original_that_cannot_be_read_refuses_the_save(self):
		for doctype in BOTH:
			for user in (D, "Administrator"):
				with self.subTest(doctype=doctype, user=user):
					d = amendment(doctype, amended_from="COA-404")
					refusal, _site = insert(d, user, {})
					self.assertEqual(
						refusal,
						f"{doctype} COA-1 is an amendment of COA-404, {NOT_READ}. "
						"Amend the certificate again from its cancelled original.",
					)

	def test_a_duplicate_starts_empty_and_reads_no_original(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = cert(doctype, new=True, filled_by=A, **{rules.FILLERS_FIELD: f"{A}\n{B}"})
				refusal, fake = insert(d, C, {"COA-0": {"filled_by": A, rules.FILLERS_FIELD: A}})
				self.assertIsNone(refusal)
				self.assertEqual((d.filled_by, d.fillers_since_draft), (C, C))
				self.assertNotIn(
					FIELDS, [c.args[2] for c in fake.db.get_value.call_args_list if len(c.args) > 2]
				)

	def test_a_stored_amendment_is_not_read_again(self):
		"""Once inserted, the amendment's list is its own stored one: a later save reads no original (so a change of
		`amended_from` afterwards changes nothing), and the original's list is not added again."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				s = stored(doctype, "Draft", [row("r1", "5")], filled_by=D, amended_from="COA-0")
				s[rules.FILLERS_FIELD] = f"{A}\n{D}"
				d = as_sent(doctype, s, amended_from="COA-7")
				with originals_site(D, {"COA-7": {"filled_by": B, rules.FILLERS_FIELD: B}}) as fake:
					with mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
						d.before_validate()
					d.validate()
				self.assertEqual(d.fillers_since_draft, f"{A}\n{D}")
				self.assertNotIn(
					FIELDS, [c.args[2] for c in fake.db.get_value.call_args_list if len(c.args) > 2]
				)

	def test_an_unrelated_amended_from_starts_from_that_certificates_fillers(self):
		"""TASKS-397 review, finding 2: the framework checks only that `amended_from` names a cancelled certificate,
		not that it is the one being amended. An insert naming an unrelated cancelled certificate starts from ITS
		fillers: no weaker than a Duplicate (which starts from no one), and each name it brings may not approve."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				d = amendment(doctype)
				insert(d, D, {"COA-0": {"filled_by": B, rules.FILLERS_FIELD: B}})
				self.assertEqual(rules.fillers_of(d.fillers_since_draft), [B, D])
				s = stored_after_insert(doctype, d)
				self.assertIn(IN_THE_LIST, to_review_and_ask(doctype, s, B, by=C) or "")
				self.assertIn(LAST_FILLER, to_review_and_ask(doctype, s, D, by=C) or "")
				self.assertIsNone(to_review_and_ask(doctype, s, C, by=D))
		# the list comes from the certificate named, read from the database, and nothing else
		for doctype in BOTH:
			with self.subTest(doctype=doctype, named="an empty one"):
				d = amendment(doctype)
				insert(d, D, {"COA-0": {"filled_by": None, rules.FILLERS_FIELD: None}})
				self.assertEqual(rules.fillers_of(d.fillers_since_draft), [D])  # as a Duplicate made by D

	def test_amended_from_is_the_frameworks_read_only_no_copy_field_on_both(self):
		for folder, doctype in (("coa_amb", "COA AMB"), ("coa_amb2", "COA AMB2")):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", folder, folder + ".json"), encoding="utf-8"
			) as f:
				meta = json.load(f)
			df = {d["fieldname"]: d for d in meta["fields"]}["amended_from"]
			self.assertEqual(meta.get("is_submittable"), 1, folder)
			self.assertEqual(
				(df["fieldtype"], df["options"], df.get("read_only"), df.get("no_copy")),
				("Link", doctype, 1, 1),
				folder,
			)


class FakeItem(frappe._dict):
	"""An Item as ERPNext's variant code handles it: fields read with `get`, written with `set` / `append`."""

	def set(self, key, value):
		self[key] = [frappe._dict(v) for v in value] if isinstance(value, list) else value

	def append(self, key, value):
		self.setdefault(key, []).append(value)


FIELD_META = [
	frappe._dict(fieldname="item_code", fieldtype="Data", reqd=1),
	frappe._dict(fieldname="item_name", fieldtype="Data", reqd=0),
	frappe._dict(fieldname="item_group", fieldtype="Link", reqd=1),
	frappe._dict(fieldname="stock_uom", fieldtype="Link", reqd=1),
	frappe._dict(fieldname="description", fieldtype="Text Editor", reqd=0),
	frappe._dict(fieldname="variant_of", fieldtype="Link", reqd=0),
	frappe._dict(fieldname="variant_based_on", fieldtype="Select", reqd=0),
	frappe._dict(fieldname="is_sales_item", fieldtype="Check", reqd=0),
	frappe._dict(fieldname="attributes", fieldtype="Table", reqd=0),
]
COPY_LIST_WITH = ["item_group", "stock_uom", "description", "is_sales_item"]
COPY_LIST_WITHOUT = ["item_group", "stock_uom", "description"]


def template(allow_sales):
	return FakeItem(
		name="TPL-1",
		item_code="TPL-1",
		item_name="Template",
		item_group="Products",
		stock_uom="Kg",
		description="Template",
		variant_of=None,
		has_variants=1,
		variant_based_on="Item Attribute",
		is_sales_item=allow_sales,
		attributes=[frappe._dict(attribute="Size", attribute_value=None)],
		meta=frappe._dict(fields=FIELD_META),
	)


def new_item(**kw):
	"""`frappe.new_doc("Item")`: the DocType's defaults, "Allow Sales" on."""
	item = FakeItem(item_code=None, variant_of=None, is_sales_item=1, attributes=[], description=None)
	item.update(kw)
	return item


@contextmanager
def item_site(stored_items, copy_list):
	"""The framework calls ERPNext's variant code and the hook make: the stored Items (name -> `is_sales_item`) and
	Item Variant Settings' copy list (the `Variant Field` rows)."""
	from erpnext.controllers import item_variant as iv

	db = mock.Mock()
	db.get_value = mock.Mock(
		side_effect=lambda dt, name, field, *a, **k: stored_items.get(name) if dt == "Item" else None
	)
	db.sql = mock.Mock(return_value=[])
	with (
		mock.patch.object(frappe, "db", db),
		mock.patch.object(ivs.frappe, "db", db),
		mock.patch.object(
			frappe, "get_all", lambda dt, fields=None, **k: [frappe._dict(field_name=f) for f in copy_list]
		),
		mock.patch.object(iv, "_", lambda s: s),
	):
		yield iv, db


def create_and_insert(tpl, copy_list):
	"""ERPNext's "Create variant": `create_variant` builds it in memory (the copy), then the insert runs
	`before_insert` (the doc_event under test), as `Document.insert` does after the defaults."""
	with item_site({tpl.name: tpl.is_sales_item}, copy_list) as (iv, _db):
		with (
			mock.patch.object(frappe, "get_doc", lambda dt, name: tpl),
			mock.patch.object(frappe, "new_doc", lambda dt: new_item()),
		):
			variant = iv.create_variant(tpl.name, {"Size": "S"})
		variant.item_code = "TPL-1-S"
		copied = variant.is_sales_item
		ivs.copy_allow_sales_from_template(variant, "before_insert")
	return copied, variant


class TestANewVariantTakesItsTemplatesAllowSalesOnce(unittest.TestCase):
	"""Decision 350."""

	def test_create_variant_of_a_template_with_the_check_off_starts_off_on_or_off_the_copy_list(self):
		for copy_list, erpnext_copied in ((COPY_LIST_WITHOUT, 1), (COPY_LIST_WITH, 0)):
			with self.subTest(on_the_copy_list=copy_list is COPY_LIST_WITH):
				copied, variant = create_and_insert(template(0), copy_list)
				self.assertEqual(copied, erpnext_copied)  # off the list ERPNext leaves the default (on)
				self.assertEqual((variant.variant_of, variant.is_sales_item), ("TPL-1", 0))

	def test_create_variant_of_a_template_with_the_check_on_starts_on(self):
		for copy_list in (COPY_LIST_WITHOUT, COPY_LIST_WITH):
			with self.subTest(on_the_copy_list=copy_list is COPY_LIST_WITH):
				_copied, variant = create_and_insert(template(1), copy_list)
				self.assertEqual(variant.is_sales_item, 1)

	def test_a_variant_made_by_hand_takes_the_stored_value_not_the_one_sent(self):
		"""A new Item with `variant_of` typed in gets no copy from ERPNext; a value sent with it is replaced."""
		for stored_value, sent in ((0, 1), (1, 0), (0, 0)):
			with (
				self.subTest(stored=stored_value, sent=sent),
				item_site({"TPL-1": stored_value}, COPY_LIST_WITHOUT),
			):
				variant = new_item(item_code="TPL-1-M", variant_of="TPL-1", is_sales_item=sent)
				ivs.copy_allow_sales_from_template(variant, "before_insert")
				self.assertEqual(variant.is_sales_item, stored_value)

	def test_a_template_change_does_not_touch_an_existing_variant_off_the_copy_list(self):
		"""The template's check is turned off after its variant exists. ERPNext's `update_variants` (the template's
		`on_update`) copies the template onto each stored variant and saves it: with the field off the copy list the
		variant keeps its own value, and that save is no insert, so the hook (wired on `before_insert` only) does not
		run. A save of the template itself carries no `variant_of`, so the hook changes nothing on it either."""
		_copied, variant = create_and_insert(template(1), COPY_LIST_WITHOUT)
		self.assertEqual(variant.is_sales_item, 1)
		changed = template(0)
		with item_site({"TPL-1": 0}, COPY_LIST_WITHOUT) as (iv, db):
			iv.copy_attributes_to_variant(
				changed, variant
			)  # what `update_variants` does before `variant.save()`
			self.assertEqual(variant.is_sales_item, 1)
			ivs.copy_allow_sales_from_template(changed, "before_insert")
			self.assertEqual(changed.is_sales_item, 0)
			db.get_value.assert_not_called()
		self.assertEqual(set(hooks.doc_events["Item"]), {"before_insert"})

	def test_a_non_variant_item_keeps_its_default(self):
		for value in (1, 0):
			with self.subTest(value=value), item_site({"TPL-1": 0}, COPY_LIST_WITHOUT) as (_iv, db):
				item = new_item(item_code="PLAIN-1", is_sales_item=value)
				ivs.copy_allow_sales_from_template(item, "before_insert")
				self.assertEqual(item.is_sales_item, value)
				db.get_value.assert_not_called()

	def test_a_template_that_cannot_be_read_changes_nothing(self):
		with item_site({}, COPY_LIST_WITHOUT):
			variant = new_item(item_code="X-1", variant_of="MISSING", is_sales_item=1)
			ivs.copy_allow_sales_from_template(variant, "before_insert")
			self.assertEqual(variant.is_sales_item, 1)

	def test_the_template_is_read_from_the_database(self):
		with item_site({"TPL-1": 0}, COPY_LIST_WITHOUT) as (_iv, db):
			ivs.copy_allow_sales_from_template(new_item(variant_of="TPL-1"), "before_insert")
			db.get_value.assert_called_once_with("Item", "TPL-1", "is_sales_item")

	def test_the_hook_is_wired_on_item_before_insert_only(self):
		path = "amb_w_tds.item_variant_sales.copy_allow_sales_from_template"
		self.assertEqual(hooks.doc_events["Item"], {"before_insert": path})
		module, name = path.rsplit(".", 1)
		self.assertIs(getattr(__import__(module, fromlist=[name]), name), ivs.copy_allow_sales_from_template)
		wired = [
			(dt, ev) for dt, events in hooks.doc_events.items() for ev, fns in events.items() if path in fns
		]
		self.assertEqual(wired, [("Item", "before_insert")])

	def test_item_variant_settings_is_not_changed(self):
		"""Decision 347 is a settings step done later: no code and no fixture of this app writes the copy list."""
		for root, _dirs, files in os.walk(PKG):
			if os.sep + "tests" in root:
				continue
			for f in files:
				if f.endswith((".py", ".json")):
					with open(os.path.join(root, f), encoding="utf-8", errors="ignore") as fh:
						text = fh.read()
					self.assertNotIn('"Variant Field"', text, f)
					self.assertNotIn("'Variant Field'", text, f)


if __name__ == "__main__":
	unittest.main()


class TestNoDuplicateOnTheCertificateForms(unittest.TestCase):
	"""TASKS-398, decisions 352 and 354."""

	def meta(self, folder):
		with open(os.path.join(PKG, "amb_w_tds", "doctype", folder, folder + ".json"), encoding="utf-8") as f:
			return json.load(f)

	def test_both_certificates_hide_the_forms_duplicate_and_keep_amend(self):
		for folder in ("coa_amb", "coa_amb2"):
			with self.subTest(folder=folder):
				meta = self.meta(folder)
				self.assertEqual(
					meta.get("allow_copy"), 1
				)  # Frappe's toolbar shows Duplicate only when it is 0
				self.assertEqual(
					meta.get("is_submittable"), 1
				)  # Amend is the cancelled document's own action
				amended_from = {d["fieldname"]: d for d in meta["fields"]}["amended_from"]
				self.assertEqual((amended_from["fieldtype"], amended_from.get("no_copy")), ("Link", 1))

	def test_the_filler_description_says_what_an_amendment_and_a_duplicate_start_with(self):
		for folder in ("coa_amb", "coa_amb2"):
			with self.subTest(folder=folder):
				field = {d["fieldname"]: d for d in self.meta(folder)["fields"]}["fillers_since_draft"]
				text = field.get("description") or ""
				self.assertIn("an amendment starts from its original's stored list and filler", text)
				self.assertIn("a duplicate starts empty", text)
				self.assertNotIn("an amendment starts its own", text)
