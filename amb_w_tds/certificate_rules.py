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
from frappe.utils import cint, cstr, flt, nowdate

from amb_w_tds.quality_vocabulary import RESULT_TO_LOT_STATUS

# The workflow state field of each certificate type (the two workflows are fixtures; not changed here).
STATE_FIELD = {"COA AMB2": "workflow_state", "COA AMB": "workflow_state_1"}
APPROVED = "Approved"
RESULT_TABLE = "coa_quality_test_parameter"
RESULT_ROW_DOCTYPE = "COA Quality Test Parameter"
# The fields of a test row that the evaluation reads (`evaluate_overall_result`, `check_parameter_compliance`,
# `_is_header_row`, and at submit `validate_test_parameters` / `evaluate_formula_parameters`, in both controllers):
# a change of any of them can change the verdict, or what the certificate says was tested, so it is a change of
# the results. `status` is not here: the evaluation writes it and never reads it.
EVALUATION_TEXT_FIELDS = ("result", "specification", "value", "acceptance_formula", "parameter_name")
EVALUATION_NUMBER_FIELDS = ("min_value", "max_value")
EVALUATION_CHECK_FIELDS = ("numeric", "formula_based_criteria", "custom_is_title_row")
EVALUATION_FIELDS = EVALUATION_TEXT_FIELDS + EVALUATION_NUMBER_FIELDS + EVALUATION_CHECK_FIELDS

# Only COA AMB is a customer certificate: it is signed and names its customers before approval (decision 312).
SIGNED_CERTIFICATES = ("COA AMB",)
SIGNATURE_FIELD = "autorizacion"
CUSTOMERS_TABLE = "custom_coa_customers"

# The lot's native Batches: `Batch` rows whose `custom_batch_amb` is the lot (amb_w_spc's projection).
LOT_DOCTYPE = "Batch AMB"
# A certificate is made for a lot (level 1) or a sub-lot (level 2); the records below follow their sub-lot
# (decision 319). The same two levels as amb_w_spc's `lot_quality.CERTIFICATE_LEVELS`; an empty level is level 1.
LOT_LEVEL_FIELD = "custom_batch_level"
CERTIFICATE_LEVELS = ("1", "2")
# TASKS-384 B3: the lot's status is written by amb_w_spc, the only writer, through these two functions. They are
# looked up when they are called (late binding): this app imports without amb_w_spc.
SPC_APP = "amb_w_spc"
SPC_LOT_QUALITY = "amb_w_spc.sfc_manufacturing.lot_quality"
# The state in which a submitted certificate still stands for its lot (COA AMB only; no COA AMB2 is submitted).
SHARED_STATE = {"COA AMB": "Certificate Shared"}
# TASKS-384 B2: the certificate's `work_order` follows the lot's `work_order_ref`; the lot's item is the Work
# Order's item (`item_to_manufacture`, what the lot picker shows).
LOT_WORK_ORDER_FIELD = "work_order_ref"
LOT_ITEM_FIELD = "item_to_manufacture"
# The customers of a COA AMB come from the specification's table, else from the Item's (decision 312).
SPECIFICATION_CUSTOMERS = ("TDS Product Specification", "custom_tds_customers")
ITEM_CUSTOMERS = ("Item", "custom_amb_customer_items")
CUSTOMER_ROW_FIELDS = (
	"customer",
	"custom_customer_name",
	"custom_customer_part_number",
	"custom_lead_time_days",
	"custom_min_order_qty",
	"custom_max_order_qty_",
)
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


def _evaluated(row):
	"""What the evaluation reads of one test row, in one comparable form: text without the spaces around it, the
	two limits as numbers (an empty limit and 0 both mean "no bound" to the evaluation), the three checks as 0/1.
	The same row read from the database and sent back by the form compares equal."""
	return (
		tuple(cstr(row.get(f)).strip() for f in EVALUATION_TEXT_FIELDS)
		+ tuple(round(flt(row.get(f)), 9) for f in EVALUATION_NUMBER_FIELDS)
		+ tuple(cint(row.get(f)) for f in EVALUATION_CHECK_FIELDS)
	)


def results_changed(doc):
	"""True when this save changes the results: a stored row with a field the evaluation reads that differs from
	the stored one (the result, but also a limit, the specification, the formula, the title mark: see
	`EVALUATION_FIELDS`), a row that was added, or a stored row that is no longer in the table."""
	before = _before(doc)
	stored = {row.get("name"): _evaluated(row) for row in (before.get(RESULT_TABLE) or [])} if before else {}
	kept = set()
	for row in doc.get(RESULT_TABLE) or []:
		name = row.get("name")
		if name not in stored or name in kept:
			return True  # a row that was added (a name sent twice is one stored row and one added)
		kept.add(name)
		if stored[name] != _evaluated(row):
			return True
	return len(kept) != len(stored)


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
	such a save changes the results (a field the evaluation reads differs from the stored row, the row is new, or
	it is deleted: the same rule as `results_changed`), the certificate the row belongs to (the one sent and the
	one stored) gets the session user as `filled_by`. Rows of any other parent are not touched. A save of the
	certificate itself runs no row event."""
	stored = None
	if doc.get("name") and not doc.is_new():
		stored = frappe.db.get_value(
			doc.doctype, doc.get("name"), ["parent", "parenttype", *EVALUATION_FIELDS], as_dict=True
		)
	if method == "on_trash":
		changed = bool(stored)
		owners = {(stored.parenttype, stored.parent)} if stored else set()
	else:
		changed = not stored or _evaluated(stored) != _evaluated(doc)
		owners = {(doc.get("parenttype"), doc.get("parent"))}
		if stored:
			owners.add((stored.parenttype, stored.parent))
	if not changed:
		return
	for parenttype, parent in sorted(o for o in owners if o[0] in STATE_FIELD and o[1]):
		frappe.db.set_value(parenttype, parent, "filled_by", frappe.session.user)


def refuse_submit_unless_approved(doc):
	"""A certificate that its workflow submits (COA AMB: Approved -> Certificate Shared) goes from docstatus 0 to 1
	only from the STORED state Approved. Every other submit is refused, for every role and every way there: the
	form's Submit, `frappe.client.submit`, a save or an insert that carries docstatus 1, a bulk submit. Without
	this a Draft could be submitted directly: the framework then names it by the first submitted state of the
	workflow, "Certificate Shared", and it would count as a certificate that stands for its lot without ever
	having been approved by a second person.

	What is read is what the database holds, not what the caller sends. A new document has no stored state, so it
	is never inserted as submitted; that covers the amendment of a cancelled certificate, which is a new draft and
	goes through approval again. From Approved, WHERE the submit may go is the lock's business
	(`ApprovedLock.refuse_edit_of_approved`). A document that is already submitted is not judged here."""
	if doc.doctype not in SHARED_STATE or cint(doc.docstatus) != 1:
		return
	before = _before(doc)
	if before and cint(before.get("docstatus")) != 0:
		return
	if _was_approved(before):
		return
	frappe.throw(
		_(
			"{0} {1} cannot be submitted: {2}. A certificate is submitted only by its workflow, from the state Approved to {3}, after another person approved it. Take it through Review and Approve first."
		).format(
			_(doc.doctype),
			doc.name or "",
			_("its stored state is {0}, not Approved").format(
				before.get(STATE_FIELD[doc.doctype]) or _("empty")
			)
			if before
			else _("it is new and was never approved"),
			SHARED_STATE[doc.doctype],
		),
		title=_("Certificate not approved"),
	)


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
				"it is not recorded who entered its results (it was filled before this was recorded), so the approver cannot be told apart from that person. Saving it again unchanged does not record it. Whoever fills the certificate must change a result and save; to keep the same value: change it, save, set it back, save again. Then another person approves."
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
	a stored certificate: the stored values, whatever the caller sent. On a new certificate that is not becoming
	Approved: empty, whatever the caller sent. A copy and an amendment are new certificates, and the form's Amend
	copies every field, the ones marked "no copy" included, so they are emptied here and not by the field mark."""
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
	else:
		doc.approved_by = None
		doc.approval_date = None


def follow_lot(doc):
	"""TASKS-384 B2. The certificate's Work Order is the lot's: written here from the lot's `work_order_ref` on
	every save of a certificate that names a lot whose record names a Work Order (one read of the lot). A lot
	without a Work Order leaves the field as it is.

	The lot's item and the certificate's product may differ on purpose (they sit at different levels of the Item
	tree, which is why the lot picker carries no item filter), so a difference is SHOWN, not refused: once, in the
	save that sets or changes the lot or the product."""
	lot = doc.get("batch_reference")
	if not lot:
		return
	row = frappe.db.get_value(LOT_DOCTYPE, lot, [LOT_WORK_ORDER_FIELD, LOT_ITEM_FIELD], as_dict=True)
	if not row:
		return
	if row.get(LOT_WORK_ORDER_FIELD):
		doc.work_order = row.get(LOT_WORK_ORDER_FIELD)
	before = _before(doc)
	touched = not before or any(before.get(f) != doc.get(f) for f in ("batch_reference", "product_item"))
	lot_item, product = row.get(LOT_ITEM_FIELD), doc.get("product_item")
	if touched and lot_item and product and lot_item != product:
		frappe.msgprint(
			_(
				"Lot {0} is of item {1}; this certificate is for product {2}. The product was not changed."
			).format(lot, lot_item, product),
			title=_("Lot and product differ"),
			indicator="orange",
			alert=True,
		)


def refuse_wrong_type(doc):
	"""TASKS-384 B2, decision 317: the product decides the type of its certificate. Judged when the certificate is
	made and when its product changes, and only for a product that is classed (see
	`amb_w_tds.api.certificate.certificate_type_for_item`); a stored certificate whose product stays is not judged
	again, so its workflow is not stopped by a later change of the classification."""
	before = _before(doc)
	product = doc.get("product_item")
	if not product or (before and before.get("product_item") == product):
		return
	from amb_w_tds.api.certificate import certificate_type_for_item

	expected = certificate_type_for_item(product)
	if expected and expected != doc.doctype:
		frappe.throw(
			_("Product {0} takes a {1}, not a {2}: make its certificate as {1}.").format(
				product, _(expected), _(doc.doctype)
			),
			title=_("Wrong certificate type"),
		)


def lot_level(value):
	"""The level of a lot record as text; an empty level is level 1 (as amb_w_spc reads it)."""
	return cstr(value).strip() or CERTIFICATE_LEVELS[0]


def lot_level_refusal(lot, level):
	return _(
		"Lot record {0} is a level {1} record. A certificate is made for a lot (level 1) or a sub-lot (level 2); the records below them follow their sub-lot. Choose the lot or the sub-lot."
	).format(lot, level)


def refuse_lot_level(doc):
	"""TASKS-384 B3/B4 (decision 319): a certificate names a lot or a sub-lot, never a record below them. Judged in
	the save that sets or changes the lot, so the wrong record is refused when it is chosen and not only when the
	certificate is approved. On a site whose lot records have no level field nothing is read and nothing is
	refused."""
	lot = doc.get("batch_reference")
	before = _before(doc)
	if not lot or (before and before.get("batch_reference") == lot):
		return
	if not frappe.get_meta(LOT_DOCTYPE).has_field(LOT_LEVEL_FIELD):
		return
	level = lot_level(frappe.db.get_value(LOT_DOCTYPE, lot, LOT_LEVEL_FIELD))
	if level not in CERTIFICATE_LEVELS:
		frappe.throw(lot_level_refusal(lot, level), title=_("Lot level"))


def customers_for(specification, item):
	"""The customers of a product: the rows of the specification's customers table, else the Item's."""
	for (doctype, table), name in ((SPECIFICATION_CUSTOMERS, specification), (ITEM_CUSTOMERS, item)):
		if not name or not frappe.db.exists(doctype, name):
			continue
		rows = [row for row in (frappe.get_doc(doctype, name).get(table) or []) if row.get("customer")]
		if rows:
			return [{field: row.get(field) for field in CUSTOMER_ROW_FIELDS} for row in rows]
	return []


def fill_customers(doc):
	"""TASKS-384 B2, decision 312: the customers list is filled when the certificate is created, on the server.
	Called by `before_insert` of a certificate that has the table (COA AMB), after the specification was read. A
	list that already has rows is left as it is."""
	if not doc.meta.has_field(CUSTOMERS_TABLE) or doc.get(CUSTOMERS_TABLE):
		return
	for row in customers_for(doc.get("linked_tds"), doc.get("product_item") or doc.get("item_code")):
		doc.append(CUSTOMERS_TABLE, row)


def note_lot_move(doc):
	"""TASKS-384 B3, decided in `validate` from the state before the save and the state now: does this save release
	the lot (the state becomes Approved) or take the release back (an Approved certificate goes back, the
	workflow's Reject)? The answer is kept on the document for `on_update`, which runs after the certificate is
	written, in the same transaction. A release speaks of the lot the certificate names now; a withdrawal of the
	lot it named when it was approved."""
	doc._lot_move = None
	if becomes_approved(doc):
		doc._lot_move = ("approved", doc.get("batch_reference"))
	elif leaves_approved(doc):
		doc._lot_move = ("withdrawn", _before(doc).get("batch_reference"))


def _spc(function):
	"""A function of amb_w_spc's lot_quality module, found at the moment of the call. Without that app, or with a
	version of it that lacks the function, the lot cannot be written: the approval (or the Reject, or the Cancel)
	fails here with a message that says so. Only the LOOKUP is guarded; the call itself is never wrapped."""
	path = f"{SPC_LOT_QUALITY}.{function}"
	if SPC_APP not in frappe.get_installed_apps():
		frappe.throw(
			_(
				"The lot's quality status is written by the app {0}, which is not installed on this site ({1}). Nothing was saved."
			).format(SPC_APP, path),
			title=_("Lot not written"),
		)
	try:
		return frappe.get_attr(path)
	except (ImportError, AttributeError) as e:
		frappe.throw(
			_(
				"The lot's quality status cannot be written: {0} is not available in the installed {1} ({2}). Nothing was saved."
			).format(path, SPC_APP, e),
			title=_("Lot not written"),
		)


def _approved_by_another(row):
	approver, filler = cstr(row.get("approved_by")).strip(), cstr(row.get("filled_by")).strip()
	return bool(approver and filler and approver != filler)


def standing_certificate(lot, doctype, name):
	"""ANOTHER certificate of the same lot record, of either type, that still stands: Approved and not submitted,
	or (COA AMB) Certificate Shared and not cancelled, with a result that maps to a lot status, AND approved by
	the two-person rule: it records who approved it and who filled it, and the two differ. A certificate in one of
	those states without that record (one written past the approval, or approved before `filled_by` existed) does
	not stand: it cannot decide the status of a lot when another certificate is taken back. Returned as
	{"doctype", "name", "result"}, or None. When several stand, the one approved last (then saved last) is taken."""
	found = []
	for certificate_doctype, field in STATE_FIELD.items():
		standing_states = [(APPROVED, 0)]
		if certificate_doctype in SHARED_STATE:
			standing_states.append((SHARED_STATE[certificate_doctype], 1))
		for state, docstatus in standing_states:
			filters = {"batch_reference": lot, field: state, "docstatus": docstatus}
			if certificate_doctype == doctype:
				filters["name"] = ["!=", name]
			for row in frappe.get_all(
				certificate_doctype,
				filters=filters,
				fields=["name", "overall_result", "approval_date", "modified", "approved_by", "filled_by"],
			):
				if row.get("overall_result") in RESULT_TO_LOT_STATUS and _approved_by_another(row):
					found.append(
						(cstr(row.get("approval_date")), cstr(row.get("modified")), certificate_doctype, row)
					)
	if not found:
		return None
	_approved, _modified, certificate_doctype, row = max(found, key=lambda f: f[:3])
	return {"doctype": certificate_doctype, "name": row.get("name"), "result": row.get("overall_result")}


def write_lot(doc):
	"""TASKS-384 B3, `on_update` of both certificates: carry out what `note_lot_move` decided. A certificate that
	names no lot has nothing to write. NO try/except: if the lot cannot be written the exception leaves this save
	and the certificate's own write is rolled back with it; the user sees why."""
	move = getattr(doc, "_lot_move", None)
	doc._lot_move = None
	if not move or not move[1]:
		return
	kind, lot = move
	if kind == "approved":
		_spc("certificate_approved")(doc.doctype, doc.name, lot, doc.get("overall_result"))
	else:
		_spc("certificate_withdrawn")(
			doc.doctype, doc.name, lot, standing=standing_certificate(lot, doc.doctype, doc.name)
		)


def withdraw_on_cancel(doc):
	"""TASKS-384 B3, `on_cancel` of COA AMB: a shared certificate that is cancelled no longer stands for its lot.
	amb_w_spc resets only what this certificate wrote. No try/except, as in `write_lot`."""
	lot = doc.get("batch_reference")
	if not lot:
		return
	_spc("certificate_withdrawn")(
		doc.doctype, doc.name, lot, standing=standing_certificate(lot, doc.doctype, doc.name)
	)


def apply(doc):
	"""Called by `validate` of both certificates, after the result was derived from the rows."""
	refuse_submit_unless_approved(doc)
	refuse_changed_results_at_share(doc)
	refuse_wrong_type(doc)
	refuse_lot_level(doc)
	follow_lot(doc)
	set_filled_by(doc)
	set_approval(doc)
	note_lot_move(doc)
