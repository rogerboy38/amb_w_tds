app_name = "amb_w_tds"
app_title = "AMB W TDS"
app_publisher = "AMB WELLNESS"
app_description = "AMB WELLNESS TDS + Migration + Quotation AMB system"
app_email = "support@amb-wellness.com"
app_license = "MIT"

# ========================================
#  MODULE LOAD + PATCH PREPARATION
# ========================================

# NOTE: Batch AMB controller migrated to amb_w_spc — see amb_w_spc/hooks.py.
#
# Donor-cleanup 2026-05-12: removed 43 lowercase_snake_case override_doctype_class entries.
# All keys used the wrong shape — Frappe expects "Title Case With Spaces" DocType names, not
# module slugs. 40 of those entries silently never matched anything (Frappe DB lookup returns
# no row for lowercase_snake_case names). The other 3 (`barrel`, `formulation`, `tds_settings`)
# matched DB rows via MariaDB case-insensitive collation but then triggered TypeError on
# `issubclass(custom_class_, None)` because vanilla class lookup was case-sensitive (modules
# had `Barrel` / `Formulation` / `TDSSettings`, not `barrel` / `formulation` / `tds_settings`).
# This caused SessionBootFailed runtime errors during desk render.
#
# If specific DocType behavior overrides are needed in amb_w_tds going forward, add them as
# `"Canonical DocType Name": "amb_w_tds....module...Class"` entries. For DocTypes migrated to
# amb_w_spc (Batch AMB, TDS Product Specification, etc.), the override belongs in amb_w_spc/hooks.py.
override_doctype_class = {}

# ========================================
#  FRONTEND JS INJECTIONS
# ========================================

# Sample Request buttons are now loaded via app_include_js (bundled approach)
# Removed doctype_js entries to avoid asset bundle issues

app_include_js = [
    # sample_request_*.js removed - owned by amb_w_spc
    # "/assets/amb_w_tds/js/sample_request_utils.js",
    # "/assets/amb_w_tds/js/sample_request_buttons.js"
]

# ========================================
#  DOCUMENT EVENTS (Critical migration hooks)
# ========================================

doc_events = {

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

    # Phase 1A Step 2B (relocated here Phase 1A.5) — TDS Product Specification form-derivation + flag-row handling.
    # custom=1 DocType so override_doctype_class is silently ignored; doc_events is the working hook.
    "TDS Product Specification": {
        "validate": [
            "amb_w_tds.overrides.tds_product_specification.derive_form",
        ],
        "before_save": [
            "amb_w_tds.overrides.tds_product_specification.propagate_flag_row_groups",
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

    # ---- Batch AMB: Controller migrated to amb_w_spc
    # "Batch AMB" doc_events removed - now handled by amb_w_spc
}

# ========================================
#  SCHEDULER EVENTS (background consistency)
# ========================================
#
#scheduler_events = {
#
#    "hourly": [
#        # ""amb_w_tds.migration.resume_unfinished_migration"",
#        # ""amb_w_tds.api.agent.hourly_sync_agents""
#    ],
#
#    "daily": [
#        # ""amb_w_tds.api.audit.daily_quotation_amb_log_rotation"",
#        # ""amb_w_tds.migration.verify_pending_documents""
#    ],
#
#    "weekly": [
#        # ""amb_w_tds.agent.performance.weekly_commission_reconciliation"",
#        # ""amb_w_tds.migration.cleanup_stale_migration_state""
#    ],
#}
#
# ========================================
#  FIXTURES (sync mandatory custom fields)
# ========================================

fixtures = [
    {"doctype": "Custom Field",           "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Property Setter",        "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Workflow",               "filters": [["document_type", "in", ["Custom Clearance","COA AMB","COA AMB2","TDS Product Specification","Direct Shipping"]]]},
    {"doctype": "Workflow State",         "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Workflow Action Master", "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Notification",           "filters": [["module", "=", "AMBWTDS"], ["is_standard", "=", 0]]},
    {"doctype": "Print Format",           "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Role",                   "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Client Script",       "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Server Script",       "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Workspace",          "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Dashboard Chart",        "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Number Card",        "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Report",        "filters": [["module", "=", "AMBWTDS"]]},
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
# DASHBOARD OVERRIDES FOR SAMPLE REQUEST AMB CONNECTIONS (Bug 87 series)
# ================================================

override_doctype_dashboards = {
    "Quotation": "amb_w_tds.amb_w_tds.utils.quotation_dashboard.get_data",
    "Lead": "amb_w_tds.amb_w_tds.utils.lead_dashboard.get_data",
    "Prospect": "amb_w_tds.amb_w_tds.utils.prospect_dashboard.get_data",
    "Opportunity": "amb_w_tds.amb_w_tds.utils.opportunity_dashboard.get_data",
    "Sales Order": "amb_w_tds.amb_w_tds.utils.sales_order_dashboard.get_data",
}
