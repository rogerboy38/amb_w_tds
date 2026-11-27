"""TASKS-384 B1, DB-free: lock and derive, on both certificates.

- COA AMB derives result and compliance from its rows on every save (the draft branch no longer returns early).
- COA AMB has the Approved lock of COA AMB2, by the same functions; the workflow's own moves pass.
- `filled_by` is set on the server when a result changes; "may this be approved" runs when the state becomes Approved,
  each refusal with its own message; approver and date are written by the server.
- "Validate All Tests" says that it saved and lets a server error reach the user.

The controllers' real `validate` is run on documents built without a database (`object.__new__`), with the three
checks that read the database replaced by no-ops. The real forms' save path is run on a scratch site (see the reply)."""

import inspect
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
BOTH = ("COA AMB", "COA AMB2")
TODAY = "2026-11-26"


def _throw(msg, *a, **k):
	raise frappe.ValidationError(msg)


def row(name, result, spec="1 - 10", title=0):
	return frappe._dict(
		name=name,
		result=result,
		parameter_name=name,
		specification=spec,
		value=None,
		min_value=None,
		max_value=None,
		custom_is_title_row=title,
		status=None,
		formula_based_criteria=0,
		acceptance_formula=None,
		numeric=0,
	)


def named(doctype, name, user="u"):
	"""What a row saved by itself writes on its certificate: the filler, and the filler added to the list of everyone
	who ever filled it (TASKS-390, decision 337; TASKS-391, decision 340; empty before here)."""
	return (doctype, name, {"filled_by": user, rules.FILLERS_FIELD: user})


def customers():
	return [frappe._dict(name="cust-1", customer="CUST-1")]


# TASKS-387: what a certificate is for, its customers and its signature, as `cert` sends them by default. The stored
# document carries the same unless a test says otherwise, so that only what a test changes is a change.
SENT_AS_STORED = ("linked_tds", "product_item", "batch_reference", "autorizacion", "custom_coa_customers")


def stored(doctype, state, rows=(), docstatus=0, **kw):
	"""The document as it is in the database before the save. Its signature was drawn by "approver"."""
	d = frappe._dict(
		doctype=doctype,
		name="COA-1",
		docstatus=docstatus,
		coa_quality_test_parameter=list(rows),
		filled_by="filler",
		approved_by=None,
		approval_date=None,
		linked_tds="TDS-1",
		product_item="ITEM-1",
		batch_reference=None,
		autorizacion="signature",
		signed_by="approver",
		custom_coa_customers=customers(),
	)
	d[rules.STATE_FIELD[doctype]] = state
	d.update(kw)
	return d


def cert(doctype="COA AMB", state="Draft", rows=None, before=None, new=False, docstatus=0, **kw):
	"""A certificate as the controller sees it during a save."""
	d = object.__new__(CLASSES[doctype])
	rows = [row("r1", "5")] if rows is None else list(rows)
	d.__dict__.update(
		doctype=doctype,
		name="COA-1",
		docstatus=docstatus,
		linked_tds="TDS-1",
		batch_reference=None,
		product_item="ITEM-1",
		coa_quality_test_parameter=rows,
		overall_result=None,
		compliance_status=None,
		failed_parameters=None,
		pass_percentage=None,
		tested_percentage=None,
		autorizacion="signature",
		custom_coa_customers=customers(),
		filled_by=None,
		approved_by=None,
		approval_date=None,
	)
	d.__dict__[rules.STATE_FIELD[doctype]] = state
	d.__dict__.update(kw)
	if new:
		d.__dict__["__islocal"] = 1
		d._doc_before_save = None
	else:
		d._doc_before_save = (
			before
			if before is not None
			else stored(
				doctype,
				"Draft",
				[row(r.name, r.result) for r in rows],
				**{f: d.__dict__.get(f) for f in SENT_AS_STORED},
			)
		)
	for name in ("validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link"):
		setattr(d, name, lambda: None)  # the three checks that read the database
	return d


@contextmanager
def site(
	user="approver",
	batch_field=True,
	batches=(),
	rejected=(),
	nc_doctype=True,
	nc_field=True,
	ncs=(),
	below=None,
	parent_field=True,
):
	"""What the rules read outside the document: the session user, and the lot's Batches, inspections and NCs.
	`below` maps a lot record to the records whose parent it is (TASKS-387)."""
	asked = []
	below = below or {}

	def get_all(doctype, filters=None, pluck=None, **kw):
		asked.append((doctype, filters))
		if doctype == "Batch AMB":
			return [name for parent in filters["parent_batch_amb"][1] for name in below.get(parent, ())]
		return list({"Batch": batches, "Quality Inspection": rejected, "Non Conformance": ncs}[doctype])

	def has_field(dt, f):
		if dt == "Batch":
			return batch_field
		if dt == "Batch AMB":
			return parent_field
		return nc_field

	fake = types.SimpleNamespace(
		session=frappe._dict(user=user),
		throw=_throw,
		# TASKS-388 (decision 331): a save that makes someone the filler of a signed COA AMB says it cleared the signature
		msgprint=mock.Mock(),
		get_meta=lambda dt: types.SimpleNamespace(has_field=lambda f: has_field(dt, f)),
		get_all=get_all,
		db=types.SimpleNamespace(
			exists=lambda dt, name=None: nc_doctype,
			get_value=mock.Mock(return_value=None),
			set_value=mock.Mock(),
		),
		asked=asked,
	)
	with ExitStack() as stack:
		stack.enter_context(mock.patch.object(rules, "frappe", fake))
		# TASKS-385: the type check now reads the product's Item; on this stand-in site no product is an Item, so no
		# type is judged here (the type has its own tests in test_certificate_links_b2).
		stack.enter_context(mock.patch.object(api, "frappe", fake))
		stack.enter_context(mock.patch.object(rules, "nowdate", lambda: TODAY))
		stack.enter_context(mock.patch.object(frappe, "throw", _throw))
		for module in (rules, amb, amb2):
			stack.enter_context(mock.patch.object(module, "_", lambda s: s))
		yield fake


def save(doc, **kw):
	"""Run what a save runs before the write: `before_validate`, then `validate`. Returns the refusal, or None."""
	with site(**kw):
		try:
			with mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
				doc.before_validate()
			doc.validate()
		except frappe.ValidationError as e:
			return str(e)
	return None


class TestCoaAmbDerivesOnEverySave(unittest.TestCase):
	def test_a_typed_result_does_not_survive_a_draft_save(self):
		d = cert(
			rows=[row("ph", "50"), row("ash", "5")], overall_result="Pass", compliance_status="Compliant"
		)
		self.assertIsNone(save(d, user="filler"))
		self.assertEqual(
			(d.overall_result, d.compliance_status, d.failed_parameters), ("Fail", "Non-Compliant", "ph")
		)
		self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["Fail", "Pass"])

	def test_each_result_is_derived_from_the_rows(self):
		for results, expected in (
			(["5", "6"], ("Pass", "Compliant")),
			(["5", ""], ("Partial", "Under Review")),
			(["50", ""], ("Fail", "Non-Compliant")),
			(["", ""], ("Pending", "Pending")),
		):
			d = cert(
				rows=[row(f"r{i}", r) for i, r in enumerate(results)],
				overall_result="Pass",
				compliance_status="Compliant",
			)
			self.assertIsNone(save(d))
			self.assertEqual((d.overall_result, d.compliance_status), expected, results)

	def test_no_rows_means_no_tests_and_nothing_left_over(self):
		d = cert(
			rows=[],
			overall_result="Pass",
			compliance_status="Compliant",
			failed_parameters="ph",
			pass_percentage=100,
			before=stored("COA AMB", "Draft"),
		)
		self.assertIsNone(save(d))
		self.assertEqual(
			(d.overall_result, d.compliance_status, d.failed_parameters, d.pass_percentage),
			("No Tests", "Pending", "", 0),
		)

	def test_a_row_whose_result_was_taken_away_is_pending_again_and_the_failing_names_are_rewritten(self):
		d = cert(rows=[row("ph", ""), row("ash", "5")], failed_parameters="ph")
		d.coa_quality_test_parameter[0].status = "Fail"
		self.assertIsNone(save(d))
		self.assertEqual(d.coa_quality_test_parameter[0].status, "Pending")
		self.assertEqual((d.overall_result, d.failed_parameters), ("Partial", ""))

	def test_a_failing_numeric_row_can_be_recorded_on_a_draft(self):
		"""`validate_test_parameters` refuses an out-of-range numeric row; it stays a submit-time check."""
		failing = row("ph", "50")
		failing.update(numeric=1, min_value=1, max_value=10)
		d = cert(rows=[failing])
		self.assertIsNone(save(d))
		self.assertEqual(d.overall_result, "Fail")


class TestTheSameLockOnCoaAmb(unittest.TestCase):
	"""The lock of COA AMB2 (#44), by the same functions, over the type's own state field."""

	def approved(self, doctype="COA AMB", **kw):
		rows = [row("r1", "5")]
		before = stored(doctype, "Approved", [row("r1", "5")], approved_by="approver", approval_date=TODAY)
		return cert(doctype, rows=rows, before=before, **kw)

	def test_both_controllers_carry_the_one_lock(self):
		for cls in CLASSES.values():
			self.assertIs(cls.refuse_edit_of_approved, amb2.ApprovedLock.refuse_edit_of_approved)
			self.assertIs(cls.before_rename, amb2.ApprovedLock.before_rename)
			self.assertIs(cls.on_trash, amb2.ApprovedLock.on_trash)
		self.assertEqual(rules.STATE_FIELD, {"COA AMB2": "workflow_state", "COA AMB": "workflow_state_1"})

	def test_an_approved_certificate_cannot_be_saved_by_anyone(self):
		for doctype in BOTH:
			for user in ("filler", "approver", "manager", "Administrator"):
				refusal = save(self.approved(doctype, state="Approved"), user=user)
				self.assertIn("its results cannot be changed", refusal or "", (doctype, user))

	def test_the_lock_reads_no_role_and_no_user(self):
		for fn in (
			amb2.ApprovedLock.refuse_edit_of_approved,
			amb2.refuse_row_of_approved,
			amb2.refuse_taking_rows_of_approved,
			amb2._is_approved_certificate,
		):
			src = inspect.getsource(fn)
			for word in ("Administrator", "get_roles", "session", "has_permission", "ignore_permissions"):
				self.assertNotIn(word, src, fn.__name__)

	def test_the_lock_runs_before_validate_and_in_validate(self):
		calls = []
		d = type(
			"D",
			(),
			{
				"doctype": "COA AMB",
				"docstatus": 0,
				"refuse_edit_of_approved": lambda self: calls.append("lock"),
			},
		)()
		with mock.patch.object(rules, "before_validate", lambda doc: calls.append("rules")):
			amb.COAAMB.before_validate(d)
		self.assertEqual(calls, ["lock", "rules"])
		src = inspect.getsource(amb.COAAMB.validate)
		self.assertLess(src.index("self.refuse_edit_of_approved()"), src.index("self.validate_linked_tds()"))

	def test_reject_to_draft_passes(self):
		for doctype in BOTH:
			self.assertIsNone(save(self.approved(doctype, state="Draft")), doctype)

	def test_the_share_of_a_coa_amb_is_the_workflows_own_submit_and_passes(self):
		d = self.approved(state="Certificate Shared", docstatus=1, _action="submit")
		self.assertIsNone(save(d))
		# the approver and the date it was approved with are still there
		self.assertEqual((d.approved_by, d.approval_date), ("approver", TODAY))

	def test_any_other_submit_of_an_approved_coa_amb_is_refused(self):
		for state in ("Approved", "Draft", "Validated"):
			refusal = save(self.approved(state=state, docstatus=1, _action="submit"))
			self.assertIn("can be submitted only by its workflow", refusal or "", state)

	def test_no_coa_amb2_is_submitted_not_even_to_the_other_types_state(self):
		refusal = save(self.approved("COA AMB2", state="Certificate Shared", docstatus=1, _action="submit"))
		self.assertIn("cannot be submitted", refusal or "")

	def test_the_results_do_not_change_in_the_share(self):
		d = self.approved(state="Certificate Shared", docstatus=1, _action="submit")
		d.coa_quality_test_parameter[0].result = "6"
		self.assertIn("cannot be changed while it is shared", save(d) or "")

	def test_a_coa_amb_is_submitted_from_no_stored_state_but_approved(self):
		"""Review 1: a Draft submitted directly became "Certificate Shared" without any approval."""
		for stored_state in ("Draft", "Validated", "Pending Supervisor", "Auto Approved", "Saved", None):
			# whatever state the caller sends with the submit, the share's own state included
			for sent in ("Certificate Shared", "Approved", stored_state):
				for user in ("filler", "manager", "Administrator"):
					d = cert(
						state=sent,
						docstatus=1,
						_action="submit",
						before=stored("COA AMB", stored_state, [row("r1", "5")]),
					)
					refusal = save(d, user=user)
					self.assertIn("cannot be submitted", refusal or "", (stored_state, sent, user))
					self.assertIn("after another person approved it", refusal)
					self.assertIn(f"its stored state is {stored_state or 'empty'}, not Approved", refusal)

	def test_that_refusal_is_made_in_before_validate_so_a_save_that_skips_validate_meets_it(self):
		d = cert(
			state="Certificate Shared",
			docstatus=1,
			_action="submit",
			before=stored("COA AMB", "Draft", [row("r1", "5")]),
		)
		d.validate = mock.Mock(
			side_effect=AssertionError("a save under ignore_validate does not run validate")
		)
		with site(), mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
			with self.assertRaises(frappe.ValidationError) as refused:
				d.before_validate()
		self.assertIn("cannot be submitted", str(refused.exception))
		src = inspect.getsource(amb.COAAMB.before_validate)
		self.assertLess(
			src.index("certificate_rules.refuse_submit_unless_approved(self)"),
			src.index("self.refuse_edit_of_approved()"),
		)

	def test_a_new_coa_amb_is_never_inserted_as_submitted(self):
		for kw in ({}, {"amended_from": "COA-0"}):
			d = cert(
				state="Certificate Shared",
				docstatus=1,
				new=True,
				_action="submit",
				approved_by="someone",
				filled_by="someone.else",
				**kw,
			)
			refusal = save(d)
			self.assertIn("cannot be submitted: it is new and was never approved", refusal or "", kw)

	def test_the_submit_refusal_reads_no_role_and_no_user_and_has_its_own_message(self):
		src = inspect.getsource(rules.refuse_submit_unless_approved)
		for word in ("Administrator", "get_roles", "session", "has_permission", "ignore_permissions"):
			self.assertNotIn(word, src)
		lock = inspect.getsource(amb2.ApprovedLock.refuse_edit_of_approved)
		self.assertNotIn("after another person approved it", lock)

	def test_a_certificate_that_is_already_submitted_and_a_coa_amb2_are_not_judged_by_it(self):
		with site():
			shared = cert(
				state="Certificate Shared",
				docstatus=1,
				before=stored("COA AMB", "Certificate Shared", [row("r1", "5")], docstatus=1),
			)
			rules.refuse_submit_unless_approved(shared)
			draft = cert(state="Draft", before=stored("COA AMB", "Draft", [row("r1", "5")]))
			rules.refuse_submit_unless_approved(draft)
			# COA AMB2 has its own, wider refusal (decision 129)
			other = cert("COA AMB2", state="Draft", docstatus=1, _action="submit")
			rules.refuse_submit_unless_approved(other)

	def db(self, state="Approved", docstatus=0):
		def get_value(doctype, name, fields, as_dict=False):
			if doctype == "COA AMB" and name == "COA-1":
				return frappe._dict(workflow_state_1=state, docstatus=docstatus)
			if doctype == "COA Quality Test Parameter":
				return frappe._dict(parent="COA-1", parenttype="COA AMB")
			return None

		return mock.Mock(get_value=get_value)

	def refused(self, fn, **kw):
		with site(), mock.patch.object(amb2.frappe, "db", self.db(**kw)):
			try:
				fn()
				return False
			except frappe.ValidationError:
				return True

	def test_a_row_of_an_approved_coa_amb_cannot_be_changed_added_or_removed_by_itself(self):
		r = type(
			"R",
			(),
			{
				"doctype": "COA Quality Test Parameter",
				"get": lambda self, k: {"parenttype": "COA AMB", "parent": "COA-1", "name": "row-1"}.get(k),
				"is_new": lambda self: False,
			},
		)()
		for method in ("before_validate", "on_trash"):
			self.assertTrue(self.refused(lambda: amb2.refuse_row_of_approved(r, method)), method)
			self.assertFalse(
				self.refused(lambda: amb2.refuse_row_of_approved(r, method), state="Draft"), method
			)
			# a shared (submitted) certificate's rows are Frappe's own business, as for COA AMB2
			self.assertFalse(
				self.refused(
					lambda: amb2.refuse_row_of_approved(r, method), state="Certificate Shared", docstatus=1
				),
				method,
			)

	def test_an_approved_coa_amb_is_not_renamed_merged_into_or_deleted(self):
		d = type(
			"D",
			(),
			{
				"doctype": "COA AMB",
				"name": "COA-1",
				"docstatus": 0,
				"get": lambda self, k: "Approved" if k == "workflow_state_1" else None,
			},
		)()
		self.assertTrue(self.refused(lambda: amb.COAAMB.before_rename(d, "COA-1", "COA-X")))
		self.assertTrue(self.refused(lambda: amb.COAAMB.before_rename(d, "COA-2", "COA-1", True)))
		self.assertFalse(self.refused(lambda: amb.COAAMB.before_rename(d, "COA-1", "COA-X"), state="Draft"))
		self.assertTrue(self.refused(lambda: amb.COAAMB.on_trash(d)))
		draft = type(
			"D", (), {"doctype": "COA AMB", "name": "COA-1", "docstatus": 0, "get": lambda self, k: "Draft"}
		)()
		self.assertFalse(self.refused(lambda: amb.COAAMB.on_trash(draft)))


class TestFilledBy(unittest.TestCase):
	def test_a_changed_result_names_the_session_user_on_both_types(self):
		for doctype in BOTH:
			d = cert(
				doctype,
				rows=[row("r1", "6")],
				before=stored(doctype, "Draft", [row("r1", "5")]),
				filled_by="someone.else",
			)
			self.assertIsNone(save(d, user="filler2"))
			self.assertEqual(d.filled_by, "filler2", doctype)

	def test_a_save_that_changes_no_result_keeps_the_stored_name_whatever_the_caller_sends(self):
		for doctype in BOTH:
			d = cert(
				doctype,
				rows=[row("r1", "5")],
				before=stored(doctype, "Draft", [row("r1", " 5 ")]),
				filled_by="typed",
			)
			self.assertIsNone(save(d, user="reviewer"))
			self.assertEqual(d.filled_by, "filler", doctype)

	def test_a_new_row_with_a_result_and_a_removed_row_with_a_result_are_changes(self):
		added = cert(
			rows=[row("r1", "5"), row(None, "7")], before=stored("COA AMB", "Draft", [row("r1", "5")])
		)
		removed = cert(
			rows=[row("r1", "5")], before=stored("COA AMB", "Draft", [row("r1", "5"), row("r2", "7")])
		)
		# Review 2: a row added or removed WITHOUT a result changes the verdict too (Pass becomes Partial, or back)
		empty_added = cert(
			rows=[row("r1", "5"), row(None, "")], before=stored("COA AMB", "Draft", [row("r1", "5")])
		)
		empty_removed = cert(
			rows=[row("r1", "5")], before=stored("COA AMB", "Draft", [row("r1", "5"), row("r2", "")])
		)
		swapped = cert(
			rows=[row("r1", "5"), row("new-row-1", "")],
			before=stored("COA AMB", "Draft", [row("r1", "5"), row("r2", "")]),
		)
		twice = cert(
			rows=[row("r1", "5"), row("r1", "5")],
			before=stored("COA AMB", "Draft", [row("r1", "5"), row("r2", "5")]),
		)
		same = cert(
			rows=[row("r2", ""), row("r1", "5")],
			before=stored("COA AMB", "Draft", [row("r1", "5"), row("r2", "")]),
		)
		cases = (
			("added", added, "u"),
			("removed", removed, "u"),
			("empty added", empty_added, "u"),
			("empty removed", empty_removed, "u"),
			("one removed and one added", swapped, "u"),
			("a name sent twice", twice, "u"),
			("the same rows in another order", same, "filler"),
		)
		for what, d, expected in cases:
			with self.subTest(what):
				self.assertIsNone(save(d, user="u"))
				self.assertEqual(d.filled_by, expected)

	CHANGES = {
		"result": "6",
		"min_value": 2,
		"max_value": 4,
		"specification": "1 - 4",
		"value": "Specification",
		"acceptance_formula": "result < 4",
		"formula_based_criteria": 1,
		"numeric": 1,
		"custom_is_title_row": 1,
		"parameter_name": "another parameter",
	}

	def test_a_change_of_any_field_the_evaluation_reads_is_a_change_of_the_results(self):
		"""Review 2: one case per field, on a save of the certificate."""
		self.assertEqual(set(self.CHANGES), set(rules.EVALUATION_FIELDS))
		for doctype in BOTH:
			for field, value in self.CHANGES.items():
				with self.subTest(doctype=doctype, field=field):
					changed = row("r1", "5")
					changed[field] = value
					d = cert(doctype, rows=[changed], before=stored(doctype, "Draft", [row("r1", "5")]))
					self.assertIsNone(save(d, user="u"))
					self.assertEqual(d.filled_by, "u")

	def test_the_same_row_read_from_the_database_and_sent_by_the_form_is_not_a_change(self):
		in_db = row("r1", "5")
		in_db.update(
			min_value=1.0, max_value=0.0, numeric=1, formula_based_criteria=0, acceptance_formula=None
		)
		sent = row("r1", " 5 ")
		sent.update(
			min_value="1", max_value=None, numeric="1", formula_based_criteria=None, acceptance_formula=""
		)
		sent.update(status="Fail", remarks="a remark", test_method="another method", idx=7)
		d = cert(rows=[sent], before=stored("COA AMB", "Draft", [in_db]))
		self.assertIsNone(save(d, user="u"))
		self.assertEqual(d.filled_by, "filler")

	def test_the_evaluation_reads_no_field_of_a_row_that_is_not_in_the_list(self):
		"""The list is checked against the code: every `param.<field>` / `row.<field>` the two controllers read in
		the functions that judge a row."""
		import re

		judging = (
			"evaluate_overall_result",
			"check_parameter_compliance",
			"_is_header_row",
			"validate_test_parameters",
			"validate_numeric_result",
			"validate_formula_criteria",
			"evaluate_formula_parameters",
			"validate_formula_criteria_for_row",
		)
		written_or_naming = {"status", "get"}
		for cls in CLASSES.values():
			read = set()
			for name in judging:
				src = inspect.getsource(getattr(cls, name))
				read |= set(re.findall(r"\b(?:param|row)\.([a-z_0-9]+)", src))
				read |= set(re.findall(r"\b(?:param|row)\.get\('([a-z_0-9]+)'\)", src))
			self.assertEqual(read - written_or_naming - set(rules.EVALUATION_FIELDS), set(), cls.__name__)
			self.assertLessEqual(
				{"result", "min_value", "max_value", "specification", "acceptance_formula"}, read
			)

	def test_an_approver_who_changes_a_limit_in_the_approving_save_is_the_filler_and_is_refused(self):
		"""Review 2, the case itself: a failing result, the limit moved by the approver, approved as Pass."""
		for field, value in (("max_value", 100), ("specification", "1 - 100"), ("custom_is_title_row", 1)):
			with self.subTest(field=field):
				in_db = row("r1", "50")
				sent = row("r1", "50")
				sent[field] = value
				d = cert(
					state="Approved",
					rows=[sent, row("r2", "5")],
					before=stored("COA AMB", "Pending Supervisor", [in_db, row("r2", "5")]),
				)
				refusal = save(d, user="approver")
				self.assertIn("you entered or changed its results last", refusal or "")
				self.assertEqual(d.overall_result, "Pass")  # what it would have been approved as

	def test_a_new_certificate_is_filled_by_its_maker_only_when_it_carries_results(self):
		with_results = cert(new=True, filled_by="typed")
		without = cert(new=True, rows=[], filled_by="typed")
		# rows without a result are rows added by the maker (Review 2: a row added is a change)
		empty_rows = cert(new=True, rows=[row("r1", "")], filled_by="typed")
		for d in (with_results, without, empty_rows):
			self.assertIsNone(save(d, user="maker"))
		self.assertEqual(
			(with_results.filled_by, without.filled_by, empty_rows.filled_by), ("maker", None, "maker")
		)

	def hook(self, sent, stored_row, method="before_validate", new=False):
		r = type(
			"R",
			(),
			{
				"doctype": "COA Quality Test Parameter",
				"get": lambda self, k: sent.get(k),
				"is_new": lambda self: new,
			},
		)()
		with site(user="u") as fake:
			row_read = frappe._dict(stored_row) if stored_row else None
			# the row's stored fields; the certificate's stored list of fillers (TASKS-390) is empty here
			fake.db.get_value = mock.Mock(
				side_effect=lambda dt, name, fields, *a, **k: None
				if fields == rules.FILLERS_FIELD
				else row_read
			)
			rules.note_filler_of_row(r, method)
		return [c.args for c in fake.db.set_value.call_args_list]

	def test_a_result_row_saved_by_itself_names_the_session_user_on_its_certificate(self):
		in_db = {"parent": "COA-1", "parenttype": "COA AMB2", "result": "5"}
		sent = {"name": "row-1", "parent": "COA-1", "parenttype": "COA AMB2", "result": "6"}
		self.assertEqual(self.hook(sent, in_db), [named("COA AMB2", "COA-1")])
		# unchanged result: nothing is written
		self.assertEqual(self.hook(dict(sent, result="5"), in_db), [])
		# a new row and a deleted row are changes with or without a result (Review 2)
		self.assertEqual(self.hook(dict(sent, result=""), None, new=True), [named("COA AMB2", "COA-1")])
		self.assertEqual(
			self.hook(sent, dict(in_db, result=""), method="on_trash"),
			[named("COA AMB2", "COA-1")],
		)
		# a new row with a result, and a deleted row that had one
		self.assertEqual(
			self.hook(dict(sent, parenttype="COA AMB"), None, new=True),
			[named("COA AMB", "COA-1")],
		)
		self.assertEqual(self.hook(sent, in_db, method="on_trash"), [named("COA AMB2", "COA-1")])
		# a row moved in the same save: both certificates learn of it
		moved = self.hook(dict(sent, parent="COA-2", parenttype="COA AMB"), in_db)
		self.assertEqual(
			moved,
			[named("COA AMB", "COA-2"), named("COA AMB2", "COA-1")],
		)
		# a row of any other parent is not touched
		other = {"parent": "LOTE-1", "parenttype": "Batch AMB", "result": "5"}
		self.assertEqual(self.hook(dict(sent, parent="LOTE-1", parenttype="Batch AMB"), other), [])

	def test_a_row_saved_by_itself_with_any_evaluated_field_changed_names_the_session_user(self):
		"""Review 2, the row saved by itself: one case per field."""
		in_db = {"parent": "COA-1", "parenttype": "COA AMB", "result": "5", "specification": "1 - 10"}
		sent = dict(in_db, name="row-1")
		self.assertEqual(self.hook(dict(sent, remarks="a remark", status="Fail"), in_db), [])
		for field, value in self.CHANGES.items():
			with self.subTest(field=field):
				self.assertEqual(self.hook(dict(sent, **{field: value}), in_db), [named("COA AMB", "COA-1")])

	def test_the_row_hook_reads_every_evaluated_field_of_the_stored_row(self):
		r = type(
			"R",
			(),
			{
				"doctype": "COA Quality Test Parameter",
				"get": lambda self, k: {"name": "row-1"}.get(k),
				"is_new": lambda self: False,
			},
		)()
		with site(user="u") as fake:
			rules.note_filler_of_row(r, "before_validate")
		self.assertEqual(
			fake.db.get_value.call_args_list[0].args[2], ["parent", "parenttype", *rules.EVALUATION_FIELDS]
		)

	def test_the_hook_is_registered_after_the_lock_on_the_result_rows(self):
		import importlib

		hooks = importlib.import_module("amb_w_tds.hooks")
		for event in ("before_validate", "on_trash"):
			self.assertEqual(
				hooks.doc_events["COA Quality Test Parameter"][event][-1],
				"amb_w_tds.certificate_rules.note_filler_of_row",
			)


class TestMayThisBeApproved(unittest.TestCase):
	def approving(self, doctype="COA AMB", rows=None, **kw):
		rows = [row("r1", "5")] if rows is None else rows
		before = stored(
			doctype,
			"Pending Supervisor",
			[row(r.name, r.result) for r in rows],
			filled_by=kw.pop("stored_filler", "filler"),
			**{f: kw[f] for f in SENT_AS_STORED if f in kw},
		)
		return cert(doctype, state="Approved", rows=rows, before=before, **kw)

	def test_a_complete_certificate_is_approved_and_the_server_writes_approver_and_date(self):
		for doctype in BOTH:
			d = self.approving(doctype, approved_by="typed", approval_date="1999-01-01")
			self.assertIsNone(save(d, user="approver"), doctype)
			self.assertEqual((d.approved_by, d.approval_date, d.filled_by), ("approver", TODAY, "filler"))

	def test_fail_and_partial_can_be_approved(self):
		for results, expected in ((["50"], "Fail"), (["5", ""], "Partial")):
			d = self.approving(rows=[row(f"r{i}", r) for i, r in enumerate(results)])
			self.assertIsNone(save(d))
			self.assertEqual(d.overall_result, expected)

	def test_each_refusal_has_its_own_message(self):
		cases = {
			"no specification is linked": dict(linked_tds=None),
			"it has no test rows": dict(rows=[]),
			"only Pass, Fail or Partial can be approved": dict(rows=[row("r1", "")]),
			"it is not recorded who entered its results (it was filled before this was recorded)": dict(
				stored_filler=None
			),
			"another person must approve it": dict(stored_filler="approver"),
		}
		for doctype in BOTH:
			seen = set()
			for text, kw in cases.items():
				refusal = save(self.approving(doctype, **dict(kw)), user="approver")
				self.assertIn(text, refusal or "", (doctype, text))
				self.assertTrue(refusal.startswith(f"{doctype} COA-1 cannot be approved: "), refusal)
				seen.add(refusal)
			self.assertEqual(len(seen), len(cases))

	def test_the_refusal_for_an_unrecorded_filler_says_what_to_do_as_the_code_behaves(self):
		"""Review 4, wording only: a certificate filled before `filled_by` existed. No backfill, no bypass."""
		refusal = save(self.approving(stored_filler=None), user="approver")
		for text in (
			"a save that changes nothing records no one",
			"A person other than the approver must re-enter or confirm a result",
			"the save in which a result changes records who made it",
			"and that person cannot approve it. Then another person approves.",
		):
			self.assertIn(text, refusal or "")
		# TASKS-390 (decision 337): the message no longer teaches the change-and-set-back
		self.assertNotIn("set it back", refusal or "")
		# and that is how the code behaves: an unchanged save records nobody, a changed result records the user
		before = stored("COA AMB", "Pending Supervisor", [row("r1", "5")], filled_by=None)
		unchanged = cert(state="Pending Supervisor", before=before)
		self.assertIsNone(save(unchanged, user="filler"))
		self.assertEqual((unchanged.filled_by, unchanged.fillers_since_draft), (None, None))
		changed = cert(state="Pending Supervisor", rows=[row("r1", "5.1")], before=before)
		self.assertIsNone(save(changed, user="filler"))
		self.assertEqual((changed.filled_by, changed.fillers_since_draft), ("filler", "filler"))
		# the filler who set it back cannot approve; another person can
		before = stored("COA AMB", "Pending Supervisor", [row("r1", "5")], filled_by="filler")
		self.assertIn(
			"another person must approve", save(cert(state="Approved", before=before), user="filler") or ""
		)
		self.assertIsNone(save(cert(state="Approved", before=before), user="approver"))

	def test_no_tests_and_pending_cannot_be_approved(self):
		for doctype in BOTH:
			no_tests = self.approving(doctype, rows=[])
			pending = self.approving(doctype, rows=[row("r1", ""), row("r2", "")])
			titles_only = self.approving(doctype, rows=[row("t", "", title=1)])
			self.assertIn("it has no test rows", save(no_tests) or "")
			self.assertEqual(no_tests.overall_result, "No Tests")
			self.assertIn("its result is Pending", save(pending) or "")
			self.assertEqual(pending.overall_result, "Pending")
			self.assertIn("it has no test rows", save(titles_only) or "")

	def test_the_filler_cannot_approve(self):
		for doctype in BOTH:
			# who filled before
			self.assertIn(
				"another person must approve it", save(self.approving(doctype), user="filler") or ""
			)
			# who changes a result in the very save that approves
			d = self.approving(doctype)
			d.coa_quality_test_parameter[0].result = "6"
			self.assertIn("another person must approve it", save(d, user="approver") or "")
			# no user is exempt
			self.assertIn(
				"another person must approve it",
				save(self.approving(doctype, stored_filler="Administrator"), user="Administrator") or "",
			)

	def test_a_coa_amb_without_signature_or_customers_is_refused_and_a_coa_amb2_is_not_asked(self):
		for kw, text in (
			(dict(autorizacion=None), "it is not signed"),
			(dict(autorizacion=""), "it is not signed"),
			(dict(custom_coa_customers=[]), "its customers list is empty"),
			(dict(custom_coa_customers=None), "its customers list is empty"),
			(dict(custom_coa_customers=[frappe._dict(customer=None)]), "its customers list is empty"),
		):
			self.assertIn(text, save(self.approving("COA AMB", **kw)) or "", kw)
			self.assertIsNone(save(self.approving("COA AMB2", **kw)), kw)

	def test_a_submitted_rejected_inspection_or_an_open_non_conformance_on_the_lots_batches_refuses(self):
		for doctype in BOTH:
			refusal = save(
				self.approving(doctype, batch_reference="LOTE-1"), batches=["B-1"], rejected=["QI-1"]
			)
			self.assertIn("submitted Quality Inspection that is Rejected", refusal or "")
			refusal = save(self.approving(doctype, batch_reference="LOTE-1"), batches=["B-1"], ncs=["NC-1"])
			self.assertIn("Non Conformance that is not closed", refusal or "")
			self.assertIsNone(save(self.approving(doctype, batch_reference="LOTE-1"), batches=["B-1"]))

	def test_what_the_two_reads_ask_for(self):
		d = self.approving(batch_reference="LOTE-1")
		with site(batches=["B-1", "B-2"]) as fake:
			d.validate()
		self.assertEqual(
			fake.asked,
			[
				# TASKS-387: the records below the lot, then the Batches of the lot and of every record below it
				("Batch AMB", {"parent_batch_amb": ["in", ["LOTE-1"]]}),
				("Batch", {"custom_batch_amb": ["in", ["LOTE-1"]]}),
				# only a SUBMITTED inspection whose status is Rejected: a draft, filled or not, is not a failure
				(
					"Quality Inspection",
					{"batch_no": ["in", ["B-1", "B-2"]], "status": "Rejected", "docstatus": 1},
				),
				(
					"Non Conformance",
					{
						"custom_batch_reference": ["in", ["B-1", "B-2"]],
						"status": ["not in", ["Closed", "Resolved", "Cancelled"]],
					},
				),
			],
		)

	def test_a_site_without_the_link_field_or_the_doctype_reads_nothing_there(self):
		d = self.approving(batch_reference="LOTE-1")
		with site(batch_field=False) as fake, self.assertRaises(frappe.ValidationError) as refused:
			d.validate()
		self.assertEqual(fake.asked, [])  # no Batch belongs to a lot on such a site: nothing is read ...
		# ... and the approval is refused (TASKS-390, decision 335: the checks fail closed)
		self.assertIn("on this site Batch has no field custom_batch_amb", str(refused.exception))
		for kw in (dict(nc_doctype=False), dict(nc_field=False)):
			d = self.approving(batch_reference="LOTE-1")
			with site(batches=["B-1"], **kw) as fake:
				d.validate()
			self.assertEqual([a[0] for a in fake.asked], ["Batch AMB", "Batch", "Quality Inspection"], kw)

	def test_a_certificate_with_no_lot_reads_no_batch(self):
		d = self.approving()
		with site() as fake:
			d.validate()
		self.assertEqual(fake.asked, [])

	def test_an_error_of_a_read_is_not_swallowed(self):
		d = self.approving(batch_reference="LOTE-1")
		with site() as fake:
			fake.get_all = mock.Mock(side_effect=RuntimeError("database"))
			with self.assertRaises(RuntimeError):
				d.validate()

	def test_the_check_runs_only_when_the_state_becomes_approved(self):
		incomplete = dict(linked_tds=None, autorizacion=None, custom_coa_customers=[])
		for state in ("Draft", "Validated", "Pending Supervisor"):
			d = cert(state=state, before=stored("COA AMB", "Draft", [row("r1", "5")]), **incomplete)
			self.assertIsNone(save(d, user="filler"), state)
			self.assertEqual((d.approved_by, d.approval_date), (None, None))

	def test_reject_empties_approver_and_date_and_any_other_save_keeps_the_stored_ones(self):
		before = stored("COA AMB", "Approved", [row("r1", "5")], approved_by="approver", approval_date=TODAY)
		d = cert(state="Draft", before=before, approved_by="approver", approval_date=TODAY)
		self.assertIsNone(save(d, user="manager"))
		self.assertEqual((d.approved_by, d.approval_date), (None, None))
		before = stored("COA AMB", "Draft", [row("r1", "5")], approved_by=None, approval_date=None)
		d = cert(before=before, approved_by="typed", approval_date="1999-01-01")
		self.assertIsNone(save(d))
		self.assertEqual((d.approved_by, d.approval_date), (None, None))

	def test_a_new_certificate_that_is_not_becoming_approved_carries_no_approver(self):
		"""Review 1: a Duplicate, an amendment (the form's Amend copies every field) or an insert by API."""
		for doctype in BOTH:
			for kw in ({}, {"amended_from": "COA-0"}):
				for state in ("Draft", "Validated", "Pending Supervisor", "Cancelled"):
					d = cert(
						doctype,
						state=state,
						new=True,
						approved_by="someone",
						approval_date="1999-01-01",
						filled_by="someone.else",
						**kw,
					)
					self.assertIsNone(save(d, user="maker"), (doctype, state))
					self.assertEqual((d.approved_by, d.approval_date), (None, None), (doctype, state, kw))
					self.assertEqual(d.filled_by, "maker")  # the one who inserts the results is their filler

	def test_a_new_certificate_cannot_be_born_approved_amended_or_not(self):
		for doctype in BOTH:
			for kw in ({}, {"amended_from": "COA-0"}):
				with_results = cert(doctype, state="Approved", new=True, approved_by="x", filled_by="y", **kw)
				self.assertIn("another person must approve it", save(with_results, user="maker") or "")
				no_results = cert(
					doctype, state="Approved", new=True, rows=[row("r1", "")], approved_by="x", **kw
				)
				self.assertIn("its result is Pending", save(no_results, user="maker") or "")

	def test_an_amended_certificate_goes_through_approval_again(self):
		"""The amendment of a cancelled COA AMB is a new draft: stored as a draft with no approver and its
		amender as filler, it is approved by another person and only then shared."""
		amended = stored("COA AMB", "Pending Supervisor", [row("r1", "5")], filled_by="amender")
		amended.amended_from = "COA-0"
		for state, docstatus in (("Certificate Shared", 1), ("Approved", 1)):
			d = cert(state=state, docstatus=docstatus, _action="submit", before=amended, amended_from="COA-0")
			self.assertIn("cannot be submitted", save(d, user="amender") or "")
		own = cert(state="Approved", before=amended, amended_from="COA-0")
		self.assertIn("another person must approve it", save(own, user="amender") or "")
		other = cert(state="Approved", before=amended, amended_from="COA-0")
		self.assertIsNone(save(other, user="approver"))
		self.assertEqual((other.approved_by, other.approval_date), ("approver", TODAY))
		approved = stored(
			"COA AMB",
			"Approved",
			[row("r1", "5")],
			filled_by="amender",
			approved_by="approver",
			approval_date=TODAY,
			amended_from="COA-0",
		)
		share = cert(
			state="Certificate Shared", docstatus=1, _action="submit", before=approved, amended_from="COA-0"
		)
		self.assertIsNone(save(share, user="filler"))

	def test_there_is_no_bypass_in_the_rules(self):
		src = inspect.getsource(rules)
		for word in ("Administrator", "get_roles", "ignore_permissions", "flags."):
			self.assertNotIn(word, src.replace("Administrator included", ""), word)


class TestValidateAllTestsSaysItSaved(unittest.TestCase):
	def call(self, module, save_effect=None):
		coa = mock.Mock(overall_result="Pass")
		coa.name = "COA-1"
		coa.save = mock.Mock(side_effect=save_effect)
		coa.get_test_summary = lambda: {"total": 2, "passed": 2, "failed": 0, "pending": 0}
		with (
			mock.patch.object(module.frappe, "get_doc", lambda dt, name: coa),
			mock.patch.object(module, "_", lambda s: s),
			mock.patch.object(module.frappe, "log_error", mock.Mock()) as log_error,
		):
			return module.validate_all_tests("COA-1"), coa, log_error

	def test_it_saves_once_and_says_so(self):
		for module in (amb, amb2):
			out, coa, _log = self.call(module)
			coa.save.assert_called_once_with()
			self.assertIn("was saved", out["message"])
			self.assertEqual(out["saved"], 1)
			self.assertNotIn("error", out)

	def test_a_refused_save_reaches_the_user_as_the_servers_error(self):
		for module in (amb, amb2):
			with self.assertRaises(frappe.ValidationError):
				self.call(module, save_effect=frappe.ValidationError("COA COA-1 is Approved"))
			self.assertNotIn("except", inspect.getsource(module.validate_all_tests))


class TestFormAndFields(unittest.TestCase):
	def fields(self, doctype):
		with open(
			os.path.join(PKG, "amb_w_tds", "doctype", doctype, doctype + ".json"), encoding="utf-8"
		) as f:
			return {d["fieldname"]: d for d in json.load(f)["fields"]}

	def test_approver_date_and_filler_are_read_only_on_both_certificates(self):
		for doctype in ("coa_amb", "coa_amb2"):
			fields = self.fields(doctype)
			for name in ("approved_by", "approval_date", "filled_by"):
				self.assertEqual(fields[name].get("read_only"), 1, (doctype, name))
				# a Duplicate does not carry them (the form's Amend does: the server empties them)
				self.assertEqual(fields[name].get("no_copy"), 1, (doctype, name))
			self.assertEqual(
				(fields["filled_by"]["fieldtype"], fields["filled_by"]["options"]), ("Link", "User")
			)

	def test_no_form_script_sets_the_approver(self):
		for doctype in ("coa_amb", "coa_amb2"):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", doctype, doctype + ".js"), encoding="utf-8"
			) as f:
				text = f.read()
			self.assertNotIn("approval_date: function", text, doctype)
			self.assertNotIn("set_value('approved_by'", text, doctype)


if __name__ == "__main__":
	unittest.main()
