# -*- coding: utf-8 -*-
# Copyright (c) 2024, AMB Wellness
import frappe
import re

def on_stock_entry_submit(doc, method):
    try:
        for item in doc.items:
            if item.serial_no:
                serials = [s.strip() for s in item.serial_no.split('\n') if s.strip()]
                for serial in serials:
                    if re.match(r'^[A-Z]{3}-\d{4}-[A-Z]\d{3}-\d{4}$', serial):
                        process_barrel(serial, item.s_warehouse, item.t_warehouse, 
                                     doc.name, doc.posting_date, frappe.session.user)
    except Exception as e:
        frappe.log_error(f"Barrel handler error: {str(e)}")

def process_barrel(serial_no, from_wh, to_wh, stock_entry, posting_date, user):
    try:
        if not frappe.db.exists("Container Barrels", {"barrel_serial_number": serial_no}):
            return
        barrel = frappe.get_doc("Container Barrels", {"barrel_serial_number": serial_no})
        new_status = detect_status(to_wh)
        if not new_status:
            barrel.current_warehouse = to_wh
            barrel.save(ignore_permissions=True)
            return
        if not is_valid_transition(barrel.status, new_status):
            return
        barrel.status = new_status
        barrel.current_warehouse = to_wh
        if new_status == "In Use":
            barrel.usage_count = (barrel.usage_count or 0) + 1
            barrel.total_fill_cycles = (barrel.total_fill_cycles or 0) + 1
            if not barrel.first_used_date:
                barrel.first_used_date = posting_date
            barrel.last_used_date = posting_date
        if new_status == "Empty":
            barrel.total_empty_cycles = (barrel.total_empty_cycles or 0) + 1
        if barrel.usage_count >= (barrel.max_reuse_count or 10):
            barrel.status = "Retired"
            barrel.retirement_reason = "Auto-retired: max uses reached"
        barrel.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Process barrel error: {str(e)}")

def detect_status(warehouse):
    if not warehouse:
        return None
    wh = warehouse.upper()
    if "RECEIVING" in wh or "RCV-003" in wh:
        return "New"
    elif any(k in wh for k in ["RAW-001", "RAW-002", "RAW-003"]):
        return "Ready for Reuse"
    elif "FG-002" in wh or "BOTTLED" in wh or "BARRELS IBC" in wh:
        return "In Use"
    elif "INSPECTION" in wh or "INS-" in wh:
        return "Cleaning"
    elif "SCRAP" in wh or "QC-004" in wh:
        return "Retired"
    return None

def is_valid_transition(current, new):
    valid = {
        "New": ["In Use", "Ready for Reuse"],
        "In Use": ["Empty", "Retired"],
        "Empty": ["Cleaning", "Retired"],
        "Cleaning": ["Ready for Reuse", "Retired"],
        "Ready for Reuse": ["In Use", "Retired"],
        "Retired": []
    }
    return current == new or new in valid.get(current, [])
