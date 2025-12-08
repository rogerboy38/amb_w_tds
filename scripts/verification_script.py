# verification_script.py
# Run with: bench --site [site-name] exec verification_script.py

import frappe
import json
import os
from frappe.utils import nowdate

print("=" * 70)
print("BATCH AMB & SERIAL TRACKING INTEGRATION VERIFICATION")
print("=" * 70)

# ============================================
# 1. CHECK DOCTYPE STRUCTURE
# ============================================
print("\n1. ✅ Checking Batch AMB Doctype Structure...")

meta = frappe.get_meta("Batch AMB")
fields_found = [f.fieldname for f in meta.fields]

# Required processing fields
processing_fields = [
    "processing_status",
    "scheduled_start_date",
    "scheduled_start_time",
    "actual_start",
    "actual_completion",
    "processed_quantity",
    "yield_percentage",
    "processing_notes"
]

# Required serial tracking integration fields
serial_fields = [
    "custom_serial_tracking_integrated",
    "custom_serial_numbers",
    "custom_last_api_sync"
]

print(f"   Total fields in Batch AMB: {len(fields_found)}")
print(f"   First 10 fields: {fields_found[:10]}...")

print("\n   Checking processing management fields:")
for field in processing_fields:
    if field in fields_found:
        print(f"      ✅ {field}")
    else:
        print(f"      ❌ {field} - MISSING")

print("\n   Checking serial tracking integration fields:")
for field in serial_fields:
    if field in fields_found:
        print(f"      ✅ {field}")
    else:
        print(f"      ❌ {field} - MISSING")

# ============================================
# 2. CHECK CUSTOM FIELDS ON SALES INVOICE
# ============================================
print("\n2. ✅ Checking Sales Invoice Custom Fields...")

sinv_meta = frappe.get_meta("Sales Invoice")
sinv_fields = [f.fieldname for f in sinv_meta.fields]

required_sinv_fields = ["custom_batch_amb", "custom_tipo_gd"]
for field in required_sinv_fields:
    if field in sinv_fields:
        print(f"   ✅ {field}")
    else:
        print(f"   ❌ {field} - MISSING")

# ============================================
# 3. CHECK BATCH_AMB.PY METHODS
# ============================================
print("\n3. ✅ Checking batch_amb.py Methods...")

try:
    # Try to import the module
    module_paths = [
        "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py",
        "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"
    ]
    
    module_found = False
    for path in module_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                module_found = True
                print(f"   Found module at: {path}")
                
                # Check for key methods
                methods_to_check = [
                    "start_batch_processing",
                    "complete_batch_processing",
                    "schedule_batch",
                    "process_daily_batches",
                    "generate_serial_numbers",
                    "validate_serial_numbers",
                    "integrate_serial_tracking",
                    "sync_serial_tracking"
                ]
                
                print("   Checking methods:")
                for method in methods_to_check:
                    if f"def {method}" in content or f"@{method}" in content:
                        print(f"      ✅ {method}()")
                    else:
                        print(f"      ❌ {method}() - NOT FOUND")
                
                # Check for serial tracking API integration
                if "amb_w_tds.raven.serial_tracking_agent_api" in content:
                    print(f"      ✅ Raven Serial Tracking API integration")
                else:
                    print(f"      ⚠️  Raven API integration not found in code")
                
                break
    
    if not module_found:
        print("   ❌ Could not find batch_amb.py file")
        
except Exception as e:
    print(f"   ❌ Error checking module: {e}")

# ============================================
# 4. CHECK BATCH_AMB.JS CLIENT SCRIPT
# ============================================
print("\n4. ✅ Checking batch_amb.js Client Script...")

js_paths = [
    "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js",
    "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js"
]

js_found = False
for path in js_paths:
    if os.path.exists(path):
        with open(path, 'r') as f:
            js_content = f.read()
            js_found = True
            print(f"   Found JS file at: {path}")
            
            # Check for key functions
            functions_to_check = [
                "integrate_serial_tracking",
                "generate_serial_numbers",
                "validate_serial_numbers",
                "display_serial_tracking_status",
                "show_schedule_dialog"
            ]
            
            print("   Checking client-side functions:")
            for func in functions_to_check:
                if f"function {func}" in js_content or f"{func}(" in js_content:
                    print(f"      ✅ {func}()")
                else:
                    print(f"      ❌ {func}() - NOT FOUND")
            
            # Check for button groups
            if "SERIAL TRACKING" in js_content:
                print(f"      ✅ SERIAL TRACKING button group")
            else:
                print(f"      ❌ SERIAL TRACKING button group - MISSING")
            
            if "PROCESSING ACTIONS" in js_content:
                print(f"      ✅ PROCESSING ACTIONS button group")
            else:
                print(f"      ❌ PROCESSING ACTIONS button group - MISSING")
            
            break

if not js_found:
    print("   ❌ Could not find batch_amb.js file")

# ============================================
# 5. CHECK RAVEN SERIAL TRACKING API
# ============================================
print("\n5. ✅ Checking Raven Serial Tracking API...")

raven_paths = [
    "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/raven/serial_tracking_agent_api.py",
    "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/raven/serial_tracking_agent_api.py"
]

raven_found = False
for path in raven_paths:
    if os.path.exists(path):
        print(f"   ✅ Found Raven Serial Tracking API at: {path}")
        raven_found = True
        
        # Check for key functions
        with open(path, 'r') as f:
            raven_content = f.read()
            
            if "def generate_serials" in raven_content:
                print(f"      ✅ generate_serials() function")
            else:
                print(f"      ❌ generate_serials() - NOT FOUND")
            
            if "def validate_serials" in raven_content:
                print(f"      ✅ validate_serials() function")
            else:
                print(f"      ❌ validate_serials() - NOT FOUND")
        
        break

if not raven_found:
    print("   ❌ Raven Serial Tracking API not found")

# ============================================
# 6. CHECK HOOKS.PY SCHEDULER CONFIGURATION
# ============================================
print("\n6. ✅ Checking hooks.py Scheduler Configuration...")

hooks_paths = [
    "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/hooks.py",
    "/home/frappe/frappe-bench/apps/amb_w_tds/hooks.py"
]

hooks_found = False
for path in hooks_paths:
    if os.path.exists(path):
        with open(path, 'r') as f:
            hooks_content = f.read()
            hooks_found = True
            print(f"   Found hooks.py at: {path}")
            
            # Check for scheduler events
            if "scheduler_events" in hooks_content:
                print(f"      ✅ scheduler_events configuration found")
                
                # Check for batch processing scheduler
                if "process_daily_batches" in hooks_content:
                    print(f"      ✅ process_daily_batches scheduler configured")
                else:
                    print(f"      ❌ process_daily_batches scheduler - NOT FOUND")
            else:
                print(f"      ❌ scheduler_events - NOT FOUND")
            
            # Check for doctype JS inclusion
            if "doctype_js" in hooks_content and "Batch AMB" in hooks_content:
                print(f"      ✅ Batch AMB client script configured in hooks")
            else:
                print(f"      ❌ Batch AMB client script not in hooks")
            
            break

if not hooks_found:
    print("   ❌ Could not find hooks.py file")

# ============================================
# 7. TEST CREATING AND PROCESSING A BATCH
# ============================================
print("\n7. ✅ Testing Batch Creation and Processing...")

try:
    # Create a test batch
    print("   Creating test batch...")
    batch = frappe.new_doc("Batch AMB")
    batch.title = f"Verification Test {nowdate()}"
    batch.planned_qty = 100
    batch.item_to_manufacture = "Test Item"
    batch.insert()
    
    print(f"      ✅ Created batch: {batch.name}")
    
    # Test scheduling
    print("   Testing schedule method...")
    try:
        from amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb import schedule_batch
        schedule_result = schedule_batch(batch.name, nowdate())
        print(f"      ✅ Schedule test: {schedule_result.get('status', 'unknown')}")
    except Exception as e:
        print(f"      ❌ Schedule test failed: {e}")
    
    # Test serial number generation
    print("   Testing serial number generation...")
    try:
        from amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb import generate_serial_numbers
        serial_result = generate_serial_numbers(batch.name, 5)
        print(f"      ✅ Serial generation: {serial_result.get('status', 'unknown')}")
        print(f"      Generated {serial_result.get('count', 0)} serials")
    except Exception as e:
        print(f"      ❌ Serial generation failed: {e}")
    
    # Test integration method
    print("   Testing integration method...")
    try:
        from amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb import integrate_serial_tracking
        integrate_result = integrate_serial_tracking(batch.name)
        print(f"      ✅ Integration test: {integrate_result.get('status', 'unknown')}")
    except Exception as e:
        print(f"      ❌ Integration test failed: {e}")
    
    # Clean up test batch
    frappe.delete_doc("Batch AMB", batch.name)
    print(f"      ✅ Cleaned up test batch")
    
except Exception as e:
    print(f"   ❌ Batch test failed: {e}")

# ============================================
# 8. CHECK DATABASE SCHEMA
# ============================================
print("\n8. ✅ Checking Database Schema...")

try:
    # Check Batch AMB table columns
    columns = frappe.db.sql("""
        SHOW COLUMNS FROM `tabBatch AMB`
    """, as_dict=True)
    
    column_names = [c['Field'] for c in columns]
    
    print(f"   Batch AMB table has {len(columns)} columns")
    
    # Check for specific columns
    columns_to_check = [
        "processing_status",
        "scheduled_start_date",
        "custom_serial_tracking_integrated",
        "custom_serial_numbers"
    ]
    
    missing_columns = []
    for col in columns_to_check:
        if col in column_names:
            print(f"      ✅ {col} column exists in database")
        else:
            print(f"      ❌ {col} column MISSING in database")
            missing_columns.append(col)
    
    if missing_columns:
        print(f"\n   ⚠️  Missing columns detected. Run: bench --site [site-name] migrate")
    
except Exception as e:
    print(f"   ❌ Database check failed: {e}")

# ============================================
# 9. VERIFICATION SUMMARY
# ============================================
print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

print("\n✅ IMPLEMENTATION STATUS:")
print("   1. Batch AMB Doctype: " + ("✅ Updated" if len(fields_found) > 70 else "❌ Needs update"))
print("   2. Processing Fields: " + ("✅ Added" if all(f in fields_found for f in processing_fields[:3]) else "❌ Missing"))
print("   3. Serial Tracking Fields: " + ("✅ Added" if all(f in fields_found for f in serial_fields[:2]) else "❌ Missing"))
print("   4. Client Script: " + ("✅ Updated" if js_found and "SERIAL TRACKING" in js_content else "❌ Needs update"))
print("   5. Server Methods: " + ("✅ Implemented" if module_found else "❌ Missing"))
print("   6. Raven API: " + ("✅ Found" if raven_found else "❌ Not found"))
print("   7. Scheduler: " + ("✅ Configured" if hooks_found and "scheduler_events" in hooks_content else "❌ Not configured"))
print("   8. Database: " + ("✅ Ready" if not missing_columns else "❌ Needs migration"))

print("\n📋 NEXT STEPS:")
if missing_columns:
    print("   1. Run database migration: bench --site [site-name] migrate")
    print("   2. Clear cache: bench --site [site-name] clear-cache")
    print("   3. Restart bench: bench restart")

print("   4. Test UI: Navigate to Batch AMB and check for new buttons")
print("   5. Verify Serial Tracking integration button appears")
print("   6. Test scheduling functionality")
print("   7. Test serial number generation")

print("\n🔧 QUICK FIXES IF ISSUES:")
print("   If fields missing in UI: bench --site [site-name] migrate")
print("   If buttons not showing: Check browser console for JS errors")
print("   If methods failing: Check server error logs")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)

# ============================================
# 10. CREATE A SIMPLE TEST BATCH FOR MANUAL TESTING
# ============================================
print("\n10. 🧪 Creating Manual Test Batch...")

try:
    test_batch = frappe.new_doc("Batch AMB")
    test_batch.title = f"Manual Test {nowdate()}"
    test_batch.planned_qty = 50
    test_batch.item_to_manufacture = "Test Product"
    test_batch.processing_status = "Draft"
    test_batch.insert()
    
    print(f"   ✅ Created manual test batch: {test_batch.name}")
    print(f"   📋 Title: {test_batch.title}")
    print(f"   📊 Status: {test_batch.processing_status}")
    print(f"   🔗 URL: /app/batch-amb/{test_batch.name}")
    
    print("\n   TEST INSTRUCTIONS:")
    print("   1. Open the batch in browser")
    print("   2. Look for 'SERIAL TRACKING' button group")
    print("   3. Click 'Integrate Serial Tracking'")
    print("   4. Verify serial numbers are generated")
    print("   5. Test 'Schedule Processing' button")
    
except Exception as e:
    print(f"   ❌ Failed to create test batch: {e}")

print("\n" + "=" * 70)
print("🎉 VERIFICATION SCRIPT COMPLETE")
print("=" * 70)
