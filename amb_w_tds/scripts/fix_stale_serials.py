"""
Fix stale serial numbers in Batch AMB
One-time migration script to correct serial numbers that were generated
from stale custom_generated_batch_name instead of the correct title field.

Usage:
    bench execute amb_w_tds.scripts.fix_stale_serials.execute

Target batch: LOTE-26-14-0002
Expected old format: 0334925261-1-C1-001 (from stale golden number)
Expected new format: LOTE-26-14-0002-C1-001 (from title)
"""
import frappe


def execute():
    batch_name = "LOTE-26-14-0002"
    
    if not frappe.db.exists("Batch AMB", batch_name):
        frappe.throw(f"Batch {batch_name} not found")
    
    batch = frappe.get_doc("Batch AMB", batch_name)
    correct_title = batch.title
    
    if not correct_title:
        frappe.throw(f"Batch {batch_name} has no title set")
    
    print(f"Processing batch: {batch_name}")
    print(f"Correct title: {correct_title}")
    print(f"Current container_barrels count: {len(batch.container_barrels)}")
    
    # Collect updates to make: (row_name, old_serial, new_serial)
    updates = []
    
    for idx, row in enumerate(batch.container_barrels, 1):
        old_serial = row.barrel_serial_number
        if not old_serial:
            continue
        
        # Check if this looks like a stale serial (starts with old golden number pattern)
        if old_serial.startswith("0334925261"):
            new_serial = f"{correct_title}-C{idx:03d}"
            print(f"  Queue update: {old_serial} -> {new_serial}")
            updates.append((row.name, old_serial, new_serial))
    
    if updates:
        # Update directly via database to bypass ALL validation including Server Scripts
        frappe.flags.in_migrate = True
        frappe.flags.ignore_permissions = True
        
        for row_name, old_serial, new_serial in updates:
            frappe.db.set_value(
                "Container Barrels",
                row_name,
                "barrel_serial_number",
                new_serial
            )
        
        frappe.db.commit()
        frappe.flags.in_migrate = False
        print(f"Updated {len(updates)} serial numbers successfully")
    else:
        print("No stale serial numbers found")
    
    return {"status": "completed", "updated": len(updates)}
