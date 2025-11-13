"""
Create any missing items required for BOM generation
Execute: bench --site [sitename] execute amb_w_tds.scripts.create_missing_items.run
"""

import frappe
from frappe import _

def run():
    """Create missing items for BOM generation"""
    print("\n" + "="*80)
    print("CREATING MISSING ITEMS")
    print("="*80 + "\n")
    
    # Check if Item Groups exist, create if needed
    required_groups = {
        "Raw Material": "Products",
        "Utilities": "Products"
    }
    
    for group_name, parent_group in required_groups.items():
        if not frappe.db.exists("Item Group", group_name):
            print(f"Creating Item Group: {group_name}")
            try:
                group = frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": group_name,
                    "parent_item_group": parent_group,
                    "is_group": 0
                })
                group.insert(ignore_permissions=True)
            except Exception as e:
                print(f"⚠ Item Group already exists or error: {str(e)}")
    
    # Define items to create - FIXED UOMs to match your system
    items_to_create = [
        # Utility Items - using correct UOM names
        {
            "item_code": "WATER-UTILITY",
            "item_name": "Water Utility",
            "item_group": "Utilities",
            "stock_uom": "Litre",  # Changed from "Liter"
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "valuation_rate": 0.001,
            "description": "Water utility consumption",
            "product_key": "UTIL-WATER"  # Added product_key
        },
        {
            "item_code": "ELECTRICITY-UTILITY",
            "item_name": "Electricity Utility",
            "item_group": "Utilities",
            "stock_uom": "Nos",  # Generic unit for kWh
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "valuation_rate": 0.15,
            "description": "Electricity utility consumption (kWh)",
            "product_key": "UTIL-ELEC"
        },
        {
            "item_code": "GAS-UTILITY",
            "item_name": "Gas Utility",
            "item_group": "Utilities",
            "stock_uom": "Nos",  # Generic unit for M3
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "valuation_rate": 0.50,
            "description": "Gas utility consumption (M3)",
            "product_key": "UTIL-GAS"
        },
        {
            "item_code": "LABOR-COST",
            "item_name": "Labor Cost",
            "item_group": "Utilities",
            "stock_uom": "Nos",  # Generic unit for Hours
            "is_stock_item": 0,
            "is_fixed_asset": 0,
            "valuation_rate": 15.00,
            "description": "Labor cost per hour",
            "product_key": "UTIL-LABOR"
        },
        # Base component items
        {
            "item_code": "MALTODEXTRIN",
            "item_name": "Maltodextrin",
            "item_group": "Raw Material",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "is_fixed_asset": 0,
            "valuation_rate": 2.50,
            "description": "Maltodextrin for powder blending",
            "product_key": "RM-MALTODEX"
        },
        {
            "item_code": "ACTIVATED-CARBON",
            "item_name": "Activated Carbon",
            "item_group": "Raw Material",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "is_fixed_asset": 0,
            "valuation_rate": 8.50,
            "description": "Activated carbon for decolorization",
            "product_key": "RM-ACTCARBON"
        },
        {
            "item_code": "CITRIC-ACID",
            "item_name": "Citric Acid",
            "item_group": "Raw Material",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "is_fixed_asset": 0,
            "valuation_rate": 3.50,
            "description": "Citric acid for pH adjustment",
            "product_key": "RM-CITRIC"
        },
        {
            "item_code": "POTASSIUM-SORBATE",
            "item_name": "Potassium Sorbate",
            "item_group": "Raw Material",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "is_fixed_asset": 0,
            "valuation_rate": 5.00,
            "description": "Potassium sorbate preservative",
            "product_key": "RM-POTSORBATE"
        },
        {
            "item_code": "ALOE-LEAF-FRESH",
            "item_name": "Fresh Aloe Vera Leaf",
            "item_group": "Raw Material",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "is_fixed_asset": 0,
            "valuation_rate": 0.30,
            "description": "Fresh aloe vera leaf for extraction",
            "product_key": "RM-ALOELEAF"
        }
    ]
    
    created = []
    skipped = []
    failed = []
    
    for item_data in items_to_create:
        item_code = item_data["item_code"]
        
        if frappe.db.exists("Item", item_code):
            skipped.append(item_code)
            print(f"⊘ Skipped {item_code} (already exists)")
            continue
        
        try:
            item = frappe.get_doc({
                "doctype": "Item",
                **item_data
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
    
    return {
        "created": created,
        "skipped": skipped,
        "failed": failed
    }

if __name__ == "__main__":
    run()
