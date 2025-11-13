"""
Replace Basic BOMs with Detailed Templates
Cancels and deletes existing basic BOMs, regenerates with enhanced templates
"""

import frappe
from amb_w_tds.services.template_bom_service import TemplateBOMService

def cancel_and_delete_bom(item_code):
    """Cancel and delete existing BOM for item"""
    existing_bom = frappe.db.get_value("BOM", 
        {"item": item_code, "is_active": 1, "docstatus": 1}, 
        "name"
    )
    
    if existing_bom:
        try:
            # Load BOM
            bom_doc = frappe.get_doc("BOM", existing_bom)
            
            # Cancel if submitted
            if bom_doc.docstatus == 1:
                bom_doc.cancel()
                frappe.db.commit()
            
            # Delete
            frappe.delete_doc("BOM", existing_bom, force=1)
            frappe.db.commit()
            
            return {"success": True, "deleted": existing_bom}
        except Exception as e:
            frappe.log_error(message=str(e), title=f"BOM Deletion Failed: {item_code}")
            return {"success": False, "error": str(e)}
    
    return {"success": True, "deleted": None, "message": "No BOM found"}

def regenerate_bom(item_code):
    """Regenerate BOM with detailed template"""
    try:
        service = TemplateBOMService()
        new_bom = service.create_bom_from_product_code(item_code)
        frappe.db.commit()
        
        # Get cost info
        bom_doc = frappe.get_doc("BOM", new_bom)
        return {
            "success": True, 
            "bom": new_bom,
            "cost": bom_doc.total_cost,
            "components": len(bom_doc.items)
        }
    except Exception as e:
        frappe.log_error(message=str(e), title=f"BOM Regeneration Failed: {item_code}")
        return {"success": False, "error": str(e)}

def run(product_codes=None):
    """
    Replace basic BOMs with detailed templates
    
    Args:
        product_codes: List of product codes to replace. If None, replaces all 32.
    """
    service = TemplateBOMService()
    
    # Default to all web codes if none specified
    if product_codes is None:
        product_codes = service._get_web_product_codes()
    
    results = {
        "replaced": [],
        "failed": [],
        "skipped": []
    }
    
    print(f"{'='*80}")
    print(f"REPLACING BASIC BOMs WITH DETAILED TEMPLATES")
    print(f"{'='*80}")
    print(f"\nProduct codes to process: {len(product_codes)}")
    print(f"Codes: {', '.join(product_codes)}\n")
    
    for i, code in enumerate(product_codes, 1):
        print(f"\n[{i}/{len(product_codes)}] Processing {code}...")
        
        # Check if item exists
        if not frappe.db.exists("Item", code):
            results["skipped"].append({
                "code": code,
                "reason": "Item does not exist"
            })
            print(f"  ⚠️  Skipped - Item does not exist")
            continue
        
        # Step 1: Cancel and delete existing BOM
        delete_result = cancel_and_delete_bom(code)
        if not delete_result["success"]:
            results["failed"].append({
                "code": code,
                "stage": "deletion",
                "error": delete_result["error"]
            })
            print(f"  ✗ Failed to delete existing BOM: {delete_result['error']}")
            continue
        
        if delete_result["deleted"]:
            print(f"  ✓ Deleted existing BOM: {delete_result['deleted']}")
        else:
            print(f"  ℹ️  No existing BOM found")
        
        # Step 2: Regenerate BOM
        regen_result = regenerate_bom(code)
        if not regen_result["success"]:
            results["failed"].append({
                "code": code,
                "stage": "regeneration",
                "error": regen_result["error"]
            })
            print(f"  ✗ Failed to regenerate BOM: {regen_result['error']}")
            continue
        
        results["replaced"].append({
            "code": code,
            "old_bom": delete_result.get("deleted"),
            "new_bom": regen_result["bom"],
            "cost": regen_result["cost"],
            "components": regen_result["components"]
        })
        print(f"  ✅ Created: {regen_result['bom']} - "
              f"{regen_result['components']} components - ${regen_result['cost']:,.2f}")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"REPLACEMENT SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successfully replaced: {len(results['replaced'])}")
    print(f"✗ Failed: {len(results['failed'])}")
    print(f"⚠️  Skipped: {len(results['skipped'])}")
    
    if results["replaced"]:
        print(f"\n{'='*80}")
        print(f"REPLACED BOMs DETAIL")
        print(f"{'='*80}")
        print(f"{'Code':<8} {'Old BOM':<18} {'New BOM':<18} {'Comp':>5} {'Cost':>15}")
        print(f"{'-'*80}")
        for item in results["replaced"]:
            old = item['old_bom'] or 'N/A'
            print(f"{item['code']:<8} {old:<18} {item['new_bom']:<18} "
                  f"{item['components']:>5} ${item['cost']:>13,.2f}")
        
        # Cost statistics
        costs = [item['cost'] for item in results["replaced"]]
        print(f"\n{'='*80}")
        print(f"COST STATISTICS")
        print(f"{'='*80}")
        print(f"Total BOMs: {len(costs)}")
        print(f"Total Value: ${sum(costs):,.2f}")
        print(f"Average Cost: ${sum(costs)/len(costs):,.2f}")
        print(f"Min Cost: ${min(costs):,.2f}")
        print(f"Max Cost: ${max(costs):,.2f}")
    
    if results["failed"]:
        print(f"\n{'='*80}")
        print(f"FAILED")
        print(f"{'='*80}")
        for item in results["failed"]:
            print(f"  {item['code']} ({item['stage']}): {item['error']}")
    
    if results["skipped"]:
        print(f"\n{'='*80}")
        print(f"SKIPPED")
        print(f"{'='*80}")
        for item in results["skipped"]:
            print(f"  {item['code']}: {item['reason']}")
    
    return results

# Convenience functions
def run_single(product_code):
    """Replace BOM for single product code"""
    return run([product_code])

def run_family(family_prefix):
    """Replace BOMs for entire family (e.g., '04' for Acetypol)"""
    service = TemplateBOMService()
    all_codes = service._get_web_product_codes()
    family_codes = [c for c in all_codes if c.startswith(family_prefix)]
    print(f"Found {len(family_codes)} codes in family '{family_prefix}': {family_codes}")
    return run(family_codes)
