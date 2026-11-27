"""TASKS-391 (tds), DB-free: decisions 340 and 341 on the certificates.

- 340: `fillers_since_draft` keeps every user who changed the results, the customers list, the lot, the product or
  the specification for the certificate's WHOLE life: entering Draft again (Return for correction, the Reject from
  Approved) no longer empties it, so the original filler cannot clear his own name by returning the certificate. An
  amendment is a new certificate and starts its own list (`no_copy`, and a new document never reads a copied value).
  The fieldname is kept; its label and description say "all", and the refusal no longer says "since Draft".
- 341: the share (COA AMB `on_submit`) no longer calls `create_quality_audit` nor `update_product_quality_status`
  (each wrote an Error Log at every share). Both methods stay, for decision 299's task. COA AMB2's `on_submit` drops
  the same two calls; no COA AMB2 is submitted (decision 129, `refuse_submit`), so that changes nothing that runs.

A save is run as the framework runs it before the write (`before_validate`, then `validate`), on documents built
without a database, as in `test_quality_chain_390`."""

import inspect
import json
import os
import unittest
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.doctype.coa_amb import coa_amb as amb
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2
from amb_w_tds.tests.test_certificate_rules_b1 import cert, row, stored
from amb_w_tds.tests.test_coa_amb2_approved_lock import _Sub
from amb_w_tds.tests.test_identity_share_freeze_387 import as_sent, run
from amb_w_tds.tests.test_quality_chain_390 import after, in_review

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOTH = ("COA AMB", "COA AMB2")
A, B, C = "first.a", "second.b", "third.c"
IN_THE_LIST = (
	"you changed its results, customers list, lot, product or specification; "
	"a person who changed none of them must approve it."
)
LAST_FILLER = "you entered or changed its results last"
STATE = rules.STATE_FIELD


def save(doctype, stored_now, user, state=None, **values):
	"""One save as `user`; asserts it is not refused and returns (the document sent, what is stored after it)."""
	d = as_sent(doctype, stored_now, state=state, **values)
	refusal = run(d, user=user)
	if refusal:
		raise AssertionError(f"{user} refused: {refusal}")
	now = after(d, stored_now)
	now.signed_by = d.__dict__.get("signed_by", now.get("signed_by"))
	return d, now


def change_and_set_back(doctype, stored_now, user):
	_d, stored_now = save(doctype, stored_now, user, coa_quality_test_parameter=_rows(stored_now, "7"))
	_d, stored_now = save(doctype, stored_now, user, coa_quality_test_parameter=_rows(stored_now, "5"))
	return stored_now


def _rows(stored_now, first_result):
	rows = [frappe._dict(r) for r in stored_now.coa_quality_test_parameter]
	rows[0].result = first_result
	return rows


def signed_by(doctype, stored_now, user):
	"""`user` draws the signature (COA AMB; COA AMB2 carries none and the save changes nothing)."""
	return save(doctype, stored_now, user, autorizacion=f"drawn by {user}")[1]


class TestTheListIsNeverEmptied(unittest.TestCase):
	"""Decision 340."""

	def test_finding_1_the_filler_returns_it_himself_and_still_cannot_approve(self):
		"""A fills every value, sends it for review, does "Return for correction" himself; B changes a value and sets
		it back (B becomes the last filler); A signs and approves: refused, because A is on the list. C may approve."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				s = stored(doctype, "Draft", [row("r1", ""), row("r2", "")], filled_by=None, signed_by=None)
				s.batch_reference = "LOT-1"
				s[rules.FILLERS_FIELD] = None
				_d, s = save(doctype, s, A, coa_quality_test_parameter=[row("r1", "5"), row("r2", "6")])
				self.assertEqual((s.filled_by, s[rules.FILLERS_FIELD]), (A, A))
				_d, s = save(doctype, s, A, state="Pending Supervisor")
				back, s = save(doctype, s, A, state="Draft")  # A's own "Return for correction"
				self.assertEqual(back.fillers_since_draft, A)  # not emptied
				s = change_and_set_back(doctype, s, B)
				self.assertEqual((s.filled_by, s[rules.FILLERS_FIELD]), (B, f"{A}\n{B}"))
				self.assertEqual([r.result for r in s.coa_quality_test_parameter], ["5", "6"])
				_d, s = save(doctype, s, B, state="Pending Supervisor")
				s = signed_by(doctype, s, A)
				refusal = run(as_sent(doctype, s, state="Approved"), user=A)
				self.assertIn(IN_THE_LIST, refusal or "")
				self.assertNotIn(LAST_FILLER, refusal)  # A is not the last filler: the list alone refuses him
				s = signed_by(doctype, s, C)
				d = as_sent(doctype, s, state="Approved")
				self.assertIsNone(run(d, user=C))
				self.assertEqual((d.approved_by, d.fillers_since_draft), (C, f"{A}\n{B}"))

	def test_a_reject_from_approved_keeps_the_list_and_its_fillers_stay_barred(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				s = in_review(
					doctype, filled_by=B, fillers=f"{A}\n{B}", approved_by=C, approval_date="2026-11-26"
				)
				s[STATE[doctype]] = "Approved"
				s.overall_result = "Pass"
				reject, s = save(doctype, s, C, state="Draft")
				self.assertEqual((reject.fillers_since_draft, reject.filled_by), (f"{A}\n{B}", B))
				_d, s = save(doctype, s, C, state="Pending Supervisor")
				s = signed_by(doctype, s, A)
				self.assertIn(IN_THE_LIST, run(as_sent(doctype, s, state="Approved"), user=A) or "")

	def test_return_for_correction_keeps_the_list_and_adds_nobody(self):
		for doctype in BOTH:
			for user in (A, C):  # a filler, or another reviewer, returns it
				with self.subTest(doctype=doctype, user=user):
					back, _s = save(doctype, in_review(doctype, filled_by=A, fillers=A), user, state="Draft")
					self.assertEqual((back.fillers_since_draft, back.filled_by), (A, A))

	def test_every_way_into_draft_keeps_it(self):
		"""Pending Supervisor, Validated or Approved back to Draft (Return for correction, the Reject, any other)."""
		for doctype in BOTH:
			for from_state in ("Validated", "Pending Supervisor", "Approved"):
				with self.subTest(doctype=doctype, from_state=from_state):
					s = in_review(doctype, filled_by=B, fillers=f"{A}\n{B}")
					s[STATE[doctype]] = from_state
					if from_state == "Approved":
						s.update(approved_by=C, approval_date="2026-11-26", overall_result="Pass")
					d, _s = save(doctype, s, C, state="Draft")
					self.assertEqual(d.fillers_since_draft, f"{A}\n{B}")

	def test_an_amendment_starts_an_empty_list(self):
		"""An Amend copies the fields it may (the form's copy honours `no_copy`; the server's `copy_doc` does not by
		default): whatever it carries, a new certificate starts its list from nothing, with its maker only if the
		maker fills it."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				amended = cert(
					doctype, new=True, amended_from="COA-1", filled_by=A, **{rules.FILLERS_FIELD: f"{A}\n{B}"}
				)
				self.assertIsNone(run(amended, user=C))
				self.assertEqual((amended.filled_by, amended.fillers_since_draft), (C, C))
				empty = cert(doctype, new=True, rows=[], amended_from="COA-1", **{rules.FILLERS_FIELD: A})
				self.assertIsNone(run(empty, user=C))
				self.assertIsNone(empty.fillers_since_draft)

	def test_the_field_keeps_its_name_and_says_all_on_both_certificates(self):
		for folder in ("coa_amb", "coa_amb2"):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", folder, folder + ".json"), encoding="utf-8"
			) as f:
				df = {d["fieldname"]: d for d in json.load(f)["fields"]}[rules.FILLERS_FIELD]
			self.assertEqual(rules.FILLERS_FIELD, "fillers_since_draft")
			self.assertEqual((df["label"], df.get("no_copy"), df.get("read_only")), ("Filled By (all)", 1, 1))
			for said in ("results", "customers list", "lot", "product", "specification", "never emptied"):
				self.assertIn(said, df["description"], (folder, said))
			self.assertNotIn("Draft", df["label"] + df["description"], folder)

	def test_the_refusal_no_longer_says_since_draft(self):
		src = inspect.getsource(rules.refuse_unless_approvable)
		self.assertIn(IN_THE_LIST, src)
		self.assertNotIn("since it last entered Draft", inspect.getsource(rules))
		self.assertFalse(hasattr(rules, "enters_draft"))


class TestTheShareSkipsTheTwoSteps(unittest.TestCase):
	"""Decision 341."""

	def share(self, stub_the_two=True):
		calls = []
		d = object.__new__(amb.COAAMB)
		d.__dict__.update(
			doctype="COA AMB", name="COA-1", batch_reference="LOT-1", product_item="ITEM-1", docstatus=1
		)
		names = ["validate_submission_prerequisites", "generate_coa_pdf"]
		if stub_the_two:
			names += ["create_quality_audit", "update_product_quality_status"]
		for name in names:
			setattr(d, name, lambda _n=name: calls.append(_n))
		shared = mock.Mock(side_effect=lambda *a: calls.append(("certificate_shared", *a)))
		db = mock.Mock()
		with (
			mock.patch.object(rules, "_find_spc", lambda f: (shared, None, None)),
			mock.patch.object(frappe, "log_error") as log_error,
			mock.patch.object(frappe, "get_doc", side_effect=AssertionError("get_doc")) as get_doc,
			mock.patch.object(frappe, "db", db),
		):
			d.on_submit()
		return calls, log_error, get_doc, db

	def test_the_share_calls_neither_in_this_order(self):
		calls, log_error, _get_doc, _db = self.share()
		self.assertEqual(
			calls,
			[
				"validate_submission_prerequisites",
				"generate_coa_pdf",
				("certificate_shared", "COA AMB", "COA-1", "LOT-1"),
			],
		)
		log_error.assert_not_called()

	def test_the_share_writes_no_error_log_with_the_real_methods_in_place(self):
		"""Not stubbed: were either called, it would insert a Quality Audit or write the Item, and log on failure."""
		calls, log_error, get_doc, db = self.share(stub_the_two=False)
		self.assertEqual(len(calls), 3)
		log_error.assert_not_called()
		get_doc.assert_not_called()
		db.set_value.assert_not_called()

	def test_the_two_methods_still_exist_on_both_certificates(self):
		for cls in (amb.COAAMB, amb2.COAAMB2):
			for name in ("create_quality_audit", "update_product_quality_status"):
				self.assertTrue(callable(getattr(cls, name, None)), (cls.__name__, name))
				self.assertIn("log_error", inspect.getsource(getattr(cls, name)))
			self.assertIn("decision 299", inspect.getsource(cls.on_submit))

	def test_coa_amb2_on_submit_drops_the_same_two(self):
		calls = []
		d = object.__new__(amb2.COAAMB2)
		for name in (
			"validate_submission_prerequisites",
			"generate_coa_pdf",
			"notify_quality_team",
			"create_quality_audit",
			"update_product_quality_status",
		):
			setattr(d, name, lambda _n=name: calls.append(_n))
		d.on_submit()
		self.assertEqual(
			calls, ["validate_submission_prerequisites", "generate_coa_pdf", "notify_quality_team"]
		)

	def test_no_coa_amb2_reaches_on_submit(self):
		"""Why dropping them from COA AMB2 changes nothing: `before_validate` and `validate`, which run before
		`on_submit` in every submit, refuse every move from docstatus 0 to 1 (decision 129)."""
		for kw in (dict(action="submit", before_docstatus=0), dict(new=True), dict(before_docstatus=0)):
			with (
				self.subTest(**kw),
				mock.patch.object(amb2, "_", lambda s: s),
				mock.patch.object(amb2.frappe, "throw", side_effect=frappe.ValidationError),
				self.assertRaises(frappe.ValidationError),
			):
				amb2.COAAMB2.refuse_submit(_Sub(docstatus=1, **kw))
		for hook in (amb2.COAAMB2.before_validate, amb2.COAAMB2.validate):
			body = inspect.getsource(hook).split('"""')[-1]
			self.assertTrue(body.strip().startswith("self.refuse_submit()"), hook.__name__)


if __name__ == "__main__":
	unittest.main()
