import frappe

def simple_migrate():
    """Simple migration test"""
    print("Testing migration...")
    
    # Try to create a simple COA AMB
    try:
        doc = frappe.get_doc({
            "doctype": "COA AMB",
            "naming_series": "COA-.YY.-.####",
            "product_item": "0638",
            "item_name": "Test Product",
            "item_code": "0638",
            "coa_quality_test_parameter": [{
                "parameter_name": "Appearance",
                "specification": "Test spec",
                "value": "Test value",  # This should show as Acceptance Criteria
                "result": "Test result",
                "status": "Pass"
            }]
        })
        
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"? Created: {doc.name}")
        return {"status": "success", "name": doc.name}
        
    except Exception as e:
        print(f"? Error: {str(e)[:200]}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    simple_migrate()
