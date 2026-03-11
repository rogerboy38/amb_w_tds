# Run in bench console to explore TDS field structure

import frappe

# 1. Check Sales Order Item fields - find all TDS related fields
print("=== Sales Order Item TDS Fields ===")
meta = frappe.get_meta("Sales Order Item")
for f in meta.fields:
    if 'tds' in f.fieldname.lower() or 'amb' in f.fieldname.lower():
        print(f"  {f.fieldname}: {f.fieldtype} (label: {f.label})")

# 2. Check Quotation Item fields
print("\n=== Quotation Item TDS Fields ===")
qt_meta = frappe.get_meta("Quotation Item")
for f in qt_meta.fields:
    if 'tds' in f.fieldname.lower() or 'amb' in f.fieldname.lower():
        print(f"  {f.fieldname}: {f.fieldtype} (label: {f.label})")

# 3. Check actual data on a sample SO
print("\n=== Sample SO Item Data ===")
so = frappe.get_doc("Sales Order", "SO-01059-ALBAFLOR")
for item in so.items:
    print(f"\nItem: {item.item_code}")
    for f in meta.fields:
        if 'tds' in f.fieldname.lower() or 'amb' in f.fieldname.lower():
            val = getattr(item, f.fieldname, None)
            if val:
                print(f"  {f.fieldname} = {val}")

# 4. Check source Quotation data
print("\n=== Source Quotation Item Data ===")
for item in so.items:
    if item.prevdoc_docname:
        qt = frappe.get_doc("Quotation", item.prevdoc_docname)
        for qt_item in qt.items:
            if qt_item.item_code == item.item_code:
                print(f"\nQuotation Item: {qt_item.item_code}")
                for f in qt_meta.fields:
                    if 'tds' in f.fieldname.lower() or 'amb' in f.fieldname.lower():
                        val = getattr(qt_item, f.fieldname, None)
                        if val:
                            print(f"  {f.fieldname} = {val}")
        break
