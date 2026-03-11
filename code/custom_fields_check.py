# Check ALL custom fields on Sales Order Item and Quotation Item
import frappe

# Get ALL custom fields on Sales Order Item
print("=== ALL Custom Fields on Sales Order Item ===")
meta = frappe.get_meta("Sales Order Item")
for f in meta.fields:
    if f.fieldtype == "Custom" or f.fieldname.startswith("custom_"):
        print(f"  {f.fieldname}: {f.fieldtype} (label: {f.label})")

print("\n=== ALL Custom Fields on Quotation Item ===")
qt_meta = frappe.get_meta("Quotation Item")
for f in qt_meta.fields:
    if f.fieldtype == "Custom" or f.fieldname.startswith("custom_"):
        print(f"  {f.fieldname}: {f.fieldtype} (label: {f.label})")
