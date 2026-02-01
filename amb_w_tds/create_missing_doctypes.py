import frappe
import os
import json

def execute():
    """Create missing doctypes that are marked as orphans"""
    print("Creating missing doctypes...")
    
    missing_doctypes = [
        "Production Plant AMB",
        "KPI Cost Breakdown", 
        "Third Party API",
        "COA AMB2",
        "TDS Settings",
        "Lote AMB",
        "RND Parent DocType"
    ]
    
    created = 0
    app_path = "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype"
    
    for doctype_name in missing_doctypes:
        # Check if already exists
        if frappe.db.exists("DocType", doctype_name):
            print(f"✓ {doctype_name} already exists")
            continue
        
        # Convert to folder name
        folder_name = doctype_name.lower().replace(" ", "_").replace("-", "_")
        folder_path = os.path.join(app_path, folder_name)
        
        if os.path.exists(folder_path):
            json_file = os.path.join(folder_path, f"{folder_name}.json")
            
            if os.path.exists(json_file):
                print(f"  Creating {doctype_name} from JSON...")
                
                try:
                    with open(json_file, 'r') as f:
                        doctype_data = json.load(f)
                    
                    # Create doctype
                    doc = frappe.get_doc({
                        "doctype": "DocType",
                        "name": doctype_name,
                        "module": doctype_data.get('module', 'amb_w_tds'),
                        "custom": 1,
                        "fields": doctype_data.get('fields', []),
                        "permissions": doctype_data.get('permissions', []),
                    })
                    
                    doc.insert(ignore_permissions=True)
                    created += 1
                    print(f"  ✓ Created {doctype_name}")
                    
                except Exception as e:
                    print(f"  ✗ Error creating {doctype_name}: {e}")
            else:
                print(f"  ✗ No JSON file for {doctype_name}")
        else:
            print(f"  ✗ Folder not found for {doctype_name}: {folder_name}")
    
    if created > 0:
        frappe.db.commit()
        print(f"\nCreated {created} doctypes")
    else:
        print("\nNo doctypes created")
