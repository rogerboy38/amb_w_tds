"""
Setup and configuration utilities for serial tracking
"""

import frappe

def configure_serial_tracking():
    """Configure serial tracking system"""
    print("🔧 Configuring Serial Tracking System...")
    
    # Check if required doctypes exist
    required_doctypes = ["Item", "Stock Entry", "Serial No", "Batch"]
    
    for doctype in required_doctypes:
        if not frappe.db.exists("DocType", doctype):
            print(f"❌ Missing doctype: {doctype}")
            return False
    
    print("✅ Required doctypes exist")
    
    # Check Item fields to see what's required
    item_fields = frappe.get_meta("Item").fields
    required_fields = []
    
    # Check which fields are mandatory
    for field in item_fields:
        if field.reqd:
            required_fields.append(field.fieldname)
    
    print(f"📋 Required Item fields: {required_fields}")
    
    # Create sample item with serial tracking
    if not frappe.db.exists("Item", "AMB-TEST-ITEM"):
        item_data = {
            "doctype": "Item",
            "item_code": "AMB-TEST-ITEM",
            "item_name": "AMB Test Item",
            "description": "Test item for serial tracking with AMB hierarchy",
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "has_serial_no": 1,
            "has_batch_no": 1,
            "serial_no_series": "AMB-.#####",
            "create_new_batch": 1,
            "batch_number_series": "BATCH-AMB-.#####"
        }
        
        # Add product_key if it exists as a field
        item_meta = frappe.get_meta("Item")
        if hasattr(item_meta, 'has_field') and item_meta.has_field('product_key'):
            item_data["product_key"] = "AMB-TEST-KEY-001"
        
        # Add other common required fields
        if "valuation_method" in required_fields:
            item_data["valuation_method"] = "FIFO"
        
        if "is_fixed_asset" in required_fields:
            item_data["is_fixed_asset"] = 0
        
        item = frappe.get_doc(item_data)
        item.insert(ignore_permissions=True)
        print("✅ Created test item: AMB-TEST-ITEM")
    
    print("✅ Configuration complete!")
    return True

def create_sample_data():
    """Create sample serial numbers"""
    print("📝 Creating sample serial data...")
    
    # Check if test item exists, create if not
    if not frappe.db.exists("Item", "AMB-TEST-ITEM"):
        configure_serial_tracking()
    
    # Create sample batches
    batches = [
        {"batch_id": "0219074251-88", "item": "AMB-TEST-ITEM", "golden": "0219074251"},
        {"batch_id": "2024123456-01", "item": "AMB-TEST-ITEM", "golden": "2024123456"},
        {"batch_id": "TEST-AMB-001", "item": "AMB-TEST-ITEM", "golden": "TESTAMB001"},
    ]
    
    for batch in batches:
        if not frappe.db.exists("Batch", batch["batch_id"]):
            try:
                batch_doc = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_id": batch["batch_id"],
                    "item": batch["item"],
                })
                
                # Add golden_number field if it exists
                batch_meta = frappe.get_meta("Batch")
                if hasattr(batch_meta, 'has_field') and batch_meta.has_field('golden_number'):
                    batch_doc.golden_number = batch["golden"]
                
                batch_doc.insert(ignore_permissions=True)
                print(f"✅ Created batch: {batch['batch_id']}")
            except Exception as e:
                print(f"⚠️ Could not create batch {batch['batch_id']}: {e}")
    
    print("✅ Sample data created!")
    return True

def get_agent_status():
    """Get agent status"""
    return {
        "agent": "serial_tracking",
        "version": "2.0.0",
        "status": "active",
        "capabilities": [
            "serial_generation",
            "validation",
            "configuration",
            "health_check"
        ],
        "raven_integrated": True
    }

def setup_test_environment():
    """Complete test environment setup"""
    print("🚀 Setting up test environment...")
    
    # 1. Configure serial tracking
    configure_serial_tracking()
    
    # 2. Create sample data
    create_sample_data()
    
    # 3. Test agent functionality
    print("🧪 Testing agent functionality...")
    
    # Test serial generation
    from amb_w_tds.raven.serial_tracking_agent_raven import SerialTrackingAgent
    agent = SerialTrackingAgent()
    
    test_results = []
    
    # Test 1: Help command
    result = agent.handle_message("help")
    test_results.append(("Help Command", "✅" if result.get("content") else "❌"))
    
    # Test 2: Generate serials
    result = agent.handle_message("generate 2 serials for batch 0219074251-88")
    test_results.append(("Serial Generation", "✅" if result.get("content") else "❌"))
    
    # Test 3: Validate serial
    result = agent.handle_message("validate serial 0219074251-0100")
    test_results.append(("Serial Validation", "✅" if result.get("content") else "❌"))
    
    print("\n📊 Test Results:")
    for test_name, status in test_results:
        print(f"  {status} {test_name}")
    
    print("\n🎉 Test environment setup complete!")
    return True

if __name__ == "__main__":
    # For command line testing
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "configure":
            frappe.init(site="frappe-bench.local")  # Update with your site
            frappe.connect()
            configure_serial_tracking()
            frappe.destroy()
        elif sys.argv[1] == "sample":
            frappe.init(site="frappe-bench.local")  # Update with your site
            frappe.connect()
            create_sample_data()
            frappe.destroy()
        elif sys.argv[1] == "setup":
            frappe.init(site="frappe-bench.local")  # Update with your site
            frappe.connect()
            setup_test_environment()
            frappe.destroy()
        elif sys.argv[1] == "status":
            print(get_agent_status())
