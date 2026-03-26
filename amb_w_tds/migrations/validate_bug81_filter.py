#!/usr/bin/env python3
"""
BUG 81 Validation Script - Child Table Filter Diagnostics
Run this in: cd ~/frappe-bench && bench console
"""

import frappe
import json

print("=" * 60)
print("BUG 81 - Child Table Filter Validation")
print("=" * 60)

# 1. Check if Sample Request AMB DocType exists
print("\n1. Checking Sample Request AMB DocType...")
try:
    doc_type = frappe.get_doc("DocType", "Sample Request AMB")
    print(f"   ✅ DocType exists: {doc_type.name}")
except Exception as e:
    print(f"   ❌ DocType not found: {e}")

# 2. Check the child table field
print("\n2. Checking 'samples' child table field...")
try:
    child_table_field = frappe.get_doc({
        "doctype": "DocField",
        "parent": "Sample Request AMB",
        "fieldname": "samples"
    })
    print(f"   ✅ Child table field exists: {child_table_field.fieldtype} -> {child_table_field.options}")
except Exception as e:
    print(f"   ❌ Child table field not found: {e}")

# 3. Check the package_type field in child table
print("\n3. Checking 'package_type' field in Sample Request AMB Item...")
try:
    pkg_field = frappe.get_doc({
        "doctype": "DocField",
        "parent": "Sample Request AMB Item",
        "fieldname": "package_type"
    })
    print(f"   ✅ Field exists: {pkg_field.fieldtype}")
    print(f"      Options: {pkg_field.options}")
    print(f"      Is Link: {pkg_field.fieldtype == 'Link'}")
except Exception as e:
    print(f"   ❌ Field not found: {e}")

# 4. Check the container_type field in child table
print("\n4. Checking 'container_type' field in Sample Request AMB Item...")
try:
    cnt_field = frappe.get_doc({
        "doctype": "DocField",
        "parent": "Sample Request AMB Item",
        "fieldname": "container_type"
    })
    print(f"   ✅ Field exists: {cnt_field.fieldtype}")
    print(f"      Options: {cnt_field.options}")
    print(f"      Is Link: {cnt_field.fieldtype == 'Link'}")
except Exception as e:
    print(f"   ❌ Field not found: {e}")

# 5. Check if Item Groups exist
print("\n5. Checking Item Groups...")
item_groups = ["FG Packaging Materials", "Sample Packaging Materials"]
for ig_name in item_groups:
    try:
        ig = frappe.get_doc("Item Group", ig_name)
        print(f"   ✅ Item Group exists: {ig.name}")
    except Exception as e:
        print(f"   ❌ Item Group NOT found: {ig_name}")

# 6. Count items in each group
print("\n6. Counting items in each group...")
for ig_name in item_groups:
    try:
        items = frappe.get_all("Item", 
            filters={"item_group": ig_name},
            fields=["name", "item_name"],
            limit=5
        )
        print(f"   {ig_name}: {len(items)} items")
        if items:
            print(f"      Sample items: {[i.name for i in items[:3]]}")
    except Exception as e:
        print(f"   ❌ Error getting items: {e}")

# 7. Check Client Script exists
print("\n7. Checking Custom/Client Script...")
try:
    scripts = frappe.get_all("Client Script",
        filters={"dt": "Sample Request AMB"},
        fields=["name", "script"]
    )
    print(f"   Found {len(scripts)} client script(s) for Sample Request AMB")
    for s in scripts:
        print(f"   - {s.name}")
        if "package_type" in (s.script or ""):
            print(f"     ✅ Contains package_type filter")
        if "container_type" in (s.script or ""):
            print(f"     ✅ Contains container_type filter")
except Exception as e:
    print(f"   ❌ Error checking scripts: {e}")

# 8. Check hooks.py configuration
print("\n8. Checking hooks.py configuration...")
try:
    from frappe import get_hooks
    doctype_js = get_hooks("doctype_js")
    sr_amb_js = doctype_js.get("Sample Request AMB", [])
    print(f"   doctype_js for 'Sample Request AMB': {sr_amb_js}")
except Exception as e:
    print(f"   ❌ Error getting hooks: {e}")

print("\n" + "=" * 60)
print("Validation Complete")
print("=" * 60)