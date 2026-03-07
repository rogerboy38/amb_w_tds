import frappe
import os
import json

def execute():
    """Force sync of amb_w_tds doctypes"""
    print("Force syncing amb_w_tds doctypes...")
    
    # Get all doctype JSON files
    app_path = "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/doctype"
    
    if not os.path.exists(app_path):
        print(f"ERROR: Doctype path not found: {app_path}")
        return
    
    synced = 0
    errors = 0
    
    for doctype_name in os.listdir(app_path):
        doctype_dir = os.path.join(app_path, doctype_name)
        
        if not os.path.isdir(doctype_dir) or doctype_name in ['__init__.py', '__pycache__']:
            continue
        
        json_file = os.path.join(doctype_dir, f"{doctype_name}.json")
        
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    doctype_data = json.load(f)
                
                # Check if exists
                if not frappe.db.exists("DocType", doctype_name):
                    print(f"  Creating {doctype_name}...")
                    
                    # Create minimal doctype
                    doc = frappe.get_doc({
                        "doctype": "DocType",
                        "name": doctype_name,
                        "module": doctype_data.get('module', 'amb_w_tds'),
                        "custom": 1,
                        "fields": doctype_data.get('fields', []),
                    })
                    
                    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                    synced += 1
                else:
                    print(f"  ✓ {doctype_name} already exists")
                    
            except Exception as e:
                print(f"  ✗ Error with {doctype_name}: {e}")
                errors += 1
    
    print(f"\nSynced: {synced}, Errors: {errors}")
    
    if synced > 0:
        print("Running frappe.db.commit()...")
        frappe.db.commit()
