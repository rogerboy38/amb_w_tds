"""TASKS-384 B3 (tds half), DB-free: the lot is released when a certificate becomes Approved and the release is taken
back when it is rejected to Draft or (COA AMB) cancelled after it was shared. The lot itself is written by amb_w_spc;
what is pinned here is WHEN this app calls it, with WHAT, and that nothing is caught around the call.

Also: the raw lot writes of both controllers are gone, and the lot picker offers a record whose status is Inherited."""

import inspect
import re
import types
import unittest
from contextlib import ExitStack, contextmanager
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.api import batch_picker
from amb_w_tds.amb_w_tds.doctype.coa_amb import coa_amb as amb
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2

CLASSES = {"COA AMB": amb.COAAMB, "COA AMB2": amb2.COAAMB2}
BOTH = ("COA AMB", "COA AMB2")
APPROVED_PATH = "amb_w_spc.sfc_manufacturing.lot_quality.certificate_approved"
WITHDRAWN_PATH = "amb_w_spc.sfc_manufacturing.lot_quality.certificate_withdrawn"


# a certificate that stands was approved by one person and filled by another
TWO_PEOPLE = {"approved_by": "approver.b", "filled_by": "filler.a"}


def _throw(msg, *a, **k):
	raise frappe.ValidationError(msg)


def row(name, result):
	return frappe._dict(
		name=name,
		result=result,
		parameter_name=name,
		specification="1 - 10",
		value=None,
		min_value=None,
		max_value=None,
		custom_is_title_row=0,
		status=None,
		formula_based_criteria=0,
		acceptance_formula=None,
		numeric=0,
	)


def cert(
	doctype,
	state,
	before_state,
	results=("5",),
	lot="LOTE-1",
	before_lot="LOTE-1",
	docstatus=0,
	before_docstatus=0,
):
	d = object.__new__(CLASSES[doctype])
	rows = [row(f"r{i}", r) for i, r in enumerate(results)]
	d.__dict__.update(
		doctype=doctype,
		name="COA-1",
		docstatus=docstatus,
		linked_tds="TDS-1",
		batch_reference=lot,
		product_item="ITEM-1",
		work_order=None,
		coa_quality_test_parameter=rows,
		overall_result=None,
		compliance_status=None,
		failed_parameters=None,
		pass_percentage=None,
		tested_percentage=None,
		autorizacion="signature",
		custom_coa_customers=[frappe._dict(name="cust-1", customer="CUST-1")],
		filled_by="filler",
		approved_by=None,
		approval_date=None,
	)
	d.__dict__[rules.STATE_FIELD[doctype]] = state
	stored = frappe._dict(
		doctype=doctype,
		name="COA-1",
		docstatus=before_docstatus,
		batch_reference=before_lot,
		product_item="ITEM-1",
		# TASKS-387: the same specification, customers and signature as sent (the approver drew the signature)
		linked_tds="TDS-1",
		autorizacion="signature",
		signed_by="approver",
		custom_coa_customers=[frappe._dict(name="cust-1", customer="CUST-1")],
		coa_quality_test_parameter=[row(r.name, r.result) for r in rows],
		filled_by="filler",
		approved_by=None,
		approval_date=None,
	)
	stored[rules.STATE_FIELD[doctype]] = before_state
	d._doc_before_save = stored
	for name in ("validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link"):
		setattr(d, name, lambda: None)
	return d


@contextmanager
def site(standing=(), installed=("frappe", "amb_w_tds", "amb_w_spc"), spc=None):
	"""The session, the other certificates of the lot, and amb_w_spc's two functions as `frappe.get_attr` finds them."""
	spc = (
		spc
		if spc is not None
		else {APPROVED_PATH: mock.Mock(name="approved"), WITHDRAWN_PATH: mock.Mock(name="withdrawn")}
	)
	asked = []

	def get_all(doctype, filters=None, fields=None, pluck=None, **kw):
		asked.append((doctype, filters))
		if doctype not in rules.STATE_FIELD:
			return []
		field = rules.STATE_FIELD[doctype]
		return [
			frappe._dict(c)
			for c in standing
			if c["doctype"] == doctype
			and c["state"] == filters[field]
			and c["docstatus"] == filters["docstatus"]
			and c["lot"] == filters["batch_reference"]
			and c["name"] != (filters.get("name") or [None, None])[1]
		]

	def get_attr(path):
		if path not in spc:
			raise AttributeError(path)
		return spc[path]

	fake = types.SimpleNamespace(
		session=frappe._dict(user="approver"),
		throw=_throw,
		msgprint=mock.Mock(),
		get_meta=lambda dt: types.SimpleNamespace(has_field=lambda f: False),
		get_all=get_all,
		get_attr=get_attr,
		get_installed_apps=lambda: list(installed),
		db=types.SimpleNamespace(exists=lambda *a, **k: False, get_value=lambda *a, **k: None),
		asked=asked,
		approved=spc.get(APPROVED_PATH),
		withdrawn=spc.get(WITHDRAWN_PATH),
	)
	with ExitStack() as stack:
		stack.enter_context(mock.patch.object(rules, "frappe", fake))
		stack.enter_context(mock.patch.object(rules, "nowdate", lambda: "2026-11-26"))
		stack.enter_context(mock.patch.object(frappe, "throw", _throw))
		for module in (rules, amb, amb2):
			stack.enter_context(mock.patch.object(module, "_", lambda s: s))
		yield fake


def save(doc, **kw):
	"""A save as the framework runs it for this purpose: `validate`, then (the write) `on_update`."""
	with site(**kw) as fake:
		doc.validate()
		doc.on_update()
	return fake


class TestApprovedReleasesTheLot(unittest.TestCase):
	def test_each_result_on_each_certificate_type_calls_the_writer_with_it(self):
		for doctype in BOTH:
			for results, result in ((("5", "6"), "Pass"), (("50", "6"), "Fail"), (("5", ""), "Partial")):
				fake = save(cert(doctype, "Approved", "Pending Supervisor", results=results))
				fake.approved.assert_called_once_with(doctype, "COA-1", "LOTE-1", result)
				fake.withdrawn.assert_not_called()

	def test_the_result_sent_is_the_one_derived_in_this_save_and_it_always_maps(self):
		d = cert("COA AMB", "Approved", "Pending Supervisor", results=("50",))
		d.overall_result = "Pass"  # typed
		fake = save(d)
		self.assertEqual(fake.approved.call_args.args[3], "Fail")
		self.assertIn(fake.approved.call_args.args[3], rules.RESULT_TO_LOT_STATUS)

	def test_no_other_save_calls_it(self):
		for doctype in BOTH:
			for state, before in (
				("Draft", "Draft"),
				("Validated", "Draft"),
				("Pending Supervisor", "Validated"),
				("Draft", "Pending Supervisor"),
			):
				fake = save(cert(doctype, state, before))
				fake.approved.assert_not_called()
				fake.withdrawn.assert_not_called()

	def test_the_share_of_a_coa_amb_writes_nothing_more(self):
		d = cert("COA AMB", "Certificate Shared", "Approved", docstatus=1)
		d._action = "submit"
		for name in (
			"validate_test_parameters",
			"validate_signature_on_submit",
			"evaluate_formula_parameters",
		):
			setattr(d, name, lambda: None)
		fake = save(d)
		fake.approved.assert_not_called()
		fake.withdrawn.assert_not_called()

	def test_a_certificate_with_no_lot_calls_nothing_and_needs_no_other_app(self):
		for doctype in BOTH:
			fake = save(
				cert(doctype, "Approved", "Pending Supervisor", lot=None, before_lot=None),
				installed=("frappe", "amb_w_tds"),
				spc={},
			)
			self.assertIsNone(fake.approved)

	def test_the_decision_is_taken_in_validate_and_carried_out_once_in_on_update(self):
		d = cert("COA AMB2", "Approved", "Pending Supervisor")
		with site() as fake:
			d.validate()
			fake.approved.assert_not_called()  # nothing is written before the certificate is
			self.assertEqual(d._lot_move, ("approved", "LOTE-1"))
			d.on_update()
			d.on_update()
			fake.approved.assert_called_once()
		# a refused approval decides nothing
		d = cert("COA AMB2", "Approved", "Pending Supervisor", results=("",))
		with site() as fake:
			with self.assertRaises(frappe.ValidationError):
				d.validate()
			d.on_update()
			fake.approved.assert_not_called()


class TestRejectAndCancelWithdraw(unittest.TestCase):
	def test_reject_to_draft_calls_withdraw_on_each_type(self):
		for doctype in BOTH:
			fake = save(cert(doctype, "Draft", "Approved"))
			fake.withdrawn.assert_called_once_with(doctype, "COA-1", "LOTE-1", standing=None)
			fake.approved.assert_not_called()

	def test_the_withdrawal_speaks_of_the_lot_the_certificate_was_approved_for(self):
		fake = save(cert("COA AMB", "Draft", "Approved", lot="LOTE-2", before_lot="LOTE-1"))
		self.assertEqual(fake.withdrawn.call_args.args[2], "LOTE-1")

	def test_another_certificate_that_still_stands_is_named(self):
		others = [
			dict(
				doctype="COA AMB2",
				name="COA2-9",
				state="Approved",
				docstatus=0,
				lot="LOTE-1",
				overall_result="Fail",
				approval_date="2026-11-20",
				modified="2026-11-20 10:00:00",
				**TWO_PEOPLE,
			),
			dict(
				doctype="COA AMB",
				name="COA-9",
				state="Certificate Shared",
				docstatus=1,
				lot="LOTE-1",
				overall_result="Pass",
				approval_date="2026-11-25",
				modified="2026-11-25 10:00:00",
				**TWO_PEOPLE,
			),
		]
		fake = save(cert("COA AMB", "Draft", "Approved"), standing=others)
		# the one approved last
		self.assertEqual(
			fake.withdrawn.call_args.kwargs,
			{"standing": {"doctype": "COA AMB", "name": "COA-9", "result": "Pass"}},
		)
		fake = save(cert("COA AMB", "Draft", "Approved"), standing=others[:1])
		self.assertEqual(
			fake.withdrawn.call_args.kwargs,
			{"standing": {"doctype": "COA AMB2", "name": "COA2-9", "result": "Fail"}},
		)

	def test_what_does_not_stand(self):
		base = dict(
			lot="LOTE-1",
			overall_result="Pass",
			approval_date="2026-11-25",
			modified="2026-11-25 10:00:00",
			**TWO_PEOPLE,
		)
		not_standing = [
			dict(
				base, doctype="COA AMB", name="COA-1", state="Approved", docstatus=0
			),  # the certificate itself
			dict(base, doctype="COA AMB", name="COA-2", state="Draft", docstatus=0),
			dict(base, doctype="COA AMB", name="COA-3", state="Cancelled", docstatus=2),
			dict(
				base, doctype="COA AMB", name="COA-4", state="Certificate Shared", docstatus=2
			),  # cancelled outside the workflow
			dict(
				base, doctype="COA AMB2", name="COA2-5", state="Approved", docstatus=1
			),  # a COA AMB2 submitted before 13.12.15
			dict(
				base, doctype="COA AMB2", name="COA2-6", state="Approved", docstatus=0, lot="LOTE-2"
			),  # another lot
			dict(
				base, doctype="COA AMB", name="COA-7", state="Approved", docstatus=0, overall_result="Pending"
			),  # no mapping
		]
		fake = save(cert("COA AMB", "Draft", "Approved"), standing=not_standing)
		self.assertEqual(fake.withdrawn.call_args.kwargs, {"standing": None})
		# a certificate of the OTHER type with the same name is another certificate
		twin = [dict(base, doctype="COA AMB2", name="COA-1", state="Approved", docstatus=0)]
		fake = save(cert("COA AMB", "Draft", "Approved"), standing=twin)
		self.assertEqual(fake.withdrawn.call_args.kwargs["standing"]["doctype"], "COA AMB2")

	def test_only_a_certificate_approved_by_a_second_person_stands(self):
		"""Review 1: a certificate submitted past the approval was "Certificate Shared" and stood for the lot, so
		one person could turn a Failed lot Passed by rejecting its properly approved certificate."""
		base = dict(
			doctype="COA AMB",
			name="COA-9",
			lot="LOTE-1",
			overall_result="Pass",
			approval_date="2026-11-25",
			modified="2026-11-25 10:00:00",
		)
		people = {
			"no approver": dict(approved_by=None, filled_by="filler.a"),
			"an empty approver": dict(approved_by=" ", filled_by="filler.a"),
			"no filler": dict(approved_by="approver.b", filled_by=None),
			"neither": dict(approved_by=None, filled_by=None),
			"neither field read": {},
			"one person": dict(approved_by="one.person", filled_by="one.person"),
		}
		for state, docstatus in (("Certificate Shared", 1), ("Approved", 0)):
			for what, who in people.items():
				with self.subTest(state=state, what=what):
					other = [dict(base, state=state, docstatus=docstatus, **who)]
					fake = save(cert("COA AMB2", "Draft", "Approved"), standing=other)
					self.assertEqual(fake.withdrawn.call_args.kwargs, {"standing": None})
			with self.subTest(state=state, what="two people"):
				other = [dict(base, state=state, docstatus=docstatus, **TWO_PEOPLE)]
				fake = save(cert("COA AMB2", "Draft", "Approved"), standing=other)
				self.assertEqual(
					fake.withdrawn.call_args.kwargs,
					{"standing": {"doctype": "COA AMB", "name": "COA-9", "result": "Pass"}},
				)
		# an unapproved one does not hide an older one that stands
		others = [
			dict(base, state="Certificate Shared", docstatus=1, approved_by=None, filled_by=None),
			dict(
				base,
				name="COA-8",
				state="Approved",
				docstatus=0,
				overall_result="Fail",
				approval_date="2026-11-01",
				**TWO_PEOPLE,
			),
		]
		fake = save(cert("COA AMB2", "Draft", "Approved"), standing=others)
		self.assertEqual(fake.withdrawn.call_args.kwargs["standing"]["name"], "COA-8")

	def test_the_standing_read_asks_for_approver_and_filler(self):
		with site() as fake:
			fake.get_all = mock.Mock(return_value=[])
			rules.standing_certificate("LOTE-1", "COA AMB", "COA-1")
		for call in fake.get_all.call_args_list:
			self.assertLessEqual({"approved_by", "filled_by", "overall_result"}, set(call.kwargs["fields"]))

	def test_the_reads_for_the_standing_certificate(self):
		fake = save(cert("COA AMB2", "Draft", "Approved"))
		self.assertEqual(
			fake.asked,
			[
				(
					"COA AMB2",
					{
						"batch_reference": "LOTE-1",
						"workflow_state": "Approved",
						"docstatus": 0,
						"name": ["!=", "COA-1"],
					},
				),
				("COA AMB", {"batch_reference": "LOTE-1", "workflow_state_1": "Approved", "docstatus": 0}),
				(
					"COA AMB",
					{"batch_reference": "LOTE-1", "workflow_state_1": "Certificate Shared", "docstatus": 1},
				),
			],
		)

	def cancel(self, lot="LOTE-1", **kw):
		d = cert("COA AMB", "Cancelled", "Certificate Shared", lot=lot, docstatus=2, before_docstatus=1)
		d.revert_product_quality_status = mock.Mock()
		with site(**kw) as fake, mock.patch.object(amb.frappe, "msgprint", mock.Mock()):
			d.on_cancel()
		return d, fake

	def test_the_cancel_of_a_shared_coa_amb_calls_withdraw(self):
		d, fake = self.cancel()
		fake.withdrawn.assert_called_once_with("COA AMB", "COA-1", "LOTE-1", standing=None)
		d.revert_product_quality_status.assert_called_once_with()
		standing = [
			dict(
				doctype="COA AMB2",
				name="COA2-9",
				state="Approved",
				docstatus=0,
				lot="LOTE-1",
				overall_result="Partial",
				approval_date="2026-11-20",
				modified="x",
				**TWO_PEOPLE,
			)
		]
		_d, fake = self.cancel(standing=standing)
		self.assertEqual(
			fake.withdrawn.call_args.kwargs,
			{"standing": {"doctype": "COA AMB2", "name": "COA2-9", "result": "Partial"}},
		)

	def test_a_cancel_without_a_lot_calls_nothing(self):
		_d, fake = self.cancel(lot=None, installed=("frappe", "amb_w_tds"), spc={})
		self.assertIsNone(fake.withdrawn)

	def test_the_cancel_of_an_old_submitted_coa_amb2_does_not_touch_a_lot(self):
		d = cert("COA AMB2", "Approved", "Approved", docstatus=2, before_docstatus=1)
		d.revert_product_quality_status = mock.Mock()
		with site() as fake, mock.patch.object(amb2.frappe, "msgprint", mock.Mock()):
			d.on_cancel()
		fake.withdrawn.assert_not_called()
		self.assertEqual(fake.asked, [])


class TestNothingIsCaught(unittest.TestCase):
	def test_an_error_of_the_writer_leaves_the_save(self):
		for doctype in BOTH:
			spc = {
				APPROVED_PATH: mock.Mock(side_effect=frappe.ValidationError("the lot is on hold")),
				WITHDRAWN_PATH: mock.Mock(side_effect=RuntimeError("database")),
			}
			with self.assertRaises(frappe.ValidationError):
				save(cert(doctype, "Approved", "Pending Supervisor"), spc=spc)
			with self.assertRaises(RuntimeError):
				save(cert(doctype, "Draft", "Approved"), spc=spc)

	def test_there_is_no_try_around_the_calls(self):
		for fn in (
			rules.write_lot,
			rules.withdraw_on_cancel,
			amb.COAAMB.on_update,
			amb2.COAAMB2.on_update,
			amb.COAAMB.on_cancel,
		):
			src = inspect.getsource(fn)
			# a statement, not the word in a docstring
			self.assertIsNone(re.search(r"^\s*(try:|except\b|finally:)", src, re.M), fn.__qualname__)

	def test_without_the_other_app_the_approval_of_a_certificate_with_a_lot_fails_with_a_clear_message(self):
		with self.assertRaises(frappe.ValidationError) as e:
			save(
				cert("COA AMB2", "Approved", "Pending Supervisor"), installed=("frappe", "amb_w_tds"), spc={}
			)
		self.assertIn("which is not installed on this site", str(e.exception))
		# installed, but an older version without the function
		with self.assertRaises(frappe.ValidationError) as e:
			save(cert("COA AMB2", "Approved", "Pending Supervisor"), spc={})
		self.assertIn("is not available in the installed", str(e.exception))

	def test_the_other_app_is_bound_late_and_never_imported_by_this_one(self):
		for module in (rules, amb, amb2):
			src = inspect.getsource(module)
			self.assertNotIn("import amb_w_spc", src)
			self.assertNotIn("from amb_w_spc", src)
		self.assertEqual(f"{rules.SPC_LOT_QUALITY}.certificate_approved", APPROVED_PATH)
		self.assertEqual(f"{rules.SPC_LOT_QUALITY}.certificate_withdrawn", WITHDRAWN_PATH)


class TestRawLotWritesAreGone(unittest.TestCase):
	def test_neither_controller_writes_a_lot_field_or_saves_a_lot(self):
		for module in (amb, amb2, rules):
			src = inspect.getsource(module)
			for gone in (
				"batch.quality_status",
				"batch.save(",
				"batch.coa_reference",
				"COA Cancelled'",
				"def update_batch_status",
				"_batch_link_holds_this_doctype",
			):
				self.assertNotIn(gone, src, (module.__name__, gone))
		for cls in CLASSES.values():
			self.assertFalse(hasattr(cls, "update_batch_status"))

	def test_the_other_three_after_submit_steps_of_coa_amb_are_still_called_in_their_order(self):
		calls = []
		d = object.__new__(amb.COAAMB)
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
			calls,
			[
				"validate_submission_prerequisites",
				"generate_coa_pdf",
				"notify_quality_team",
				"create_quality_audit",
				"update_product_quality_status",
			],
		)


class TestPickerOffersInherited(unittest.TestCase):
	def search(self, own=(), inherited=(), has_field=True, txt="", has_level=False, **kw):
		calls = []

		def get_list(doctype, **q):
			calls.append(q)
			rows = inherited if q["filters"][:2] == batch_picker.inherited_filters() else own
			return [frappe._dict(r) for r in rows][q["start"] : q["start"] + q["page_length"]]

		with (
			mock.patch.object(frappe, "get_list", get_list),
			mock.patch.object(batch_picker, "has_source_field", lambda: has_field),
			mock.patch.object(batch_picker, "has_level_field", lambda: has_level),
		):
			return batch_picker.search_batches("Batch AMB", txt, "name", **kw), calls

	def lot(self, name, creation, status="Pending"):
		return dict(
			name=name, item_to_manufacture="I", quality_status=status, batch_status="Draft", creation=creation
		)

	def test_the_second_set_is_inherited_and_not_cancelled(self):
		self.assertEqual(
			batch_picker.inherited_filters(),
			[
				["Batch AMB", "batch_status", "!=", "Cancelled"],
				["Batch AMB", "status_source", "=", "Inherited"],
			],
		)
		self.assertIn(
			batch_picker.INHERITED,
			rules.RESULT_TO_LOT_STATUS
			and __import__("amb_w_tds.quality_vocabulary", fromlist=["x"]).STATUS_SOURCES,
		)

	def test_a_released_sub_lot_whose_status_is_inherited_is_offered_beside_the_pending_ones(self):
		own = [self.lot("L-3", "2026-11-03"), self.lot("L-1", "2026-11-01")]
		inherited = [self.lot("S-2", "2026-11-02", "Passed"), self.lot("S-0", "2026-10-30", "Failed")]
		out, calls = self.search(own, inherited)
		self.assertEqual([r[0] for r in out], ["L-3", "S-2", "L-1", "S-0"])
		self.assertEqual(out[1], ("S-2", "I", "Passed / Draft"))
		self.assertEqual(
			[c["filters"] for c in calls], [batch_picker.picker_filters(), batch_picker.inherited_filters()]
		)

	def test_a_record_in_both_sets_is_listed_once_and_the_page_is_cut_after_the_merge(self):
		own = [
			self.lot("L-3", "2026-11-03"),
			self.lot("S-2", "2026-11-02", "Hold"),
			self.lot("L-1", "2026-11-01"),
		]
		inherited = [self.lot("S-2", "2026-11-02", "Hold"), self.lot("S-0", "2026-10-30", "Passed")]
		out, calls = self.search(own, inherited, start=1, page_len=2)
		self.assertEqual([r[0] for r in out], ["S-2", "L-1"])
		for c in calls:
			self.assertEqual((c["start"], c["page_length"]), (0, 3))

	def test_the_text_search_goes_to_both_reads(self):
		_out, calls = self.search(txt="abc")
		self.assertEqual(len(calls), 2)
		for c in calls:
			self.assertEqual(
				[f[1] for f in c["or_filters"]],
				["name", "title", "custom_golden_number", "item_to_manufacture"],
			)

	def test_a_site_without_the_field_reads_once_as_before(self):
		out, calls = self.search(
			[self.lot("L-1", "2026-11-01")],
			[self.lot("S-2", "2026-11-02", "Passed")],
			has_field=False,
			start=0,
			page_len=20,
		)
		self.assertEqual([r[0] for r in out], ["L-1"])
		self.assertEqual(len(calls), 1)
		self.assertEqual(
			(calls[0]["filters"], calls[0]["start"], calls[0]["page_length"]),
			(batch_picker.picker_filters(), 0, 20),
		)

	LEVEL = ["Batch AMB", "custom_batch_level", "in", ["1", "2", ""]]

	def test_both_sets_offer_only_a_lot_or_a_sub_lot(self):
		"""Review 6: the Inherited set offered containers. An empty level is a level 1 record: the "" in the list
		makes the framework's `in` read an unset level as empty."""
		self.assertEqual(batch_picker.level_filter(), self.LEVEL)
		_out, calls = self.search(has_level=True)
		self.assertEqual(
			[c["filters"] for c in calls],
			[batch_picker.picker_filters() + [self.LEVEL], batch_picker.inherited_filters() + [self.LEVEL]],
		)
		_out, calls = self.search(has_level=True, has_field=False)
		self.assertEqual([c["filters"] for c in calls], [batch_picker.picker_filters() + [self.LEVEL]])
		self.assertEqual(tuple(self.LEVEL[3][:2]), rules.CERTIFICATE_LEVELS)

	def test_a_site_without_the_level_field_has_no_level_term(self):
		for has_field in (True, False):
			_out, calls = self.search(has_level=False, has_field=has_field)
			for c in calls:
				self.assertNotIn("custom_batch_level", repr(c["filters"]))

	def test_the_level_guard_reads_the_lots_own_field(self):
		meta = mock.Mock(has_field=lambda f: f == "custom_batch_level")
		with mock.patch.object(frappe, "get_meta", lambda dt: meta if dt == "Batch AMB" else None):
			self.assertTrue(batch_picker.has_level_field())
		with mock.patch.object(frappe, "get_meta", lambda dt: mock.Mock(has_field=lambda f: False)):
			self.assertFalse(batch_picker.has_level_field())

	def test_the_guard_reads_the_lots_own_fields(self):
		meta = mock.Mock(has_field=lambda f: f == "status_source")
		with mock.patch.object(frappe, "get_meta", lambda dt: meta if dt == "Batch AMB" else None):
			self.assertTrue(batch_picker.has_source_field())
		with mock.patch.object(frappe, "get_meta", lambda dt: mock.Mock(has_field=lambda f: False)):
			self.assertFalse(batch_picker.has_source_field())


if __name__ == "__main__":
	unittest.main()
