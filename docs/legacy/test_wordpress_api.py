"""
Archived Server Script: test_wordpress_api

V13.6.0 P3 Server Script Migration
Decision: DEL / archive_enabled_one_shot
Script Type: API
Reference DocType: None
Disabled: 0
Module: null

Runtime status:
  DO NOT IMPORT. Archive only.
"""

ORIGINAL_SCRIPT = """
# Test WordPress API using frappe.call
result = frappe.call(
    "rnd_nutrition.rnd_nutrition.wordpress_api.publish_to_wordpress",
    title="Test Post from ERPNext",
    content="<p>This is a test post.</p>",
    status="draft"
)
frappe.response["message"] = result
"""
