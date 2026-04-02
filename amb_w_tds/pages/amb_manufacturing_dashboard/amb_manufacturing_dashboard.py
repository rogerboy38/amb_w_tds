# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
    """Render Manufacturing Dashboard"""
    # Get all batches with their pipeline status
    batches = frappe.get_all(
        "Batch AMB",
        fields=["name", "batch_id", "item_name", "pipeline_status", "custom_batch_level", "creation"],
        order_by="creation desc",
        limit=100
    )
    
    # Group by status
    status_counts = {}
    for batch in batches:
        status = batch.pipeline_status or "Not Started"
        status_counts[status] = status_counts.get(status, 0) + 1
    
    context.batches = batches
    context.status_counts = status_counts
    context.title = "AMB Manufacturing Dashboard"
