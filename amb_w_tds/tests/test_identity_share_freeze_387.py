"""TASKS-387 (tds half), DB-free: decisions 321, 322 and 323 on both certificates.

- 321: the lot, product and specification are refused in Pending Supervisor (the way back is "Return for correction",
  Pending Supervisor -> Draft, in both workflow fixtures); in Draft / Validated a change of them names the changer as
  `filled_by`, and so does a change of COA AMB's customers list in every editable state; COA AMB's signature names its
  signer in `signed_by`, and only that user may approve.
- 322: the share of a COA AMB (stored Approved, docstatus 0 -> 1) changes nothing but its state, and keeps the stored
  Work Order; no save at docstatus 0 goes into a state its workflow gives docstatus 1.
- 323: the Batches a certificate's approval reads are those of its lot record and of every record below it.

The paths are the user's: a plain save (`frappe.client.save` / `submit`: the document as the caller sends it, no
reload), `frappe.client.set_value` (the stored document with the values set on it, then saved) and the form's workflow
action (`apply_workflow`: the stored document with only the state set). What a save runs before the write is run here
as the framework runs it: `before_validate`, then `validate`. The workflow states are read from the fixture."""

import copy
import json
import os
import types
import unittest
from contextlib import contextmanager
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.doctype.coa_amb import coa_amb as amb
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2
from amb_w_tds.tests.test_certificate_rules_b1 import CLASSES, TODAY, cert, customers, row, site, stored

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOTH = ("COA AMB", "COA AMB2")
WORKFLOW_OF = {"COA AMB": "submit_and_start_workflow_1", "COA AMB2": "submit_and_start_workflow"}
FILLER, APPROVER, THIRD = "filler.b", "approver.c", "third.d"


def _fixture(name):
	with open(os.path.join(PKG, "fixtures", name), encoding="utf8") as f:
		return json.load(f)


def _workflows():
	return {w["name"]: w for w in _fixture("workflow.json")}


@contextmanager
def site387(user=APPROVER, tds_product=None, below=None, batches_of=None, rejected=(), lots=None):
	"""The B1 stand-in site, plus: the active workflow of each certificate (from the fixture), the product of a
	specification, the records below a lot (`below`), the Batches of each lot record (`batches_of`) and the lot
	records themselves (`lots`: name -> Work Order). Without `batches_of`, the lot has one stock Batch (TASKS-390,
	decision 335: an approval of a certificate whose lot has none is refused)."""
	workflows = _workflows()
	with site(
		user=user, below=below, rejected=rejected, batches=("B-1",) if batches_of is None else ()
	) as fake:

		def get_value(doctype, name=None, fields=None, *a, **k):
			if doctype == "Workflow":
				return WORKFLOW_OF.get(name["document_type"])
			if doctype == rules.SPECIFICATION_DOCTYPE:
				return tds_product
			if doctype == rules.LOT_DOCTYPE and lots and name in lots:
				return frappe._dict(work_order_ref=lots[name], item_to_manufacture=None)
			return None

		fake.db.get_value = mock.Mock(side_effect=get_value)
		fake.get_cached_doc = lambda doctype, name: frappe._dict(
			states=[frappe._dict(s) for s in workflows[name]["states"]]
		)
		fake.msgprint = mock.Mock()
		if batches_of is not None:
			plain = fake.get_all

			def get_all(doctype, filters=None, pluck=None, **kw):
				if doctype == "Batch":
					fake.asked.append((doctype, filters))
					return [b for lot in filters["custom_batch_amb"][1] for b in batches_of.get(lot, ())]
				return plain(doctype, filters=filters, pluck=pluck, **kw)

			fake.get_all = get_all
		yield fake


def run(doc, **kw):
	"""One save of `doc` as sent: `before_validate`, then `validate`. Returns the refusal, or None."""
	with site387(**kw):
		try:
			with mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
				doc.before_validate()
			doc.validate()
		except frappe.ValidationError as e:
			return str(e)
	return None


def as_sent(doctype, before, state=None, docstatus=None, **values):
	"""The stored document as a caller would send it back: every stored field, its rows copied, `values` set on it.
	With only `state` set it is the form's workflow action (`apply_workflow` reloads, then sets the state); with
	`values` it is `frappe.client.set_value` (the stored document, the values set, saved) or a plain save."""
	d = cert(doctype, before=before)
	for k, v in before.items():
		d.__dict__[k] = copy.deepcopy(v)
	if state is not None:
		d.__dict__[rules.STATE_FIELD[doctype]] = state
	if docstatus is not None:
		d.__dict__["docstatus"] = docstatus
	d.__dict__.update(values)
	return d


def in_review(doctype="COA AMB", filler=FILLER, **kw):
	"""A certificate in Pending Supervisor, filled by `filler`, signed by the approver."""
	before = stored(doctype, "Pending Supervisor", [row("r1", "5"), row("r2", "6")], filled_by=filler)
	before.update(signed_by=APPROVER, batch_reference="LOT-1")
	before.update(kw)
	return before


class TestIdentityLockedInPendingSupervisor(unittest.TestCase):
	"""Decision 321: lot, product, specification refused in Pending Supervisor, on every path, for every user."""

	NEW = {"batch_reference": "LOT-2", "product_item": "ITEM-2", "linked_tds": "TDS-2"}

	def test_the_filler_moving_the_lot_in_pending_supervisor_is_refused_with_the_way_back(self):
		for doctype in BOTH:
			refusal = run(as_sent(doctype, in_review(doctype), batch_reference="LOT-2"), user=FILLER)
			self.assertIn("is Pending Supervisor: its batch_reference cannot be changed", refusal or "")
			self.assertIn('Use "Return for correction" to take it back to Draft', refusal)

	def test_each_identity_field_on_each_path_for_every_user(self):
		for doctype in BOTH:
			for field, value in self.NEW.items():
				for user in (FILLER, APPROVER, THIRD, "Administrator"):
					for state in (
						"Pending Supervisor",
						"Approved",
						"Draft",
					):  # plain save, set_value, with a move
						with self.subTest(doctype=doctype, field=field, user=user, state=state):
							d = as_sent(doctype, in_review(doctype), state=state, **{field: value})
							refusal = run(d, user=user)
							self.assertIn(f"its {field} cannot be changed", refusal or "")
							self.assertIsNone(d._lot_move if hasattr(d, "_lot_move") else None)

	def test_a_plain_save_with_state_approved_and_a_new_lot_is_refused_and_nothing_is_released(self):
		d = as_sent("COA AMB", in_review(), state="Approved", batch_reference="LOT-2")
		refusal = run(d, user=APPROVER)
		self.assertIn("Return for correction", refusal or "")
		self.assertIsNone(getattr(d, "_lot_move", None))
		self.assertIsNone(d.get("approved_by"))

	def test_the_same_identity_sent_back_is_no_change(self):
		for doctype in BOTH:
			self.assertIsNone(run(as_sent(doctype, in_review(doctype)), user=THIRD), doctype)

	def test_the_product_the_framework_fetches_from_the_unchanged_specification_is_not_a_change(self):
		"""`product_item` is `fetch_from: linked_tds.product_item`: on every draft save the framework writes it from
		the specification before any rule runs. That write is the server's, not the user's."""
		before = in_review(product_item="ITEM-OLD")
		d = as_sent("COA AMB", before, product_item="ITEM-SPEC")
		self.assertIsNone(run(d, user=THIRD, tds_product="ITEM-SPEC"))
		self.assertEqual(d.filled_by, FILLER)  # and it names nobody as the filler
		# a product that is not the specification's is the user's change
		d = as_sent("COA AMB", before, product_item="ITEM-OTHER")
		self.assertIn("its product_item cannot be changed", run(d, user=THIRD, tds_product="ITEM-SPEC") or "")
		# and so is any product with another specification sent with it
		d = as_sent("COA AMB", before, product_item="ITEM-SPEC", linked_tds="TDS-2")
		self.assertIn(
			"its product_item, linked_tds cannot be changed",
			run(d, user=THIRD, tds_product="ITEM-SPEC") or "",
		)

	def test_it_is_refused_in_before_validate_so_a_save_that_skips_validate_meets_it(self):
		d = as_sent("COA AMB", in_review(), batch_reference="LOT-2")
		d.validate = mock.Mock(side_effect=AssertionError("validate is not reached"))
		with site387(), mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
			with self.assertRaises(frappe.ValidationError):
				d.before_validate()

	def test_the_rule_reads_no_role_and_no_user(self):
		import inspect

		for fn in (rules.refuse_identity_change_in_review, rules.identity_changes):
			src = inspect.getsource(fn)
			for word in ("Administrator", "get_roles", "session", "has_permission", "ignore_permissions"):
				self.assertNotIn(word, src, fn.__name__)


class TestReturnForCorrection(unittest.TestCase):
	"""Decision 321: Pending Supervisor -> Draft keeps everything and writes no lot; then the lot is corrected in
	Draft by B, who becomes the filler; C approves; B cannot."""

	def test_the_return_keeps_every_row_and_result_and_writes_no_lot(self):
		for doctype in BOTH:
			for user in (FILLER, APPROVER):
				d = as_sent(doctype, in_review(doctype), state="Draft")  # the form's action: the stored doc
				self.assertIsNone(run(d, user=user), (doctype, user))
				self.assertEqual(
					[(r.name, r.result) for r in d.coa_quality_test_parameter], [("r1", "5"), ("r2", "6")]
				)
				self.assertEqual((d.filled_by, d.approved_by, d.approval_date), (FILLER, None, None))
				self.assertIsNone(d._lot_move)  # nothing was released, nothing is taken back
				with mock.patch.object(rules, "_spc", mock.Mock(side_effect=AssertionError("no lot call"))):
					rules.write_lot(d)

	def test_return_correct_the_lot_then_c_approves_and_b_cannot(self):
		doctype = "COA AMB"
		returned = stored(
			doctype,
			"Draft",
			[row("r1", "5"), row("r2", "6")],
			filled_by=FILLER,
			signed_by=APPROVER,
			batch_reference="LOT-1",
		)
		# B corrects the lot in Draft: B is the filler
		moved = as_sent(doctype, returned, batch_reference="LOT-2")
		self.assertIsNone(run(moved, user=FILLER))
		self.assertEqual(moved.filled_by, FILLER)
		# a third person who corrects the lot is the filler from then on
		by_third = as_sent(doctype, returned, batch_reference="LOT-2")
		self.assertIsNone(run(by_third, user=THIRD))
		self.assertEqual(by_third.filled_by, THIRD)
		# Review and send for approval: nothing changes, the filler stays B
		reviewed = stored(
			doctype,
			"Pending Supervisor",
			[row("r1", "5"), row("r2", "6")],
			filled_by=FILLER,
			signed_by=APPROVER,
			batch_reference="LOT-2",
		)
		# B cannot approve; C (who signed) can, and the lot named now is the one released
		self.assertIn(
			"another person must approve it",
			run(as_sent(doctype, reviewed, state="Approved"), user=FILLER) or "",
		)
		approval = as_sent(doctype, reviewed, state="Approved")
		self.assertIsNone(run(approval, user=APPROVER))
		self.assertEqual(approval._lot_move, ("approved", "LOT-2"))
		self.assertEqual(approval.approved_by, APPROVER)

	def test_an_identity_change_in_draft_or_validated_is_filling(self):
		for doctype in BOTH:
			for state in ("Draft", "Validated"):
				for field, value in TestIdentityLockedInPendingSupervisor.NEW.items():
					with self.subTest(doctype=doctype, state=state, field=field):
						before = stored(doctype, state, [row("r1", "5")], filled_by=FILLER)
						d = as_sent(doctype, before, **{field: value})
						self.assertIsNone(run(d, user=THIRD, tds_product=None))
						self.assertEqual(d.filled_by, THIRD)

	def test_an_approved_certificate_is_still_released_and_withdrawn_as_before(self):
		"""Item 1.4: past Validated the lot is written exactly as before; only the fields are locked."""
		for doctype in BOTH:
			approval = as_sent(doctype, in_review(doctype), state="Approved")
			self.assertIsNone(run(approval, user=APPROVER), doctype)
			self.assertEqual(approval._lot_move, ("approved", "LOT-1"))
			approved = stored(
				doctype,
				"Approved",
				[row("r1", "5"), row("r2", "6")],
				filled_by=FILLER,
				approved_by=APPROVER,
				approval_date=TODAY,
				signed_by=APPROVER,
				batch_reference="LOT-1",
			)
			reject = as_sent(doctype, approved, state="Draft")
			self.assertIsNone(run(reject, user=APPROVER), doctype)
			self.assertEqual(reject._lot_move, ("withdrawn", "LOT-1"))


class TestTheReturnTransitionInTheFixtures(unittest.TestCase):
	def test_both_workflows_have_it_for_quality_user_and_quality_manager(self):
		for name in WORKFLOW_OF.values():
			w = _workflows()[name]
			rows = sorted(
				(t["state"], t["next_state"], t["allowed"], int(t["allow_self_approval"]), t.get("condition"))
				for t in w["transitions"]
				if t["action"] == "Return for correction"
			)
			self.assertEqual(
				rows,
				[
					("Pending Supervisor", "Draft", "Quality Manager", 1, None),
					("Pending Supervisor", "Draft", "Quality User", 1, None),
				],
				name,
			)

	def test_the_action_master_row_and_the_hooks_name_list_carry_it(self):
		self.assertIn("Return for correction", {a["name"] for a in _fixture("workflow_action_master.json")})
		import importlib

		hooks = importlib.import_module("amb_w_tds.hooks")
		masters = [
			f for f in hooks.fixtures if isinstance(f, dict) and f.get("doctype") == "Workflow Action Master"
		]
		self.assertIn("Return for correction", masters[0]["filters"][0][2])

	def test_what_frappe_does_with_the_owner_on_this_transition(self):
		"""`has_approval_access` (checked only in `apply_workflow`): with `allow_self_approval` 1 the owner of the
		certificate may return it; with 0 the owner could not (Administrator always may). 1 is set."""
		from frappe.model.workflow import has_approval_access

		doc = frappe._dict(owner=FILLER)
		self.assertTrue(has_approval_access(FILLER, doc, frappe._dict(allow_self_approval=1)))
		self.assertFalse(has_approval_access(FILLER, doc, frappe._dict(allow_self_approval=0)))
		self.assertTrue(has_approval_access(APPROVER, doc, frappe._dict(allow_self_approval=0)))


class TestCustomersListIsFilling(unittest.TestCase):
	"""Decision 321: a change of the customers list (COA AMB) names its changer as the filler, in Draft, Validated
	and Pending Supervisor; that person cannot approve."""

	def changed_lists(self):
		two = customers() + [frappe._dict(name="cust-2", customer="CUST-2")]
		other_field = [frappe._dict(name="cust-1", customer="CUST-1", custom_customer_part_number="P-9")]
		return {
			"a row added": two,
			"a row removed": [],
			"a field of a row changed": other_field,
			"a row replaced": [frappe._dict(name="cust-9", customer="CUST-1")],
		}

	def test_c_changes_the_customers_list_in_review_and_cannot_approve_and_another_can(self):
		for what, rows in self.changed_lists().items():
			with self.subTest(what):
				d = as_sent("COA AMB", in_review(), custom_coa_customers=rows)
				self.assertIsNone(run(d, user=APPROVER))
				self.assertEqual(d.filled_by, APPROVER)
				changed = in_review(filled_by=APPROVER, custom_coa_customers=rows or customers())
				refusal = run(as_sent("COA AMB", changed, state="Approved"), user=APPROVER)
				self.assertIn("another person must approve it", refusal or "")
				# another approver, who signed, can
				changed.update(signed_by=THIRD)
				self.assertIsNone(run(as_sent("COA AMB", changed, state="Approved"), user=THIRD))
		# in the very save that approves
		d = as_sent(
			"COA AMB", in_review(), state="Approved", custom_coa_customers=self.changed_lists()["a row added"]
		)
		self.assertIn("another person must approve it", run(d, user=APPROVER) or "")
		self.assertIsNone(getattr(d, "_lot_move", None))

	def test_in_draft_and_validated_too(self):
		for state in ("Draft", "Validated"):
			before = stored("COA AMB", state, [row("r1", "5")], filled_by=FILLER)
			d = as_sent("COA AMB", before, custom_coa_customers=[])
			self.assertIsNone(run(d, user=THIRD))
			self.assertEqual(d.filled_by, THIRD, state)

	def test_the_same_list_in_another_order_is_not_a_change(self):
		two = customers() + [frappe._dict(name="cust-2", customer="CUST-2")]
		before = in_review(custom_coa_customers=two)
		d = as_sent("COA AMB", before, custom_coa_customers=list(reversed(copy.deepcopy(two))))
		self.assertIsNone(run(d, user=THIRD))
		self.assertEqual(d.filled_by, FILLER)

	def test_a_customer_name_refetched_by_the_framework_is_not_a_change(self):
		"""Review finding 1: `Customer Item.custom_customer_name` is fetched from the Customer on every draft save,
		before any rule runs. A renamed Customer must not make the approver the filler."""
		before = in_review(
			filled_by=FILLER,
			signed_by=APPROVER,
			custom_coa_customers=[
				frappe._dict(name="cust-1", customer="CUST-1", custom_customer_name="Old name")
			],
		)
		sent = [frappe._dict(name="cust-1", customer="CUST-1", custom_customer_name="New name")]
		d = as_sent("COA AMB", before, state="Approved", custom_coa_customers=sent)
		self.assertIsNone(run(d, user=APPROVER))
		self.assertEqual(d.filled_by, FILLER)
		self.assertIn("custom_customer_name", rules._fetched_row_fields(None))
		# a field the user types is still a change
		typed = [frappe._dict(name="cust-1", customer="CUST-2", custom_customer_name="Old name")]
		d = as_sent("COA AMB", before, custom_coa_customers=typed)
		self.assertIsNone(run(d, user=APPROVER))
		self.assertEqual(d.filled_by, APPROVER)

	def row_hook(
		self, sent, stored_row, parent_state="Pending Supervisor", method="before_validate", new=False
	):
		r = types.SimpleNamespace(doctype="Customer Item", get=lambda k: sent.get(k), is_new=lambda: new)
		with site387(user=THIRD) as fake:

			def get_value(doctype, name, fields, as_dict=False):
				if doctype == "Customer Item":
					return frappe._dict(stored_row) if stored_row else None
				if doctype == "COA AMB" and fields == rules.FILLERS_FIELD:
					return None  # TASKS-390: no one is on the stored list before this row
				if doctype == "COA AMB":
					return frappe._dict(workflow_state_1=parent_state, docstatus=0)
				return None

			fake.db.get_value = get_value
			try:
				rules.note_customer_row(r, method)
			except frappe.ValidationError as e:
				return str(e)
		return [c.args for c in fake.db.set_value.call_args_list]

	def test_a_customers_row_saved_by_itself_is_filling_or_refused_when_approved(self):
		in_db = {
			"name": "cust-1",
			"parent": "COA-1",
			"parenttype": "COA AMB",
			"parentfield": "custom_coa_customers",
			"customer": "CUST-1",
		}
		changed = dict(in_db, customer="CUST-2")
		self.assertEqual(
			self.row_hook(changed, in_db),
			[("COA AMB", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD})],
		)
		self.assertEqual(self.row_hook(dict(in_db), in_db), [])  # unchanged: nothing
		self.assertEqual(
			self.row_hook(in_db, in_db, method="on_trash"),
			[("COA AMB", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD})],
		)
		self.assertEqual(
			self.row_hook(dict(in_db, name=None), None, new=True),
			[("COA AMB", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD})],
		)
		self.assertIn(
			"its customers list cannot be changed", self.row_hook(changed, in_db, parent_state="Approved")
		)
		# a row of an Item is not judged
		item_row = dict(in_db, parenttype="Item", parent="ITEM-1", parentfield="customer_items")
		self.assertEqual(self.row_hook(dict(item_row, customer="CUST-2"), item_row), [])

	def test_the_row_hook_is_registered(self):
		import importlib

		hooks = importlib.import_module("amb_w_tds.hooks")
		path = "amb_w_tds.certificate_rules.note_customer_row"
		self.assertEqual(hooks.doc_events["Customer Item"], {"before_validate": path, "on_trash": path})


class TestTheApproverSigns(unittest.TestCase):
	"""Decision 321: `signed_by` is who last drew the signature; the approver must be that user; signing is not
	filling."""

	def test_drawing_or_changing_the_signature_names_the_signer_and_not_the_filler(self):
		for state in ("Draft", "Validated", "Pending Supervisor"):
			before = in_review(signed_by=None)
			before[rules.STATE_FIELD["COA AMB"]] = state
			d = as_sent("COA AMB", before, autorizacion="another drawing", signed_by="typed")
			self.assertIsNone(run(d, user=THIRD), state)
			self.assertEqual((d.signed_by, d.filled_by), (THIRD, FILLER), state)

	def test_signed_by_cannot_be_typed_and_an_emptied_signature_has_no_signer(self):
		d = as_sent("COA AMB", in_review(), signed_by=THIRD)
		self.assertIsNone(run(d, user=THIRD))
		self.assertEqual(d.signed_by, APPROVER)
		d = as_sent("COA AMB", in_review(), autorizacion="")
		self.assertIsNone(run(d, user=THIRD))
		self.assertIsNone(d.signed_by)

	def test_a_new_certificate_carries_no_signer(self):
		d = cert("COA AMB", new=True, autorizacion="copied", signed_by=THIRD)
		self.assertIsNone(run(d, user=THIRD))
		self.assertIsNone(d.signed_by)

	def test_the_approver_who_did_not_sign_is_refused_and_the_one_who_signs_passes(self):
		signed_by_other = in_review(signed_by=THIRD)
		refusal = run(as_sent("COA AMB", signed_by_other, state="Approved"), user=APPROVER)
		self.assertIn("its signature was not drawn by you. Sign it yourself as approver", refusal or "")
		# a signature from before the field: no signer, and the message says it must be drawn again
		unsigned_before = in_review(signed_by=None)
		refusal = run(as_sent("COA AMB", unsigned_before, state="Approved"), user=APPROVER)
		self.assertIn("must be drawn again by the approver", refusal or "")
		# the approver draws it (a save in Pending Supervisor), then approves
		drawn = as_sent("COA AMB", unsigned_before, autorizacion="approver's drawing")
		self.assertIsNone(run(drawn, user=APPROVER))
		self.assertEqual((drawn.signed_by, drawn.filled_by), (APPROVER, FILLER))
		then = in_review(signed_by=APPROVER, autorizacion="approver's drawing")
		approval = as_sent("COA AMB", then, state="Approved")
		self.assertIsNone(run(approval, user=APPROVER))
		self.assertEqual(approval._lot_move, ("approved", "LOT-1"))
		# or in the very save that approves
		at_once = as_sent("COA AMB", unsigned_before, state="Approved", autorizacion="approver's drawing")
		self.assertIsNone(run(at_once, user=APPROVER))

	def test_not_signed_keeps_its_own_message_first(self):
		refusal = run(
			as_sent("COA AMB", in_review(autorizacion=None, signed_by=None), state="Approved"), user=APPROVER
		)
		self.assertIn("it is not signed. Sign it, save, then approve.", refusal or "")

	def test_a_coa_amb2_is_not_asked(self):
		before = in_review("COA AMB2", signed_by=None)
		self.assertIsNone(run(as_sent("COA AMB2", before, state="Approved"), user=APPROVER))

	def test_the_field_is_a_read_only_link_to_user_not_copied(self):
		with open(os.path.join(PKG, "amb_w_tds", "doctype", "coa_amb", "coa_amb.json"), encoding="utf8") as f:
			meta = json.load(f)
		field = {d["fieldname"]: d for d in meta["fields"]}["signed_by"]
		self.assertEqual(
			(field["fieldtype"], field["options"], field["read_only"], field["no_copy"]),
			("Link", "User", 1, 1),
		)
		self.assertIn("signed_by", meta["field_order"])
		with open(
			os.path.join(PKG, "amb_w_tds", "doctype", "coa_amb2", "coa_amb2.json"), encoding="utf8"
		) as f:
			self.assertNotIn("signed_by", {d["fieldname"] for d in json.load(f)["fields"]})


def approved_doc(**kw):
	"""A COA AMB as stored at Approved: every group of fields of REPLY-385 Part B 2 carries a value."""
	before = stored(
		"COA AMB",
		"Approved",
		[row("r1", "5"), row("r2", "6")],
		filled_by=FILLER,
		approved_by=APPROVER,
		approval_date=TODAY,
		signed_by=APPROVER,
		batch_reference="LOT-1",
		work_order="WO-1",
		preservative_system="PS-1",
		coa_preservatives=[frappe._dict(name="pres-1", compound="Sorbate", percentage=0.1)],
		custom_coa_footnote="a footnote",
		coa_language="English",
		item_name="Product",
		item_code="0227",
		custom_golden_number="G-1",
		coa_number="COA-1",
		custom_version="1",
		cas_number="CAS",
		inci_name="INCI",
		shelf_life="24 months",
		packaging="drum",
		storage_and_handling_conditions="cool",
		spc_parameters=[frappe._dict(name="spc-1", parameter_name="pH", value=5)],
		qr_token=None,
		owner=FILLER,
		overall_result="Pass",
		compliance_status="Compliant",
	)
	for r in before.coa_quality_test_parameter:
		r.update(test_method="M-1", remarks="", parameter_group="G", custom_uom="%", status="Pass")
	before.update(kw)
	return before


def share(before=None, **values):
	"""The direct submit (`frappe.client.submit`): the document as sent, docstatus 1, Certificate Shared."""
	d = as_sent("COA AMB", before or approved_doc(), state="Certificate Shared", docstatus=1, **values)
	d.__dict__["_action"] = "submit"
	return d


class TestTheShareFreezesTheCertificate(unittest.TestCase):
	"""Decision 322: one case per group of fields of REPLY-385 Part B 2, on the direct-submit path."""

	GROUPS = {
		"the customers list": dict(custom_coa_customers=[]),
		"a customer's row": dict(custom_coa_customers=[frappe._dict(name="cust-1", customer="CUST-2")]),
		"the signature": dict(autorizacion="another drawing"),
		"the lot": dict(batch_reference="LOT-2"),
		"the product": dict(product_item="ITEM-2"),
		"the specification": dict(linked_tds="TDS-2"),
		"the preservatives system": dict(preservative_system="PS-2"),
		"the preservatives table": dict(
			coa_preservatives=[frappe._dict(name="pres-1", compound="Sorbate", percentage=0.2)]
		),
		"the footnote": dict(custom_coa_footnote="another"),
		"the language": dict(coa_language="Spanish"),
		"the item name": dict(item_name="Other"),
		"the item code": dict(item_code="9999"),
		"the golden number": dict(custom_golden_number="G-2"),
		"the certificate number": dict(coa_number="COA-9"),
		"the version": dict(custom_version="2"),
		"the specification's copied fields": dict(shelf_life="12 months"),
		"the SPC parameters table": dict(
			spc_parameters=[frappe._dict(name="spc-1", parameter_name="pH", value=6)]
		),
		"the Work Order": dict(work_order="WO-2"),
		"the QR token": dict(qr_token="token-typed"),
		"the owner": dict(owner=THIRD),
	}
	EXPECTED = {
		"the customers list": "table custom_coa_customers: 0 rows instead of the 1 stored",
		"a customer's row": "table custom_coa_customers, row 1 (cust-1): field customer",
		"the preservatives table": "table coa_preservatives, row 1 (pres-1): field percentage",
		"the SPC parameters table": "table spc_parameters, row 1 (spc-1): field value",
	}

	def test_each_group_is_refused_by_name(self):
		for what, values in self.GROUPS.items():
			with self.subTest(what):
				refusal = run(share(**copy.deepcopy(values)), user=FILLER)
				self.assertIn("it is shared exactly as it was approved, and this save changes", refusal or "")
				self.assertIn(self.EXPECTED.get(what, f"field {next(iter(values))}"), refusal)
				self.assertIn("Nothing was shared", refusal)

	def test_the_non_evaluated_fields_of_a_test_row(self):
		for field in ("test_method", "remarks", "parameter_group", "custom_uom", "custom_method"):
			with self.subTest(field):
				d = share()
				d.coa_quality_test_parameter[1][field] = "changed"
				refusal = run(d, user=FILLER)
				self.assertIn(f"table coa_quality_test_parameter, row 2 (r2): field {field}", refusal or "")

	def test_an_evaluated_field_keeps_its_own_message(self):
		d = share()
		d.coa_quality_test_parameter[0].result = "7"
		self.assertIn("its results cannot be changed while it is shared", run(d, user=FILLER) or "")

	def test_rows_in_another_order_and_a_row_replaced(self):
		d = share()
		d.coa_quality_test_parameter.reverse()
		self.assertIn(
			"table coa_quality_test_parameter, row 1: row r2 instead of the stored row r1", run(d) or ""
		)
		d = share()
		d.coa_quality_test_parameter[0]["idx"] = 9
		self.assertIn("row 1 (r1): field idx", run(d) or "")

	def test_the_forms_share_passes_and_what_is_not_compared(self):
		"""`apply_workflow` reloads: the stored certificate with the state and docstatus only. The modification stamps,
		the framework's metadata columns, the result fields and the rows' status are not compared; `filled_by`,
		approver, date and signer are written from the stored certificate whatever is sent."""
		self.assertIsNone(run(share(), user=FILLER))
		loose = share(
			modified="2026-11-27 10:00:00",
			modified_by=THIRD,
			_comments='[{"comment": "x"}]',
			_assign='["someone"]',
			_seen='["someone"]',
			_user_tags="tag",
			_liked_by="[]",
			overall_result="Fail",
			compliance_status="Pending",
			failed_parameters="x",
			pass_percentage=1,
			tested_percentage=1,
			filled_by=THIRD,
			approved_by=THIRD,
			approval_date="1999-01-01",
			signed_by=THIRD,
		)
		for r in loose.coa_quality_test_parameter:
			r.update(status="Fail", docstatus=1, modified="x", modified_by=THIRD)
		self.assertIsNone(run(loose, user=FILLER))
		self.assertEqual(
			(loose.filled_by, loose.approved_by, loose.approval_date, loose.signed_by, loose.overall_result),
			(FILLER, APPROVER, TODAY, APPROVER, "Pass"),
		)

	def test_the_stored_work_order_is_kept(self):
		"""The lot's Work Order moved since the approval: the share keeps the stored one and does not refuse."""
		d = share()
		self.assertIsNone(run(d, user=FILLER, lots={"LOT-1": "WO-MOVED"}))
		self.assertEqual(d.work_order, "WO-1")
		# a draft save still follows the lot
		draft = as_sent(
			"COA AMB",
			stored("COA AMB", "Draft", [row("r1", "5")], batch_reference="LOT-1", work_order="WO-1"),
		)
		self.assertIsNone(run(draft, user=FILLER, lots={"LOT-1": "WO-MOVED"}))
		self.assertEqual(draft.work_order, "WO-MOVED")

	def test_it_runs_in_before_validate(self):
		d = share(custom_coa_footnote="another")
		d.validate = mock.Mock(side_effect=AssertionError("validate is not reached"))
		with site387(), mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
			with self.assertRaises(frappe.ValidationError) as refused:
				d.before_validate()
		self.assertIn("field custom_coa_footnote", str(refused.exception))

	def test_values_read_from_the_database_and_sent_as_json_compare_by_their_field_type(self):
		"""On a site the DocType's description gives each field's type: a date sent as text, a number sent as text or
		an empty check is the same value as the stored one."""
		import datetime

		fields = [
			frappe._dict(fieldname="approval_date", fieldtype="Date"),
			frappe._dict(fieldname="pass_percentage", fieldtype="Percent"),
			frappe._dict(fieldname="show_draft_tds", fieldtype="Check"),
			frappe._dict(fieldname="cpk_value", fieldtype="Float"),
			frappe._dict(fieldname="custom_coa_footnote", fieldtype="Small Text"),
		]
		meta = types.SimpleNamespace(
			get_valid_columns=lambda: [
				"name",
				"creation",
				"approval_date",
				"show_draft_tds",
				"cpk_value",
				"custom_coa_footnote",
			],
			get=lambda key: fields if key == "fields" else None,
			get_table_fields=lambda: [],
			has_field=lambda f: False,
		)
		before = frappe._dict(
			name="COA-1",
			creation=datetime.datetime(2026, 11, 1, 9, 0, 0, 5),
			approval_date=datetime.date(2026, 11, 26),
			show_draft_tds=0,
			cpk_value=1.5,
			custom_coa_footnote=None,
		)
		sent = frappe._dict(
			name="COA-1",
			creation="2026-11-01 09:00:00.000005",
			approval_date="2026-11-26",
			show_draft_tds=None,
			cpk_value="1.5",
			custom_coa_footnote="",
		)
		with site387() as fake:
			fake.get_meta = lambda dt: meta
			self.assertIsNone(
				rules._first_difference_at_share(
					types.SimpleNamespace(doctype="COA AMB", get=sent.get), before
				)
			)
			sent["cpk_value"] = "1.6"
			self.assertEqual(
				rules._first_difference_at_share(
					types.SimpleNamespace(doctype="COA AMB", get=sent.get), before
				),
				"field cpk_value",
			)


class TestNoDraftInASubmittedState(unittest.TestCase):
	def test_a_docstatus_0_save_into_certificate_shared_is_refused_and_writes_no_lot(self):
		for user in (FILLER, APPROVER, "Administrator"):
			d = as_sent("COA AMB", approved_doc(), state="Certificate Shared")
			refusal = run(d, user=user)
			self.assertIn(
				"cannot be saved as Certificate Shared without being submitted", refusal or "", user
			)
			self.assertIsNone(getattr(d, "_lot_move", None))

	def test_the_states_docstatus_is_read_from_the_workflow(self):
		"""COA AMB2's workflow has no submitted state, so nothing is refused there; give it one and it is."""
		d = as_sent("COA AMB2", stored("COA AMB2", "Draft", [row("r1", "5")]), state="Validated")
		self.assertIsNone(run(d))
		wf = _workflows()
		wf["submit_and_start_workflow"]["states"][1]["doc_status"] = "1"  # Validated
		with mock.patch(f"{__name__}._workflows", lambda: wf):
			d = as_sent("COA AMB2", stored("COA AMB2", "Draft", [row("r1", "5")]), state="Validated")
			self.assertIn("cannot be saved as Validated without being submitted", run(d) or "")

	def test_a_save_that_keeps_the_stored_state_and_the_real_share_are_not_judged_by_it(self):
		self.assertIsNone(run(share(), user=FILLER))
		with site387() as fake:
			kept = as_sent("COA AMB", approved_doc(workflow_state_1="Certificate Shared"))
			rules.refuse_draft_in_submitted_state(kept)
			fake.db.get_value.assert_not_called()


class TestTheLotCertificateReadsBelow(unittest.TestCase):
	"""Decision 323: the Batches of a lot record and of every record below it."""

	def test_the_rejected_inspection_of_a_sub_lots_batch_refuses_the_lots_certificate(self):
		before = in_review(batch_reference="LOT")
		refusal = run(
			as_sent("COA AMB", before, state="Approved"),
			below={"LOT": ["SUB"], "SUB": ["CONT"]},
			batches_of={"SUB": ["B-SUB"]},
			rejected=["QI-1"],
		)
		self.assertIn("lot LOT has a submitted Quality Inspection that is Rejected: QI-1", refusal or "")

	def test_without_the_walk_it_would_find_nothing(self):
		with site387(below={}, batches_of={"SUB": ["B-SUB"]}):
			self.assertEqual(rules.lot_batches("LOT"), [])
		with site387(below={"LOT": ["SUB"]}, batches_of={"SUB": ["B-SUB"]}) as fake:
			self.assertEqual(rules.lot_batches("LOT"), ["B-SUB"])
		self.assertEqual(fake.asked[-1], ("Batch", {"custom_batch_amb": ["in", ["LOT", "SUB"]]}))

	def test_every_level_below_at_most_four_and_a_loop_ends(self):
		chain = {"L1": ["L2a", "L2b"], "L2a": ["L3"], "L3": ["L4"], "L4": ["L5"], "L5": ["L6"]}
		with site387(below=chain):
			self.assertEqual(rules.lot_records("L1"), ["L1", "L2a", "L2b", "L3", "L4", "L5"])
		with site387(below={"A": ["B"], "B": ["A", "C"], "C": ["B"]}) as fake:
			self.assertEqual(rules.lot_records("A"), ["A", "B", "C"])
		self.assertLessEqual(len([a for a in fake.asked if a[0] == "Batch AMB"]), rules.LOT_LEVELS_BELOW)

	def test_a_site_without_the_parent_field_reads_the_record_alone(self):
		with site(parent_field=False) as fake:
			self.assertEqual(rules.lot_records("LOT"), ["LOT"])
		self.assertEqual(fake.asked, [])


if __name__ == "__main__":
	unittest.main()
