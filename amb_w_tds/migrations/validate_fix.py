# Validation script - Run in bench console

import frappe
import os

print("\n" + "="*60)
print("VALIDATION: amb_w_tds Site Status")
print("="*60)

# 1. Check JS files
print("\n1. Checking Sample Request AMB JS...")

js_path = "apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/sample_request_amb/sample_request_amb.js"
if os.path.exists(js_path):
    with open(js_path) as f:
        content = f.read()
    
    # Check for problematic patterns
    issues = []
    if "frm.set_query" in content and "samples" in content:
        issues.append("Contains filter code that may crash form")
    
    if issues:
        for issue in issues:
            print(f"   ⚠ {issue}")
    else:
        print("   ✓ JS file exists - clean version")
else:
    print(f"   ✗ JS file NOT FOUND")

# 2. Check hooks.py
print("\n2. Checking hooks.py...")

hooks_path = "apps/amb_w_tds/amb_w_tds/hooks.py"
if os.path.exists(hooks_path):
    with open(hooks_path) as f:
        hooks_content = f.read()
    
    # Check before_migrate
    if "before_migrate" in hooks_content:
        print("   ✓ before_migrate hook exists")
    
    # Check for problematic patterns
    if "UPDATE `tabDocType`" in hooks_content:
        print("   ⚠ WARNING: Contains SQL UPDATE - may break site!")
    else:
        print("   ✓ No SQL UPDATE in hooks")
        
    if "override_doctype_dashboards" in hooks_content and "override_doctype_dashboards = {" in hooks_content:
        print("   ⚠ WARNING: override_doctype_dashboards is active - may break standard doctypes!")
    else:
        print("   ✓ override_doctype_dashboards is commented out")
else:
    print(f"   ✗ hooks.py NOT FOUND")

# 3. Check install.py
print("\n3. Checking install.py...")

install_path = "apps/amb_w_tds/amb_w_tds/install.py"
if os.path.exists(install_path):
    with open(install_path) as f:
        install_content = f.read()
    
    if "UPDATE `tabDocType`" in install_content:
        print("   ⚠ WARNING: Contains SQL UPDATE - may break site!")
    else:
        print("   ✓ No SQL UPDATE in install.py")
        
    if "frappe.db.sql" in install_content:
        print("   ⚠ WARNING: Contains database modifications")
    else:
        print("   ✓ No database modifications")
else:
    print(f"   ✗ install.py NOT FOUND")

# 4. Check DocType fields
print("\n4. Checking Sample Request AMB Item fields...")

try:
    meta = frappe.get_meta("Sample Request AMB Item")
    fields = {df.fieldname: df for df in meta.fields}
    
    for fname in ["package_type", "container_type"]:
        if fname in fields:
            df = fields[fname]
            print(f"   ✓ {fname}: {df.fieldtype} -> {df.options}")
        else:
            print(f"   ✗ {fname}: NOT FOUND")
except Exception as e:
    print(f"   ✗ Error: {e}")

# 5. Test if Sample Request AMB can load
print("\n5. Testing Sample Request AMB form...")

try:
    # Just check if DocType exists
    if frappe.db.exists("DocType", "Sample Request AMB"):
        print("   ✓ Sample Request AMB DocType exists")
    else:
        print("   ✗ Sample Request AMB DocType NOT FOUND")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "="*60)
print("Validation complete")
print("="*60 + "\n")
