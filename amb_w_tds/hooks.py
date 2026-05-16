app_name = "amb_w_tds"
app_version = "10.0.0"
app_title = "AMB W TDS"
app_publisher = "AMB WELLNESS"
app_description = "AMB WELLNESS TDS + Migration + Quotation AMB system"
app_email = "support@amb-wellness.com"
app_license = "MIT"

doctype_class = {
    "Batch AMB":  "amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.BatchAMB"
}

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

doctype_js = {
    "Quotation AMB": "amb_w_tds/amb_w_tds/doctype/quotation_amb/quotation_amb.js",
    "Batch AMB": "amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js",
    "Work Order": "amb_w_tds/public/js/work_order_list.js",
    "Lead": "amb_w_tds/public/js/lead_sample_request.js",
    "Prospect": "amb_w_tds/public/js/prospect_sample_request.js",
    "Opportunity": "amb_w_tds/public/js/opportunity_sample_request.js",
    "Quotation": "amb_w_tds/public/js/quotation_sample_request.js",
    "Sales Order": "amb_w_tds/public/js/sales_order_sample_request.js",
    "Sample Request AMB": "amb_w_tds/amb_w_tds/doctype/sample_request_amb/sample_request_amb.js",
}

app_include_js = [
    "/assets/amb_w_tds/js/batch_widget.js",
    "/assets/amb_w_tds/js/work_order_list.js",
]

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
}

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

    # BUG82: Client Script for Sample Request AMB Link field filters
    {
        "doctype": "Client Script",
        "filters": [
            ["dt", "=", "Sample Request AMB"]
        ]
    },
]

# ================================================
# FRAPPE MONKEY PATCHES (BOM Tree Fix v16)
# ================================================

override_whitelisted_methods = {
	"frappe.desk.treeview.get_all_nodes": "amb_w_tds.amb_w_tds.api.bom_tree_fix.get_all_nodes_fixed"
}

before_migrate = [
    "amb_w_tds.install.before_migrate",
]

default_mail_footer = """
    <div>
        Document generated by AMB Frappe Cloud System
    </div>
"""