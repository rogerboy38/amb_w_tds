import frappe


def execute():
    """T-label Phase 2 - backfill Sample Request AMB related_to_type / related_to_doc
    from the legacy quotation / sales_order_related links.

    Precedence: Sales Order > Quotation. Idempotent: only fills rows whose
    related_to_doc is still empty, so re-running is safe. Legacy fields are kept
    (to be hidden later) for one release so a pre-flight count can verify the
    migration before they are dropped.
    """
    if not frappe.db.has_column("Sample Request AMB", "related_to_doc"):
        return

    rows = frappe.get_all(
        "Sample Request AMB",
        filters={"related_to_doc": ["in", [None, ""]]},
        or_filters=[
            ["sales_order_related", "is", "set"],
            ["quotation", "is", "set"],
        ],
        fields=["name", "sales_order_related", "quotation"],
    )

    fixed = 0
    for r in rows:
        if r.get("sales_order_related"):
            rt, rn = "Sales Order", r.sales_order_related
        elif r.get("quotation"):
            rt, rn = "Quotation", r.quotation
        else:
            continue
        frappe.db.set_value(
            "Sample Request AMB",
            r.name,
            {"related_to_type": rt, "related_to_doc": rn},
            update_modified=False,
        )
        fixed += 1

    frappe.db.commit()
    print("backfill_sr_related_to: filled %d Sample Request AMB row(s)" % fixed)
