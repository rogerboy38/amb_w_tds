"""One Batch Reference picker for COA AMB and COA AMB2 (13.12.2).

Both forms call `search_batches` through `frm.set_query('batch_reference', {query: ...})`, so the terms live here
and nowhere else. The 13.12.0/13.12.1 pickers were two copies of each other: COA AMB2 kept `docstatus = 1`, a
state Batch AMB (not submittable) never reaches, so it listed nothing.

Terms: the batch is not Cancelled and its quality status is Pending, Hold or not yet set. There is NO item filter:
the product on a COA and the item on a batch sit at different levels of the Item tree, so each line shows the
batch's item and the person chooses.
"""

import frappe

BATCH_DOCTYPE = "Batch AMB"
# `quality_status` is a Select of Pending / Passed / Failed / Hold; "" stands for a batch nobody has assessed yet.
QUALITY_STATUSES = ["Pending", "Hold", ""]
CANCELLED = "Cancelled"
SEARCH_FIELDS = ["name", "title", "custom_golden_number", "item_to_manufacture"]


def picker_filters():
    """The fixed terms, as get_list filters (kept in one function so a test can pin them)."""
    return [
        [BATCH_DOCTYPE, "batch_status", "!=", CANCELLED],
        [BATCH_DOCTYPE, "quality_status", "in", QUALITY_STATUSES],
    ]


@frappe.whitelist()
def search_batches(doctype=None, txt="", searchfield=None, start=0, page_len=20, filters=None):
    """Link-search query (the signature `frappe.desk.search` calls). Rows: (batch, item, "quality / batch status")."""
    txt = (txt or "").strip()
    or_filters = [[BATCH_DOCTYPE, f, "like", f"%{txt}%"] for f in SEARCH_FIELDS] if txt else None
    rows = frappe.get_list(
        BATCH_DOCTYPE,
        filters=picker_filters(),
        or_filters=or_filters,
        fields=["name", "item_to_manufacture", "quality_status", "batch_status"],
        order_by="creation desc, name desc",
        start=int(start or 0),
        page_length=int(page_len or 20),
    )
    return [
        (r.name, r.item_to_manufacture or "-", f"{r.quality_status or '-'} / {r.batch_status or '-'}")
        for r in rows
    ]
