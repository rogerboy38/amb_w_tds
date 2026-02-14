"""
Dynamic setup for serial tracking based on your Item doctype requirements
"""

import frappe

def setup_serial_tracking():
    """Setup serial tracking system based on actual field requirements"""
    print("🔧 Setting up Serial Tracking System")
    print("=" * 60)
    
    # Check required fields for Item
    item_meta = frappe.get_meta("Item")
    required_fields = [f.fieldname for f in item_meta.fields if f.reqd]
    
    print(f"📋 Item has {len(required_fields)} required fields:")
    for fieldname in required_fields:
        field = item_meta.get_field(fieldname)
        print(f"  • {fieldname} ({field.fieldtype})")
    
    # Create test item with correct fields
    print("\n🎯 Creating test item...")
    
    item_data = {
        "doctype": "Item",
        "item_code": "AMB-TEST-ITEM",
        "item_name": "AMB Test Item",
        "description": "Test item for serial tracking with AMB hierarchy",
        "item_group": "All Item Groups",  # Required Link field
        "stock_uom": "Nos",  # Required Link field
        "product_key": "AMB-TEST-KEY-001",  # Required Data field
        "is_stock_item": 1,
        "has_serial_no": 1,
        "has_batch_no": 1,
        "serial_no_series": "AMB-.#####",
        "create_new_batch": 1,
        "batch_number_series": "BATCH-AMB-.#####",
        "valuation_method": "FIFO",  # Optional but good to set
        "is_fixed_asset": 0,  # Has default of 0
    }
    
    try:
        # Check if item already exists
        if frappe.db.exists("Item", "AMB-TEST-ITEM"):
            print("✅ Test item already exists: AMB-TEST-ITEM")
        else:
            item = frappe.get_doc(item_data)
            item.insert(ignore_permissions=True)
            print("✅ Created test item: AMB-TEST-ITEM")
        
        # Create sample batches
        print("\n📦 Creating sample batches...")
        
        batches = [
            {"batch_id": "0219074251-88", "item": "AMB-TEST-ITEM", "golden": "0219074251"},
            {"batch_id": "2024123456-01", "item": "AMB-TEST-ITEM", "golden": "2024123456"},
        ]
        
        for batch in batches:
            if not frappe.db.exists("Batch", batch["batch_id"]):
                batch_doc = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_id": batch["batch_id"],
                    "item": batch["item"],
                })
                
                # Add golden_number if field exists
                batch_meta = frappe.get_meta("Batch")
                if batch_meta.has_field('golden_number'):
                    batch_doc.golden_number = batch["golden"]
                
                batch_doc.insert(ignore_permissions=True)
                print(f"✅ Created batch: {batch['batch_id']}")
            else:
                print(f"📦 Batch already exists: {batch['batch_id']}")
        
        print("\n" + "=" * 60)
        print("🎉 Setup complete!")
        print("Test item: AMB-TEST-ITEM")
        print("Sample batches created:")
        print("  • 0219074251-88")
        print("  • 2024123456-01")
        print("\nYou can now test the serial tracking agent in Raven.")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_serial_tracking()
