"""One Batch Reference picker for COA AMB and COA AMB2 (13.12.2).

Both forms call `search_batches` through `frm.set_query('batch_reference', {query: ...})`, so the terms live here
and nowhere else. The 13.12.0/13.12.1 pickers were two copies of each other: COA AMB2 kept `docstatus = 1`, a
state Batch AMB (not submittable) never reaches, so it listed nothing.

Terms: the batch is not Cancelled and its quality status is Pending, Hold or not yet set. There is NO item filter:
the product on a COA and the item on a batch sit at different levels of the Item tree, so each line shows the
batch's item and the person chooses.

TASKS-384 B3/B4: a record whose status is INHERITED from the certificate of the lot above it is offered as well,
whatever that status is, so a sub-lot under a released lot can still get its own certificate. The two sets are read
with the same call each and merged (newest first), because one `get_list` cannot say "A or B" beside the text
search, which already is an "or". On a site where Batch AMB has no `status_source` field yet there is one read, as
before.
"""

import frappe

BATCH_DOCTYPE = "Batch AMB"
# `quality_status` is a Select of Pending / Passed / Failed / Hold; "" stands for a batch nobody has assessed yet.
QUALITY_STATUSES = ["Pending", "Hold", ""]
CANCELLED = "Cancelled"
# amb_w_spc's field that says who decides a record's status; "Inherited" = the certificate of the lot above it.
SOURCE_FIELD = "status_source"
INHERITED = "Inherited"
SEARCH_FIELDS = ["name", "title", "custom_golden_number", "item_to_manufacture"]


def picker_filters():
    """The fixed terms, as get_list filters (kept in one function so a test can pin them)."""
    return [
        [BATCH_DOCTYPE, "batch_status", "!=", CANCELLED],
        [BATCH_DOCTYPE, "quality_status", "in", QUALITY_STATUSES],
    ]


def inherited_filters():
    """The second set (TASKS-384): not Cancelled, and the status comes from the lot above."""
    return [
        [BATCH_DOCTYPE, "batch_status", "!=", CANCELLED],
        [BATCH_DOCTYPE, SOURCE_FIELD, "=", INHERITED],
    ]


def has_source_field():
    """False on a site where amb_w_spc has not added `status_source` to Batch AMB yet: nothing is Inherited there."""
    return bool(frappe.get_meta(BATCH_DOCTYPE).has_field(SOURCE_FIELD))


@frappe.whitelist()
def search_batches(doctype=None, txt="", searchfield=None, start=0, page_len=20, filters=None):
    """Link-search query (the signature `frappe.desk.search` calls). Rows: (batch, item, "quality / batch status")."""
    txt = (txt or "").strip()
    start, page_len = int(start or 0), int(page_len or 20)
    or_filters = [[BATCH_DOCTYPE, f, "like", f"%{txt}%"] for f in SEARCH_FIELDS] if txt else None
    fields = ["name", "item_to_manufacture", "quality_status", "batch_status"]
    order_by = "creation desc, name desc"

    def line(r):
        return (r.name, r.item_to_manufacture or "-", f"{r.quality_status or '-'} / {r.batch_status or '-'}")

    if not has_source_field():
        rows = frappe.get_list(
            BATCH_DOCTYPE,
            filters=picker_filters(),
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            start=start,
            page_length=page_len,
        )
        return [line(r) for r in rows]

    # Two reads, each from the top down to the end of the page asked for, merged in the same order (newest first,
    # then the name) and cut to the page: the page is the same as one query over "A or B" would give.
    merged = {}
    for terms in (picker_filters(), inherited_filters()):
        for r in frappe.get_list(
            BATCH_DOCTYPE,
            filters=terms,
            or_filters=or_filters,
            fields=[*fields, "creation"],
            order_by=order_by,
            start=0,
            page_length=start + page_len,
        ):
            merged.setdefault(r.name, r)
    rows = sorted(merged.values(), key=lambda r: (str(r.creation), r.name), reverse=True)
    return [line(r) for r in rows[start : start + page_len]]
