"""Rules shared by the two certificates, COA AMB and COA AMB2 (TASKS-384 B1).

One place for what both controllers do the same way on the server:

- `filled_by`: who last changed a test result (decision 313). Set here, never taken from the caller.
- "may this be approved": run when the workflow state becomes Approved (decisions 312 and 313). Each refusal
  has its own message. There is no bypass for any role or user, Administrator included.
- `approved_by` / `approval_date`: filled here at approval, kept as stored on every other save.

The Approved lock itself (TASKS-335 / 361 / 365) lives in `coa_amb2.py` and reads `STATE_FIELD` from here.
"""

import frappe
from frappe import _
from frappe.utils import cint, cstr, nowdate

from amb_w_tds.quality_vocabulary import RESULT_TO_LOT_STATUS

# The workflow state field of each certificate type (the two workflows are fixtures; not changed here).
STATE_FIELD = {"COA AMB2": "workflow_state", "COA AMB": "workflow_state_1"}
APPROVED = "Approved"
RESULT_TABLE = "coa_quality_test_parameter"
RESULT_ROW_DOCTYPE = "COA Quality Test Parameter"

# Only COA AMB is a customer certificate: it is signed and names its customers before approval (decision 312).
SIGNED_CERTIFICATES = ("COA AMB",)
SIGNATURE_FIELD = "autorizacion"
CUSTOMERS_TABLE = "custom_coa_customers"

# The lot's native Batches: `Batch` rows whose `custom_batch_amb` is the lot (amb_w_spc's projection).
LOT_DOCTYPE = "Batch AMB"
BATCH_LOT_FIELD = "custom_batch_amb"
# rnd_warehouse_management's release check reads Quality Inspection by `batch_no` and Non Conformance by
# `custom_batch_reference`; the same two keys are read here.
NON_CONFORMANCE = "Non Conformance"
NON_CONFORMANCE_BATCH_FIELD = "custom_batch_reference"
# "Closed" is what rnd's check asks for; ERPNext's own list is Open / Resolved / Cancelled and has no "Closed".
# A Non Conformance in any of these three is finished and does not stop an approval (narrowest reading).
NON_CONFORMANCE_CLOSED_STATUSES = ("Closed", "Resolved", "Cancelled")


def state_of(doc):
	return doc.get(STATE_FIELD[doc.doctype])


def _before(doc):
	return None if doc.is_new() else doc.get_doc_before_save()


def _was_approved(before):
	"""True when the stored document is Approved and not submitted."""
	return bool(
		before and cint(before.get("docstatus")) == 0 and before.get(STATE_FIELD[before.doctype]) == APPROVED
	)


def becomes_approved(doc):
	"""This save takes the certificate to Approved (the workflow's Approve, or any other way to that state)."""
	return cint(doc.docstatus) == 0 and state_of(doc) == APPROVED and not _was_approved(_before(doc))


def leaves_approved(doc):
	"""This save takes an Approved certificate to another state without submitting it (the workflow's Reject)."""
	return cint(doc.docstatus) == 0 and state_of(doc) != APPROVED and _was_approved(_before(doc))


def _result(row):
	return cstr(row.get("result")).strip()


def results_changed(doc):
	"""True when this save changes a test result: a row whose `result` differs from the stored one, a new row that
	carries a result, or a stored row with a result that is no longer in the table."""
	before = _before(doc)
	stored = {row.get("name"): _result(row) for row in (before.get(RESULT_TABLE) or [])} if before else {}
	kept = set()
	for row in doc.get(RESULT_TABLE) or []:
		name = row.get("name")
		if name in stored:
			kept.add(name)
			if stored[name] != _result(row):
				return True
		elif _result(row):
			return True
	return any(result for name, result in stored.items() if name not in kept)


def set_filled_by(doc):
	"""`filled_by` is the user who last changed a test result (decision 313). It is written here and nowhere else:
	a value sent by the caller is replaced by the stored one, so the field cannot be typed."""
	before = _before(doc)
	if results_changed(doc):
		doc.filled_by = frappe.session.user
	else:
		doc.filled_by = before.get("filled_by") if before else None


def note_filler_of_row(doc, method=None):
	"""doc_events hook on the result row DocType (`before_validate`, `on_trash`): a result row saved, inserted or
	deleted BY ITSELF does not pass through the certificate's `validate`, so `set_filled_by` never sees it. When
	such a save changes a result, the certificate the row belongs to (the one sent and the one stored) gets the
	session user as `filled_by`. Rows of any other parent are not touched. A save of the certificate itself runs no
	row event."""
	stored = None
	if doc.get("name") and not doc.is_new():
		stored = frappe.db.get_value(
			doc.doctype, doc.get("name"), ["parent", "parenttype", "result"], as_dict=True
		)
	if method == "on_trash":
		changed = bool(stored and cstr(stored.result).strip())
		owners = {(stored.parenttype, stored.parent)} if stored else set()
	else:
		changed = (cstr(stored.result).strip() if stored else "") != _result(doc)
		owners = {(doc.get("parenttype"), doc.get("parent"))}
		if stored:
			owners.add((stored.parenttype, stored.parent))
	if not changed:
		return
	for parenttype, parent in sorted(o for o in owners if o[0] in STATE_FIELD and o[1]):
		frappe.db.set_value(parenttype, parent, "filled_by", frappe.session.user)


def refuse_changed_results_at_share(doc):
	"""The submit of an Approved COA AMB (Approved -> Certificate Shared) is the workflow's own move and passes the
	lock; the results it was approved with do not change in that save."""
	if cint(doc.docstatus) == 1 and _was_approved(_before(doc)) and results_changed(doc):
		frappe.throw(
			_(
				"{0} {1} is Approved: its results cannot be changed while it is shared. A Quality Manager must Reject it to Draft first."
			).format(_(doc.doctype), doc.name),
			title=_("Approved certificate"),
		)


def lot_batches(lot):
	"""The names of the native Batches of a lot record. On a site where `Batch` has no `custom_batch_amb` (the
	projection of amb_w_spc is not installed) no Batch belongs to a lot, so the list is empty and the two checks
	that read it find nothing: that is said here, not hidden; any error of the read itself is raised."""
	if not lot or not frappe.get_meta("Batch").has_field(BATCH_LOT_FIELD):
		return []
	return frappe.get_all("Batch", filters={BATCH_LOT_FIELD: lot}, pluck="name")


def rejected_inspections(batches):
	"""Submitted Quality Inspections with status Rejected on these Batches. A draft inspection, filled or not, is
	not a failure (Quality, 2026-11-26: results are captured in the certificate itself)."""
	if not batches:
		return []
	return frappe.get_all(
		"Quality Inspection",
		filters={"batch_no": ["in", batches], "status": "Rejected", "docstatus": 1},
		pluck="name",
	)


def open_non_conformances(batches):
	"""Non Conformances of these Batches that are not finished. On a site without the Non Conformance DocType, or
	where it has no `custom_batch_reference` field, a Non Conformance cannot name a Batch: nothing is read and
	nothing is refused."""
	if not batches or not frappe.db.exists("DocType", NON_CONFORMANCE):
		return []
	if not frappe.get_meta(NON_CONFORMANCE).has_field(NON_CONFORMANCE_BATCH_FIELD):
		return []
	return frappe.get_all(
		NON_CONFORMANCE,
		filters={
			NON_CONFORMANCE_BATCH_FIELD: ["in", batches],
			"status": ["not in", list(NON_CONFORMANCE_CLOSED_STATUSES)],
		},
		pluck="name",
	)


def _is_header_row(row):
	"""A title row of the table, as both controllers read it; never a test."""
	if row.get("custom_is_title_row"):
		return True
	return cstr(row.get("value") or row.get("specification") or "").strip().lower() == "specification"


def _refuse(doc, reason):
	frappe.throw(
		_("{0} {1} cannot be approved: {2}").format(_(doc.doctype), doc.name or "", reason),
		title=_("Approval refused"),
	)


def refuse_unless_approvable(doc):
	""" "May this be approved" (TASKS-384 B1). Run when the state becomes Approved, after the result was derived from
	the rows and `filled_by` was set for this save. No role and no user is exempt."""
	if not doc.get("linked_tds"):
		_refuse(doc, _("no specification is linked."))
	if not [row for row in (doc.get(RESULT_TABLE) or []) if not _is_header_row(row)]:
		_refuse(doc, _("it has no test rows."))
	if doc.get("overall_result") not in RESULT_TO_LOT_STATUS:
		_refuse(
			doc,
			_("its result is {0}; only Pass, Fail or Partial can be approved.").format(
				doc.get("overall_result") or _("empty")
			),
		)
	if not doc.get("filled_by"):
		_refuse(
			doc,
			_(
				"it is not recorded who entered its results, so the approver cannot be told apart from that person. A result must be saved again by whoever fills the certificate."
			),
		)
	if doc.get("filled_by") == frappe.session.user:
		_refuse(doc, _("you entered or changed its results last; another person must approve it."))
	if doc.doctype in SIGNED_CERTIFICATES:
		if not doc.get(SIGNATURE_FIELD):
			_refuse(doc, _("it is not signed. Sign it, save, then approve."))
		if not [row for row in (doc.get(CUSTOMERS_TABLE) or []) if row.get("customer")]:
			_refuse(doc, _("its customers list is empty."))
	batches = lot_batches(doc.get("batch_reference"))
	rejected = rejected_inspections(batches)
	if rejected:
		_refuse(
			doc,
			_("lot {0} has a submitted Quality Inspection that is Rejected: {1}.").format(
				doc.get("batch_reference"), ", ".join(rejected)
			),
		)
	open_ncs = open_non_conformances(batches)
	if open_ncs:
		_refuse(
			doc,
			_("lot {0} has a Non Conformance that is not closed: {1}.").format(
				doc.get("batch_reference"), ", ".join(open_ncs)
			),
		)


def set_approval(doc):
	"""`approved_by` and `approval_date` belong to the server. At approval: the session user and today. When an
	Approved certificate goes back (Reject): emptied, the certificate is no longer approved. On any other save of
	a stored certificate: the stored values, whatever the caller sent."""
	before = _before(doc)
	if becomes_approved(doc):
		refuse_unless_approvable(doc)
		doc.approved_by = frappe.session.user
		doc.approval_date = nowdate()
	elif leaves_approved(doc):
		doc.approved_by = None
		doc.approval_date = None
	elif before:
		doc.approved_by = before.get("approved_by")
		doc.approval_date = before.get("approval_date")


def apply(doc):
	"""Called by `validate` of both certificates, after the result was derived from the rows."""
	refuse_changed_results_at_share(doc)
	set_filled_by(doc)
	set_approval(doc)
