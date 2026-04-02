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
    
    updated_count = 0
    
    for idx, row in enumerate(batch.container_barrels, 1):
        old_serial = row.barrel_serial_number
        if not old_serial:
            continue
        
        # Check if this looks like a stale serial (starts with old golden number pattern)
        if old_serial.startswith("0334925261"):
            new_serial = f"{correct_title}-C{idx:03d}"
            print(f"  Updating: {old_serial} -> {new_serial}")
            row.barrel_serial_number = new_serial
            updated_count += 1
    
    if updated_count > 0:
        # Save without validation to avoid issues
        batch.flags.do_not_validate = True
        batch.flags.ignore_permissions = True
        batch.save()
        frappe.db.commit()
        print(f"Updated {updated_count} serial numbers successfully")
    else:
        print("No stale serial numbers found")
    
    return {"status": "completed", "updated": updated_count}
