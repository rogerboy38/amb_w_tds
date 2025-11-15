"""
Regenerate all BOMs from templates with correct rates and quantities
Run: bench execute amb_w_tds.scripts.regenerate_all_boms.regenerate_all_web_product_boms
"""

import frappe
from amb_w_tds.services.template_bom_service import TemplateBOMService

# All web product codes
WEB_PRODUCTS = [
    # Spray Dried (200:1)
    '0307', '0323',
    
    # Acetypol (varies by grade)
    '0401', '0417', '0433', '0449', '0465',
    
    # Highpol (varies by grade)
    '0501', '0517', '0533', '0549', '0565', '0581',
    
    # QX Blends (varies by ratio)
    '0601', '0602', '0603', '0604', '0605', '0606',
    '0607', '0608', '0609', '0610', '0611',
    
    # Liquids (1:1 to 30:1)
    '0701', '0702', '0703', '0704', '0705', '0706', '0707', '0708'
]


def regenerate_all_web_product_boms(delete_old=True, skip_existing=False):
    """
    Regenerate all web product BOMs from templates
    
    Args:
        delete_old: Whether to delete old BOMs before creating new ones
        skip_existing: If True, skip items that already have active BOMs
    """
    
    print("=" * 80)
    print("🔧 Regenerating All Web Product BOMs")
    print("=" * 80)
    
    service = TemplateBOMService()
    
    successes = []
    failures = []
    skipped = []
    
    print(f"\n📦 Processing {len(WEB_PRODUCTS)} items...\n")
    
    for item_code in WEB_PRODUCTS:
        try:
            # Check if item exists
            if not frappe.db.exists("Item", item_code):
                print(f"⚠️  {item_code}: Item not found")
                skipped.append({"item": item_code, "reason": "Item not found"})
                continue
            
            # Check for existing active BOM
            if skip_existing:
                existing = frappe.db.exists("BOM", {
                    "item": item_code,
                    "is_active": 1,
                    "docstatus": 1
                })
                if existing:
                    print(f"⏭️  {item_code}: Already has active BOM")
                    skipped.append({"item": item_code, "reason": "Already exists"})
                    continue
            
            # Delete old BOMs
            if delete_old:
                old_boms = frappe.get_all("BOM", filters={"item": item_code}, pluck="name")
                for old_bom in old_boms:
                    try:
                        bom_doc = frappe.get_doc("BOM", old_bom)
                        if bom_doc.docstatus == 1:
                            bom_doc.cancel()
                        frappe.delete_doc("BOM", old_bom, force=1)
                    except:
                        pass
            
            # Create new BOM
            print(f"🔨 {item_code}...", end=" ")
            new_bom_name = service.create_bom_from_product_code(item_code)
            frappe.db.commit()
            
            # Verify
            new_bom = frappe.get_doc("BOM", new_bom_name)
            cost_per_kg = new_bom.total_cost / new_bom.quantity
            ops_count = len(new_bom.operations)
            
            successes.append({
                'item': item_code,
                'bom': new_bom_name,
                'cost': cost_per_kg,
                'ops': ops_count
            })
            
            print(f"✅ {new_bom_name} (${cost_per_kg:,.2f}/kg, {ops_count} ops)")
            
        except Exception as e:
            error = str(e)[:80]
            failures.append({'item': item_code, 'error': error})
            print(f"❌ {error}")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    print(f"\n✅ Success: {len(successes)}/{len(WEB_PRODUCTS)}")
    print(f"⏭️  Skipped: {len(skipped)}/{len(WEB_PRODUCTS)}")
    print(f"❌ Failed: {len(failures)}/{len(WEB_PRODUCTS)}")
    
    if failures:
        print(f"\n❌ Failed items:")
        for f in failures:
            print(f"   {f['item']}: {f['error']}")
    
    # Final count
    total_active = frappe.db.count("BOM", {
        "item": ["like", "0%"],
        "is_active": 1,
        "docstatus": 1
    })
    
    print(f"\n📦 Total Active BOMs: {total_active}/32")
    print("=" * 80)
    
    return {
        "successes": successes,
        "failures": failures,
        "skipped": skipped,
        "total_active": total_active
    }


def regenerate_single_bom(item_code, delete_old=True):
    """Regenerate BOM for a single item"""
    
    print(f"🔧 Regenerating BOM for {item_code}...")
    
    if not frappe.db.exists("Item", item_code):
        print(f"❌ Item {item_code} not found")
        return None
    
    service = TemplateBOMService()
    
    try:
        # Delete old
        if delete_old:
            old_boms = frappe.get_all("BOM", filters={"item": item_code}, pluck="name")
            for old_bom in old_boms:
                try:
                    bom_doc = frappe.get_doc("BOM", old_bom)
                    if bom_doc.docstatus == 1:
                        bom_doc.cancel()
                    frappe.delete_doc("BOM", old_bom, force=1)
                    print(f"   🗑️  Deleted {old_bom}")
                except Exception as e:
                    print(f"   ⚠️  {old_bom}: {str(e)}")
        
        # Create new
        new_bom_name = service.create_bom_from_product_code(item_code)
        frappe.db.commit()
        
        # Verify
        new_bom = frappe.get_doc("BOM", new_bom_name)
        cost_per_kg = new_bom.total_cost / new_bom.quantity
        
        print(f"✅ Created {new_bom_name}")
        print(f"   Cost: ${cost_per_kg:,.2f}/kg")
        print(f"   Operations: {len(new_bom.operations)}")
        
        return new_bom_name
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return None


def regenerate_by_family(family_code):
    """Regenerate BOMs for a product family (03, 04, 05, 06, 07)"""
    
    family_items = [p for p in WEB_PRODUCTS if p.startswith(family_code)]
    
    if not family_items:
        print(f"❌ No items found for family {family_code}")
        return
    
    family_names = {
        '03': 'Spray Dried',
        '04': 'Acetypol',
        '05': 'Highpol',
        '06': 'QX Blends',
        '07': 'Liquids'
    }
    
    print(f"🔧 Regenerating {family_names.get(family_code, family_code)} BOMs...")
    print(f"   Items: {', '.join(family_items)}\n")
    
    results = []
    
    for item_code in family_items:
        bom_name = regenerate_single_bom(item_code)
        results.append({"item": item_code, "bom": bom_name, "success": bool(bom_name)})
        print()
    
    success_count = sum(1 for r in results if r['success'])
    print(f"📊 {success_count}/{len(family_items)} BOMs created successfully")
    
    return results


if __name__ == "__main__":
    regenerate_all_web_product_boms()
