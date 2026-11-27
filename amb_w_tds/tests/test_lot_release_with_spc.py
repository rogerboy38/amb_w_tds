"""TASKS-384 B3/B4, the two apps together, DB-free: this app's REAL path from a certificate's save to the lot
(`validate` -> `note_lot_move`, `on_update` -> `write_lot` -> `_spc` -> the call) against amb_w_spc's REAL
`certificate_approved` and `certificate_withdrawn`, over a lot table held in memory.

Each app's own tests stop at the border: this app's pin WHEN it calls the other and with WHAT, against a mock;
amb_w_spc's pin what its functions do when called by hand. Nothing there fails when the two disagree (an argument's
name or order, the shape of `standing`, a result the other side does not map). This file does.

What is real: both controllers' `validate` and `on_update`, `certificate_rules` whole (the standing certificate is
found by its real function, from the certificates this test keeps), and amb_w_spc's `lot_quality` whole except its
data-access seam `LotTable`, replaced by `Table` below the way amb_w_spc's own tests replace it. What is not: the
database, and `frappe.get_attr`, which needs a site to list the installed apps and is stood in for by the import it
performs.

TASKS-390: the lot records' stock Batches are kept too (a Batch on the sub-lot and on the container, as amb_w_spc's
projection links them): without one an approval is refused here (decision 335). The calls carry `others` at the
approval and a `standing` LIST at the withdrawal (decision 338), and the share of a COA AMB calls amb_w_spc's
`certificate_shared` (decision 334).

Skipped when amb_w_spc cannot be imported, or when its `lot_quality` is older than TASKS-390 (no `others` keyword, no
`certificate_shared`): this app's calls of 13.12.23 do not fit it. Run with both apps on the path:
PYTHONPATH=<amb_w_tds clone>:<amb_w_spc clone> python -m unittest amb_w_tds.tests.test_lot_release_with_spc

Mail (TASKS-390 review, finding 4). amb_w_spc's frappe is a mock here, and `Site.running` sets its
`are_emails_muted()` to True: EVERY approval, Reject and share below runs the MUTED path of amb_w_spc's summary
(`_send_summary` returns before `sendmail`), on purpose, not by a truthy mock. None of those tests claims that mail
was sent. They are: every test of TestCertificateToLotThroughBothApps, TestTheRejectChangesOnlyTheStateThroughBothApps
and TestTheWorstResultWinsThroughBothApps, and in TestTheShareThroughBothApps
`test_the_share_writes_no_lot_status_and_no_row_of_its_own` and `test_muted_mail_is_not_queued_and_is_noted`
(muted is what that one tests). The ONE test that runs unmuted is `test_no_team_mail_at_the_share`: it answers
amb_w_spc's reads (the certificate, the lot record's Work Order, its owner, the three users) and asserts exactly one
`sendmail`, its recipients, and that this app's frappe neither reads "Has Role" nor sends."""

import copy
import importlib
import inspect
import types
import unittest
from contextlib import ExitStack, contextmanager
from unittest import mock

import frappe

from amb_w_tds import certificate_rules as rules
from amb_w_tds.amb_w_tds.doctype.coa_amb import coa_amb as amb
from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as amb2

try:
	from amb_w_spc.sfc_manufacturing import lot_quality as lq
except ImportError:  # the other app is not on the path: every test below is skipped
	lq = None

# TASKS-390: the interface this app's 13.12.23 calls (contract points 1 and 2)
SPC_OF_390 = bool(
	lq is not None
	and "others" in inspect.signature(lq.certificate_approved).parameters
	and callable(getattr(lq, "certificate_shared", None))
)
SKIP_REASON = (
	"amb_w_spc is not importable here"
	if lq is None
	else "amb_w_spc's lot_quality predates TASKS-390 (no `others` keyword in certificate_approved, or no "
	"certificate_shared): run against the spc head that has them"
)
# the records that hold stock (a native Batch names them in `custom_batch_amb`)
STOCKED = ("SUB", "CONT")

CLASSES = {"COA AMB": amb.COAAMB, "COA AMB2": amb2.COAAMB2}
BOTH = ("COA AMB", "COA AMB2")
FILLER, APPROVER = "filler.a", "approver.b"
TODAY = "2026-11-26"
PENDING = ("Pending", "", None, None)


def _throw(msg, *a, **k):
	raise frappe.ValidationError(msg)


class Table:
	"""The lot table in memory, behind amb_w_spc's seam: what `lot_quality` asks of `LotTable`."""

	def __init__(self):
		self.rows = {}
		self.history = []

	def add(self, name, level, parent=None):
		self.rows[name] = dict.fromkeys(lq.RECORD_FIELDS)
		self.rows[name].update(name=name, custom_batch_level=level, parent_batch_amb=parent)
		self.rows[name]["quality_status"] = "Pending"
		return self

	def get(self, name):
		return dict(self.rows[name]) if name in self.rows else None

	def children(self, names):
		names = list(names)
		return [dict(r) for _name, r in sorted(self.rows.items()) if r["parent_batch_amb"] in names]

	def released_by(self, certificate_doctype, certificate):
		this = (certificate_doctype, certificate)
		return [
			dict(r)
			for _name, r in sorted(self.rows.items())
			if (r.get("released_by_doctype"), r.get("released_by")) == this
		]

	def write_columns(self, names, values):
		assert set(values) <= set(lq.GUARDED_FIELDS), values
		for name in names:
			self.rows[name].update(values)

	def save(self, name, values, reason=None, note=None, always=False):
		before = {f: self.rows[name].get(f) for f in (*lq.GUARDED_FIELDS, *values)}
		after = dict(before, **values)
		same = all(self._text(f, before[f]) == self._text(f, after[f]) for f in before)
		if same and not always:
			return False
		self.rows[name].update(values)
		self.history.append((name, reason))
		return True

	@staticmethod
	def _text(fieldname, value):
		return value or ("Pending" if fieldname == "quality_status" else "")

	def state(self, name):
		r = self.rows[name]
		return (
			r["quality_status"] or "Pending",
			r["status_source"] or "",
			r["released_by_doctype"],
			r["released_by"],
		)


def lot_tree():
	"""A lot, a sub-lot under it and a container under the sub-lot."""
	return Table().add("LOT", "1").add("SUB", "2", "LOT").add("CONT", "3", "SUB")


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


RESULTS = {"Pass": ("5", "6"), "Fail": ("50", "6"), "Partial": ("5", "")}
STATUS = {"Pass": "Passed", "Fail": "Failed", "Partial": "Hold"}


class Site:
	"""The certificates this test keeps (what the database would hold), the lot table, and one save at a time."""

	def __init__(self, table, stocked=STOCKED):
		self.table = table
		self.stocked = set(stocked)
		self.certificates = {}  # (doctype, name) -> what is stored

	def _stored(self, doctype, name, lot, result):
		key = (doctype, name)
		if key not in self.certificates:
			d = frappe._dict(
				doctype=doctype,
				name=name,
				docstatus=0,
				batch_reference=lot,
				product_item="ITEM-1",
				# TASKS-387: what `move` sends; the approver drew the signature (`signed_by`)
				linked_tds="TDS-1",
				autorizacion="signature",
				signed_by=APPROVER,
				custom_coa_customers=[frappe._dict(name="cust-1", customer="CUSTOMER-1")],
				coa_quality_test_parameter=[row(f"r{i}", r) for i, r in enumerate(RESULTS[result])],
				filled_by=FILLER,
				approved_by=None,
				approval_date=None,
				overall_result=None,
				modified=f"{TODAY} 10:00:00",
			)
			d[rules.STATE_FIELD[doctype]] = "Pending Supervisor"
			self.certificates[key] = d
		return self.certificates[key]

	def get_all(self, doctype, filters=None, fields=None, pluck=None, **kw):
		"""The standing-certificate read of `certificate_rules`, answered from the certificates kept here; the
		records below a lot record and the stock Batches of the records (TASKS-390)."""
		if doctype == rules.LOT_DOCTYPE:
			return [r["name"] for r in self.table.children(filters[rules.LOT_PARENT_FIELD][1])]
		if doctype == "Batch":
			return [f"B-{n}" for n in filters[rules.BATCH_LOT_FIELD][1] if n in self.stocked]
		if doctype not in rules.STATE_FIELD:
			return []  # the lot's inspections, non conformances: none
		out = []
		for (certificate_doctype, name), d in sorted(self.certificates.items()):
			if certificate_doctype != doctype:
				continue
			wanted = dict(filters)
			unlike = wanted.pop("name", None)
			if unlike and name == unlike[1]:
				continue
			if all(d.get(k) == v for k, v in wanted.items()):
				out.append(frappe._dict({f: d.get(f) for f in fields}))
		return out

	def lot_value(self, doctype, name, fields, as_dict=False):
		record = self.table.get(name) or {}
		if isinstance(fields, str):
			return record.get(fields)
		return frappe._dict({f: record.get(f) for f in fields}) if record else None

	@contextmanager
	def running(self, user):
		def get_attr(path):
			module, function = path.rsplit(".", 1)
			return getattr(importlib.import_module(module), function)

		tds = types.SimpleNamespace(
			session=frappe._dict(user=user),
			throw=_throw,
			msgprint=mock.Mock(),
			get_meta=lambda dt: types.SimpleNamespace(has_field=lambda f: dt in (rules.LOT_DOCTYPE, "Batch")),
			get_all=self.get_all,
			get_attr=get_attr,
			get_installed_apps=lambda: ["frappe", "amb_w_tds", "amb_w_spc"],
			db=types.SimpleNamespace(exists=lambda *a, **k: False, get_value=self.lot_value),
			sendmail=mock.Mock(name="tds sendmail"),
		)
		spc = mock.MagicMock(name="frappe")
		spc.throw.side_effect = _throw
		spc.ValidationError = frappe.ValidationError
		spc.session.user = user
		spc.are_emails_muted.return_value = True  # the muted path, said, not a truthy mock (see the top)
		self.tds, self.spc = tds, spc
		with ExitStack() as stack:
			stack.enter_context(mock.patch.object(rules, "frappe", tds))
			stack.enter_context(mock.patch.object(rules, "nowdate", lambda: TODAY))
			stack.enter_context(mock.patch.object(frappe, "throw", _throw))
			for module in (rules, amb, amb2, lq):
				stack.enter_context(mock.patch.object(module, "_", lambda s: s))
			stack.enter_context(mock.patch.object(lq, "frappe", spc))
			stack.enter_context(mock.patch.object(lq, "LotTable", lambda: self.table))
			yield

	def move(self, doctype, name, lot, to_state, result="Pass", user=APPROVER):
		"""One save of the certificate that takes it to `to_state`, as the framework runs it: `validate`, the
		write (kept here only when nothing refused), `on_update`."""
		before = self._stored(doctype, name, lot, result)
		d = object.__new__(CLASSES[doctype])
		d.__dict__.update({k: v for k, v in before.items() if k != "coa_quality_test_parameter"})
		d.__dict__.update(
			coa_quality_test_parameter=[frappe._dict(r) for r in before.coa_quality_test_parameter],
			custom_coa_customers=[frappe._dict(r) for r in before.custom_coa_customers],
			work_order=None,
			compliance_status=None,
			failed_parameters=None,
			pass_percentage=None,
			tested_percentage=None,
		)
		d.__dict__[rules.STATE_FIELD[doctype]] = to_state
		d._doc_before_save = before
		for check in ("validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link"):
			setattr(d, check, lambda: None)  # the three checks that read the database
		with self.running(user):
			d.validate()
			after = frappe._dict(before)
			after.update({k: d.__dict__.get(k) for k in before if k != "coa_quality_test_parameter"})
			d.on_update()
		self.certificates[(doctype, name)] = after
		return d

	def approve(self, doctype, name, lot, result="Pass", user=APPROVER):
		return self.move(doctype, name, lot, "Approved", result, user)

	def reject(self, doctype, name, lot, user=APPROVER):
		return self.move(doctype, name, lot, "Draft", user=user)


@unittest.skipUnless(SPC_OF_390, SKIP_REASON)
class TestCertificateToLotThroughBothApps(unittest.TestCase):
	def test_an_approval_writes_the_lot_its_sub_lot_and_its_container(self):
		for doctype in BOTH:
			for result, status in STATUS.items():
				with self.subTest(doctype=doctype, result=result):
					site = Site(lot_tree())
					d = site.approve(doctype, "CERT-1", "LOT", result)
					self.assertEqual(
						(d.overall_result, d.approved_by, d.filled_by), (result, APPROVER, FILLER)
					)
					self.assertEqual(site.table.state("LOT"), (status, "Own certificate", doctype, "CERT-1"))
					for below in ("SUB", "CONT"):
						self.assertEqual(
							site.table.state(below), (status, "Inherited", doctype, "CERT-1"), below
						)

	def test_a_sub_lots_own_certificate_writes_the_sub_lot_and_its_container_only(self):
		site = Site(lot_tree())
		site.approve("COA AMB2", "CERT-S", "SUB", "Fail")
		self.assertEqual(site.table.state("LOT"), PENDING)
		self.assertEqual(site.table.state("SUB"), ("Failed", "Own certificate", "COA AMB2", "CERT-S"))
		self.assertEqual(site.table.state("CONT"), ("Failed", "Inherited", "COA AMB2", "CERT-S"))

	def test_a_reject_returns_all_three_to_pending(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				site = Site(lot_tree())
				site.approve(doctype, "CERT-1", "LOT", "Pass")
				d = site.reject(doctype, "CERT-1", "LOT")
				self.assertEqual((d.approved_by, d.approval_date), (None, None))
				for name in ("LOT", "SUB", "CONT"):
					self.assertEqual(site.table.state(name), PENDING, name)

	def test_a_reject_with_a_certificate_that_still_stands_gives_the_lot_that_ones_status(self):
		site = Site(lot_tree())
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		site.approve("COA AMB", "CERT-PASS", "LOT", "Pass")
		# TASKS-390 (decision 338): the standing Fail is worse, so the record keeps it at the approval of the Pass
		self.assertEqual(site.table.state("LOT"), ("Failed", "Own certificate", "COA AMB2", "CERT-FAIL"))
		site.reject("COA AMB", "CERT-PASS", "LOT")
		self.assertEqual(site.table.state("LOT"), ("Failed", "Own certificate", "COA AMB2", "CERT-FAIL"))
		for below in ("SUB", "CONT"):
			self.assertEqual(site.table.state(below), ("Failed", "Inherited", "COA AMB2", "CERT-FAIL"), below)

	def test_a_certificate_that_no_second_person_approved_does_not_stand_in_for_a_rejected_one(self):
		"""Review 1, end to end: the lot is Failed by a properly approved certificate; another certificate of the
		lot sits in "Certificate Shared" without an approver (submitted past the approval, as was possible).
		Rejecting the first must not turn the lot Passed."""
		site = Site(lot_tree())
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		unapproved = site._stored("COA AMB", "CERT-DIRECT", "LOT", "Pass")
		unapproved.update(
			docstatus=1,
			workflow_state_1="Certificate Shared",
			overall_result="Pass",
			approval_date=TODAY,
			approved_by=None,
		)
		site.reject("COA AMB2", "CERT-FAIL", "LOT")
		for name in ("LOT", "SUB", "CONT"):
			self.assertEqual(site.table.state(name), PENDING, name)
		# the same certificate with the record of two people does stand: the difference is that record only
		site = Site(lot_tree())
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		approved = site._stored("COA AMB", "CERT-SHARED", "LOT", "Pass")
		approved.update(
			docstatus=1,
			workflow_state_1="Certificate Shared",
			overall_result="Pass",
			approval_date=TODAY,
			approved_by=APPROVER,
		)
		site.reject("COA AMB2", "CERT-FAIL", "LOT")
		self.assertEqual(site.table.state("LOT"), ("Passed", "Own certificate", "COA AMB", "CERT-SHARED"))

	def test_the_other_apps_refusal_leaves_the_save_and_nothing_is_written(self):
		"""A certificate that already names a container (made before the level was checked here): amb_w_spc
		refuses at approval and this app catches nothing."""
		site = Site(lot_tree())
		with self.assertRaises(frappe.ValidationError) as refused:
			site.approve("COA AMB2", "CERT-C", "CONT", "Pass")
		self.assertIn("level 3", str(refused.exception))
		for name in ("LOT", "SUB", "CONT"):
			self.assertEqual(site.table.state(name), PENDING, name)
		self.assertEqual(site.table.history, [])

	def test_the_filler_cannot_release_a_lot(self):
		site = Site(lot_tree())
		with self.assertRaises(frappe.ValidationError):
			site.approve("COA AMB2", "CERT-1", "LOT", "Pass", user=FILLER)
		self.assertEqual(site.table.state("LOT"), PENDING)

	def test_a_return_for_correction_writes_no_lot_record(self):
		"""TASKS-387 (decision 321): Pending Supervisor -> Draft releases nothing and takes nothing back."""
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				site = Site(lot_tree())
				site.move(doctype, "CERT-1", "LOT", "Draft", user=FILLER)
				for name in ("LOT", "SUB", "CONT"):
					self.assertEqual(site.table.state(name), PENDING, name)
				self.assertEqual(site.table.history, [])

	def test_an_approver_who_did_not_sign_releases_nothing_and_the_one_who_signed_does(self):
		"""TASKS-387 (decision 321): COA AMB's signature is the approver's own."""
		site = Site(lot_tree())
		site._stored("COA AMB", "CERT-1", "LOT", "Pass").update(signed_by=FILLER)
		with self.assertRaises(frappe.ValidationError) as refused:
			site.approve("COA AMB", "CERT-1", "LOT", "Pass")
		self.assertIn("Sign it yourself as approver", str(refused.exception))
		self.assertEqual(site.table.history, [])
		self.assertEqual(site.table.state("LOT"), PENDING)
		site.certificates[("COA AMB", "CERT-1")].update(signed_by=APPROVER)
		site.approve("COA AMB", "CERT-1", "LOT", "Pass")
		self.assertEqual(site.table.state("LOT"), ("Passed", "Own certificate", "COA AMB", "CERT-1"))

	def test_the_table_of_this_test_answers_everything_the_seam_offers(self):
		"""If amb_w_spc's seam grows a method, the table above must grow it too, or the tests above would run
		that method against the mock and pass for nothing."""
		seam = {n for n, _f in inspect.getmembers(lq.LotTable, inspect.isfunction) if not n.startswith("_")}
		mine = {n for n, _f in inspect.getmembers(Table, inspect.isfunction) if not n.startswith("_")}
		self.assertEqual(seam - mine, set())

	def test_this_app_and_the_other_name_the_same_three_functions(self):
		for function in ("certificate_approved", "certificate_withdrawn", "certificate_shared"):
			self.assertTrue(callable(getattr(lq, function)))
		self.assertEqual(rules.SPC_LOT_QUALITY, lq.__name__)
		self.assertIn("standing", inspect.signature(lq.certificate_withdrawn).parameters)
		self.assertIn("others", inspect.signature(lq.certificate_approved).parameters)
		self.assertEqual(
			list(inspect.signature(lq.certificate_shared).parameters),
			["certificate_doctype", "certificate", "lot"],
		)

	def test_an_approval_of_a_lot_with_no_stock_batch_is_refused_and_writes_nothing(self):
		"""TASKS-390 (decision 335): no Batch on the record or below it; the checks cannot run."""
		site = Site(lot_tree(), stocked=())
		with self.assertRaises(frappe.ValidationError) as refused:
			site.approve("COA AMB2", "CERT-1", "LOT", "Pass")
		self.assertIn("no stock Batch is linked to lot record LOT or below it", str(refused.exception))
		self.assertEqual(site.table.history, [])
		self.assertEqual(site.table.state("LOT"), PENDING)


class FullSite(Site):
	"""TASKS-388 (decision 332): the same site, with `before_validate` run before `validate` (as the framework runs
	it) and values the caller sends with the state. The workflow of each certificate is not read here (no Workflow)."""

	def lot_value(self, doctype, name, fields, as_dict=False):
		if doctype == "Workflow":
			return None
		return super().lot_value(doctype, name, fields, as_dict)

	def reject_with(self, doctype, name, lot, user=APPROVER, **values):
		before = self._stored(doctype, name, lot, "Pass")
		d = object.__new__(CLASSES[doctype])
		d.__dict__.update({k: copy.deepcopy(v) for k, v in before.items()})
		d.__dict__.update(values)
		d.__dict__[rules.STATE_FIELD[doctype]] = "Draft"
		d._doc_before_save = before
		for check in ("validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link"):
			setattr(d, check, lambda: None)
		with self.running(user), mock.patch.object(amb2, "refuse_taking_rows_of_approved", lambda d: None):
			d.before_validate()
			d.validate()
			d.on_update()
		after = frappe._dict(before)
		after.update({k: d.__dict__.get(k) for k in before})
		self.certificates[(doctype, name)] = after
		return d


@unittest.skipUnless(SPC_OF_390, SKIP_REASON)
class TestTheRejectChangesOnlyTheStateThroughBothApps(unittest.TestCase):
	def test_the_workflows_reject_withdraws_the_lot_as_before(self):
		for doctype in BOTH:
			with self.subTest(doctype=doctype):
				site = FullSite(lot_tree())
				site.approve(doctype, "CERT-1", "LOT", "Pass")
				self.assertEqual(site.table.state("LOT"), ("Passed", "Own certificate", doctype, "CERT-1"))
				d = site.reject_with(doctype, "CERT-1", "LOT")
				self.assertEqual((d.approved_by, d.approval_date, d.filled_by), (None, None, FILLER))
				for name in ("LOT", "SUB", "CONT"):
					self.assertEqual(site.table.state(name), PENDING, name)

	def test_a_reject_that_carries_a_new_lot_is_refused_and_the_lot_stays_released(self):
		site = FullSite(lot_tree().add("LOT-2", "1"))
		site.approve("COA AMB", "CERT-1", "LOT", "Pass")
		written = list(site.table.history)
		with self.assertRaises(frappe.ValidationError) as refused:
			site.reject_with("COA AMB", "CERT-1", "LOT", batch_reference="LOT-2")
		self.assertIn("field batch_reference", str(refused.exception))
		self.assertEqual(site.table.history, written)
		self.assertEqual(site.table.state("LOT"), ("Passed", "Own certificate", "COA AMB", "CERT-1"))
		self.assertEqual(site.table.state("LOT-2"), PENDING)


@unittest.skipUnless(SPC_OF_390, SKIP_REASON)
class TestTheWorstResultWinsThroughBothApps(unittest.TestCase):
	"""TASKS-390 (decision 338): this app passes every other standing certificate; amb_w_spc gives the record the
	worst (Failed over Hold over Passed)."""

	def test_fail_then_pass_stays_failed(self):
		site = Site(lot_tree())
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		site.approve("COA AMB", "CERT-PASS", "LOT", "Pass")
		self.assertEqual(site.table.state("LOT"), ("Failed", "Own certificate", "COA AMB2", "CERT-FAIL"))
		for below in ("SUB", "CONT"):
			self.assertEqual(site.table.state(below), ("Failed", "Inherited", "COA AMB2", "CERT-FAIL"), below)

	def test_pass_then_fail_is_failed(self):
		site = Site(lot_tree())
		site.approve("COA AMB", "CERT-PASS", "LOT", "Pass")
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		self.assertEqual(site.table.state("LOT"), ("Failed", "Own certificate", "COA AMB2", "CERT-FAIL"))

	def test_a_hold_over_a_pass_and_a_fail_over_a_hold(self):
		site = Site(lot_tree())
		site.approve("COA AMB", "CERT-PASS", "LOT", "Pass")
		site.approve("COA AMB2", "CERT-HOLD", "LOT", "Partial")
		self.assertEqual(site.table.state("LOT")[0], "Hold")
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		self.assertEqual(site.table.state("LOT")[0], "Failed")

	def test_rejecting_the_fail_gives_the_pass_that_still_stands(self):
		site = Site(lot_tree())
		site.approve("COA AMB", "CERT-PASS", "LOT", "Pass")
		site.approve("COA AMB2", "CERT-FAIL", "LOT", "Fail")
		site.reject("COA AMB2", "CERT-FAIL", "LOT")
		self.assertEqual(site.table.state("LOT"), ("Passed", "Own certificate", "COA AMB", "CERT-PASS"))
		for below in ("SUB", "CONT"):
			self.assertEqual(site.table.state(below), ("Passed", "Inherited", "COA AMB", "CERT-PASS"), below)


@unittest.skipUnless(SPC_OF_390, SKIP_REASON)
class TestTheShareThroughBothApps(unittest.TestCase):
	"""TASKS-390 (decision 334): COA AMB's `on_submit` reaches amb_w_spc's real `certificate_shared`."""

	def share(self, muted=True, answer=None):
		"""The approval (muted), then the share; `answer(spc)` sets up amb_w_spc's frappe for the share."""
		site = Site(lot_tree())
		site.approve("COA AMB", "CERT-1", "LOT", "Pass")
		approved_state, history = site.table.state("LOT"), list(site.table.history)
		d = object.__new__(amb.COAAMB)
		d.__dict__.update(doctype="COA AMB", name="CERT-1", batch_reference="LOT", docstatus=1)
		steps = []
		for name in (
			"validate_submission_prerequisites",
			"generate_coa_pdf",
			"create_quality_audit",
			"update_product_quality_status",
		):
			setattr(d, name, lambda _n=name: steps.append(_n))
		with site.running(APPROVER):
			site.spc.are_emails_muted.return_value = muted
			if answer:
				answer(site.spc)
			d.on_submit()
		return site, approved_state, history, steps, site.spc

	def test_the_share_writes_no_lot_status_and_no_row_of_its_own(self):
		site, approved_state, history, steps, _spc = self.share()
		self.assertEqual(site.table.state("LOT"), approved_state)
		self.assertEqual(site.table.history, history)
		self.assertEqual(len(steps), 4)

	def test_muted_mail_is_not_queued_and_is_noted(self):
		_site, _state, _history, _steps, spc = self.share(muted=True)
		spc.sendmail.assert_not_called()
		spc.log_error.assert_not_called()
		self.assertIn("summary not sent: mail is muted", str(spc.mock_calls))

	def test_no_team_mail_at_the_share(self):
		"""Mail NOT muted: amb_w_spc's `certificate_shared` sends exactly one summary, to the filler, the user who
		shared and the Work Order's owner (tokens, not addresses), queued without `now`; this app's own frappe reads
		no "Has Role" and sends nothing, and neither does the frappe module this test imports."""
		owner = "wo.owner"
		users = {FILLER: FILLER + ".token", APPROVER: APPROVER + ".token", owner: owner + ".token"}

		def get_value(doctype, name, fields=None, *a, **k):
			if doctype == "COA AMB":
				return {"filled_by": FILLER, "docstatus": 1, "overall_result": "Pass"}
			if doctype == lq.DOCTYPE and fields == "work_order_ref":
				return "WO-1" if name == "LOT" else None
			if doctype == "Work Order" and fields == "owner":
				return owner if name == "WO-1" else None
			if doctype == "User":
				return {"enabled": 1, "email": users[name]} if name in users else None
			raise AssertionError(f"read not expected: {doctype} {name} {fields}")

		def answer(spc):
			spc.db.get_value.side_effect = get_value
			spc.utils.validate_email_address.side_effect = (
				lambda email: email
			)  # the tokens are taken as valid
			spc.local.message_log = []
			spc.sendmail.return_value = mock.Mock(name="queued")

		asked = []
		site_get_all = Site.get_all

		def recording_get_all(site, doctype, *a, **k):
			asked.append(doctype)
			return site_get_all(site, doctype, *a, **k)

		with (
			mock.patch.object(Site, "get_all", recording_get_all),
			mock.patch.object(frappe, "sendmail", mock.Mock(name="frappe.sendmail")) as module_sendmail,
		):
			site, state, _history, steps, spc = self.share(muted=False, answer=answer)
		self.assertEqual(spc.sendmail.call_count, 1)
		call = spc.sendmail.call_args
		self.assertEqual(call.kwargs["recipients"], [users[FILLER], users[APPROVER], users[owner]])
		self.assertEqual(
			(call.kwargs["reference_doctype"], call.kwargs["reference_name"]), ("COA AMB", "CERT-1")
		)
		self.assertNotIn("now", call.kwargs)
		spc.log_error.assert_not_called()
		self.assertNotIn(lq.NOT_SENT, str(spc.mock_calls))  # nothing noted as not sent
		self.assertEqual(len(steps), 4)
		self.assertEqual(site.table.state("LOT"), state)
		# this app's frappe: no role read, no mail (its reads went through the recorder above)
		self.assertIn("Batch", asked)  # the recorder saw this app's reads (the approval's)
		self.assertNotIn("Has Role", asked)
		site.tds.sendmail.assert_not_called()
		module_sendmail.assert_not_called()
		# amb_w_spc did not read roles either (the recipients are named people only)
		self.assertNotIn("Has Role", str(spc.db.get_value.call_args_list) + str(spc.get_all.call_args_list))


if __name__ == "__main__":
	unittest.main()
