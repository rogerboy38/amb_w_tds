"""
Archived Server Script: fix_invoice_debit_to

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
# Fix party_account_currency via frappe.db.set_value + recreate GL entries
# No imports, no raw SQL UPDATE — safe_exec compatible
invoices = ["ACC-SINV-2026-00004", "ACC-SINV-2026-00001"]
results = []

for inv_name in invoices:
    try:
        si_data = frappe.db.get_value(
            'Sales Invoice', inv_name,
            ['docstatus', 'debit_to', 'party_account_currency', 'currency', 'conversion_rate'],
            as_dict=True
        )
        if not si_data or si_data.docstatus != 1:
            results.append({"invoice": inv_name, "error": "Not found or not submitted"})
            continue
        
        gl_count_before = frappe.db.count('GL Entry', {'voucher_no': inv_name})
        old_pac = si_data.party_account_currency
        
        # Step 1: Create Property Setter to allow on_submit editing
        existing_ps = frappe.db.exists('Property Setter', {
            'doc_type': 'Sales Invoice',
            'field_name': 'party_account_currency',
            'property': 'allow_on_submit'
        })
        ps_name = None
        if existing_ps:
            frappe.db.set_value('Property Setter', existing_ps, 'value', '1')
            ps_name = existing_ps
        else:
            ps = frappe.get_doc({
                'doctype': 'Property Setter',
                'doc_type': 'Sales Invoice',
                'field_name': 'party_account_currency',
                'property': 'allow_on_submit',
                'property_type': 'Check',
                'value': '1',
                'doctype_or_field': 'DocField'
            })
            ps.insert(ignore_permissions=True)
            ps_name = ps.name
        frappe.db.commit()
        
        # Step 2: Use set_value to update party_account_currency
        frappe.db.set_value('Sales Invoice', inv_name, 'party_account_currency', 'MXN', update_modified=True)
        frappe.db.commit()
        
        # Verify
        new_pac = frappe.db.get_value('Sales Invoice', inv_name, 'party_account_currency')
        
        # Step 3: Cleanup Property Setter
        if ps_name:
            frappe.delete_doc('Property Setter', ps_name, ignore_permissions=True)
            frappe.db.commit()
        
        # Step 4: Reload and make GL entries
        si = frappe.get_doc('Sales Invoice', inv_name)
        si.make_gl_entries()
        frappe.db.commit()
        
        gl_count_after = frappe.db.count('GL Entry', {'voucher_no': inv_name})
        
        results.append({
            "invoice": inv_name,
            "success": True,
            "old_pac": old_pac,
            "new_pac": new_pac,
            "debit_to": si_data.debit_to,
            "currency": si_data.currency,
            "conversion_rate": str(si_data.conversion_rate),
            "gl_before": gl_count_before,
            "gl_after": gl_count_after
        })
    except Exception as e:
        results.append({
            "invoice": inv_name,
            "error": str(e)
        })

frappe.response["message"] = results
"""
