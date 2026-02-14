app_name = "amb_w_tds"
app_title = "amb_w_tds"
app_publisher = "AMB-Wellness"
app_description = "AMB-WELLNESS TDS Management"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"

# ==================== DOCTYPE CONFIGURATION ====================
# CRITICAL: This tells Frappe to use our custom BatchAMB class
doctype_class = {
    "Batch AMB": "amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.BatchAMB"
}

# DocType JS - Link to the JS file
doctype_js = {
    "Batch AMB": "amb_w_tds/doctype/batch_amb/batch_amb.js"
}

# ==================== RAVEN AGENT CONFIGURATION ====================
raven_agents = ["amb_w_tds.raven.config:get_agents"]

# ==================== APP INCLUSIONS ====================
app_include_js = [
    "/assets/amb_w_tds/js/batch_widget.js"
]

# ==================== DOCUMENT EVENTS ====================
doc_events = {
    "Stock Entry": {
        "on_submit": "amb_w_tds.stock_entry_hooks.on_stock_entry_submit",
        "after_submit": "amb_w_tds.raven.utils.on_stock_entry_submit"
    }
}

# ==================== SCHEDULED EVENTS ====================
scheduler_events = {
    "daily": [
        "amb_w_tds.raven.utils.daily_compliance_check"
    ],
    "hourly": [
        "amb_w_tds.raven.utils.hourly_health_check"
    ],
    "weekly": [
        "amb_w_tds.raven.utils.weekly_performance_report"
    ]
}

# ==================== OTHER CONFIGURATIONS ====================
get_website_user_home_page = "amb_w_tds.pages.barrel_dashboard.barrel_dashboard"

standard_portal_menu = [
    {"title": "Barrel Dashboard", "route": "/barrel_dashboard", "reference_doctype": "Barrel"},
    {"title": "Container Barrels Dashboard", "route": "/container_barrels_dashboard", "reference_doctype": "Container Selection"}
]

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "=", "Batch AMB"]
        ]
    }
]

# ==================== WEBHOOKS ====================
webhooks = [
    {
        "doctype": "Stock Entry",
        "webhook_doctype": "Stock Entry",
        "webhook_docevent": "on_submit",
        "condition": "doc.purpose == 'Material Receipt'",
        "enabled": 1
    }
]

# ==================== DOCTYPE LIST VIEW SETTINGS ====================
default_mail_footer = """
	<span>
		Sent via ERPNext
	</span>
"""
