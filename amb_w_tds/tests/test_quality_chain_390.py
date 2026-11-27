"""TASKS-390 (tds half), DB-free: decisions 334, 335, 337 and 338 on the certificates.

- 334: the share of a COA AMB no longer runs the old `notify_quality_team`; it calls amb_w_spc's
  `certificate_shared(certificate_doctype, certificate, lot)`, looked up late, nothing caught around it.
- 335: the approval checks fail closed: a certificate that names a lot is refused when `Batch` has no
  `custom_batch_amb` field on the site, or when no stock Batch is linked to the lot record or to a record below it.
- 337: every user who changed the results, the customers list or the identity since the certificate last entered
  Draft is kept in `fillers_since_draft`; none of them may approve. Entering Draft again starts a new list.
- 338: every other certificate that stands for the record is passed to amb_w_spc: `others` at the approval, the
  `standing` list at the withdrawal.

A save is run as the framework runs it before the write (`before_validate`, then `validate`), on documents built
without a database, as in the other suites (`test_certificate_rules_b1`, `test_identity_share_freeze_387`)."""

import inspect
import json
import os
import re
import types
import unittest
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.doctype.coa_amb import coa_amb as amb
from amb_w_tds.tests.test_certificate_rules_b1 import cert, row, site, stored
from amb_w_tds.tests.test_identity_share_freeze_387 import as_sent, run

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOTH = ("COA AMB", "COA AMB2")
A, B, C = "first.a", "second.b", "third.c"
NO_BATCH = "no stock Batch is linked to lot record"
NO_FIELD = "on this site Batch has no field custom_batch_amb"
IN_THE_LIST = (
	"you changed its results, customers list, lot, product or specification since it last entered Draft"
)
LAST_FILLER = "you entered or changed its results last"


def in_review(doctype, filled_by=A, fillers=None, lot="LOT-1", **kw):
	"""A certificate in Pending Supervisor, signed by C (who may approve it), with its list of fillers."""
	before = stored(
		doctype,
		"Pending Supervisor",
		[row("r1", "5"), row("r2", "6")],
		filled_by=filled_by,
		batch_reference=lot,
		signed_by=C,
	)
	before[rules.FILLERS_FIELD] = fillers
	before.update(kw)
	return before


def after(d, before):
	"""What the database holds after the save of `d` (the stored document with what the save wrote)."""
	out = frappe._dict(before)
	for k in list(before) + [rules.FILLERS_FIELD, "filled_by", "approved_by", "approval_date"]:
		if k in d.__dict__:
			out[k] = d.__dict__[k]
	out.coa_quality_test_parameter = [frappe._dict(r) for r in d.coa_quality_test_parameter]
	return out


class TestTheChecksFailClosed(unittest.TestCase):
	"""Decision 335."""

	def approve(self, doctype, user=C, **kw):
		return run(as_sent(doctype, in_review(doctype, signed_by=user), state="Approved"), user=user, **kw)

	def test_no_batch_linked_to_the_lot_or_below_it_is_refused_with_its_own_message_for_every_role(self):
		for doctype in BOTH:
			for user in (C, "Administrator"):
				with self.subTest(doctype=doctype, user=user):
					refusal = self.approve(doctype, user=user, batches_of={}, below={"LOT-1": ["SUB-1"]})
					self.assertEqual(
						refusal,
						f"{doctype} COA-1 cannot be approved: no stock Batch is linked to lot record LOT-1 or below it: "
						"the inspection and non-conformance checks cannot be run.",
					)

	def test_a_site_whose_batch_has_no_lot_field_is_refused_with_its_own_message(self):
		for doctype in BOTH:
			d = as_sent(doctype, in_review(doctype), state="Approved")
			with site(user=C, batch_field=False) as fake:
				with self.assertRaises(frappe.ValidationError) as refused:
					d.validate()
			self.assertIn(NO_FIELD, str(refused.exception))
			self.assertIn("so no stock Batch can be linked to lot record LOT-1", str(refused.exception))
			self.assertIn("the inspection and non-conformance checks cannot be run", str(refused.exception))
			self.assertNotIn(NO_BATCH, str(refused.exception))
			self.assertEqual(
				[a for a in fake.asked if a[0] == "Batch"], []
			)  # no read of a field that is not there

	def test_a_linked_tree_passes(self):
		"""A Batch on the record below (amb_w_spc links a Batch to a sub-lot), or on the record itself."""
		for doctype in BOTH:
			for batches_of in ({"SUB-1": ["B-SUB"]}, {"LOT-1": ["B-LOT"]}, {"CONT-1": ["B-CONT"]}):
				with self.subTest(doctype=doctype, batches_of=batches_of):
					d = as_sent(doctype, in_review(doctype), state="Approved")
					refusal = run(
						d, user=C, batches_of=batches_of, below={"LOT-1": ["SUB-1"], "SUB-1": ["CONT-1"]}
					)
					self.assertIsNone(refusal)
					self.assertEqual((d.approved_by, d._lot_move), (C, ("approved", "LOT-1")))

	def test_a_linked_batch_still_runs_the_two_checks(self):
		d = as_sent("COA AMB", in_review("COA AMB"), state="Approved")
		refusal = run(
			d, user=C, batches_of={"SUB-1": ["B-SUB"]}, below={"LOT-1": ["SUB-1"]}, rejected=["QI-1"]
		)
		self.assertIn("submitted Quality Inspection that is Rejected", refusal or "")

	def test_only_the_approval_is_judged_and_a_certificate_without_a_lot_is_not(self):
		"""Narrowest reading: a certificate that names no lot releases none; it reads no Batch, as before."""
		for doctype in BOTH:
			d = as_sent(doctype, in_review(doctype, lot=None), state="Approved")
			self.assertIsNone(run(d, user=C, batches_of={}))
			for state in ("Draft", "Validated", "Pending Supervisor"):
				d = as_sent(doctype, in_review(doctype), state=state)
				self.assertIsNone(run(d, user=C, batches_of={}), (doctype, state))


class TestEveryFillerSinceDraft(unittest.TestCase):
	"""Decision 337."""

	def test_the_change_and_set_back_trick_is_refused(self):
		"""A entered every value. B changes one value, saves, sets it back, saves: B is now the last filler. A may not
		approve all the same, nor may B; C may."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				stored_now = in_review(doctype, filled_by=A, fillers=A)
				changed = as_sent(doctype, stored_now)
				changed.coa_quality_test_parameter[0].result = "7"
				self.assertIsNone(run(changed, user=B))
				stored_now = after(changed, stored_now)
				back = as_sent(doctype, stored_now)
				back.coa_quality_test_parameter[0].result = "5"
				self.assertIsNone(run(back, user=B))
				stored_now = after(back, stored_now)
				self.assertEqual((stored_now.filled_by, stored_now[rules.FILLERS_FIELD]), (B, f"{A}\n{B}"))
				self.assertEqual([r.result for r in stored_now.coa_quality_test_parameter], ["5", "6"])
				# the change cleared the signature (decision 331): C draws it again
				sign = as_sent(doctype, stored_now, autorizacion="drawn by C")
				self.assertIsNone(run(sign, user=C))
				stored_now = after(sign, stored_now)
				stored_now.signed_by = sign.signed_by
				self.assertEqual(stored_now[rules.FILLERS_FIELD], f"{A}\n{B}")  # signing is not filling
				refusal = run(as_sent(doctype, stored_now, state="Approved"), user=A)
				self.assertIn(IN_THE_LIST, refusal or "")
				self.assertIn("a person who changed none of them must approve it", refusal)
				self.assertIn(LAST_FILLER, run(as_sent(doctype, stored_now, state="Approved"), user=B) or "")
				d = as_sent(doctype, stored_now, state="Approved")
				self.assertIsNone(run(d, user=C))
				self.assertEqual(d.approved_by, C)

	def test_two_fillers_and_a_third_who_approves_passes(self):
		for doctype in BOTH:
			stored_now = stored(doctype, "Draft", [row("r1", ""), row("r2", "")], filled_by=None, signed_by=C)
			stored_now.batch_reference = "LOT-1"
			first = as_sent(doctype, stored_now)
			first.coa_quality_test_parameter[0].result = "5"
			self.assertIsNone(run(first, user=A))
			stored_now = after(first, stored_now)
			second = as_sent(doctype, stored_now)
			second.coa_quality_test_parameter[1].result = "6"
			self.assertIsNone(run(second, user=B))
			stored_now = after(second, stored_now)
			self.assertEqual(stored_now[rules.FILLERS_FIELD], f"{A}\n{B}")
			stored_now[rules.STATE_FIELD[doctype]] = "Pending Supervisor"
			stored_now.update(autorizacion="drawn by C", signed_by=C)
			for user in (A, B):
				self.assertIsNotNone(run(as_sent(doctype, stored_now, state="Approved"), user=user), user)
			d = as_sent(doctype, stored_now, state="Approved")
			self.assertIsNone(run(d, user=C), doctype)
			self.assertEqual((d.approved_by, d.filled_by, d.fillers_since_draft), (C, B, f"{A}\n{B}"))

	def test_return_for_correction_starts_a_new_list_without_the_one_who_returns(self):
		for doctype in BOTH:
			stored_now = in_review(doctype, filled_by=B, fillers=f"{A}\n{B}")
			back = as_sent(doctype, stored_now, state="Draft")  # the workflow's "Return for correction"
			self.assertIsNone(run(back, user=C))
			self.assertIsNone(back.fillers_since_draft)
			self.assertEqual(back.filled_by, B)  # the last filler stays as stored
			stored_now = after(back, stored_now)
			# the next change in Draft starts the new list
			fix = as_sent(doctype, stored_now)
			fix.coa_quality_test_parameter[0].result = "5.5"
			self.assertIsNone(run(fix, user=C))
			self.assertEqual((fix.filled_by, fix.fillers_since_draft), (C, C))

	def test_the_reject_from_approved_starts_a_new_list_too(self):
		for doctype in BOTH:
			approved = in_review(
				doctype, filled_by=B, fillers=f"{A}\n{B}", approved_by=C, approval_date="2026-11-26"
			)
			approved[rules.STATE_FIELD[doctype]] = "Approved"
			approved.overall_result = "Pass"
			reject = as_sent(doctype, approved, state="Draft")
			self.assertIsNone(run(reject, user=C), doctype)
			self.assertEqual((reject.fillers_since_draft, reject.filled_by), (None, B))

	def test_a_save_that_stays_in_draft_or_moves_on_keeps_the_list(self):
		for doctype in BOTH:
			for before_state, state in (
				("Draft", "Draft"),
				("Draft", "Validated"),
				("Validated", "Pending Supervisor"),
			):
				before = in_review(doctype, filled_by=B, fillers=f"{A}\n{B}")
				before[rules.STATE_FIELD[doctype]] = before_state
				d = as_sent(doctype, before, state=state)
				self.assertIsNone(run(d, user=C))
				self.assertEqual(d.fillers_since_draft, f"{A}\n{B}", (doctype, state))

	def test_the_list_cannot_be_typed(self):
		for doctype in BOTH:
			for typed in ("", None, A, f"{A}\n{B}\n{C}"):
				d = as_sent(
					doctype,
					in_review(doctype, filled_by=B, fillers=f"{A}\n{B}"),
					**{rules.FILLERS_FIELD: typed},
				)
				self.assertIsNone(run(d, user=C))
				self.assertEqual(d.fillers_since_draft, f"{A}\n{B}", typed)
			# a new certificate (also a Duplicate or an Amend, which copy it) starts with its maker only, if they fill
			d = cert(doctype, new=True, **{rules.FILLERS_FIELD: f"{A}\n{B}"})
			self.assertIsNone(run(d, user=C))
			self.assertEqual(d.fillers_since_draft, C)
			d = cert(doctype, new=True, rows=[], **{rules.FILLERS_FIELD: f"{A}\n{B}"})
			self.assertIsNone(run(d, user=C))
			self.assertIsNone(d.fillers_since_draft)

	def test_each_kind_of_filling_adds_to_the_list(self):
		"""The customers list and the identity (in Draft) as well as the results."""
		before = in_review("COA AMB", filled_by=A, fillers=A)
		before[rules.STATE_FIELD["COA AMB"]] = "Draft"
		for values in (
			dict(custom_coa_customers=[frappe._dict(name="cust-2", customer="CUST-2")]),
			dict(batch_reference="LOT-2"),
			dict(linked_tds="TDS-2"),
		):
			d = as_sent("COA AMB", before, **values)
			self.assertIsNone(run(d, user=B), values)
			self.assertEqual(d.fillers_since_draft, f"{A}\n{B}", values)

	def test_a_certificate_from_before_the_list_counts_its_stored_filler(self):
		"""Narrowest reading: no list stored (a certificate from before 13.12.23) = the stored `filled_by`."""
		for doctype in BOTH:
			stored_now = in_review(doctype, filled_by=A, fillers=None)
			self.assertIn(LAST_FILLER, run(as_sent(doctype, stored_now, state="Approved"), user=A) or "")
			self.assertIsNone(run(as_sent(doctype, stored_now, state="Approved"), user=C))

	def test_the_unrecorded_filler_message_no_longer_teaches_the_trick(self):
		refusal = run(as_sent("COA AMB", in_review("COA AMB", filled_by=None), state="Approved"), user=C)
		self.assertIn("A person other than the approver must re-enter or confirm a result", refusal or "")
		self.assertNotIn("set it back", refusal)
		self.assertNotIn("change it, save", refusal)

	def row_hook(self, hook, row_doctype, sent, stored_row, stored_fillers):
		r = types.SimpleNamespace(doctype=row_doctype, get=lambda k: sent.get(k), is_new=lambda: False)
		with site(user=B) as fake:

			def get_value(doctype, name, fields, as_dict=False):
				if doctype == row_doctype:
					return frappe._dict(stored_row)
				if fields == rules.FILLERS_FIELD:
					return stored_fillers
				if doctype in rules.STATE_FIELD:
					return frappe._dict({rules.STATE_FIELD[doctype]: "Pending Supervisor", "docstatus": 0})
				return None

			fake.db.get_value = get_value
			hook(r, "before_validate")
		return [
			c.args
			for c in fake.db.set_value.call_args_list
			if c.args[2] != {"autorizacion": None, "signed_by": None}
		]

	def test_a_result_row_or_a_customers_row_saved_by_itself_adds_to_the_stored_list(self):
		result_row = {"parent": "COA-1", "parenttype": "COA AMB", "result": "5"}
		customer_row = {
			"name": "cust-1",
			"parent": "COA-1",
			"parenttype": "COA AMB",
			"parentfield": "custom_coa_customers",
			"customer": "CUST-1",
		}
		for hook, row_doctype, in_db, sent in (
			(
				rules.note_filler_of_row,
				"COA Quality Test Parameter",
				result_row,
				dict(result_row, name="r1", result="6"),
			),
			(rules.note_customer_row, "Customer Item", customer_row, dict(customer_row, customer="CUST-2")),
		):
			for stored_fillers, expected in (
				(A, f"{A}\n{B}"),
				(None, B),
				(f"{A}\n{B}", f"{A}\n{B}"),
				("", B),
			):
				with self.subTest(hook=hook.__name__, stored=stored_fillers):
					self.assertEqual(
						self.row_hook(hook, row_doctype, sent, in_db, stored_fillers),
						[("COA AMB", "COA-1", {"filled_by": B, rules.FILLERS_FIELD: expected})],
					)

	def test_the_field_is_on_both_certificates_read_only_and_not_copied(self):
		for folder in ("coa_amb", "coa_amb2"):
			with open(
				os.path.join(PKG, "amb_w_tds", "doctype", folder, folder + ".json"), encoding="utf-8"
			) as f:
				meta = json.load(f)
			fields = {d["fieldname"]: d for d in meta["fields"]}
			df = fields[rules.FILLERS_FIELD]
			self.assertEqual(
				(df["fieldtype"], df.get("read_only"), df.get("no_copy")), ("Small Text", 1, 1), folder
			)
			order = meta["field_order"]
			self.assertEqual(order.index(rules.FILLERS_FIELD), order.index("filled_by") + 1, folder)

	def test_the_share_and_the_reject_do_not_compare_it(self):
		"""It is written from the stored certificate in the share, and emptied in the Reject (`set_filled_by`)."""
		self.assertIn(rules.FILLERS_FIELD, rules.SHARE_DERIVED_FIELDS)


class TestAllStandingCertificatesArePassed(unittest.TestCase):
	"""Decision 338: `others` at the approval, the `standing` list at the withdrawal."""

	STANDING = [
		{"doctype": "COA AMB2", "name": "COA2-9", "result": "Fail"},
		{"doctype": "COA AMB", "name": "COA-8", "result": "Pass"},
	]

	def write(self, kind, standing):
		d = types.SimpleNamespace(
			doctype="COA AMB", name="COA-1", _lot_move=(kind, "LOT-1"), get=lambda k: "Pass"
		)
		calls = {"certificate_approved": mock.Mock(), "certificate_withdrawn": mock.Mock()}
		asked = []

		def standing_certificates(lot, doctype, name):
			asked.append((lot, doctype, name))
			return list(standing)

		with (
			mock.patch.object(rules, "_spc", lambda f: calls[f]),
			mock.patch.object(rules, "standing_certificates", standing_certificates),
		):
			rules.write_lot(d)
		self.assertEqual(asked, [("LOT-1", "COA AMB", "COA-1")])  # excluding the one being judged
		return calls

	def test_the_approval_passes_every_other_standing_certificate_as_others(self):
		for standing in (self.STANDING, []):
			calls = self.write("approved", standing)
			calls["certificate_approved"].assert_called_once_with(
				"COA AMB", "COA-1", "LOT-1", "Pass", others=standing
			)
			calls["certificate_withdrawn"].assert_not_called()

	def test_the_withdrawal_passes_them_as_the_standing_list(self):
		for standing in (self.STANDING, []):
			calls = self.write("withdrawn", standing)
			calls["certificate_withdrawn"].assert_called_once_with(
				"COA AMB", "COA-1", "LOT-1", standing=standing
			)
			calls["certificate_approved"].assert_not_called()

	def test_the_cancel_passes_them_as_the_standing_list(self):
		d = types.SimpleNamespace(doctype="COA AMB", name="COA-1", get=lambda k: "LOT-1")
		withdrawn = mock.Mock()
		with (
			mock.patch.object(rules, "_spc", lambda f: {"certificate_withdrawn": withdrawn}[f]),
			mock.patch.object(rules, "standing_certificates", lambda *a: list(self.STANDING)),
		):
			rules.withdraw_on_cancel(d)
		withdrawn.assert_called_once_with("COA AMB", "COA-1", "LOT-1", standing=self.STANDING)


class TestTheShareMailsLikeARelease(unittest.TestCase):
	"""Decision 334, the tds half: COA AMB's `on_submit` calls amb_w_spc's `certificate_shared`."""

	def doc(self, lot="LOT-1", calls=None):
		d = object.__new__(amb.COAAMB)
		d.__dict__.update(doctype="COA AMB", name="COA-1", batch_reference=lot)
		for name in (
			"validate_submission_prerequisites",
			"generate_coa_pdf",
			"create_quality_audit",
			"update_product_quality_status",
		):
			setattr(d, name, lambda _n=name: calls.append(_n))
		return d

	def test_the_steps_after_the_share_in_their_order_without_the_old_team_mail(self):
		calls = []
		shared = mock.Mock(side_effect=lambda *a: calls.append(("certificate_shared", *a)))
		looked_up = []

		def spc(function):
			looked_up.append(function)
			return shared

		with mock.patch.object(rules, "_spc", spc):
			self.doc(calls=calls).on_submit()
		self.assertEqual(
			calls,
			[
				"validate_submission_prerequisites",
				"generate_coa_pdf",
				("certificate_shared", "COA AMB", "COA-1", "LOT-1"),
				"create_quality_audit",
				"update_product_quality_status",
			],
		)
		self.assertEqual(looked_up, ["certificate_shared"])  # looked up late, at the call

	def test_the_old_notify_quality_team_is_deleted_from_coa_amb(self):
		self.assertFalse(hasattr(amb.COAAMB, "notify_quality_team"))
		src = inspect.getsource(amb)
		for gone in ("notify_quality_team()", "now=True", "Quality Inspector", "COA AMB - Notification"):
			self.assertNotIn(gone, src, gone)

	def test_a_certificate_without_a_lot_looks_nothing_up(self):
		calls = []
		with mock.patch.object(rules, "_spc", mock.Mock(side_effect=AssertionError("looked up"))):
			self.doc(lot=None, calls=calls).on_submit()
		self.assertEqual(len(calls), 4)

	def test_nothing_is_caught_around_the_call(self):
		calls = []
		with (
			mock.patch.object(rules, "_spc", lambda f: mock.Mock(side_effect=RuntimeError("database"))),
			self.assertRaises(RuntimeError),
		):
			self.doc(calls=calls).on_submit()
		for fn in (rules.share_summary, amb.COAAMB.on_submit):
			self.assertIsNone(re.search(r"^\s*(try:|except\b|finally:)", inspect.getsource(fn), re.M), fn)

	def test_the_lookup_is_the_one_of_the_two_lot_writes(self):
		"""The same late binding and absence handling: without amb_w_spc, or a version of it without the function,
		the share is refused with the message that says so."""
		d = self.doc(calls=[])
		for installed, get_attr, text in (
			(["frappe", "amb_w_tds"], None, "which is not installed on this site"),
			(
				["frappe", "amb_w_tds", "amb_w_spc"],
				AttributeError("certificate_shared"),
				"is not available in the installed",
			),
		):
			fake = types.SimpleNamespace(
				get_installed_apps=lambda installed=installed: installed,
				get_attr=mock.Mock(side_effect=get_attr),
				throw=lambda msg, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(msg)),
			)
			with (
				mock.patch.object(rules, "frappe", fake),
				mock.patch.object(rules, "_", lambda s: s),
				self.assertRaises(frappe.ValidationError) as refused,
			):
				d.on_submit()
			self.assertIn(text, str(refused.exception))
			self.assertIn(f"{rules.SPC_LOT_QUALITY}.certificate_shared", str(refused.exception))


if __name__ == "__main__":
	unittest.main()
