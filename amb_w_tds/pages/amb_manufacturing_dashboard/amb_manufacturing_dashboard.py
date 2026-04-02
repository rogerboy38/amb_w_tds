# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.utils import nowdate, add_days


def get_context(context):
    """Get dashboard data"""
    context.brand_html = get_brand_html()
    context.stats = get_pipeline_stats()
    context.active_batches = get_active_batches()
    context.pending_actions = get_pending_actions()
    context.recent_activity = get_recent_activity()
    context.weight_summary = get_weight_summary()


def get_brand_html():
    """Dashboard header"""
    return """
    <div class="dashboard-header">
        <h1>🏭 AMB Manufacturing Dashboard</h1>
        <p class="text-muted">Real-time production overview</p>
    </div>
    """


def get_pipeline_stats():
    """Pipeline overview by status"""
    stats = {}
    statuses = ["Draft", "WO Linked", "In Production", "Weighing", "QI Pending", "QI Passed", "COA Ready", "Ready for Delivery", "Delivered", "Closed"]
    
    for status in statuses:
        count = frappe.db.count("Batch AMB", {"pipeline_status": status, "docstatus": ["!=", 2]})
        stats[status] = count
    
    return stats


def get_active_batches():
    """Active batches by level"""
    batches = frappe.get_all(
        "Batch AMB",
        filters={"docstatus": ["!=", 2], "pipeline_status": ["not in", ["Delivered", "Closed"]]},
        fields=["name", "title", "custom_batch_level", "pipeline_status", "item_to_manufacture", "total_net_weight", "modified"],
        order_by="modified desc",
        limit=20
    )
    return batches


def get_pending_actions():
    """Pending actions requiring attention"""
    actions = []
    
    # Batches awaiting WO
    wo_pending = frappe.get_all(
        "Batch AMB",
        filters={"docstatus": 0, "pipeline_status": "Draft", "work_order_ref": ["is", "not set"]},
        pluck="name",
        limit=5
    )
    for b in wo_pending:
        actions.append({"type": "warning", "batch": b, "action": "Link Work Order"})
    
    # Batches awaiting weighing
    weighing = frappe.get_all(
        "Batch AMB",
        filters={"docstatus": ["!=", 2], "pipeline_status": "In Production"},
        fields=["name", "total_net_weight"],
        limit=5
    )
    for b in weighing:
        if not b.total_net_weight or b.total_net_weight == 0:
            actions.append({"type": "info", "batch": b.name, "action": "Capture Weights"})
    
    # Batches awaiting QI
    qi_pending = frappe.get_all(
        "Batch AMB",
        filters={"docstatus": ["!=", 2], "pipeline_status": "Weighing"},
        pluck="name",
        limit=5
    )
    for b in qi_pending:
        actions.append({"type": "info", "batch": b, "action": "Submit for QI"})
    
    return actions[:10]


def get_recent_activity():
    """Recent batch modifications"""
    logs = frappe.get_all(
        "Batch AMB",
        filters={"docstatus": ["!=", 2]},
        fields=["name", "title", "pipeline_status", "modified"],
        order_by="modified desc",
        limit=10
    )
    return logs


def get_weight_summary():
    """Weight summary across all active batches"""
    summary = frappe.db.sql("""
        SELECT 
            SUM(total_gross_weight) as total_gross,
            SUM(total_net_weight) as total_net,
            SUM(total_tara_weight) as total_tara,
            COUNT(name) as batch_count,
            SUM(barrel_count) as barrel_count
        FROM `tabBatch AMB`
        WHERE docstatus != 2 AND pipeline_status NOT IN ('Delivered', 'Closed')
    """, as_dict=True)
    
    if summary:
        return summary[0]
    return {"total_gross": 0, "total_net": 0, "total_tara": 0, "batch_count": 0, "barrel_count": 0}
