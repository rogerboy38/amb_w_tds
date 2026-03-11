# Check SO status and try direct update
import frappe

so = frappe.get_doc("Sales Order", "SO-01059-ALBAFLOR")
print(f"SO Status: {so.docstatus} (0=Draft, 1=Submitted)")

# Get source quotation
for item in so.items:
    if item.prevdoc_docname:
        qt = frappe.get_doc("Quotation", item.prevdoc_docname)
        for qt_item in qt.items:
            if qt_item.item_code == item.item_code:
                print(f"Quotation Item: {qt_item.item_code}, custom_tds_amb = {getattr(qt_item, 'custom_tds_amb', None)}")
                print(f"SO Item: {item.item_code}, custom_tds_amb = {getattr(item, 'custom_tds_amb', None)}")
                
                # Try direct update
                if so.docstatus == 1:
                    # For submitted SOs, update directly in DB
                    frappe.db.set_value("Sales Order Item", item.name, "custom_tds_amb", getattr(qt_item, 'custom_tds_amb', None))
                    frappe.db.commit()
                    print(f"Updated via DB!")
                break
        break
