app_name = "amb_w_tds"
app_version = "9.2.0"
app_title = "AMB W TDS"
app_publisher = "AMB WELLNESS"
app_description = "AMB WELLNESS TDS + Migration + Quotation AMB system"
app_email = "support@amb-wellness.com"
app_license = "MIT"

# ========================================
#  MODULE LOAD + PATCH PREPARATION
# ========================================

# register custom DocTypes for override / extension
doctype_class = {
    "Batch AMB":  "amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.BatchAMB"
}

# Override DocTypes to prevent orphan deletion (Frappe GitHub Issue #37799)
# These custom DocTypes must be explicitly mapped to their class to prevent
# bench migrate from incorrectly deleting them as "orphans"
override_doctype_class = {
    "Sample Request AMB": "amb_w_tds.amb_w_tds.doctype.sample_request_amb.sample_request_amb.SampleRequestAMB",
    "Sample Request AMB Item": "amb_w_tds.amb_w_tds.doctype.sample_request_amb_item.sample_request_amb_item.SampleRequestAMBItem",
    "RND Parent DocType": "amb_w_tds.amb_w_tds.doctype.rnd_parent_doctype.rnd_parent_doctype.RNDParentDocType",
    "Production Plant AMB": "amb_w_tds.amb_w_tds.doctype.production_plant_amb.production_plant_amb.ProductionPlantAMB",
    "Lote AMB": "amb_w_tds.amb_w_tds.doctype.lote_amb.lote_amb.LoteAMB",
    "Third Party API": "amb_w_tds.amb_w_tds.doctype.third_party_api.third_party_api.ThirdPartyAPI",
    "KPI Cost Breakdown": "amb_w_tds.amb_w_tds.doctype.kpi_cost_breakdown.kpi_cost_breakdown.KPICostBreakdown",
    "COA AMB2": "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2.COAMB2",
}

# ========================================
#  FRONTEND JS INJECTIONS
# ========================================

# Doctype-specific JS (loaded dynamically per doctype - works in Docker AND sandbox)
doctype_js = {
    # Original doctype scripts (RESTORED - DO NOT REMOVE)
    "Quotation AMB": "amb_w_tds/amb_w_tds/doctype/quotation_amb/quotation_amb.js",
    "Batch AMB": "amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js",
    "Work Order": "amb_w_tds/public/js/work_order_list.js",
    # Sample Request buttons (loaded via doctype_js - works in Docker without bench build)
    "Lead": "amb_w_tds/public/js/sample_request_buttons.js",
    "Prospect": "amb_w_tds/public/js/sample_request_buttons.js",
    "Opportunity": "amb_w_tds/public/js/sample_request_buttons.js",
    "Quotation": "amb_w_tds/public/js/sample_request_buttons.js",
    "Sales Order": "amb_w_tds/public/js/sample_request_buttons.js",
}

# Global app-level JS bundles (compiled by bench build)
app_include_js = [
    "/assets/amb_w_tds/js/batch_widget.js",
]

# ========================================
#  DOCUMENT EVENTS (Critical migration hooks)
# ========================================

doc_events = {

    # ---- BOM validation hooks (Phase 5)
    "BOM": {
        "on_submit": "amb_w_tds.bom_hooks.on_bom_submit",
        "on_update": "amb_w_tds.bom_hooks.on_bom_update",
    },

    # ---- stock trace / costing / batch migrations
    "Stock Entry": {
        "on_submit": [
            # ""amb_w_tds.stock_entry_hooks.on_stock_entry_submit"",
            # ""amb_w_tds.raven.utils.on_stock_entry_submit""
        ],
        "before_insert": [
            # ""amb_w_tds.api.agent.pre_stock_entry_agent_validation""
        ],
    },

    # ---- AMB Quotation + Sales Partner auto mapping + idempotency
    "Quotation AMB": {

        # Idempotency + sales_partner assignment
        "before_insert": [
            # # ""amb_w_tds.api.agent.apply_agent_hooks"",
            # ""amb_w_tds.api.quotation_amb.idempotency_check""
        ],

        # logging + lineage trace + legacy ID mapping
        "before_save": [
            # ""amb_w_tds.api.agent.apply_activity_log"",
            # ""amb_w_tds.api.quotation_amb.audit_linkage""
        ],

        # enforce workflow + commission + agent
        "before_submit": [
            # ""amb_w_tds.api.quotation_amb.validate_commission"",
            # ""amb_w_tds.api.quotation_amb.ensure_sales_partner""
        ],
    },
}

# ========================================
#  SCHEDULER EVENTS (background consistency)
# ========================================
#
scheduler_events = {

    "hourly": [
        # "amb_w_tds.migration.resume_unfinished_migration",
        # "amb_w_tds.api.agent.hourly_sync_agents"
    ],

    "daily": [
        # "amb_w_tds.api.audit.daily_quotation_amb_log_rotation",
        # "amb_w_tds.migration.verify_pending_documents"
    ],

    "weekly": [
        # BOM Health Check - runs weekly (Phase 5)
        "amb_w_tds.scripts.scheduled_bom_health.run",
        # "amb_w_tds.agent.performance.weekly_commission_reconciliation",
        # "amb_w_tds.migration.cleanup_stale_migration_state"
    ],
}
#
# ========================================
# FIXTURES (sync mandatory custom fields)
# ========================================

fixtures = [

    # sales_partner + agent tracking required fields
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["Quotation AMB", "Quotation", "Batch AMB"]],
        ]
    },

    # AMB workflows + automatic migration workflow states
    {
        "doctype": "Workflow",
        "filters": [
            ["name", "like", "AMB%"]
        ]
    },
]

# ========================================
# Webhooks and Portal Exposure (future)
# ========================================

default_mail_footer = """
    <div>
        Document generated by AMB Frappe Cloud System
    </div>
"""

# ================================================
# FRAPPE MONKEY PATCHES (BOM Tree Fix v16)
# ================================================

override_whitelisted_methods = {
	"frappe.desk.treeview.get_all_nodes": "amb_w_tds.amb_w_tds.api.bom_tree_fix.get_all_nodes_fixed"
}

# ================================================
# WORKSPACE ORPHAN FIX (Frappe GitHub Issue #37799)
# This runs BEFORE migration to prevent Workspace deletion
# ================================================
before_migrate = [
    "amb_w_tds.install.before_migrate",
    "amb_w_tds.install.mark_doctypes_as_owned",
    "amb_w_tds.patches.fix_workspace_orphan.apply_patch"
]

# ================================================
# BUG 74: Add Sample Request AMB to Quotation Connections
# Shows Sample Request AMB links in Quotation's Connections tab
# ================================================
override_doctype_dashboards = {
    "Quotation": "amb_w_tds.amb_w_tds.utils.quotation_dashboard.get_dashboard_data"
}
