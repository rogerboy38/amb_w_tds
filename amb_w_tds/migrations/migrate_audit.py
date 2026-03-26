# Diagnostic script to check what's happening during migrate
# Run in: bench console

import frappe
import glob
import os

print("\n" + "="*60)
print("DIAGNOSTIC: amb_w_tds migrate hooks")
print("="*60)

# 1. Check install.py functions
print("\n1. Checking install.py hooks...")

install_path = "apps/amb_w_tds/amb_w_tds/install.py"
if os.path.exists(install_path):
    print(f"   ✓ install.py exists")
    
    with open(install_path) as f:
        content = f.read()
    
    if "def before_migrate" in content:
        print("   ✓ before_migrate() function exists")
    if "def after_migrate" in content:
        print("   ✓ after_migrate() function exists")
        # Count how many DocTypes would be reimported
        doctype_count = len(glob.glob("apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/*/*.json"))
        print(f"   ⚠ after_migrate would force-import {doctype_count} DocTypes!")
else:
    print(f"   ✗ install.py NOT FOUND")

# 2. Check hooks.py
print("\n2. Checking hooks.py...")

hooks_path = "apps/amb_w_tds/amb_w_tds/hooks.py"
if os.path.exists(hooks_path):
    with open(hooks_path) as f:
        hooks_content = f.read()
    
    if "before_migrate" in hooks_content:
        print("   ✓ before_migrate hook registered")
    if "after_migrate" in hooks_content:
        print("   ⚠ after_migrate hook registered - CAN BREAK SITE!")

# 3. List all DocTypes that would be reimported
print("\n3. DocTypes that would be force-reimported by after_migrate...")

json_files = glob.glob("apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/*/*.json")
print(f"   Total: {len(json_files)} JSON files")
for jf in json_files[:10]:
    print(f"   - {jf.split('/')[-1]}")
if len(json_files) > 10:
    print(f"   ... and {len(json_files)-10} more")

# 4. Check for overrides in override_doctype_class
print("\n4. Checking override_doctype_class...")

try:
    from amb_w_tds.hooks import override_doctype_class
    if override_doctype_class:
        print(f"   ⚠ {len(override_doctype_class)} DocTypes in override_doctype_class")
        print("   This can cause conflicts if overriding standard ERPNext doctypes")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "="*60)
print("RECOMMENDATION: Disable after_migrate to prevent site damage")
print("="*60 + "\n")
