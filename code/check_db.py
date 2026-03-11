# Check DB directly for the specific Quotation
import frappe

# Check Quotation SAL-QTN-2025-01059
qt_name = "SAL-QTN-2025-01059"
items = frappe.get_all("Quotation Item", 
    filters={"parent": qt_name},
    fields=["name", "item_code", "custom_tds_amb"]
)

print(f"=== Quotation: {qt_name} ===")
for item in items:
    print(f"  Item: {item.item_code} | custom_tds_amb: {item.custom_tds_amb}")
