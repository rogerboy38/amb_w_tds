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

# Phase 1C-B (V14.3.1) — Parameter Selection picker stylesheet.
app_include_css = [
    "/assets/amb_w_tds/css/phase_1c_tab.css",
]

# Phase 1C-B (V14.3.1) — Parameter Selection picker JS, composes with the canonical
# tds_product_specification.js (Frappe merges frappe.ui.form.on() calls across files).
doctype_js = {
    "TDS Product Specification": "public/js/phase_1c_tab.js",
}

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
#  FIXTURES (L153 fixtures-discipline rollout 2026-05-20)
# ========================================
# For Custom Field / Property Setter / Client Script / Server Script: filter
# by DocType (dt / doc_type / reference_doctype) rather than module. Module
# attribution drifts on records created via UI; DocType-level filtering captures
# all customizations belonging to this app regardless of which module they
# happened to land in. Per cowork-ops 2026-05-20T21:44Z directive (post L153
# ratification).
#
# Split with amb_w_spc: amb_w_tds claims TDS / Sales / COA / BOM / Customer /
# CRM / HR-light / Logistics / Quotation domain DocTypes; amb_w_spc claims
# QC / Manufacturing / SPC / Stock / Warehouse / Work Order domain DocTypes.
# Shared ERPNext DocTypes go to whichever app has the dominant use case.

_AMB_W_TDS_DOCTYPES = [
    # Owned by amb_w_tds (defined in this app)
    "AMB KPI Factors", "Animal Trial", "Barrel", "BOM Enhancement",
    "BOM Formula", "BOM Formula Amino Acid", "BOM Template", "BOM Template Item",
    "BOM Version", "Certification Document", "COA AMB", "COA AMB2",
    "COA Quality Test Parameter", "Container Selection", "Container Sync Log",
    "Container Type Rule", "Country Regulation", "Distribution Contact",
    "Distribution Organization", "Formulation", "Intended Purpose",
    "Juice Conversion Config", "KPI Cost Breakdown", "Lote AMB",
    "Market Entry Plan", "Market Research", "Plant Configuration",
    "Product Compliance", "Product Development Project", "Production Plant AMB",
    "Quotation AMB", "Quotation AMB Sales Partner", "RND Parent Doctype",
    "Sample Request AMB", "Sample Request AMB Item", "TDS Default Parameter",
    "TDS Product Specification", "TDS Product Specification V2", "TDS Settings",
    "Third Party API",
    # ERPNext DocTypes amb_w_tds customizes (sales / COA / BOM / TDS-driven)
    "Address", "Asset", "Asset Maintenance Log", "Asset Repair",
    "Assignment Rule", "Attendance", "BOM", "BOM Creator", "Communication",
    "Company", "Contact", "Cost Center", "CRM Deal", "CRM Lead", "CRM Product",
    "Customer", "Customer Item", "Delivery Note", "Delivery Note Item",
    "Department", "Designation", "Email Account", "Employee", "Event",
    # Removed in V14.3.4 (2026-05-21T05:21Z corrective): 5 orphan-drift entries
    # below were never present in any AMB substrate (provenance probe confirmed
    # NOT IN VM3 EITHER — pure stale claim list residue). Triggered L156
    # silent file-level abort on sync_fixtures during sysmayal hostinger-vpt
    # rehearsal pull. Excluding them prevents future fixture re-capture.
    # Excluded: HD Ticket Type, Freight Location, Event Category AMB,
    # Custom Clearance (workflow-only ref), Direct Shipping (workflow-only ref).
    "GoCardless Mandate",
    "Incoterm", "Industry Type", "Issue", "Item",
    "Item Group", "Item Tax Template Detail", "Item Variant", "Lead",
    "Mode of Payment", "Operation", "Opportunity", "Packed Item",
    "Packing Slip", "Payment Entry", "Payment Term",
    "Payroll Employee Detail", "Payroll Entry", "Pick List", "POS Invoice",
    "POS Invoice Item", "Pricing Rule", "Print Format", "Print Settings",
    "Production Plan", "Project", "Project Update", "Prospect",
    "Purchase Invoice", "Purchase Invoice Item", "Purchase Order",
    "Purchase Order Item", "Purchase Receipt", "Purchase Receipt Item",
    "Quality Goal Objective", "Quality Procedure", "Quality Review",
    "Quality Review Objective", "Quotation", "Quotation Item",
    "Quotation Item Escalated", "Request for Quotation",
    "Request for Quotation Item", "Salary Slip", "Sales Invoice",
    "Sales Invoice Item", "Sales Order", "Sales Order Item", "Sales Stage",
    "Sales Taxes and Charges", "Shipment", "Shipment Parcel", "Shipping Rule",
    "Subscription", "Supplier", "Supplier Quotation", "Supplier Quotation Item",
    "Task", "Terms and Conditions", "Timesheet", "UTM Campaign", "Web Form",
]

# L153 §4.1 follow-on: Server Scripts with reference_doctype=NULL (scheduled /
# API / cron-driven) aren't captured by the dt-based filter above. Cowork-ops's
# proposed module-based catch-all (AMBWTDS + reference_doctype is not set)
# would match 0 records because none of these scripts have module=AMBWTDS —
# module attribution drift bites here too. Explicit name list instead, per
# triage 2026-05-20T23:30Z.
_AMB_W_TDS_NOREF_SERVER_SCRIPTS = [
    "Create Sample Request from Lead",  # Lead → TDS sample request pipeline
    "coa_amb_api",                       # COA AMB API
    "fix_invoice_debit_to",              # Sales Invoice fix
    "load_tds_parameters",               # TDS Product Specification loader
]

fixtures = [
    {"doctype": "Custom Field",           "filters": [["dt", "in", _AMB_W_TDS_DOCTYPES]]},
    {"doctype": "Property Setter",        "filters": [["doc_type", "in", _AMB_W_TDS_DOCTYPES]]},
    {"doctype": "Client Script",          "filters": [["dt", "in", _AMB_W_TDS_DOCTYPES]]},
    # Task #63 (2026-05-28) — 7 L1 category placeholder Quality Inspection
    # Parameter records. These are the Link targets the picker's title-row
    # injection in phase_1c_tab_v2.js writes into IQI.specification when
    # users add params from each L1 category. Tight `name in [...]` filter
    # so re-export only picks up the 7 placeholders, not all 60+ QIP records.
    {"doctype": "Quality Inspection Parameter",
     "filters": [["name", "in", ["Organoleptic", "Physicochemical", "Microbiological",
                                  "Pesticides", "Contaminants", "Other Analysis",
                                  "Aloe Vera Nutrients"]]]},
    # Server Script: UNION via or_filters only (empty filters) — Frappe's
    # get_list semantics are: filters=AND, or_filters=OR, combined=AND-of-both.
    # So filters + or_filters in same dict means BOTH must match (intersection,
    # not union). For UNION, put both conditions inside or_filters (one list,
    # all OR'd). Two separate fixture entries for same doctype also fails — the
    # second one's export_json call overwrites the first one's JSON file
    # (frappe/utils/fixtures.py L94 — one filename per (doctype, prefix)).
    # The `prefix` key would let two entries write separate files but UNION is
    # cleaner for "any of these conditions" semantics.
    {
        "doctype": "Server Script",
        "or_filters": [
            ["reference_doctype", "in", _AMB_W_TDS_DOCTYPES],
            ["name", "in", _AMB_W_TDS_NOREF_SERVER_SCRIPTS],
        ],
    },
    # V14.3.4: dropped "Custom Clearance" + "Direct Shipping" (orphan DocTypes — not on any AMB substrate).
    {"doctype": "Workflow",               "filters": [["document_type", "in", ["COA AMB","COA AMB2","TDS Product Specification"]]]},
    {"doctype": "Workflow State",         "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Workflow Action Master", "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Notification",           "filters": [["module", "=", "AMBWTDS"], ["is_standard", "=", 0]]},
    {"doctype": "Role",                   "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Workspace",              "filters": [["name", "like", "AMB%"]]},
    {"doctype": "Dashboard Chart",        "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Number Card",            "filters": [["module", "=", "AMBWTDS"]]},
    {"doctype": "Report",                 "filters": [["module", "=", "AMBWTDS"]]},
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
