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
# All 43 custom DocTypes in amb_w_tds must be explicitly mapped to prevent
# bench migrate from incorrectly deleting them as "orphans"
override_doctype_class = {
    "amb_kpi_factors": "amb_w_tds.amb_w_tds.doctype.amb_kpi_factors.amb_kpi_factors.AMBKPIFactors",
    "animal_trial": "amb_w_tds.amb_w_tds.doctype.animal_trial.animal_trial.AnimalTrial",
    "barrel": "amb_w_tds.amb_w_tds.doctype.barrel.barrel.Barrel",
    "batch_amb": "amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.BatchAMB",
    "batch_amb_item": "amb_w_tds.amb_w_tds.doctype.batch_amb_item.batch_amb_item.BatchAMBItem",
    "batch_processing_history": "amb_w_tds.amb_w_tds.doctype.batch_processing_history.batch_processing_history.BatchProcessingHistory",
    "bom_enhancement": "amb_w_tds.amb_w_tds.doctype.bom_enhancement.bom_enhancement.BOMEnhancement",
    "bom_formula": "amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula.BOMFormula",
    "bom_formula_amino_acid": "amb_w_tds.amb_w_tds.doctype.bom_formula_amino_acid.bom_formula_amino_acid.BOMFormulaAminoAcid",
    "bom_template": "amb_w_tds.amb_w_tds.doctype.bom_template.bom_template.BOMTemplate",
    "bom_template_item": "amb_w_tds.amb_w_tds.doctype.bom_template_item.bom_template_item.BOMTemplateItem",
    "bom_version": "amb_w_tds.amb_w_tds.doctype.bom_version.bom_version.BOMVersion",
    "certification_document": "amb_w_tds.amb_w_tds.doctype.certification_document.certification_document.CertificationDocument",
    "coa_amb": "amb_w_tds.amb_w_tds.doctype.coa_amb.coa_amb.COAAMB",
    "coa_amb2": "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2.CoaAmb",
    "coa_quality_test_parameter": "amb_w_tds.amb_w_tds.doctype.coa_quality_test_parameter.coa_quality_test_parameter.COAQualityTestParameter",
    "container_barrels": "amb_w_tds.amb_w_tds.doctype.container_barrels.container_barrels.ContainerBarrels",
    "container_selection": "amb_w_tds.amb_w_tds.doctype.container_selection.container_selection.ContainerSelection",
    "container_sync_log": "amb_w_tds.amb_w_tds.doctype.container_sync_log.container_sync_log.ContainerSyncLog",
    "container_type_rule": "amb_w_tds.amb_w_tds.doctype.container_type_rule.container_type_rule.ContainerTypeRule",
    "country_regulation": "amb_w_tds.amb_w_tds.doctype.country_regulation.country_regulation.CountryRegulation",
    "distribution_contact": "amb_w_tds.amb_w_tds.doctype.distribution_contact.distribution_contact.DistributionContact",
    "distribution_organization": "amb_w_tds.amb_w_tds.doctype.distribution_organization.distribution_organization.DistributionOrganization",
    "formulation": "amb_w_tds.amb_w_tds.doctype.formulation.formulation.Formulation",
    "intended_purpose": "amb_w_tds.amb_w_tds.doctype.intended_purpose.intended_purpose.IntendedPurpose",
    "juice_conversion_config": "amb_w_tds.amb_w_tds.doctype.juice_conversion_config.juice_conversion_config.JuiceConversionConfig",
    "kpi_cost_breakdown": "amb_w_tds.amb_w_tds.doctype.kpi_cost_breakdown.kpi_cost_breakdown.KpiCostBreakdown",
    "lote_amb": "amb_w_tds.amb_w_tds.doctype.lote_amb.lote_amb.LoteAmb",
    "market_entry_plan": "amb_w_tds.amb_w_tds.doctype.market_entry_plan.market_entry_plan.MarketEntryPlan",
    "market_research": "amb_w_tds.amb_w_tds.doctype.market_research.market_research.MarketResearch",
    "plant_configuration": "amb_w_tds.amb_w_tds.doctype.plant_configuration.plant_configuration.PlantConfiguration",
    "product_compliance": "amb_w_tds.amb_w_tds.doctype.product_compliance.product_compliance.ProductCompliance",
    "product_development_project": "amb_w_tds.amb_w_tds.doctype.product_development_project.product_development_project.ProductDevelopmentProject",
    "production_plant_amb": "amb_w_tds.amb_w_tds.doctype.production_plant_amb.production_plant_amb.ProductionPlantAmb",
    "quotation_amb": "amb_w_tds.amb_w_tds.doctype.quotation_amb.quotation_amb.QuotationAMB",
    "quotation_amb_sales_partner": "amb_w_tds.amb_w_tds.doctype.quotation_amb_sales_partner.quotation_amb_sales_partner.QuotationAMBSalesPartner",
    "rnd_parent_doctype": "amb_w_tds.amb_w_tds.doctype.rnd_parent_doctype.rnd_parent_doctype.RndParentDoctype",
    "sample_request_amb": "amb_w_tds.amb_w_tds.doctype.sample_request_amb.sample_request_amb.SampleRequestAMB",
    "sample_request_amb_item": "amb_w_tds.amb_w_tds.doctype.sample_request_amb_item.sample_request_amb_item.SampleRequestAMBItem",
    "tds_product_specification": "amb_w_tds.amb_w_tds.doctype.tds_product_specification.tds_product_specification.TDSProductSpecification",
    "tds_product_specification_v2": "amb_w_tds.amb_w_tds.doctype.tds_product_specification_v2.tds_product_specification_v2.TDSProductSpecificationv",
    "tds_settings": "amb_w_tds.amb_w_tds.doctype.tds_settings.tds_settings.TDSSettings",
    "third_party_api": "amb_w_tds.amb_w_tds.doctype.third_party_api.third_party_api.ThirdPartyApi",
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
    # Sample Request buttons - separate files per doctype (works without bench build)
    "Lead": "amb_w_tds/public/js/lead_sample_request.js",
    "Prospect": "amb_w_tds/public/js/prospect_sample_request.js",
    "Opportunity": "amb_w_tds/public/js/opportunity_sample_request.js",
    "Quotation": "amb_w_tds/public/js/quotation_sample_request.js",
    "Sales Order": "amb_w_tds/public/js/sales_order_sample_request.js",
    # Sample Request AMB
    "Sample Request AMB": "amb_w_tds/amb_w_tds/amb_w_tds/doctype/sample_request_amb/sample_request_amb.js",
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
]

# ================================================
# BUG 74: Add Sample Request AMB to Quotation Connections
# Shows Sample Request AMB links in Quotation's Connections tab
# ================================================
# NOTE: override_doctype_dashboards breaks standard ERPNext doctypes (BUG 79)
# Use standard 'links' in DocType JSON instead (see sample_request_amb.json)
# override_doctype_dashboards = {
#     "Quotation": "amb_w_tds.amb_w_tds.utils.quotation_dashboard.get_dashboard_data"
# }

# ================================================
# BUG 79: Add Sample Request AMB to Connections tab - REVERTED
# We use standard Frappe 'links' instead of override_doctype_dashboards
# because overriding dashboards for standard ERPNext doctypes breaks them
# ================================================
# Links are now defined in the Sample Request AMB DocType JSON files
# See sample_request_amb.json for link definitions
