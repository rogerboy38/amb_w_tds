# Find SOs where source Quotation HAS custom_tds_amb data
import frappe

# Get SOs with source Quotations
sos = frappe.get_all("Sales Order", 
    filters={
        "docstatus": 0,  # Draft
        "name": ["like", "SO-010%"]
    },
    fields=["name"]
)

print("=== SOs with TDS in source Quotation ===")
for so in sos[:20]:
    so_doc = frappe.get_doc("Sales Order", so.name)
    for item in so_doc.items:
        if item.prevdoc_docname:
            qt = frappe.get_doc("Quotation", item.prevdoc_docname)
            for qt_item in qt.items:
                if qt_item.item_code == item.item_code:
                    tds_val = getattr(qt_item, 'custom_tds_amb', None)
                    if tds_val:
                        print(f"{so.name} | Item: {item.item_code} | TDS: {tds_val}")
                    break
            break
