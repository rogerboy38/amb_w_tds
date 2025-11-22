from __future__ import unicode_literals
import frappe

def execute():
    """Add concentration system configuration"""
    print("🚀 Setting up concentration system for FoxPro migration...")
    
    create_default_conversion_factors()
    update_existing_batches_with_concentration()
    
    print("✅ Concentration system setup completed")

def create_default_conversion_factors():
    """Create default juice conversion factors"""
    
    conversion_factors = [
        {
            "from_concentration": "1X",
            "to_concentration": "30X", 
            "conversion_factor": 25.0,
            "description": "Conversion from Normal Juice (1X) to Concentrate (30X)"
        },
        {
            "from_concentration": "30X",
            "to_concentration": "200X", 
            "conversion_factor": 2.0,
            "description": "Conversion from Concentrate (30X) to Pure Powder (200X)"
        },
        {
            "from_concentration": "1X", 
            "to_concentration": "200X",
            "conversion_factor": 10.0,
            "description": "Direct conversion from Normal Juice (1X) to Pure Powder (200X)"
        }
    ]
    
    for factor in conversion_factors:
        # Check if already exists
        existing = frappe.db.exists("Juice Conversion Config", {
            "from_concentration": factor["from_concentration"],
            "to_concentration": factor["to_concentration"]
        })
        
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Juice Conversion Config",
                **factor
            })
            doc.insert(ignore_permissions=True)
            print(f"✅ Created conversion: {factor['from_concentration']} → {factor['to_concentration']}")

def update_existing_batches_with_concentration():
    """Try to set concentration type based on existing batch names"""
    
    batches = frappe.get_all("Batch AMB", fields=["name", "custom_golden_number", "title"])
    
    for batch in batches:
        golden_number = batch.get("custom_golden_number") or batch.get("title", "")
        
        # Detect concentration type from golden number pattern
        concentration_type = None
        if golden_number:
            if golden_number.startswith("02"):  # Juice products (0227...)
                concentration_type = "1X"
            elif golden_number.startswith("03"):  # Powder products (0301, 0302, 0303...)
                concentration_type = "200X"
            elif "30X" in golden_number.upper():
                concentration_type = "30X"
        
        if concentration_type:
            try:
                frappe.db.set_value("Batch AMB", batch.name, "concentration_type", concentration_type)
                print(f"✅ Set {concentration_type} for batch {batch.name}")
            except Exception as e:
                print(f"⚠️ Could not set concentration for {batch.name}: {e}")
