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
            filters={"work_order_ref": doc.work_order, "custom_batch_level": "1"},
            limit=1,
            pluck="name"
        )
        if batches:
            batch_amb = batches[0]
    
    if batch_amb:
        try:
            batch = frappe.get_doc("Batch AMB", batch_amb)
            if hasattr(batch, "pipeline_status") and batch.pipeline_status == "WO Linked":
                batch.pipeline_status = "In Production"
                batch.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.msgprint(f"Batch {batch_amb} moved to In Production")
        except Exception as e:
            frappe.log_error(f"Pipeline hook error: {str(e)}")


def on_quality_inspection_submit(doc, method):
    """
    Quality Inspection on_submit hook:
    - Find linked Batch AMB
    - Update pipeline_status based on result
    """
    # Try to find linked Batch AMB
    batch_amb = None
    
    # Check various link fields
    if hasattr(doc, "batch_amb") and doc.batch_amb:
        batch_amb = doc.batch_amb
    elif hasattr(doc, "batch_no") and doc.batch_no:
        batch_amb = doc.batch_no
    elif hasattr(doc, "reference_name") and doc.reference_name:
        # Check if reference is a Batch AMB
        if frappe.db.exists("Batch AMB", doc.reference_name):
            batch_amb = doc.reference_name
    
    if batch_amb:
        try:
            batch = frappe.get_doc("Batch AMB", batch_amb)
            if hasattr(batch, "pipeline_status"):
                # Map inspection status to pipeline status
                if doc.inspection_type == "In Process":
                    if batch.pipeline_status in ["In Production", "Weighing"]:
                        batch.pipeline_status = "QI Pending"
                elif doc.status == "Accepted" or doc.inspection_type == "Final":
                    batch.pipeline_status = "QI Passed"
                elif doc.status == "Rejected":
                    # Keep in QI Pending for failed inspection
                    pass
                batch.save(ignore_permissions=True)
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"QI pipeline hook error: {str(e)}")


def on_delivery_note_submit(doc, method):
    """
    Delivery Note on_submit hook:
    - Find linked Batch AMB
    - Update pipeline_status to Delivered
    """
    # Try to find linked Batch AMB via items
    batch_amb = None
    
    for item in doc.items:
        if hasattr(item, "batch_no") and item.batch_no:
            # Check if batch_no is a Batch AMB
            if frappe.db.exists("Batch AMB", item.batch_no):
                batch_amb = item.batch_no
                break
        elif hasattr(item, "batch_amb") and item.batch_amb:
            batch_amb = item.batch_amb
            break
    
    if batch_amb:
        try:
            batch = frappe.get_doc("Batch AMB", batch_amb)
            if hasattr(batch, "pipeline_status"):
                if batch.pipeline_status in ["Ready for Delivery", "COA Ready", "QI Passed"]:
                    batch.pipeline_status = "Delivered"
                    batch.save(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.msgprint(f"Batch {batch_amb} marked as Delivered")
        except Exception as e:
            frappe.log_error(f"Delivery Note pipeline hook error: {str(e)}")
