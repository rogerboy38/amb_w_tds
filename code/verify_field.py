# Verify the custom field was added to Sales Order Item
import frappe

print("=== Sales Order Item - Check custom_tds_amb ===")
meta = frappe.get_meta("Sales Order Item")
for f in meta.fields:
    if f.fieldname == "custom_tds_amb":
        print(f"FOUND: {f.fieldname} - {f.fieldtype} - {f.label}")
        break
else:
    print("NOT FOUND!")

# Check if it has data now
print("\n=== Check SO Item Data ===")
so = frappe.get_doc("Sales Order", "SO-01059-ALBAFLOR")
for item in so.items:
    val = getattr(item, 'custom_tds_amb', None)
    print(f"Item {item.item_code}: custom_tds_amb = {val}")
