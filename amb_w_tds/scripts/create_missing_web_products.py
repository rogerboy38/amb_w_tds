"""
Create missing web product items
Execute: bench --site [sitename] execute amb_w_tds.scripts.create_missing_web_products.run
"""

import frappe

def run():
    """Create missing web product items"""
    print("\n" + "="*80)
    print("CREATING MISSING WEB PRODUCT ITEMS")
    print("="*80 + "\n")
    
    # Define missing web products - FIXED
    web_products = [
        {
            "item_code": "0417",
            "item_name": "Aloe Acetypol 15/18",
            "item_group": "Aloe Products",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "description": "Aloe Acetypol 15/18 - Decolorized aloe vera powder",
            "product_key": "PROD-0417"  # Added
        },
        {
            "item_code": "0706",
            "item_name": "Innovaloe Aloe Vera Gel Concentrate 10:1 Organic",
            "item_group": "Aloe Products",
            "stock_uom": "Litre",  # Changed from "Liter"
            "is_stock_item": 1,
            "description": "Innovaloe Aloe Vera Gel Concentrate 10:1 - Organic certified",
            "product_key": "PROD-0706"  # Added
        }
    ]
    
    # Check if Item Group exists
    if not frappe.db.exists("Item Group", "Aloe Products"):
        print("Creating Item Group: Aloe Products")
        try:
            group = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "Aloe Products",
                "parent_item_group": "Products",
                "is_group": 0
            })
            group.insert(ignore_permissions=True)
        except Exception as e:
            print(f"⚠ Item Group error: {str(e)}")
    
    created = []
    skipped = []
    failed = []
    
    for product in web_products:
        item_code = product["item_code"]
        
        if frappe.db.exists("Item", item_code):
            skipped.append(item_code)
            print(f"⊘ Skipped {item_code} (already exists)")
            continue
        
        try:
            item = frappe.get_doc({
                "doctype": "Item",
                **product
            })
            item.insert(ignore_permissions=True)
            created.append(item_code)
            print(f"✓ Created {item_code}")
        except Exception as e:
            failed.append({"item": item_code, "error": str(e)})
            print(f"✗ Failed to create {item_code}: {str(e)}")
    
    frappe.db.commit()
    
    print("\n" + "="*80)
    print(f"Created: {len(created)}, Skipped: {len(skipped)}, Failed: {len(failed)}")
    print("="*80 + "\n")
    
    if failed:
        print("Failed items:")
        for fail in failed:
            print(f"  - {fail['item']}: {fail['error']}")
    
    return {"created": created, "skipped": skipped, "failed": failed}

if __name__ == "__main__":
    run()
