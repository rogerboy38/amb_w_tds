"""
Archived Server Script: Fix SAT CFDI Permissions

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
# Fix select permission on SAT CFDI Use doctype
# The mexico_compliance app's query uses frappe.qb.get_query which requires select permission

sat_doctypes = ['SAT CFDI Use', 'SAT Payment Option', 'SAT Payment Method']
results = []

for dt in sat_doctypes:
    # Update all existing DocPerm rows to have select=1
    perms = frappe.db.get_all('DocPerm', filters={'parent': dt}, fields=['name', 'role', 'select'])
    for perm in perms:
        if not perm.select:
            frappe.db.set_value('DocPerm', perm.name, 'select', 1)
            results.append(f'Updated {dt} - {perm.role}: select=1')
        else:
            results.append(f'{dt} - {perm.role}: already has select')


frappe.response['message'] = results
"""
