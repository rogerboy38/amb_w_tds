"""
Archived Server Script: Clear WordPress Post IDs

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
# Clear WordPress Post IDs from all Blog Content records
blogs = frappe.get_all('Blog Content', fields=['name'])
cleared = 0
for blog in blogs:
    frappe.db.set_value('Blog Content', blog.name, 'wp_post_id', 0)
    frappe.db.set_value('Blog Content', blog.name, 'wp_post_url', '')
    frappe.db.set_value('Blog Content', blog.name, 'wp_edit_url', '')
    cleared += 1
frappe.db.commit()
frappe.response['message'] = f'Cleared WordPress fields for {cleared} blog posts'
"""
