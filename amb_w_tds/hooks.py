app_name = "amb_w_tds"
app_version = "10.0.0"
app_title = "AMB W TDS"
app_publisher = "Your Company"
app_description = "AMB With TDS"
app_email = "support@yourcompany.com"
app_license = "MIT"

doctype_class = {
    "Batch AMB":  "amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.BatchAMB"
}

# ========================================
#  FRONTEND JS INJECTIONS
# ========================================

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

doctype_js = {
    "Quotation": "amb_w_tds/amb_w_tds/doctype/batch_amb/quotation_sample_request.js",
    "Lead": "amb_w_tds/amb_w_tds/doctype/batch_amb/lead_sample_request.js",
    "Prospect": "amb_w_tds/amb_w_tds/doctype/batch_amb/prospect_sample_request.js",
    "Opportunity": "amb_w_tds/amb_w_tds/doctype/batch_amb/opportunity_sample_request.js",
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
        "on_submit": "amb_w_tds.amb_w_tds.doctype.batch_amb.pipeline_hooks.on_stock_entry_submit",
        "before_insert": [],
    },

    # ---- Quality Inspection auto-links to Batch AMB
    "Quality Inspection": {
        "on_submit": "amb_w_tds.amb_w_tds.doctype.batch_amb.pipeline_hooks.on_quality_inspection_submit",
    },

    # ---- Delivery Note updates Batch AMB pipeline
    "Delivery Note": {
        "on_submit": "amb_w_tds.amb_w_tds.doctype.batch_amb.pipeline_hooks.on_delivery_note_submit",
    },

    # ---- AMB Quotation + Sales Partner auto mapping + idempotency
    "Quotation AMB": {
        "before_insert": [],
        "before_save": [],
        "before_submit": [],
    },
}

# ========================================
#  SCHEDULER EVENTS (background consistency)
# ========================================

scheduler_events = {

    "hourly": [],

    "daily": [],

    "weekly": [
        # BOM Health Check - runs weekly (Phase 5)
        "amb_w_tds.scripts.scheduled_bom_health.run",
    ],
}

# ========================================
#  FIXTURES (sync mandatory custom fields)
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

# ========================================
#  DOCTYPE DASHBOARD OVERRIDES
# ========================================
override_doctype_dashboards = {
    "Quotation": "amb_w_tds.amb_w_tds.utils.quotation_dashboard.get_data",
}

# ========================================
#  PAGE ROUTES
# ========================================
page_js = {
    "amb-manufacturing-dashboard": "amb_w_tds.public.js.dashboard_override"
}