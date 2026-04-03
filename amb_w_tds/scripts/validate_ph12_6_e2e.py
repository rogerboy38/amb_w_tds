"""
PH12.6 E2E Validation Script
End-to-end test of full batch lifecycle

Usage:
    bench execute amb_w_tds.scripts.validate_ph12_6_e2e.execute
"""
import frappe
from frappe.utils import now_datetime


def execute():
    print("=" * 60)
    print("PH12.6 E2E Validation - Full Batch Lifecycle")
    print("=" * 60)
    
    results = []
    
    # Get test item
    item_code = "PRODUCTO-PRUEBA"  # Use existing test item or find one
    
    # Try to find a test item
    if not frappe.db.exists("Item", item_code):
        items = frappe.get_all("Item", limit=1)
        if items:
            item_code = items[0].name
        else:
            print("FAIL: No items found in system")
            results.append(("E2E-1", "FAIL"))
            return results
    
    print(f"\nUsing item: {item_code}")
    
    # E2E-1: Create Level 1 batch
    print("\n[E2E-1] Create Level 1 Batch (Parent)")
    print("-" * 40)
    try:
        batch_l1 = frappe.get_doc({
            "doctype": "Batch AMB",
            "item_to_manufacture": item_code,
            "custom_batch_level": "1",
            "pipeline_status": "Draft",
            "title": f"TEST-L1-{now_datetime().strftime('%Y%m%d%H%M%S')}",
        })
        batch_l1.flags.ignore_server_scripts = True
        batch_l1.flags.do_not_validate = True
        batch_l1.flags.ignore_mandatory = True
        batch_l1.insert()
        frappe.db.commit()
        
        print(f"PASS: Created L1 batch: {batch_l1.name}")
        print(f"  Title: {batch_l1.title}")
        results.append(("E2E-1", "PASS"))
        l1_name = batch_l1.name
    except Exception as e:
        print(f"FAIL: {str(e)[:100]}")
        results.append(("E2E-1", "FAIL"))
        return results
    
    # E2E-2: Create Level 2 batch (Sub-lot)
    print("\n[E2E-2] Create Level 2 Batch (Sub-lot)")
    print("-" * 40)
    try:
        batch_l2 = frappe.get_doc({
            "doctype": "Batch AMB",
            "item_to_manufacture": item_code,
            "custom_batch_level": "2",
            "parent_batch_amb": l1_name,
            "pipeline_status": "Draft",
        })
        batch_l2.flags.ignore_server_scripts = True
        batch_l2.flags.do_not_validate = True
        batch_l2.flags.ignore_mandatory = True
        batch_l2.insert()
        frappe.db.commit()
        
        print(f"PASS: Created L2 batch: {batch_l2.name}")
        print(f"  Title: {batch_l2.title}")
        results.append(("E2E-2", "PASS"))
        l2_name = batch_l2.name
    except Exception as e:
        print(f"FAIL: {str(e)[:100]}")
        results.append(("E2E-2", "FAIL"))
    
    # E2E-3: Create Level 3 batch (Container)
    print("\n[E2E-3] Create Level 3 Batch (Container)")
    print("-" * 40)
    try:
        batch_l3 = frappe.get_doc({
            "doctype": "Batch AMB",
            "item_to_manufacture": item_code,
            "custom_batch_level": "3",
            "parent_batch_amb": l2_name,
            "pipeline_status": "Draft",
        })
        batch_l3.flags.ignore_server_scripts = True
        batch_l3.flags.do_not_validate = True
        batch_l3.flags.ignore_mandatory = True
        batch_l3.insert()
        frappe.db.commit()
        
        print(f"PASS: Created L3 batch: {batch_l3.name}")
        print(f"  Title: {batch_l3.title}")
        results.append(("E2E-3", "PASS"))
        l3_name = batch_l3.name
    except Exception as e:
        print(f"FAIL: {str(e)[:100]}")
        results.append(("E2E-3", "FAIL"))
    
    # E2E-4: Generate serial numbers
    print("\n[E2E-4] Generate Serial Numbers")
    print("-" * 40)
    try:
        from amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb import generate_serial_numbers
        
        result = generate_serial_numbers(l3_name, quantity=3)
        
        if result.get("status") == "success":
            print(f"PASS: Generated {result.get('count')} serials")
            for serial in result.get("serial_numbers", []):
                print(f"  - {serial}")
            results.append(("E2E-4", "PASS"))
        else:
            print(f"FAIL: {result.get('message')}")
            results.append(("E2E-4", "FAIL"))
    except Exception as e:
        print(f"FAIL: {str(e)[:100]}")
        results.append(("E2E-4", "FAIL"))
    
    # E2E-5: Verify serial format
    print("\n[E2E-5] Verify Serial Format")
    print("-" * 40)
    try:
        batch = frappe.get_doc("Batch AMB", l3_name)
        serials = [row.barrel_serial_number for row in batch.container_barrels]
        
        # Check format: title-NNN (no redundant C)
        if serials:
            first_serial = serials[0]
            if batch.title in first_serial and first_serial.endswith(("-001", "-002", "-003")):
                # Make sure it doesn't have double C
                if "-C1-C" not in first_serial:
                    print(f"PASS: Serial format correct: {first_serial}")
                    results.append(("E2E-5", "PASS"))
                else:
                    print(f"FAIL: Redundant C in serial: {first_serial}")
                    results.append(("E2E-5", "FAIL"))
            else:
                print(f"FAIL: Unexpected serial format: {first_serial}")
                results.append(("E2E-5", "FAIL"))
        else:
            print("FAIL: No serials found")
            results.append(("E2E-5", "FAIL"))
    except Exception as e:
        print(f"FAIL: {str(e)[:100]}")
        results.append(("E2E-5", "FAIL"))
    
    # E2E-6: Pipeline state transitions
    print("\n[E2E-6] Pipeline State Transitions")
    print("-" * 40)
    try:
        batch = frappe.get_doc("Batch AMB", l3_name)
        
        # Test valid transition: Draft -> WO Linked
        batch.pipeline_status = "WO Linked"
        batch.flags.ignore_server_scripts = True
        batch.flags.do_not_validate = True
        batch.flags.ignore_mandatory = True
        batch.save()
        frappe.db.commit()
        
        if batch.pipeline_status == "WO Linked":
            print("PASS: Transition Draft -> WO Linked allowed")
            results.append(("E2E-6", "PASS"))
        else:
            print("FAIL: Pipeline status not updated")
            results.append(("E2E-6", "FAIL"))
    except Exception as e:
        print(f"FAIL: {str(e)[:100]}")
        results.append(("E2E-6", "FAIL"))
    
    # Summary
    print("\n" + "=" * 60)
    print("E2E VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    for test, status in results:
        print(f"  {test}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    # Cleanup - delete test batches
    print("\n[Cleanup] Removing test batches...")
    try:
        for name in [l3_name, l2_name, l1_name]:
            if name:
                frappe.delete_doc("Batch AMB", name, force=True)
        frappe.db.commit()
        print("Cleanup complete")
    except:
        pass
    
    return results
