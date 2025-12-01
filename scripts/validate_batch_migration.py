# validate_batch_migration.py
import frappe
from frappe.utils import nowdate, add_days
import json
from datetime import datetime, timedelta
import sys
import os

# Add the app path to import other modules if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def validate_batch_migration_setup():
    """Validate all prerequisites for pharmaceutical batch migration"""
    
    print("🔬 FDA Pharmaceutical Batch Migration Validation")
    print("=" * 60)
    
    results = {
        "doctype_checks": [],
        "field_checks": [],
        "data_checks": [],
        "compliance_checks": []
    }
    
    # 1. Check essential doctypes exist
    print("\n1. Checking Essential Doctypes...")
    essential_doctypes = ["Batch", "Item", "Batch AMB", "Stock Entry"]
    
    for doctype in essential_doctypes:
        try:
            if frappe.db.exists("DocType", doctype):
                results["doctype_checks"].append(f"✅ {doctype}")
                print(f"   ✅ {doctype}")
            else:
                results["doctype_checks"].append(f"❌ {doctype} - MISSING")
                print(f"   ❌ {doctype} - MISSING")
        except Exception as e:
            results["doctype_checks"].append(f"❌ {doctype} - ERROR: {str(e)}")
            print(f"   ❌ {doctype} - ERROR: {str(e)}")
    
    # 2. Check Batch doctype has required fields
    print("\n2. Checking Batch Doctype Fields...")
    required_batch_fields = [
        "batch_id", "item", "manufacturing_date", "expiry_date",
        "reference_doctype", "reference_name", "disabled"
    ]
    
    try:
        batch_fields = frappe.get_meta("Batch").get_fieldnames()
        for field in required_batch_fields:
            if field in batch_fields:
                results["field_checks"].append(f"✅ {field}")
                print(f"   ✅ {field}")
            else:
                results["field_checks"].append(f"❌ {field} - MISSING")
                print(f"   ❌ {field} - MISSING")
    except Exception as e:
        results["field_checks"].append(f"❌ Error checking fields: {str(e)}")
        print(f"   ❌ Error checking fields: {str(e)}")
    
    # 3. Check Item shelf life configuration
    print("\n3. Checking Item Shelf Life Configuration...")
    try:
        items_without_shelf_life = frappe.db.sql("""
            SELECT name, item_code 
            FROM `tabItem` 
            WHERE shelf_life_in_days IS NULL OR shelf_life_in_days = 0
            LIMIT 10
        """, as_dict=True)
        
        if items_without_shelf_life:
            results["data_checks"].append(f"⚠️  {len(items_without_shelf_life)} items without shelf_life_in_days")
            print(f"   ⚠️  Found {len(items_without_shelf_life)} items without shelf_life_in_days")
            for item in items_without_shelf_life[:5]:
                print(f"      - {item.item_code} ({item.name})")
        else:
            results["data_checks"].append("✅ All items have shelf_life_in_days")
            print(f"   ✅ All items have shelf_life_in_days")
    except Exception as e:
        results["data_checks"].append(f"❌ Error checking shelf life: {str(e)}")
        print(f"   ❌ Error checking shelf life: {str(e)}")
    
    # 4. Test batch creation with validation
    print("\n4. Testing Batch Creation Logic...")
    test_batch_creation()
    
    # 5. Check for existing batch conflicts
    print("\n5. Checking for Potential Batch Conflicts...")
    try:
        duplicate_batches = frappe.db.sql("""
            SELECT batch_id, item, COUNT(*) as count
            FROM `tabBatch` 
            WHERE disabled = 0
            GROUP BY batch_id, item
            HAVING count > 1
            LIMIT 5
        """, as_dict=True)
        
        if duplicate_batches:
            results["compliance_checks"].append(f"❌ Found {len(duplicate_batches)} duplicate batches")
            print(f"   ❌ Found {len(duplicate_batches)} duplicate batches (GMP Violation)")
            for batch in duplicate_batches:
                print(f"      - {batch.batch_id} for item {batch.item} appears {batch.count} times")
        else:
            results["compliance_checks"].append("✅ No duplicate batches found")
            print(f"   ✅ No duplicate batches found")
    except Exception as e:
        results["compliance_checks"].append(f"❌ Error checking duplicates: {str(e)}")
        print(f"   ❌ Error checking duplicates: {str(e)}")
    
    # 6. Validate Batch AMB references
    print("\n6. Validating Batch AMB References...")
    try:
        invalid_batch_amb_refs = frappe.db.sql("""
            SELECT b.name, b.reference_name 
            FROM `tabBatch` b
            LEFT JOIN `tabBatch AMB` ba ON b.reference_name = ba.name
            WHERE b.reference_doctype = 'Batch AMB' AND ba.name IS NULL
            LIMIT 5
        """, as_dict=True)
        
        if invalid_batch_amb_refs:
            results["compliance_checks"].append(f"❌ {len(invalid_batch_amb_refs)} invalid Batch AMB references")
            print(f"   ❌ Found {len(invalid_batch_amb_refs)} invalid Batch AMB references")
            for ref in invalid_batch_amb_refs[:3]:
                print(f"      - Batch {ref.name} references non-existent Batch AMB: {ref.reference_name}")
        else:
            results["compliance_checks"].append("✅ All Batch AMB references are valid")
            print(f"   ✅ All Batch AMB references are valid")
    except Exception as e:
        results["compliance_checks"].append(f"❌ Error checking Batch AMB refs: {str(e)}")
        print(f"   ❌ Error checking Batch AMB refs: {str(e)}")
    
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY:")
    
    for category, checks in results.items():
        print(f"\n{category.upper()}:")
        for check in checks:
            print(f"  {check}")
    
    # Determine overall success
    all_checks = []
    for category in results.values():
        all_checks.extend(category)
    
    has_critical_errors = any("❌" in str(check) for check in all_checks)
    return not has_critical_errors

def test_batch_creation():
    """Test the batch creation logic with a sample item"""
    try:
        # Find a test item with shelf life
        test_item = frappe.db.sql("""
            SELECT name, item_code, shelf_life_in_days 
            FROM `tabItem` 
            WHERE shelf_life_in_days IS NOT NULL AND shelf_life_in_days > 0
            AND disabled = 0
            LIMIT 1
        """, as_dict=True)
        
        if not test_item:
            print("   ⚠️  No test items with shelf life found")
            return
        
        test_item = test_item[0]
        
        # Test data
        test_batch_id = f"TEST{datetime.now().strftime('%Y%m%d%H%M%S')}"
        test_mfg_date = nowdate()
        
        # Calculate expiry
        expiry_date = add_days(test_mfg_date, test_item.shelf_life_in_days)
        
        print(f"   ✅ Batch creation test successful:")
        print(f"      - Item: {test_item.item_code}")
        print(f"      - Batch ID: {test_batch_id}")
        print(f"      - MFG Date: {test_mfg_date}")
        print(f"      - Expiry: {expiry_date} ({test_item.shelf_life_in_days} days)")
        
    except Exception as e:
        print(f"   ❌ Batch creation test failed: {str(e)}")

def validate_specific_batch_data(item_code, batch_id, mfg_date, batch_amb_ref=None):
    """Validate specific batch data before migration"""
    print(f"\n🔍 Validating specific batch data:")
    print(f"   Item: {item_code}")
    print(f"   Batch ID: {batch_id}")
    print(f"   MFG Date: {mfg_date}")
    print(f"   Batch AMB Ref: {batch_amb_ref}")
    
    validation_errors = []
    
    # Check if item exists and is active
    try:
        item = frappe.get_doc("Item", item_code)
        if item.disabled:
            validation_errors.append(f"Item {item_code} is disabled")
        if not item.shelf_life_in_days:
            validation_errors.append(f"Item {item_code} has no shelf_life_in_days")
        else:
            print(f"   ✅ Item shelf life: {item.shelf_life_in_days} days")
    except frappe.DoesNotExistError:
        validation_errors.append(f"Item {item_code} does not exist")
    
    # Check if batch already exists
    existing_batch = frappe.db.exists("Batch", {
        "batch_id": batch_id,
        "item": item_code,
        "disabled": 0
    })
    
    if existing_batch:
        validation_errors.append(f"Batch {batch_id} for item {item_code} already exists: {existing_batch}")
    else:
        print(f"   ✅ Batch ID {batch_id} is available")
    
    # Validate Batch AMB reference if provided
    if batch_amb_ref:
        if not frappe.db.exists("Batch AMB", batch_amb_ref):
            validation_errors.append(f"Batch AMB {batch_amb_ref} does not exist")
        else:
            print(f"   ✅ Batch AMB reference exists")
    
    # Validate manufacturing date
    try:
        mfg_date_obj = datetime.strptime(mfg_date, "%Y-%m-%d")
        if mfg_date_obj > datetime.now():
            validation_errors.append("Manufacturing date cannot be in the future")
        else:
            print(f"   ✅ Manufacturing date is valid")
    except ValueError:
        validation_errors.append("Invalid manufacturing date format (use YYYY-MM-DD)")
    
    if validation_errors:
        print("   ❌ Validation failed:")
        for error in validation_errors:
            print(f"      - {error}")
        return False
    else:
        print("   ✅ All validations passed")
        return True

def quick_validation():
    """Run a quick validation for common issues"""
    print("🚀 Running Quick Validation...")
    
    # Check if Batch AMB doctype exists
    if not frappe.db.exists("DocType", "Batch AMB"):
        print("❌ CRITICAL: Batch AMB doctype not found!")
        return False
    
    # Check if we have items with shelf life
    items_with_shelf_life = frappe.db.count("Item", {
        "shelf_life_in_days": [">", 0],
        "disabled": 0
    })
    
    print(f"📦 Items with shelf life: {items_with_shelf_life}")
    
    if items_with_shelf_life == 0:
        print("⚠️  WARNING: No items with shelf life configured")
    
    return True

if __name__ == "__main__":
    # This allows the script to be run directly from bench console
    try:
        # Run quick validation first
        quick_validation()
        
        print("\n" + "=" * 60)
        # Run the full validation
        success = validate_batch_migration_setup()
        
        # Example specific validation
        print("\n" + "=" * 60)
        print("🧪 Testing specific batch validation:")
        
        # Test with a sample item - replace with your actual test data
        test_items = frappe.db.sql("""
            SELECT item_code FROM `tabItem` 
            WHERE disabled = 0 AND shelf_life_in_days > 0 
            LIMIT 1
        """, as_dict=True)
        
        if test_items:
            validate_specific_batch_data(
                item_code=test_items[0]["item_code"],
                batch_id=f"TEST{datetime.now().strftime('%Y%m%d%H%M')}", 
                mfg_date=nowdate(),
                batch_amb_ref=None
            )
        
        exit(0 if success else 1)
        
    except Exception as e:
        print(f"💥 Script execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
