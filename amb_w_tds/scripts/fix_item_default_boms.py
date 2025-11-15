"""
Fix Item Master default_bom references to point to active BOMs
Run: bench execute amb_w_tds.scripts.fix_item_default_boms.fix_all_item_default_boms
"""

import frappe

def fix_all_item_default_boms():
    """Update all items to use active default BOMs instead of cancelled ones"""
    
    print("=" * 80)
    print("🔧 Fixing Item Master Default BOM References")
    print("=" * 80)
    
    # Find items with cancelled BOM references
    items_with_cancelled_boms = frappe.db.sql("""
        SELECT 
            i.item_code,
            i.default_bom as old_bom,
            b.docstatus,
            b.is_active
        FROM `tabItem` i
        LEFT JOIN `tabBOM` b ON b.name = i.default_bom
        WHERE i.item_code LIKE '0%'
            AND i.default_bom IS NOT NULL
            AND (b.docstatus != 1 OR b.is_active = 0)
    """, as_dict=True)
    
    print(f"\n📦 Found {len(items_with_cancelled_boms)} items with invalid BOM references\n")
    
    updated = 0
    cleared = 0
    
    for item in items_with_cancelled_boms:
        # Find active default BOM
        active_bom = frappe.db.get_value("BOM", {
            "item": item.item_code,
            "is_active": 1,
            "is_default": 1,
            "docstatus": 1
        }, "name")
        
        if active_bom:
            frappe.db.set_value("Item", item.item_code, "default_bom", active_bom)
            print(f"✅ {item.item_code}: {item.old_bom} → {active_bom}")
            updated += 1
        else:
            frappe.db.set_value("Item", item.item_code, "default_bom", None)
            print(f"⚠️  {item.item_code}: Cleared (no active BOM found)")
            cleared += 1
    
    frappe.db.commit()
    
    print(f"\n📊 Summary:")
    print(f"   Updated: {updated}")
    print(f"   Cleared: {cleared}")
    print(f"\n✅ Complete!")
    print("=" * 80)
    
    return {"updated": updated, "cleared": cleared}


def fix_single_item(item_code):
    """Fix default_bom for a single item"""
    
    if not frappe.db.exists("Item", item_code):
        print(f"❌ Item {item_code} not found")
        return
    
    item = frappe.get_doc("Item", item_code)
    old_bom = item.default_bom
    
    # Find active default BOM
    active_bom = frappe.db.get_value("BOM", {
        "item": item_code,
        "is_active": 1,
        "is_default": 1,
        "docstatus": 1
    }, "name")
    
    if active_bom:
        item.default_bom = active_bom
        item.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ {item_code}: {old_bom} → {active_bom}")
    else:
        print(f"⚠️  No active default BOM found for {item_code}")


if __name__ == "__main__":
    fix_all_item_default_boms()
