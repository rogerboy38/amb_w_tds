# Phase 12.5 - Pipeline Hooks for Document Auto-Linking
# Auto-links Stock Entry, Quality Inspection, Delivery Note to Batch AMB pipeline

import frappe


def on_stock_entry_submit(doc, method):
    """
    Stock Entry on_submit hook:
    - If purpose=Manufacture, find/create L1 Batch AMB
    - Set pipeline_status=In Production
    """
    if doc.purpose != "Manufacture":
        return

    # Try to find linked Batch AMB
    batch_amb = None
    if doc.batch_amb_reference:
        batch_amb = doc.batch_amb_reference
    elif doc.work_order:
        # Find Batch AMB linked to Work Order
        batches = frappe.get_all(
            "Batch AMB",
            filters={"work_order": doc.work_order, "custom_batch_level": "1"},
            order_by="creation desc",
            limit=1
        )
        if batches:
            batch_amb = batches[0].name

    if batch_amb:
        frappe.db.set_value("Batch AMB", batch_amb, "pipeline_status", "In Production")
        frappe.publish_realtime(
            "batch_amb_updated",
            {"batch": batch_amb, "status": "In Production"},
            after_commit=True
        )


def on_quality_inspection_submit(doc, method):
    """
    Quality Inspection on_submit hook:
    - If linked to Batch AMB, set pipeline_status=Quality Check
    """
    if not doc.batch_amb_reference:
        return

    frappe.db.set_value(
        "Batch AMB", 
        doc.batch_amb_reference, 
        "pipeline_status", 
        "Quality Check"
    )
    frappe.publish_realtime(
        "batch_amb_updated",
        {"batch": doc.batch_amb_reference, "status": "Quality Check"},
        after_commit=True
    )


def on_delivery_note_submit(doc, method):
    """
    Delivery Note on_submit hook:
    - If linked to Batch AMB, set pipeline_status=Shipped
    """
    if not doc.batch_amb_reference:
        return

    frappe.db.set_value(
        "Batch AMB",
        doc.batch_amb_reference,
        "pipeline_status",
        "Shipped"
    )
    frappe.publish_realtime(
        "batch_amb_updated",
        {"batch": doc.batch_amb_reference, "status": "Shipped"},
        after_commit=True
    )
