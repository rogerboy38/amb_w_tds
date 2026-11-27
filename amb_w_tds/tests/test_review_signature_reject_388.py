"""TASKS-388 (tds half), DB-free: decisions 330, 331 and 332.

- 330: in both certificate workflows the state Pending Supervisor gives the edit right to Quality Manager beside
  Quality User. Frappe stores one role per state row (`Workflow Document State.allow_edit`), so the right is a SECOND
  row for the same state. Frappe's form takes the union of the rows of a state; its server functions read the first
  row of a state for its docstatus and update field, which both rows share. A Quality Manager without Quality User
  draws the signature in Pending Supervisor and approves.
- 331: a save that makes someone the filler (results, customers list, identity) empties COA AMB's signature and its
  signer in that save and says so; a save that only draws the signature clears nothing.
- 332: the save from stored Approved (docstatus 0) to another state at docstatus 0 changes nothing but the state and
  what the server derives, resets or fetches; any other difference is refused by name. The lot is withdrawn as before.

The save paths are those of `test_identity_share_freeze_387` (a plain save, `set_value`, the form's workflow action);
Frappe's own workflow functions (`frappe.model.workflow`, `Workflow.validate_docstatus`) are run on the fixture."""

import copy
import inspect
import os
import types
import unittest
from contextlib import ExitStack, contextmanager
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2
from amb_w_tds.tests.test_certificate_rules_b1 import CLASSES, TODAY, _throw, customers, row, stored
from amb_w_tds.tests.test_identity_share_freeze_387 import (
	APPROVER,
	BOTH,
	FILLER,
	PKG,
	THIRD,
	WORKFLOW_OF,
	_workflows,
	approved_doc,
	as_sent,
	in_review,
	share,
	site387,
)

QM_ONLY = ("Quality Manager", "Employee")  # a Quality Manager who does not hold Quality User
FRAPPE = os.path.dirname(os.path.abspath(frappe.__file__))


def run(doc, msgprint=None, workflow_roles=None, **kw):
	"""One save of `doc` as sent: `before_validate`, then `validate` (and, with `workflow_roles`, Frappe's own
	`validate_workflow` for a user with those roles, as `Document._validate` runs it). Returns the refusal, or None.
	`msgprint` collects what the user was told."""
	with site387(**kw) as fake, ExitStack() as stack:
		if workflow_roles is not None:
			stack.enter_context(frappe_workflow(workflow_roles))
		try:
			with mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
				doc.before_validate()
			doc.validate()
			if workflow_roles is not None:
				from frappe.model.workflow import validate_workflow

				validate_workflow(doc)
		except frappe.ValidationError as e:
			return str(e)
		finally:
			if msgprint is not None:
				msgprint.extend(c.args[0] for c in fake.msgprint.call_args_list)
	return None


class _Row(frappe._dict):
	def as_dict(self, *a, **k):
		return frappe._dict(self)


def fixture_workflow(doctype):
	"""The certificate's workflow as Frappe's cached Workflow would hold it, from the fixture."""
	w = _workflows()[WORKFLOW_OF[doctype]]
	return frappe._dict(
		name=w["name"],
		document_type=doctype,
		workflow_state_field=w["workflow_state_field"],
		states=[_Row(s) for s in w["states"]],
		transitions=[_Row(t) for t in w["transitions"]],
	)


@contextmanager
def frappe_workflow(roles):
	"""Frappe's workflow module, unchanged, over the fixture's workflows and a user with `roles`."""
	import frappe.model.workflow as wf

	with ExitStack() as stack:
		stack.enter_context(mock.patch.object(wf, "get_workflow", fixture_workflow))
		stack.enter_context(mock.patch.object(frappe, "get_roles", lambda *a, **k: list(roles)))
		stack.enter_context(mock.patch.object(frappe, "throw", _throw))
		stack.enter_context(mock.patch.object(wf, "_", lambda s: s))
		stack.enter_context(mock.patch.object(frappe, "bold", lambda s: s))
		yield wf


def as_document(doctype, values):
	"""A stored certificate as a Document (Frappe's `get_transitions` asks for one), permission check stood in for."""
	d = object.__new__(CLASSES[doctype])
	d.__dict__.update(copy.deepcopy(dict(values)))
	d.check_permission = lambda *a, **k: None
	return d


def editable_by(states, state):
	"""Frappe's form rule (`frappe.workflow.get_document_state_roles` / `is_read_only`, workflow.js): the roles
	that may edit a document in `state` are the `allow_edit` of EVERY row of the workflow for that state."""
	return {s["allow_edit"] for s in states if s["state"] == state}


class TestQualityManagerMayEditInPendingSupervisor(unittest.TestCase):
	"""Decision 330."""

	def test_the_fixture_has_a_second_pending_supervisor_row_for_quality_manager(self):
		for doctype, name in WORKFLOW_OF.items():
			with self.subTest(doctype):
				states = _workflows()[name]["states"]
				rows = [s for s in states if s["state"] == "Pending Supervisor"]
				self.assertEqual([r["allow_edit"] for r in rows], ["Quality User", "Quality Manager"])
				# the same row in every other column: the docstatus and the update field Frappe reads from the first
				first, second = (dict(r) for r in rows)
				first.pop("allow_edit"), second.pop("allow_edit")
				self.assertEqual(first, second)
				self.assertEqual((first["doc_status"], first["update_field"]), ("0", None))
				# the two rows are next to each other, as the TDS workflow's two "Pending Director" rows are
				at = [i for i, s in enumerate(states) if s["state"] == "Pending Supervisor"]
				self.assertEqual(at[1], at[0] + 1)

	def test_what_the_form_lets_each_role_edit(self):
		for doctype, name in WORKFLOW_OF.items():
			states = _workflows()[name]["states"]
			self.assertEqual(editable_by(states, "Pending Supervisor"), {"Quality User", "Quality Manager"})
			self.assertTrue(editable_by(states, "Pending Supervisor") & set(QM_ONLY), doctype)
			# without the new row the Quality Manager who does not hold Quality User had a read-only form there
			without = [
				s
				for s in states
				if (s["state"], s["allow_edit"]) != ("Pending Supervisor", "Quality Manager")
			]
			self.assertFalse(editable_by(without, "Pending Supervisor") & set(QM_ONLY), doctype)
			# nothing else moved: every other state is editable by exactly whom it was
			for state in {s["state"] for s in states} - {"Pending Supervisor"}:
				self.assertEqual(len([s for s in states if s["state"] == state]), 1, state)

	def test_frappes_form_takes_every_row_of_the_state(self):
		"""The rule `editable_by` models is Frappe 16's own: the rows are filtered by state, and every row's role is
		taken; the form is read-only only when the user holds none of them."""
		with open(
			os.path.join(FRAPPE, "public", "js", "frappe", "model", "workflow.js"), encoding="utf8"
		) as f:
			js = f.read()
		self.assertIn(
			'frappe.get_children(frappe.workflow.workflows[doctype], "states", { state: state })', js
		)
		self.assertIn("return workflow_states.map((d) => d.allow_edit);", js)
		self.assertIn("allow_edit_roles.includes(role)", js)
		# and the server never reads the edit right: nothing in Frappe's Python refuses a save by `allow_edit`
		with open(os.path.join(FRAPPE, "model", "workflow.py"), encoding="utf8") as f:
			self.assertNotIn("allow_edit", f.read())
		with open(os.path.join(FRAPPE, "model", "document.py"), encoding="utf8") as f:
			self.assertNotIn("allow_edit", f.read())

	def test_frappes_workflow_validation_and_import_accept_the_two_rows(self):
		"""`Workflow.validate` (run by the fixture import) checks each transition against the FIRST row of its
		states; both rows share their docstatus, so nothing it refuses changes."""
		from frappe.workflow.doctype.workflow.workflow import Workflow

		for doctype in BOTH:
			w = fixture_workflow(doctype)
			with mock.patch.object(frappe, "throw", _throw), mock.patch.object(frappe, "_", lambda s: s):
				Workflow.validate_docstatus(w)  # raises on a refused transition

	def test_frappes_transitions_and_state_settings_are_unchanged_by_the_second_row(self):
		for doctype in BOTH:
			with self.subTest(doctype), frappe_workflow(QM_ONLY) as wf:
				doc = as_document(doctype, in_review(doctype))
				actions = sorted(t["action"] for t in wf.get_transitions(doc))
				self.assertEqual(actions, ["Approve", "Reject", "Return for correction"])
				# `apply_workflow` takes the first row of the next state; `set_workflow_state_on_action` the first row
				# of a docstatus: neither can meet the second row before the first
				w = fixture_workflow(doctype)
				first = next(d for d in w.states if d.state == "Pending Supervisor")
				self.assertEqual(first.allow_edit, "Quality User")
				self.assertEqual(w.states[0].state, "Draft")  # the default state of a new certificate
				# the submit of an Approved COA AMB is still named Certificate Shared (the first docstatus-1 row)
				if doctype == "COA AMB":
					shared = as_document(doctype, approved_doc())
					shared.docstatus = 1
					shared.set = lambda k, v: shared.__dict__.__setitem__(k, v)
					with mock.patch.object(frappe, "get_doc", lambda *a: w):
						wf.set_workflow_state_on_action(shared, w.name, "submit")
					self.assertEqual(shared.workflow_state_1, "Certificate Shared")

	def test_a_quality_manager_without_quality_user_signs_in_review_and_approves(self):
		"""The server path: the Quality Manager draws the signature in Pending Supervisor (a save), then approves (the
		save of the workflow's Approve, checked by Frappe's own `validate_workflow` for that user's roles)."""
		before = in_review(signed_by=None, autorizacion=None)
		told = []
		drawn = as_sent("COA AMB", before, autorizacion="the manager's drawing")
		self.assertIsNone(run(drawn, msgprint=told, workflow_roles=QM_ONLY, user=APPROVER))
		self.assertEqual((drawn.signed_by, drawn.filled_by), (APPROVER, FILLER))
		self.assertEqual(told, [])  # drawing the signature clears nothing (decision 331)
		signed = in_review(signed_by=APPROVER, autorizacion="the manager's drawing")
		approval = as_sent("COA AMB", signed, state="Approved")
		approval._doc_before_save = as_document("COA AMB", signed)  # Frappe's transition check reads it
		self.assertIsNone(run(approval, workflow_roles=QM_ONLY, user=APPROVER))
		self.assertEqual((approval.approved_by, approval.filled_by), (APPROVER, FILLER))
		self.assertEqual(approval._lot_move, ("approved", "LOT-1"))
		# COA AMB2 (no signature): the Quality Manager approves what another filled
		approval2 = as_sent("COA AMB2", in_review("COA AMB2"), state="Approved")
		approval2._doc_before_save = as_document("COA AMB2", in_review("COA AMB2"))
		self.assertIsNone(run(approval2, workflow_roles=QM_ONLY, user=APPROVER))
		self.assertEqual(approval2.approved_by, APPROVER)

	def test_a_quality_manager_who_changes_a_result_there_is_the_filler_as_anyone(self):
		before = in_review()
		d = as_sent("COA AMB", before)
		d.coa_quality_test_parameter[0].result = "7"
		self.assertIsNone(run(d, workflow_roles=QM_ONLY, user=APPROVER))
		self.assertEqual(d.filled_by, APPROVER)


def signed_draft(doctype="COA AMB", **kw):
	"""A certificate returned for correction: in Draft, filled by B, signed by C."""
	before = stored(
		doctype,
		"Draft",
		[row("r1", "5"), row("r2", "6")],
		filled_by=FILLER,
		signed_by=APPROVER,
		autorizacion="C's drawing",
		batch_reference="LOT-1",
	)
	before.update(kw)
	return before


class TestAChangeClearsTheSignature(unittest.TestCase):
	"""Decision 331."""

	def test_c_signs_it_is_returned_a_result_changes_and_c_must_sign_again(self):
		# C draws the signature in Pending Supervisor
		drawn = as_sent("COA AMB", in_review(signed_by=None, autorizacion=None), autorizacion="C's drawing")
		self.assertIsNone(run(drawn, user=APPROVER))
		self.assertEqual(drawn.signed_by, APPROVER)
		# "Return for correction" keeps the signature (it changes nothing that is filled)
		returned = as_sent("COA AMB", in_review(autorizacion="C's drawing"), state="Draft")
		told = []
		self.assertIsNone(run(returned, msgprint=told, user=FILLER))
		self.assertEqual((returned.autorizacion, returned.signed_by), ("C's drawing", APPROVER))
		self.assertEqual(told, [])
		# B changes a result in Draft: signature and signer are emptied in that save, and B is told
		corrected = as_sent("COA AMB", signed_draft())
		corrected.coa_quality_test_parameter[0].result = "7"
		self.assertIsNone(run(corrected, msgprint=told, user=FILLER))
		self.assertEqual(
			(corrected.autorizacion, corrected.signed_by, corrected.filled_by), (None, None, FILLER)
		)
		self.assertEqual(len(told), 1)
		self.assertIn("The signature of COA AMB COA-1 was cleared: this save changed its results", told[0])
		# back in review, C cannot approve until C signs again
		unsigned = in_review(autorizacion=None, signed_by=None)
		refusal = run(as_sent("COA AMB", unsigned, state="Approved"), user=APPROVER)
		self.assertIn("it is not signed", refusal or "")
		resigned = as_sent("COA AMB", unsigned, autorizacion="C's new drawing")
		self.assertIsNone(run(resigned, user=APPROVER))
		self.assertEqual(resigned.signed_by, APPROVER)
		approval = as_sent("COA AMB", in_review(autorizacion="C's new drawing"), state="Approved")
		self.assertIsNone(run(approval, user=APPROVER))
		self.assertEqual(approval._lot_move, ("approved", "LOT-1"))

	def test_a_customers_change_clears_it_too(self):
		for state in ("Draft", "Validated", "Pending Supervisor"):
			with self.subTest(state):
				before = signed_draft()
				before[rules.STATE_FIELD["COA AMB"]] = state
				told = []
				d = as_sent(
					"COA AMB",
					before,
					custom_coa_customers=customers() + [frappe._dict(name="c2", customer="C2")],
				)
				self.assertIsNone(run(d, msgprint=told, user=THIRD))
				self.assertEqual((d.autorizacion, d.signed_by, d.filled_by), (None, None, THIRD))
				self.assertIn("this save changed its customers list", told[0])

	def test_an_identity_change_in_draft_clears_it(self):
		for field, value in (
			("batch_reference", "LOT-2"),
			("linked_tds", "TDS-2"),
			("product_item", "ITEM-2"),
		):
			with self.subTest(field):
				told = []
				d = as_sent("COA AMB", signed_draft(), **{field: value})
				self.assertIsNone(run(d, msgprint=told, user=THIRD))
				self.assertEqual((d.autorizacion, d.signed_by), (None, None))
				self.assertIn(f"this save changed {field}", told[0])

	def test_a_save_that_only_draws_the_signature_or_changes_nothing_clears_nothing(self):
		for state in ("Draft", "Validated", "Pending Supervisor"):
			before = signed_draft()
			before[rules.STATE_FIELD["COA AMB"]] = state
			told = []
			d = as_sent("COA AMB", before, autorizacion="another drawing")
			self.assertIsNone(run(d, msgprint=told, user=THIRD))
			self.assertEqual((d.autorizacion, d.signed_by, d.filled_by), ("another drawing", THIRD, FILLER))
			unchanged = as_sent("COA AMB", before)
			self.assertIsNone(run(unchanged, msgprint=told, user=THIRD))
			self.assertEqual((unchanged.autorizacion, unchanged.signed_by), ("C's drawing", APPROVER))
			self.assertEqual(told, [], state)

	def test_the_clear_wins_over_a_signature_drawn_in_the_same_save(self):
		"""`set_signed_by` names the user who drew a new signature; the clear runs after it and is not undone."""
		d = as_sent("COA AMB", signed_draft(), autorizacion="drawn with the change")
		d.coa_quality_test_parameter[1].result = "8"
		told = []
		self.assertIsNone(run(d, msgprint=told, user=THIRD))
		self.assertEqual((d.autorizacion, d.signed_by, d.filled_by), (None, None, THIRD))
		self.assertEqual(len(told), 1)
		order = inspect.getsource(rules.apply)
		self.assertLess(
			order.index("set_signed_by(doc)"), order.index("clear_signature_on_filling(doc, filling)")
		)
		self.assertLess(
			order.index("clear_signature_on_filling(doc, filling)"), order.index("set_approval(doc)")
		)

	def test_a_change_in_the_save_that_approves_is_still_refused_as_the_fillers(self):
		d = as_sent("COA AMB", in_review(), state="Approved")
		d.coa_quality_test_parameter[0].result = "7"
		self.assertIn("another person must approve it", run(d, user=APPROVER) or "")
		self.assertIsNone(getattr(d, "_lot_move", None))

	def test_nothing_to_clear_says_nothing(self):
		told = []
		d = as_sent("COA AMB", signed_draft(autorizacion=None, signed_by=None))
		d.coa_quality_test_parameter[0].result = "7"
		self.assertIsNone(run(d, msgprint=told, user=THIRD))
		self.assertEqual(told, [])

	def test_a_new_certificate_and_a_coa_amb2_are_not_judged(self):
		"""Narrowest readings: a new certificate carries no signer already (decision 321); COA AMB2 is not signed
		for its approval (decision 312), so its `autorizacion` is left as it is."""
		from amb_w_tds.tests.test_certificate_rules_b1 import cert

		told = []
		new = cert("COA AMB", new=True, autorizacion="copied")
		self.assertIsNone(run(new, msgprint=told, user=THIRD))
		self.assertEqual((new.autorizacion, new.signed_by, new.filled_by), ("copied", None, THIRD))
		amb2_doc = as_sent("COA AMB2", signed_draft("COA AMB2"))
		amb2_doc.coa_quality_test_parameter[0].result = "7"
		self.assertIsNone(run(amb2_doc, msgprint=told, user=THIRD))
		self.assertEqual((amb2_doc.autorizacion, amb2_doc.filled_by), ("C's drawing", THIRD))
		self.assertEqual(told, [])

	def row_hook(
		self,
		hook,
		row_doctype,
		sent,
		stored_row,
		parent_signature,
		parenttype="COA AMB",
		method="before_validate",
	):
		r = types.SimpleNamespace(doctype=row_doctype, get=lambda k: sent.get(k), is_new=lambda: False)
		with site387(user=THIRD) as fake:

			def get_value(doctype, name, fields, as_dict=False, for_update=False):
				if doctype == row_doctype:
					return frappe._dict(stored_row)
				if doctype in rules.STATE_FIELD and fields == [rules.SIGNATURE_FIELD, rules.SIGNER_FIELD]:
					return frappe._dict(parent_signature)
				if doctype in rules.STATE_FIELD and fields == ["filled_by", rules.FILLERS_FIELD]:
					return frappe._dict()  # TASKS-390: no filler and no one on the stored list before this row
				if doctype in rules.STATE_FIELD:
					return frappe._dict({rules.STATE_FIELD[doctype]: "Draft", "docstatus": 0})
				return None

			fake.db.get_value = get_value
			hook(r, method)
		return [c.args for c in fake.db.set_value.call_args_list], [
			c.args[0] for c in fake.msgprint.call_args_list
		]

	def test_a_row_saved_by_itself_that_makes_someone_the_filler_clears_the_stored_signature(self):
		signed = {"autorizacion": "C's drawing", "signed_by": APPROVER}
		cleared = ("COA AMB", "COA-1", {"autorizacion": None, "signed_by": None})
		# a result row
		in_db = {"parent": "COA-1", "parenttype": "COA AMB", "result": "5"}
		sent = dict(in_db, name="row-1", result="6")
		writes, told = self.row_hook(
			rules.note_filler_of_row, "COA Quality Test Parameter", sent, in_db, signed
		)
		self.assertEqual(
			writes, [("COA AMB", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD}), cleared]
		)
		self.assertIn("this save changed its results", told[0])
		# unchanged row: nothing; unsigned certificate: only the filler; COA AMB2: only the filler
		self.assertEqual(
			self.row_hook(
				rules.note_filler_of_row, "COA Quality Test Parameter", dict(sent, result="5"), in_db, signed
			),
			([], []),
		)
		self.assertEqual(
			self.row_hook(rules.note_filler_of_row, "COA Quality Test Parameter", sent, in_db, {})[0],
			[("COA AMB", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD})],
		)
		amb2_row = dict(in_db, parenttype="COA AMB2")
		self.assertEqual(
			self.row_hook(
				rules.note_filler_of_row,
				"COA Quality Test Parameter",
				dict(amb2_row, name="row-1", result="6"),
				amb2_row,
				signed,
			),
			([("COA AMB2", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD})], []),
		)
		# a customers row
		cust = {
			"name": "cust-1",
			"parent": "COA-1",
			"parenttype": "COA AMB",
			"parentfield": "custom_coa_customers",
			"customer": "C1",
		}
		writes, told = self.row_hook(
			rules.note_customer_row, "Customer Item", dict(cust, customer="C2"), cust, signed
		)
		self.assertEqual(
			writes, [("COA AMB", "COA-1", {"filled_by": THIRD, rules.FILLERS_FIELD: THIRD}), cleared]
		)
		self.assertIn("this save changed its customers list", told[0])


def approved(doctype="COA AMB", **kw):
	if doctype == "COA AMB":
		return approved_doc(**kw)
	before = stored(
		doctype,
		"Approved",
		[row("r1", "5"), row("r2", "6")],
		filled_by=FILLER,
		approved_by=APPROVER,
		approval_date=TODAY,
		batch_reference="LOT-1",
		work_order="WO-1",
		custom_coa_footnote="a footnote",
		overall_result="Pass",
		compliance_status="Compliant",
	)
	before.update(kw)
	return before


class TestTheRejectFromApprovedChangesOnlyTheState(unittest.TestCase):
	"""Decision 332."""

	def test_the_workflows_reject_passes_and_withdraws_the_lot_as_before(self):
		for doctype in BOTH:
			with self.subTest(doctype):
				reject = as_sent(
					doctype, approved(doctype), state="Draft"
				)  # `apply_workflow`: the stored doc, the state
				self.assertIsNone(run(reject, user=APPROVER))
				self.assertEqual((reject.approved_by, reject.approval_date), (None, None))
				self.assertEqual(reject.filled_by, FILLER)
				self.assertEqual(reject._lot_move, ("withdrawn", "LOT-1"))
				withdrawn = mock.Mock()
				with (
					site387(),
					mock.patch.object(rules, "_spc", lambda f: {"certificate_withdrawn": withdrawn}[f]),
					mock.patch.object(rules, "standing_certificates", lambda *a: []),
				):
					rules.write_lot(reject)
				self.assertEqual(withdrawn.call_args.args, (doctype, "COA-1", "LOT-1"))
				self.assertIn("standing", withdrawn.call_args.kwargs)

	def test_the_reject_through_frappes_workflow_validation(self):
		for doctype in BOTH:
			reject = as_sent(doctype, approved(doctype), state="Draft")
			reject._doc_before_save = as_document(doctype, approved(doctype))
			self.assertIsNone(run(reject, workflow_roles=("Quality Manager",), user=APPROVER), doctype)

	CHANGES = {
		"a new lot": (dict(batch_reference="LOT-2"), "field batch_reference"),
		"the customers": (
			dict(custom_coa_customers=[]),
			"table custom_coa_customers: 0 rows instead of the 1 stored",
		),
		"a customer's row": (
			dict(custom_coa_customers=[frappe._dict(name="cust-1", customer="CUST-2")]),
			"table custom_coa_customers, row 1 (cust-1): field customer",
		),
		"the signature": (dict(autorizacion="another drawing"), "field autorizacion"),
		"the footnote": (dict(custom_coa_footnote="another"), "field custom_coa_footnote"),
		"the Work Order": (dict(work_order="WO-2"), "field work_order"),
		"the specification": (dict(linked_tds="TDS-2"), "field linked_tds"),
	}

	def test_a_plain_save_out_of_approved_with_a_change_is_refused_by_name(self):
		for what, (values, named) in self.CHANGES.items():
			for state in ("Draft", "Pending Supervisor", "Validated"):
				with self.subTest(what=what, state=state):
					d = as_sent("COA AMB", approved(), state=state, **copy.deepcopy(values))
					refusal = run(d, user=APPROVER)
					self.assertIn(
						f"is Approved: going back to {state} changes nothing but its state", refusal or ""
					)
					self.assertIn(f"this save changes {named}. Nothing was saved.", refusal)
					self.assertIsNone(getattr(d, "_lot_move", None))  # nothing withdrawn

	def test_a_changed_result_row_is_refused_and_coa_amb2_too(self):
		d = as_sent("COA AMB", approved(), state="Draft")
		d.coa_quality_test_parameter[0].result = "7"
		self.assertIn(
			"table coa_quality_test_parameter, row 1 (r1): field result", run(d, user=APPROVER) or ""
		)
		for values, named in (
			(dict(batch_reference="LOT-2"), "field batch_reference"),
			(dict(custom_coa_footnote="x"), "field custom_coa_footnote"),
		):
			d = as_sent("COA AMB2", approved("COA AMB2"), state="Draft", **values)
			self.assertIn(f"this save changes {named}", run(d, user=APPROVER) or "")

	def test_every_user_is_refused(self):
		for user in (FILLER, APPROVER, THIRD, "Administrator"):
			d = as_sent("COA AMB", approved(), state="Draft", batch_reference="LOT-2")
			self.assertIn("field batch_reference", run(d, user=user) or "", user)

	def test_what_the_server_derives_or_resets_is_not_compared(self):
		loose = as_sent(
			"COA AMB",
			approved(),
			state="Draft",
			modified="2026-11-28 10:00:00",
			modified_by=THIRD,
			_comments="[]",
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
			r.update(status="Fail", modified="x")
		self.assertIsNone(run(loose, user=APPROVER))
		self.assertEqual(
			(loose.filled_by, loose.signed_by, loose.approved_by, loose.approval_date, loose.overall_result),
			(FILLER, APPROVER, None, None, "Pass"),
		)

	def test_what_the_framework_fetches_at_docstatus_0_is_not_compared(self):
		"""At docstatus 0 Frappe re-fetches the specification's fields before any rule runs: the specification's
		product or item name changed since the approval, or a Customer renamed, must not stop the Reject."""
		d = as_sent(
			"COA AMB",
			approved(),
			state="Draft",
			product_item="ITEM-SPEC-NOW",
			item_name="Renamed",
			tds_version="3",
			custom_coa_customers=[
				frappe._dict(name="cust-1", customer="CUST-1", custom_customer_name="Renamed")
			],
		)
		self.assertIsNone(run(d, user=APPROVER))
		# at the share (docstatus 1) Frappe fetches nothing, so the same values are still refused there
		self.assertIn("field item_name", run(share(item_name="Renamed"), user=FILLER) or "")

	def test_a_fetch_if_empty_field_filled_by_the_framework_and_one_typed(self):
		stored_empty = approved(cas_number=None)
		fetched = mock.Mock(return_value=frappe._dict(cas_number="CAS-OF-THE-SPEC"))
		d = as_sent("COA AMB", stored_empty, state="Draft", cas_number="CAS-OF-THE-SPEC")
		self.assertIsNone(run_with_spec(d, fetched))
		self.assertEqual(fetched.call_args.args, (rules.SPECIFICATION_DOCTYPE, "TDS-1", ["cas_number"]))
		typed = as_sent("COA AMB", stored_empty, state="Draft", cas_number="TYPED")
		self.assertIn("field cas_number", run_with_spec(typed, fetched) or "")
		# a stored value is never replaced by the framework, so a change of it is the caller's
		changed = as_sent("COA AMB", approved(), state="Draft", cas_number="CAS-OF-THE-SPEC")
		self.assertIn("field cas_number", run_with_spec(changed, fetched) or "")

	def test_the_stored_work_order_is_kept(self):
		d = as_sent("COA AMB", approved(), state="Draft")
		self.assertIsNone(run(d, user=APPROVER, lots={"LOT-1": "WO-MOVED"}))
		self.assertEqual(d.work_order, "WO-1")

	def test_it_runs_in_before_validate(self):
		for doctype in BOTH:
			d = as_sent(doctype, approved(doctype), state="Draft", batch_reference="LOT-2")
			d.validate = mock.Mock(side_effect=AssertionError("validate is not reached"))
			with site387(), mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
				with self.assertRaises(frappe.ValidationError) as refused:
					d.before_validate()
			self.assertIn("field batch_reference", str(refused.exception))

	def test_the_named_fetched_fields_are_the_shipped_ones(self):
		import json

		for folder in ("coa_amb", "coa_amb2"):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", folder, f"{folder}.json"), encoding="utf8"
			) as f:
				fields = json.load(f)["fields"]
			always = sorted(
				d["fieldname"] for d in fields if d.get("fetch_from") and not d.get("fetch_if_empty")
			)
			if_empty = sorted(
				d["fieldname"] for d in fields if d.get("fetch_from") and d.get("fetch_if_empty")
			)
			self.assertEqual(always, sorted(rules.REFETCHED_CERTIFICATE_FIELDS), folder)
			self.assertEqual(if_empty, sorted(rules.FETCHED_IF_EMPTY_CERTIFICATE_FIELDS), folder)
			self.assertEqual(
				{d["fetch_from"].split(".")[0] for d in fields if d.get("fetch_from")}, {"linked_tds"}
			)

	def test_the_share_and_a_save_that_stays_approved_are_not_judged_by_it(self):
		self.assertIsNone(run(share(), user=FILLER))
		with mock.patch.object(rules, "_first_difference_at_share", side_effect=AssertionError("not asked")):
			with site387():
				rules.refuse_changes_leaving_approved(as_sent("COA AMB", approved()))
				rules.refuse_changes_leaving_approved(as_sent("COA AMB", in_review(), state="Draft"))


def run_with_spec(doc, spec_value):
	"""A save on the stand-in site whose specification answers `spec_value` for the fields fetched from it."""
	with site387(user=APPROVER) as fake:
		plain = fake.db.get_value

		def get_value(doctype, name=None, fields=None, *a, **k):
			if doctype == rules.SPECIFICATION_DOCTYPE and isinstance(fields, list):
				return spec_value(doctype, name, fields)
			return plain(doctype, name, fields, *a, **k)

		fake.db.get_value = get_value
		try:
			with mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
				doc.before_validate()
			doc.validate()
		except frappe.ValidationError as e:
			return str(e)
	return None


if __name__ == "__main__":
	unittest.main()
