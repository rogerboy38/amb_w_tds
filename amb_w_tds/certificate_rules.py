"""Rules shared by the two certificates, COA AMB and COA AMB2 (TASKS-384 B1).

One place for what both controllers do the same way on the server:

- `filled_by`: who last changed what the certificate certifies (decision 313; TASKS-387 decision 321): a test
  result, the customers list, or (in Draft / Validated) the lot, product or specification. Set here, never taken
  from the caller.
- `signed_by` (COA AMB): who last drew or changed the signature; the approver must be that person (decision 321).
  A save that makes someone the filler empties the signature and its signer and says so (TASKS-388, decision 331).
- Pending Supervisor: the lot, product and specification are refused there; "Return for correction" takes the
  certificate back to Draft (decision 321).
- The share (COA AMB, Approved -> Certificate Shared) changes nothing but the state (decision 322); nor does the save
  that takes an Approved certificate back to a docstatus-0 state, the workflow's Reject (TASKS-388, decision 332).
- "may this be approved": run when the workflow state becomes Approved (decisions 312 and 313). Each refusal
  has its own message. There is no bypass for any role or user, Administrator included.
- `approved_by` / `approval_date`: filled here at approval, kept as stored on every other save.

The Approved lock itself (TASKS-335 / 361 / 365) lives in `coa_amb2.py` and reads `STATE_FIELD` from here.
"""

import datetime
from types import SimpleNamespace

import frappe
from frappe import _, _dict
from frappe.utils import cint, cstr, flt, get_datetime, getdate, nowdate

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
# TASKS-387 (decision 321): who last drew or changed the signature. Written by the server, never taken from the caller.
SIGNER_FIELD = "signed_by"
# TASKS-390 (decision 337): everyone who changed what the certificate certifies (its results, its customers list, its
# lot, product or specification) since it last entered Draft, one user id per line (a Small Text field on both
# certificates; read-only, no copy). Written by the server, never taken from the caller; none of them may approve.
# `filled_by` stays the LAST of them. Entering Draft again (Return for correction, the Reject) starts a new list.
FILLERS_FIELD = "fillers_since_draft"
DRAFT = "Draft"

# TASKS-387 (decision 321): what the certificate is FOR. A change of any of them in Draft or Validated is filling
# (the changer becomes `filled_by`); in Pending Supervisor it is refused (the way back is "Return for correction");
# in Approved the lock refuses every change.
IDENTITY_FIELDS = ("batch_reference", "product_item", "linked_tds")
PENDING_SUPERVISOR = "Pending Supervisor"
RETURN_FOR_CORRECTION = "Return for correction"
SPECIFICATION_DOCTYPE = "TDS Product Specification"
# The framework's own columns of a row: not what a row says. A customers row that differs only in these is the same
# row (its place in the list included: the order of the customers is not what the certificate certifies).
ROW_META_FIELDS = frozenset(
	("doctype", "name", "idx", "owner", "creation", "modified", "modified_by", "docstatus")
).union(("parent", "parentfield", "parenttype"))

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
# TASKS-387 (decision 323): the records below a lot record name it in `parent_batch_amb`. They are read level by level,
# at most this many levels below the certificate's record (a lot is level 1; the deepest level is 4 or, for a
# formulated record, 5), with a guard against a loop in the data.
LOT_PARENT_FIELD = "parent_batch_amb"
LOT_LEVELS_BELOW = 4
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


def _comparable(value, fieldtype=None):
	"""One value in a form that compares equal whether it was read from the database or sent by a client: a check
	or an integer as a number, a number rounded, a date or a moment as its text, an empty value as "". Without a
	field type (a framework column, or a document without its DocType's description) the value's own type decides."""
	if fieldtype in ("Check", "Int"):
		return cint(value)
	if fieldtype in ("Float", "Currency", "Percent"):
		return round(flt(value), 9)
	if fieldtype == "Date":
		return cstr(getdate(value)) if value else ""
	if fieldtype == "Datetime":
		return cstr(get_datetime(value)) if value else ""
	if value is None:
		return ""
	if isinstance(value, bool):
		return int(value)
	if isinstance(value, int | float):
		return round(float(value), 9)
	if isinstance(value, datetime.date | datetime.timedelta):
		return cstr(value)
	return cstr(value)


# The framework's columns whose type is not in the DocType's field list.
STANDARD_FIELD_TYPES = {"docstatus": "Int", "idx": "Int", "creation": "Datetime", "modified": "Datetime"}


def _description(doctype):
	"""(columns, field types, table fields) of a DocType as the framework describes it, or None when the site's
	description has none of that (a document built without the database, in a test)."""
	meta = frappe.get_meta(doctype)
	columns = getattr(meta, "get_valid_columns", None)
	if not callable(columns):
		return None
	types = dict(STANDARD_FIELD_TYPES)
	for df in meta.get("fields") or []:
		types[df.fieldname] = df.fieldtype
	tables = [(df.fieldname, df.options) for df in meta.get_table_fields()]
	return list(columns()), types, tables


def _plain_fields(d):
	"""The field names a document or a row carries, read from the object itself (no DocType description)."""
	values = d if isinstance(d, dict) else getattr(d, "__dict__", {})
	return [
		k
		for k, v in values.items()
		if not k.startswith("_") and k != "flags" and not callable(v) and not isinstance(v, list)
	]


def _rows_differ(stored_rows, rows, row_doctype, ignore=ROW_META_FIELDS):
	"""True when a table differs from the stored one: a row added (or a name sent twice), a stored row removed, or
	any field of a row that is not in `ignore` changed. Rows are matched by name; their order is not compared."""
	description = _description(row_doctype) if row_doctype else None
	types = description[1] if description else {}
	stored_by_name = {r.get("name"): r for r in stored_rows or []}
	kept = set()
	for r in rows or []:
		name = r.get("name")
		if name not in stored_by_name or name in kept:
			return True
		kept.add(name)
		old = stored_by_name[name]
		fields = description[0] if description else set(_plain_fields(old)) | set(_plain_fields(r))
		for f in fields:
			if f not in ignore and _comparable(old.get(f), types.get(f)) != _comparable(
				r.get(f), types.get(f)
			):
				return True
	return len(kept) != len(stored_by_name)


def customers_changed(doc):
	"""TASKS-387 (decision 321): the customers list of a stored COA AMB differs from the stored one: a row added or
	removed, or any field of a row changed. A certificate without that table never changes it."""
	before = _before(doc)
	if not before or (doc.get(CUSTOMERS_TABLE) is None and before.get(CUSTOMERS_TABLE) is None):
		return False
	row_doctype = None
	description = _description(doc.doctype)
	if description:
		row_doctype = dict(description[2]).get(CUSTOMERS_TABLE)
	ignore = tuple(ROW_META_FIELDS) + _fetched_row_fields(row_doctype)
	return _rows_differ(before.get(CUSTOMERS_TABLE), doc.get(CUSTOMERS_TABLE), row_doctype, ignore=ignore)


# TASKS-387 review, finding 1: fields of a customers row that the framework re-fetches on every save of a draft
# (`fetch_from`, not "fetch if empty"), before any rule runs. Their change is the server's, not the user's, and is
# not a change of the customers list. The shipped `Customer Item.custom_customer_name` fetches `customer.customer_name`;
# it is named here too so a document built without the database (a test) is judged the same way.
FETCHED_CUSTOMER_ROW_FIELDS = ("custom_customer_name",)


def _fetched_row_fields(row_doctype):
	fields = set(FETCHED_CUSTOMER_ROW_FIELDS)
	if row_doctype:
		meta = frappe.get_meta(row_doctype)
		for df in meta.get("fields") or []:
			if df.get("fetch_from") and not df.get("fetch_if_empty"):
				fields.add(df.get("fieldname"))
	return tuple(sorted(fields))


def _product_follows_specification(doc, before):
	"""The product field of both certificates is fetched by the framework from the specification
	(`fetch_from: linked_tds.product_item`) on every save of a draft, before any rule runs. When the specification is
	the stored one and the product now is that specification's product, the change was made by the server, not by
	the user, and is not a change of identity."""
	specification = doc.get("linked_tds")
	if not specification or cstr(specification) != cstr(before.get("linked_tds")):
		return False
	fetched = frappe.db.get_value(SPECIFICATION_DOCTYPE, specification, "product_item")
	return bool(fetched) and cstr(fetched) == cstr(doc.get("product_item"))


def identity_changes(doc):
	"""TASKS-387 (decision 321): the identity fields (lot, product, specification) that this save of a stored
	certificate changes, in that order. A new certificate changes none (it is judged as it is made: see
	`set_filled_by`). The product written by the framework's fetch from an unchanged specification is not a change
	(`_product_follows_specification`); the server writes no other identity field in a save of a stored certificate."""
	before = _before(doc)
	if not before:
		return []
	changed = []
	for field in IDENTITY_FIELDS:
		if cstr(doc.get(field)) == cstr(before.get(field)):
			continue
		if field == "product_item" and _product_follows_specification(doc, before):
			continue
		changed.append(field)
	return changed


def filling_changes(doc):
	"""What this save changes of what the certificate certifies, as text, in this order: its results, its customers
	list, the identity fields it changes (`identity_changes`). Empty when it changes none of them. A new certificate
	changes only its results (when it carries test rows); see `set_filled_by`."""
	before = _before(doc)
	changes = []
	if results_changed(doc):
		changes.append(_("its results"))
	if before:
		if customers_changed(doc):
			changes.append(_("its customers list"))
		changes.extend(identity_changes(doc))
	return changes


def fillers_of(value):
	"""The users of a stored `fillers_since_draft` value, in their order, each once (empty lines dropped)."""
	return list(dict.fromkeys(u.strip() for u in cstr(value).splitlines() if u.strip()))


def with_filler(value, user):
	"""`fillers_since_draft` with `user` added at the end (once)."""
	users = fillers_of(value)
	return "\n".join(users if user in users else [*users, user])


def enters_draft(doc, before):
	"""TASKS-390 (decision 337): this save takes a stored certificate INTO Draft from another state (the workflow's
	"Return for correction" and Reject, or any other way there). A new certificate is not entering Draft again."""
	return bool(
		before
		and cint(doc.docstatus) == 0
		and state_of(doc) == DRAFT
		and before.get(STATE_FIELD[doc.doctype]) != DRAFT
	)


def set_filled_by(doc):
	"""`filled_by` is the user who last changed what the certificate certifies (decision 313; TASKS-387 decision
	321): a test result (`results_changed`), the customers list (`customers_changed`), or the lot, product or
	specification (`identity_changes`; the last two are refused in Pending Supervisor before this runs, and every
	change is refused in Approved). It is written here and nowhere else: a value sent by the caller is replaced by the
	stored one, so the field cannot be typed. The signature is not filling (`set_signed_by`).

	A new certificate is filled by its maker when it carries test rows, as before: its identity and the customers
	the server fills in from the specification (`fill_customers`) do not name the maker by themselves. A certificate
	without test rows cannot be approved, and whoever adds them becomes the filler, so this changes no approval.

	TASKS-390 (decision 337): `fillers_since_draft` holds every user named so in this way since the certificate last
	entered Draft: the stored list, emptied in the save that enters Draft again (`enters_draft`: the one who returns
	or rejects changes nothing, so is not added for that), with the session user added when this save changes what
	the certificate certifies. A value sent by the caller is replaced, as for `filled_by`.

	Returns what made the session user the filler (`filling_changes`), empty when nobody was named by this save."""
	before = _before(doc)
	changes = filling_changes(doc)
	fillers = "" if not before or enters_draft(doc, before) else cstr(before.get(FILLERS_FIELD))
	if changes:
		doc.filled_by = frappe.session.user
		fillers = with_filler(fillers, frappe.session.user)
	else:
		doc.filled_by = before.get("filled_by") if before else None
	setattr(doc, FILLERS_FIELD, "\n".join(fillers_of(fillers)) or None)
	return changes


def _signature_cleared_message(doctype, name, changes):
	frappe.msgprint(
		_(
			"The signature of {0} {1} was cleared: this save changed {2}, and whoever changes that becomes its filler. The approver must draw the signature again before approving."
		).format(_(doctype), name or "", ", ".join(changes)),
		title=_("Signature cleared"),
		indicator="orange",
	)


def clear_signature_on_filling(doc, changes):
	"""TASKS-388 (decision 331), COA AMB: a save of a stored certificate that makes someone the filler (`changes`, from
	`set_filled_by`: a change of the results, of the customers list or of the lot, product or specification) also
	empties the signature (`autorizacion`) and its signer (`signed_by`) in that save, and the user is told so (a
	message, not a refusal). Run AFTER `set_signed_by`, so a signature drawn in the same save is cleared too and the
	clear is not undone. A save that only draws the signature names no filler and clears nothing. A new certificate is
	not judged here: it never carries a signer (`set_signed_by`), so its signature cannot serve an approval."""
	if doc.doctype not in SIGNED_CERTIFICATES or not changes or not _before(doc):
		return
	if not (doc.get(SIGNATURE_FIELD) or doc.get(SIGNER_FIELD)):
		return
	setattr(doc, SIGNATURE_FIELD, None)
	setattr(doc, SIGNER_FIELD, None)
	_signature_cleared_message(doc.doctype, doc.name, changes)


def _clear_stored_signature(parenttype, parent, what):
	"""TASKS-388 (decision 331), for a row saved by itself that makes someone the filler of a COA AMB (the row hooks
	below): the certificate's stored signature and signer are emptied in the same transaction, and the user told."""
	if parenttype not in SIGNED_CERTIFICATES:
		return
	stored = frappe.db.get_value(parenttype, parent, [SIGNATURE_FIELD, SIGNER_FIELD], as_dict=True)
	if not stored or not (stored.get(SIGNATURE_FIELD) or stored.get(SIGNER_FIELD)):
		return
	frappe.db.set_value(parenttype, parent, {SIGNATURE_FIELD: None, SIGNER_FIELD: None})
	_signature_cleared_message(parenttype, parent, [what])


def set_signed_by(doc):
	"""TASKS-387 (decision 321), COA AMB: `signed_by` is the user who last drew or changed the signature
	(`autorizacion`) in a save of the stored certificate; emptied with the signature. Written here and nowhere else:
	a value sent by the caller is replaced by the stored one. A new certificate carries no signer, signature or not:
	the form's Amend and Duplicate copy the signature of the certificate they come from, so whoever saves a new
	certificate has not necessarily drawn what it carries. Changing the signature does not make anyone the filler."""
	if doc.doctype not in SIGNED_CERTIFICATES:
		return
	before = _before(doc)
	if not before:
		doc.signed_by = None
	elif cstr(doc.get(SIGNATURE_FIELD)) != cstr(before.get(SIGNATURE_FIELD)):
		doc.signed_by = frappe.session.user if doc.get(SIGNATURE_FIELD) else None
	else:
		doc.signed_by = before.get(SIGNER_FIELD)


def refuse_identity_change_in_review(doc):
	"""TASKS-387 (decision 321): in Pending Supervisor the lot, product and specification of a certificate are not
	changed, by any user (no role is exempt), on any path (the form, `frappe.client.save` / `submit` /
	`set_value`). What decides is the STORED state: a plain save that sends another state with a new lot in the same
	call (Pending Supervisor -> Approved, or -> Draft) is refused as well. The way to correct them is the workflow's
	"Return for correction" (Pending Supervisor -> Draft); in Draft they can be changed, and the changer becomes the
	filler. Called in `before_validate`, which runs for every save and submit."""
	before = _before(doc)
	if not before or cint(before.get("docstatus")) != 0:
		return
	if before.get(STATE_FIELD[doc.doctype]) != PENDING_SUPERVISOR:
		return
	changed = identity_changes(doc)
	if changed:
		frappe.throw(
			_(
				'{0} {1} is {2}: its {3} cannot be changed in this state. Use "{4}" to take it back to Draft, correct it there and send it for review again.'
			).format(
				_(doc.doctype),
				doc.name,
				_(PENDING_SUPERVISOR),
				", ".join(changed),
				_(RETURN_FOR_CORRECTION),
			),
			title=_("Certificate under review"),
		)


def _note_filler_on_stored(parenttype, parent):
	"""For a row saved by itself (the two row hooks below): the session user becomes the stored certificate's
	`filled_by` and is added to its stored `fillers_since_draft` (TASKS-390, decision 337), in one write, in the
	same transaction as the row."""
	user = frappe.session.user
	stored = frappe.db.get_value(parenttype, parent, FILLERS_FIELD)
	frappe.db.set_value(parenttype, parent, {"filled_by": user, FILLERS_FIELD: with_filler(stored, user)})


def note_filler_of_row(doc, method=None):
	"""doc_events hook on the result row DocType (`before_validate`, `on_trash`): a result row saved, inserted or
	deleted BY ITSELF does not pass through the certificate's `validate`, so `set_filled_by` never sees it. When
	such a save changes the results (a field the evaluation reads differs from the stored row, the row is new, or
	it is deleted: the same rule as `results_changed`), the certificate the row belongs to (the one sent and the
	one stored) gets the session user as `filled_by`, and a COA AMB loses its stored signature and signer
	(`_clear_stored_signature`, TASKS-388 decision 331). Rows of any other parent are not touched. A save of the
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
		_note_filler_on_stored(parenttype, parent)
		_clear_stored_signature(parenttype, parent, _("its results"))  # TASKS-388 (decision 331)


def note_customer_row(doc, method=None):
	"""TASKS-387 (decision 321), doc_events hook on the customers row DocType (`Customer Item`; `before_validate`,
	`on_trash`): a row of a certificate's customers list saved, inserted or deleted BY ITSELF does not pass through
	the certificate's save. When it changes the list (a new row, a deleted row, any field of the row, or the row
	moved to another parent), the certificate it belongs to (the one sent and the one stored) is refused when it is
	Approved (the lock), else gets the session user as `filled_by` and loses its stored signature and signer
	(TASKS-388, decision 331), as `note_filler_of_row` does for a result row.
	Rows of any other parent (an Item, a specification) are not judged."""
	stored = None
	if doc.get("name") and not doc.is_new():
		stored = frappe.db.get_value(doc.doctype, doc.get("name"), "*", as_dict=True)
	owners = set()
	if method != "on_trash":
		owners.add((doc.get("parenttype"), doc.get("parent")))
	if stored:
		owners.add((stored.get("parenttype"), stored.get("parent")))
	owners = sorted(o for o in owners if o[0] in STATE_FIELD and o[1])
	if not owners:
		return
	if method == "on_trash":
		changed = bool(stored)
	else:
		changed = (
			not stored
			or any(cstr(stored.get(f)) != cstr(doc.get(f)) for f in ("parent", "parenttype", "parentfield"))
			or _rows_differ([stored], [doc], doc.doctype)
		)
	if not changed:
		return
	for parenttype, parent in owners:
		state = frappe.db.get_value(parenttype, parent, [STATE_FIELD[parenttype], "docstatus"], as_dict=True)
		if state and cint(state.get("docstatus")) == 0 and state.get(STATE_FIELD[parenttype]) == APPROVED:
			frappe.throw(
				_(
					"{0} {1} is Approved: its customers list cannot be changed. A Quality Manager must Reject it to Draft first."
				).format(_(parenttype), parent),
				title=_("Approved certificate"),
			)
	for parenttype, parent in owners:
		_note_filler_on_stored(parenttype, parent)
		_clear_stored_signature(parenttype, parent, _("its customers list"))  # TASKS-388 (decision 331)


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


def is_share(doc):
	"""This save submits a certificate whose stored state is Approved (COA AMB: the workflow's share, Approved ->
	Certificate Shared; every other submit from Approved is refused by the lock)."""
	return cint(doc.docstatus) == 1 and _was_approved(_before(doc))


# TASKS-387 (decision 322): what the share may change. Not compared at the share:
# - the state field and `docstatus` (the share's own move), `modified` / `modified_by` (written by the framework in
#   every save, before any rule runs);
# - the framework's metadata columns `_user_tags`, `_comments`, `_assign`, `_liked_by`, `_seen`: tags, the comment
#   cache, assignments, likes and views are written by the framework outside the certificate's save (`db.set_value`,
#   and `_seen` by `reset_seen` at the start of this very save); they are not part of what is certified, and a form
#   read before a comment was added would otherwise not be shared;
# - what this save derives from the stored rows: the result fields, recomputed from the same rows in `validate`
#   (`evaluate_overall_result`), and the `status` of each test row (written by the evaluation and by
#   `evaluate_formula_parameters`, never read by them);
# - what this save writes from the stored certificate whatever the caller sends: `filled_by` (`set_filled_by`: the
#   results, customers and identity are unchanged, so the stored one), `approved_by` / `approval_date`
#   (`set_approval`: the stored ones), `signed_by` (`set_signed_by`: the signature is unchanged, so the stored one).
# Everything else is compared, the framework's `name`, `owner`, `creation`, `idx`, and each row's `idx`, `parent`,
# `parentfield`, `parenttype`, `owner` and `creation` included. The QR token and the shared PDF are written in
# `on_submit`, AFTER this comparison (`coa_qr.on_coa_submit`: the token by `db.set_value`, the PDF as an attached
# File): the token sent in the share must still be the stored one, and the PDF is no field of the certificate.
# Also after it, in `before_save`: `set_coa_number` (only when the number is empty) and `set_approval_info` (only
# when the approval date is empty).
SHARE_UNCOMPARED_FIELDS = frozenset(
	("docstatus", "modified", "modified_by", "_user_tags", "_comments", "_assign", "_liked_by", "_seen")
)
SHARE_DERIVED_FIELDS = frozenset(
	("overall_result", "compliance_status", "failed_parameters", "pass_percentage", "tested_percentage")
).union(("filled_by", FILLERS_FIELD, "approved_by", "approval_date", SIGNER_FIELD))
SHARE_UNCOMPARED_ROW_FIELDS = frozenset(("docstatus", "modified", "modified_by"))
SHARE_DERIVED_ROW_FIELDS = {RESULT_ROW_DOCTYPE: frozenset(("status",))}


# TASKS-388 (decision 332): the fields of both certificates that the framework fetches from the specification
# (`fetch_from: linked_tds.<field>`), as shipped in coa_amb.json and coa_amb2.json. In a save at docstatus 0 the
# framework writes them before any rule runs (`BaseDocument.get_invalid_links`, called by `_validate_links`): the
# first group always (the value sent is overwritten), the second ("fetch if empty") only when the value is empty.
# At docstatus 1 (the share) it writes none of them. Named here so that a document built without the database (a
# test) is judged as on a site; on a site the DocType's description is read as well.
REFETCHED_CERTIFICATE_FIELDS = (
	"product_item",
	"item_name",
	"item_code",
	"tds_settings",
	"tds_naming_series",
	"tds_version",
	"tds_sequence",
)
FETCHED_IF_EMPTY_CERTIFICATE_FIELDS = (
	"cas_number",
	"inci_name",
	"shelf_life",
	"packaging",
	"storage_and_handling_conditions",
	"formula_based_criteria",
)


def _fetch_fields(doctype):
	"""({field: df} fetched on every draft save, {field: df} fetched when empty) of a DocType, from its description
	when the site has one, and the shipped fields of the certificates named above."""
	always = {f: _dict(fieldname=f, fetch_from=f"linked_tds.{f}") for f in REFETCHED_CERTIFICATE_FIELDS}
	if_empty = {
		f: _dict(fieldname=f, fetch_from=f"linked_tds.{f}", fetch_if_empty=1)
		for f in FETCHED_IF_EMPTY_CERTIFICATE_FIELDS
	}
	meta = frappe.get_meta(doctype)
	if callable(getattr(meta, "get", None)):
		for df in meta.get("fields") or []:
			if df.get("fetch_from"):
				(if_empty if df.get("fetch_if_empty") else always)[df.get("fieldname")] = df
				(always if df.get("fetch_if_empty") else if_empty).pop(df.get("fieldname"), None)
	return always, if_empty


def _fetched_from_empty(doc, before, df):
	"""A "fetch if empty" field that was empty in the stored certificate and now holds exactly what the framework
	fetches into it in this save (Frappe's own `set_fetch_from_value`, on the value read from the linked record):
	the server's write, not the caller's. The link is the stored one; a change of the link is compared by itself."""
	if cstr(before.get(df.fieldname)).strip() or not cstr(doc.get(df.fieldname)).strip():
		return False
	link_field, source = df.fetch_from.split(".", 1)
	link = doc.get(link_field)
	if not link or cstr(link) != cstr(before.get(link_field)):
		return False
	link_doctype = SPECIFICATION_DOCTYPE
	meta = frappe.get_meta(doc.doctype)
	if callable(getattr(meta, "get_field", None)) and meta.get_field(link_field):
		link_doctype = meta.get_field(link_field).options or link_doctype
	values = frappe.db.get_value(link_doctype, link, [source], as_dict=True)
	if not values:
		return False
	from frappe.model.base_document import BaseDocument

	probe = SimpleNamespace()
	BaseDocument.set_fetch_from_value(probe, link_doctype, df, values)
	return cstr(getattr(probe, df.fieldname, None)) == cstr(doc.get(df.fieldname))


def _first_difference_at_share(doc, before, refetched=False):
	"""The first difference between this save and the stored certificate, as text, or None. Parent fields first (in
	the DocType's order), then each table: its number of rows, the name of each row in its place, then each field.

	`refetched` (TASKS-388, decision 332: a save at docstatus 0, where the framework fetches before any rule runs):
	the fields it always fetches, of the certificate and of each row (`_fetch_fields`, `_fetched_row_fields`), are
	not compared, and a "fetch if empty" field is not a difference when it was empty and now holds what the framework
	fetches into it (`_fetched_from_empty`)."""
	description = _description(doc.doctype)
	ignore = SHARE_UNCOMPARED_FIELDS | SHARE_DERIVED_FIELDS | {STATE_FIELD[doc.doctype]}
	fetched_if_empty = {}
	if refetched:
		always, fetched_if_empty = _fetch_fields(doc.doctype)
		ignore = ignore | set(always)
	if description:
		columns, types, tables = description
	else:
		tables = [
			(f, None)
			for f in dict.fromkeys(
				[k for k, v in (before.items() if isinstance(before, dict) else []) if isinstance(v, list)]
				+ [k for k, v in getattr(doc, "__dict__", {}).items() if isinstance(v, list)]
			)
		]
		table_names = {t for t, _o in tables}
		columns = [
			f for f in dict.fromkeys(_plain_fields(before) + _plain_fields(doc)) if f not in table_names
		]
		types = dict(STANDARD_FIELD_TYPES)
	for f in columns:
		if f in ignore:
			continue
		if _comparable(before.get(f), types.get(f)) != _comparable(doc.get(f), types.get(f)):
			if f in fetched_if_empty and _fetched_from_empty(doc, before, fetched_if_empty[f]):
				continue
			return _("field {0}").format(f)
	for table, row_doctype in tables:
		old_rows, new_rows = list(before.get(table) or []), list(doc.get(table) or [])
		if len(old_rows) != len(new_rows):
			return _("table {0}: {1} rows instead of the {2} stored").format(
				table, len(new_rows), len(old_rows)
			)
		row_description = _description(row_doctype) if row_doctype else None
		row_types = row_description[1] if row_description else dict(STANDARD_FIELD_TYPES)
		row_ignore = SHARE_UNCOMPARED_ROW_FIELDS | SHARE_DERIVED_ROW_FIELDS.get(row_doctype, frozenset())
		if not row_doctype and table == RESULT_TABLE:
			row_ignore = row_ignore | SHARE_DERIVED_ROW_FIELDS[RESULT_ROW_DOCTYPE]
		if refetched:
			row_ignore = row_ignore | set(_fetched_row_fields(row_doctype))
		for place, (old, new) in enumerate(zip(old_rows, new_rows, strict=True), 1):
			if cstr(old.get("name")) != cstr(new.get("name")):
				return _("table {0}, row {1}: row {2} instead of the stored row {3}").format(
					table, place, new.get("name") or _("(new)"), old.get("name")
				)
			fields = (
				row_description[0]
				if row_description
				else list(dict.fromkeys(_plain_fields(old) + _plain_fields(new)))
			)
			for f in fields:
				if f in row_ignore:
					continue
				if _comparable(old.get(f), row_types.get(f)) != _comparable(new.get(f), row_types.get(f)):
					return _("table {0}, row {1} ({2}): field {3}").format(table, place, old.get("name"), f)
	return None


def refuse_changes_at_share(doc):
	"""TASKS-387 (decision 322): the share of a COA AMB (stored Approved at docstatus 0 -> docstatus 1) changes
	nothing of the certificate but its state: every parent field and every row of every child table (all its
	fields, the rows matched by their name in their place, their number too) is compared with the stored Approved
	certificate, and the first difference is refused by name. What is not compared is listed above
	(`SHARE_UNCOMPARED_FIELDS`, `SHARE_DERIVED_FIELDS`, the rows' own). The form's share (`apply_workflow`) reloads the
	certificate from the database and passes; a direct `frappe.client.submit` / `save` carries what the caller sent.
	Called in `before_validate`, which runs also when `validate` is skipped; the result rows keep their own message
	first (`refuse_changed_results_at_share`)."""
	if not is_share(doc):
		return
	refuse_changed_results_at_share(doc)
	difference = _first_difference_at_share(doc, _before(doc))
	if difference:
		frappe.throw(
			_(
				"{0} {1} is Approved: it is shared exactly as it was approved, and this save changes {2}. Nothing was shared. To change it, a Quality Manager must Reject it to Draft first."
			).format(_(doc.doctype), doc.name, difference),
			title=_("Approved certificate"),
		)


def refuse_changes_leaving_approved(doc):
	"""TASKS-388 (decision 332): the save that takes a certificate from the stored state Approved (docstatus 0) to
	another state at docstatus 0 (the workflow's Reject, or a plain save that sends another state) changes nothing
	but the state. The share's comparison is used (`_first_difference_at_share`): every parent field and every row of
	every table against the stored certificate, the first difference refused by name, with the share's exclusions
	(the derived fields include `approved_by` / `approval_date`, which `set_approval` empties in this save, and
	`filled_by` / `signed_by`, which stay as stored), and, because the framework fetches at docstatus 0 before any
	rule runs, what it fetches (`refetched`). The withdrawal of the lot is as before (`note_lot_move`, `write_lot`).
	Corrections are made afterwards, in Draft. Both certificates, every role and path; in `before_validate`."""
	if not leaves_approved(doc):
		return
	difference = _first_difference_at_share(doc, _before(doc), refetched=True)
	if difference:
		frappe.throw(
			_(
				"{0} {1} is Approved: going back to {2} changes nothing but its state, and this save changes {3}. Nothing was saved. Take it back first (the workflow's Reject), then correct it in Draft."
			).format(_(doc.doctype), doc.name, _(state_of(doc) or ""), difference),
			title=_("Approved certificate"),
		)


def _state_docstatus(doctype, state):
	"""The docstatus the certificate's active workflow gives a state (0, 1 or 2), else None (no workflow, or a
	state the workflow does not have)."""
	workflow = frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1}, "name")
	if not workflow:
		return None
	for row in frappe.get_cached_doc("Workflow", workflow).get("states") or []:
		if row.get("state") == state:
			return cint(row.get("doc_status"))
	return None


def refuse_draft_in_submitted_state(doc):
	"""TASKS-387 (decision 322): a save at docstatus 0 does not take a certificate INTO a state that its workflow
	gives docstatus 1 (COA AMB: Certificate Shared). Without this, a plain save from the stored state Approved with
	that state and docstatus 0 passed the lock and the workflow check, counted as leaving Approved (so it withdrew
	the lot) and left a draft in a submitted state. The state's docstatus is read from the workflow. A save that
	keeps the stored state is not judged here. Both certificates; every role."""
	if cint(doc.docstatus) != 0:
		return
	state = state_of(doc)
	before = _before(doc)
	if not state or (before and before.get(STATE_FIELD[doc.doctype]) == state):
		return
	if _state_docstatus(doc.doctype, state) == 1:
		frappe.throw(
			_(
				"{0} {1} cannot be saved as {2} without being submitted: in its workflow {2} is a submitted state. Use the workflow's action."
			).format(_(doc.doctype), doc.name or "", _(state)),
			title=_("Workflow state"),
		)


def lot_records(lot):
	"""TASKS-387 (decision 323): the lot record and every record below it, read level by level through
	`parent_batch_amb` (at most `LOT_LEVELS_BELOW` levels below; a record met twice is not read again, so a loop in
	the data ends). On a site whose lot records have no parent field, the record alone."""
	if not lot:
		return []
	records, level = [lot], [lot]
	if not frappe.get_meta(LOT_DOCTYPE).has_field(LOT_PARENT_FIELD):
		return records
	seen = {lot}
	for _depth in range(LOT_LEVELS_BELOW):
		below = [
			name
			for name in frappe.get_all(LOT_DOCTYPE, filters={LOT_PARENT_FIELD: ["in", level]}, pluck="name")
			if name not in seen
		]
		if not below:
			break
		seen.update(below)
		records.extend(below)
		level = below
	return records


def lot_batches(lot):
	"""The names of the native Batches of a lot record AND of every record below it (TASKS-387, decision 323:
	amb_w_spc's projection links a Batch to a level-2 record, so a lot (level 1) has Batches only through its
	sub-lots; `lot_records`). On a site where `Batch` has no `custom_batch_amb` (the projection of amb_w_spc is not
	installed) no Batch belongs to a lot, so the list is empty and the two checks that read it find nothing: that is
	said here, not hidden; any error of the read itself is raised."""
	if not lot or not frappe.get_meta("Batch").has_field(BATCH_LOT_FIELD):
		return []
	return frappe.get_all("Batch", filters={BATCH_LOT_FIELD: ["in", lot_records(lot)]}, pluck="name")


def approvable_lot_batches(doc):
	"""TASKS-390 (decision 335): the Batches the two approval checks read (`lot_batches`), failing CLOSED. A
	certificate that names a lot record is refused, with its own message, when the site's `Batch` has no
	`custom_batch_amb` field (no Batch can name a lot there), or when no Batch is linked to the record or to any record
	below it: in both cases the Rejected-inspection and open-Non-Conformance checks could not be run, and an empty
	answer would pass them. Every role. A certificate that names no lot releases no lot and reads no Batch (as
	before)."""
	lot = doc.get("batch_reference")
	if not lot:
		return []
	if not frappe.get_meta("Batch").has_field(BATCH_LOT_FIELD):
		_refuse(
			doc,
			_(
				"on this site Batch has no field {0}, so no stock Batch can be linked to lot record {1}: the inspection and non-conformance checks cannot be run."
			).format(BATCH_LOT_FIELD, lot),
		)
	batches = lot_batches(lot)
	if not batches:
		_refuse(
			doc,
			_(
				"no stock Batch is linked to lot record {0} or below it: the inspection and non-conformance checks cannot be run."
			).format(lot),
		)
	return batches


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
				"it is not recorded who entered its results (it was filled before this was recorded), so the approver cannot be told apart from that person. A person other than the approver must re-enter or confirm a result: the save in which a result changes records who made it (a save that changes nothing records no one), and that person cannot approve it. Then another person approves."
			),
		)
	if doc.get("filled_by") == frappe.session.user:
		_refuse(
			doc,
			_(
				"you entered or changed its results last (or its customers list, lot, product or specification); another person must approve it."
			),
		)
	# TASKS-390 (decision 337): not only the last filler; everyone who filled since it last entered Draft.
	if frappe.session.user in fillers_of(doc.get(FILLERS_FIELD)):
		_refuse(
			doc,
			_(
				"you changed its results, customers list, lot, product or specification since it last entered Draft; a person who changed none of them must approve it."
			),
		)
	if doc.doctype in SIGNED_CERTIFICATES:
		if not doc.get(SIGNATURE_FIELD):
			_refuse(doc, _("it is not signed. Sign it, save, then approve."))
		if doc.get(SIGNER_FIELD) != frappe.session.user:
			_refuse(
				doc,
				_(
					"its signature was not drawn by you. Sign it yourself as approver: draw your signature, save, then approve. A signature drawn before the signer was recorded, or copied into a new certificate, has no recorded signer and must be drawn again by the approver."
				),
			)
		if not [row for row in (doc.get(CUSTOMERS_TABLE) or []) if row.get("customer")]:
			_refuse(doc, _("its customers list is empty."))
	batches = approvable_lot_batches(doc)
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
	save that sets or changes the lot or the product.

	Not in the share: there the stored Work Order stays (TASKS-387, decision 322). Nor in the save that takes an
	Approved certificate back (TASKS-388, decision 332: it changes only the state); the next save in Draft follows the
	lot."""
	if is_share(doc) or leaves_approved(doc):
		return  # the share and the Reject keep the stored Work Order (decisions 322, 332)
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
	"""TASKS-384 B2, decisions 317 and 320: the product decides the type of its certificate, through the Item's own
	"Allow Sales" check (see `amb_w_tds.api.certificate.certificate_type_for_item`). Judged when the certificate is
	made and when its product changes; a stored certificate whose product stays is not judged again, so its workflow
	is not stopped by a later change of the check on the Item. A product that is not an Item is not judged here."""
	before = _before(doc)
	product = doc.get("product_item")
	if not product or (before and before.get("product_item") == product):
		return
	from amb_w_tds.api.certificate import ALLOW_SALES_LABEL, CUSTOMER_CERTIFICATE, certificate_type_for_item

	expected = certificate_type_for_item(product)
	if expected and expected != doc.doctype:
		frappe.throw(
			_(
				'Product {0} takes a {1}, not a {2}: the "{3}" check on Item {0} is {4}. Make its certificate as {1}, or, if the check is wrong, correct it on the Item first.'
			).format(
				product,
				_(expected),
				_(doc.doctype),
				_(ALLOW_SALES_LABEL),
				_("on") if expected == CUSTOMER_CERTIFICATE else _("off"),
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


def standing_certificates(lot, doctype, name):
	"""TASKS-390 (decision 338): EVERY other certificate of the same lot record that still stands (the definition of
	`standing_certificate` below, unchanged), the one approved last first (then saved last). Returned as a list of
	{"doctype", "name", "result"}, empty when none stands. Passed to amb_w_spc as `others` at an approval and as
	`standing` at a withdrawal, where the record takes the worst of them."""
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
	found.sort(key=lambda f: f[:3], reverse=True)
	return [
		{"doctype": certificate_doctype, "name": row.get("name"), "result": row.get("overall_result")}
		for _approved, _modified, certificate_doctype, row in found
	]


def standing_certificate(lot, doctype, name):
	"""ANOTHER certificate of the same lot record, of either type, that still stands: Approved and not submitted,
	or (COA AMB) Certificate Shared and not cancelled, with a result that maps to a lot status, AND approved by
	the two-person rule: it records who approved it and who filled it, and the two differ. A certificate in one of
	those states without that record (one written past the approval, or approved before `filled_by` existed) does
	not stand: it cannot decide the status of a lot when another certificate is taken back. Returned as
	{"doctype", "name", "result"}, or None. When several stand, the one approved last (then saved last) is taken
	(the first of `standing_certificates`). Since TASKS-390 the two calls to amb_w_spc pass them all."""
	found = standing_certificates(lot, doctype, name)
	return found[0] if found else None


def write_lot(doc):
	"""TASKS-384 B3, `on_update` of both certificates: carry out what `note_lot_move` decided. A certificate that
	names no lot has nothing to write. NO try/except: if the lot cannot be written the exception leaves this save
	and the certificate's own write is rolled back with it; the user sees why."""
	move = getattr(doc, "_lot_move", None)
	doc._lot_move = None
	if not move or not move[1]:
		return
	kind, lot = move
	# TASKS-390 (decision 338): every other certificate that stands for the record is passed, so that amb_w_spc gives
	# the record the worst of them (Failed over Hold over Passed).
	others = standing_certificates(lot, doc.doctype, doc.name)
	if kind == "approved":
		_spc("certificate_approved")(doc.doctype, doc.name, lot, doc.get("overall_result"), others=others)
	else:
		_spc("certificate_withdrawn")(doc.doctype, doc.name, lot, standing=others)


def withdraw_on_cancel(doc):
	"""TASKS-384 B3, `on_cancel` of COA AMB: a shared certificate that is cancelled no longer stands for its lot.
	amb_w_spc resets only what this certificate wrote. No try/except, as in `write_lot`."""
	lot = doc.get("batch_reference")
	if not lot:
		return
	_spc("certificate_withdrawn")(
		doc.doctype, doc.name, lot, standing=standing_certificates(lot, doc.doctype, doc.name)
	)


def share_summary(doc):
	"""TASKS-390 (decision 334), `on_submit` of COA AMB (the share, Approved -> Certificate Shared): one summary of
	the share, sent by amb_w_spc under the rules of a release (`certificate_shared`: the filler, the user who shared and
	the lot's Work Order owner; queued; muted or no account noted on the lot's history; never fails the share; it
	writes no lot status). It replaces the old `notify_quality_team`. Looked up late (`_spc`), like the two lot
	writes; a certificate that names no lot has nothing to tell. No try/except around the call."""
	lot = doc.get("batch_reference")
	if not lot:
		return
	_spc("certificate_shared")(doc.doctype, doc.name, lot)


def apply(doc):
	"""Called by `validate` of both certificates, after the result was derived from the rows."""
	refuse_submit_unless_approved(doc)
	refuse_changed_results_at_share(doc)
	refuse_wrong_type(doc)
	refuse_lot_level(doc)
	follow_lot(doc)
	filling = set_filled_by(doc)
	set_signed_by(doc)
	# TASKS-388 (decision 331): after `set_signed_by`, so the clear wins over a signature drawn in the same save.
	clear_signature_on_filling(doc, filling)
	set_approval(doc)
	note_lot_move(doc)


def before_validate(doc):
	"""TASKS-387: called by `before_validate` of both certificates, after the Approved lock. `before_validate` runs
	for every save and submit, also when the caller skips `validate`."""
	refuse_draft_in_submitted_state(doc)
	refuse_identity_change_in_review(doc)
	refuse_changes_at_share(doc)
	refuse_changes_leaving_approved(doc)  # TASKS-388 (decision 332)
