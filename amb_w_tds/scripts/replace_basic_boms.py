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

def handle_cancelled_linked_bom(item_code):
    """
    Handle a cancelled BOM that's linked to other BOMs
    
    Strategy:
    1. Find all BOMs that use this item as a component (children)
    2. Cancel and delete children first
    3. Delete this BOM
    4. Recreate this BOM
    5. Recreate children BOMs
    
    Returns:
        dict: Results with success status and details
    """
    import frappe
    
    print(f"\n🔍 Analyzing dependencies for {item_code}...")
    
    # Find the cancelled BOM
    cancelled_bom = frappe.db.get_value("BOM",
        {"item": item_code, "docstatus": 2},
        ["name"],
        as_dict=True
    )
    
    if not cancelled_bom:
        return {"success": False, "error": f"No cancelled BOM found for {item_code}"}
    
    print(f"  Found cancelled BOM: {cancelled_bom.name}")
    
    # Find all BOMs that use this item as a component (children)
    child_boms = frappe.db.sql("""
        SELECT DISTINCT b.name, b.item
        FROM `tabBOM` b
        JOIN `tabBOM Item` bi ON bi.parent = b.name
        WHERE bi.item_code = %s
        AND b.docstatus = 1
        AND b.is_active = 1
    """, (item_code,), as_dict=True)
    
    print(f"  Found {len(child_boms)} BOMs using {item_code}:")
    for cb in child_boms:
        print(f"    - {cb.name} (Item: {cb.item})")
    
    # Step 1: Cancel and delete child BOMs
    cancelled_children = []
    for cb in child_boms:
        print(f"\n  📦 Handling child BOM: {cb.name}")
        try:
            child_doc = frappe.get_doc("BOM", cb.name)
            
            # Cancel if submitted
            if child_doc.docstatus == 1:
                child_doc.cancel()
                frappe.db.commit()
                print(f"    ✓ Cancelled {cb.name}")
            
            # Delete
            frappe.delete_doc("BOM", cb.name, force=1)
            frappe.db.commit()
            print(f"    ✓ Deleted {cb.name}")
            
            cancelled_children.append(cb.item)
            
        except Exception as e:
            print(f"    ✗ Failed to handle {cb.name}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to delete child BOM {cb.name}: {str(e)}"
            }
    
    # Step 2: Now delete the parent BOM (0307)
    print(f"\n  🗑️  Deleting parent BOM: {cancelled_bom.name}")
    try:
        frappe.delete_doc("BOM", cancelled_bom.name, force=1)
        frappe.db.commit()
        print(f"    ✓ Deleted {cancelled_bom.name}")
    except Exception as e:
        print(f"    ✗ Failed to delete {cancelled_bom.name}: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to delete parent BOM: {str(e)}"
        }
    
    # Step 3: Recreate parent BOM (0307)
    print(f"\n  🔨 Recreating parent BOM for {item_code}")
    parent_result = regenerate_bom(item_code)
    
    if not parent_result['success']:
        return {
            "success": False,
            "error": f"Failed to recreate parent BOM: {parent_result.get('error')}"
        }
    
    print(f"    ✓ Created {parent_result['bom']} (${parent_result['cost']:,.2f})")
    
    # Step 4: Recreate child BOMs
    print(f"\n  🔨 Recreating child BOMs...")
    recreated_children = []
    failed_children = []
    
    for child_item in cancelled_children:
        print(f"    Recreating BOM for {child_item}...")
        child_result = regenerate_bom(child_item)
        
        if child_result['success']:
            print(f"      ✓ Created {child_result['bom']} (${child_result['cost']:,.2f})")
            recreated_children.append(child_item)
        else:
            print(f"      ✗ Failed: {child_result.get('error')}")
            failed_children.append({
                'item': child_item,
                'error': child_result.get('error')
            })
    
    return {
        "success": True,
        "parent": {
            "item": item_code,
            "bom": parent_result['bom'],
            "cost": parent_result['cost']
        },
        "children": {
            "total": len(cancelled_children),
            "recreated": len(recreated_children),
            "failed": len(failed_children),
            "failed_details": failed_children
        }
    }


def run_in_dependency_order():
    """
    Regenerate BOMs in dependency order with proper dependency handling
    
    Handles:
    - Cancelled BOMs (creates new versions)
    - Inactive BOMs (reactivates)
    - Linked dependencies (breaks and rebuilds)
    
    Returns:
        dict: Results summary with successful, failed, skipped counts
    """
    import frappe
    from amb_w_tds.services.template_bom_service import TemplateBOMService
    
    service = TemplateBOMService()
    web_codes = service._get_web_product_codes()
    
    # Define dependency groups
    phase_1_independent = [
        '0323',  # Spray dried (uses 0705)
        '0501', '0517', '0533', '0549', '0565', '0581',  # Highpol (uses 0302)
        '0701', '0702', '0703', '0704', '0706', '0707', '0708'  # Liquids (use raw materials)
    ]
    
    phase_2_dependent = [
        '0401', '0417', '0433', '0449', '0465',  # Acetypol (uses 0307)
        '0601', '0602', '0603', '0604', '0605', '0606', '0607', '0608', '0609', '0610', '0611'  # QX (uses 0307)
    ]
    
    results = {
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    print("\n" + "=" * 80)
    print("PHASE 0: FIXING BASE INTERMEDIATES (0705, 0307)")
    print("=" * 80)
    
    # ============================================================================
    # STEP 1: Fix BOM-0705 (base juice - needed by 0323 and 0307)
    # ============================================================================
    print("\n📦 Checking BOM-0705...")
    
    bom_0705 = frappe.db.get_value("BOM",
        {"item": "0705"},
        ["name", "docstatus", "is_active", "is_default"],
        as_dict=True
    )
    
    if bom_0705:
        print(f"  Found: {bom_0705.name}")
        print(f"  Status: docstatus={bom_0705.docstatus}, is_active={bom_0705.is_active}")
        
        # If cancelled (docstatus=2), we MUST create a new BOM
        if bom_0705.docstatus == 2:
            print(f"  ⚠️  BOM is CANCELLED - creating new version...")
            
            # Check if it has children that depend on it
            children_0705 = frappe.db.sql("""
                SELECT DISTINCT b.name, b.item
                FROM `tabBOM` b
                JOIN `tabBOM Item` bi ON bi.parent = b.name
                WHERE bi.item_code = '0705'
                AND b.docstatus IN (0, 1)
            """, as_dict=True)
            
            if children_0705:
                print(f"  Found {len(children_0705)} BOMs depending on 0705:")
                for child in children_0705:
                    print(f"    - {child.name} (Item: {child.item})")
                
                # Cancel and delete children first
                for child in children_0705:
                    try:
                        child_doc = frappe.get_doc("BOM", child.name)
                        if child_doc.docstatus == 1:
                            child_doc.cancel()
                            frappe.db.commit()
                        frappe.delete_doc("BOM", child.name, force=1)
                        frappe.db.commit()
                        print(f"    ✓ Deleted {child.name}")
                    except Exception as e:
                        print(f"    ✗ Failed to delete {child.name}: {str(e)}")
            
            # Now delete the cancelled BOM-0705
            try:
                frappe.delete_doc("BOM", bom_0705.name, force=1)
                frappe.db.commit()
                print(f"  ✓ Deleted cancelled {bom_0705.name}")
            except Exception as e:
                print(f"  ✗ Failed to delete {bom_0705.name}: {str(e)}")
                results['failed'] += 1
                return results
            
            # Create new BOM-0705
            print(f"  🔨 Creating new BOM for 0705...")
            result_0705 = regenerate_bom("0705")
            
            if result_0705['success']:
                print(f"  ✅ Created {result_0705['bom']} (${result_0705['cost']:,.2f})")
                results['successful'] += 1
            else:
                print(f"  ✗ Failed to create 0705: {result_0705.get('error')}")
                results['failed'] += 1
                return results
        
        # If inactive but submitted, just reactivate
        elif bom_0705.docstatus == 1 and not bom_0705.is_active:
            print(f"  ⚠️  BOM is INACTIVE - reactivating...")
            try:
                bom_doc = frappe.get_doc("BOM", bom_0705.name)
                bom_doc.is_active = 1
                bom_doc.is_default = 1
                bom_doc.save()
                frappe.db.commit()
                print(f"  ✅ Reactivated {bom_0705.name}")
                results['successful'] += 1
            except Exception as e:
                print(f"  ✗ Failed to reactivate: {str(e)}")
                results['failed'] += 1
                return results
        
        # If draft, submit it
        elif bom_0705.docstatus == 0:
            print(f"  ⚠️  BOM is DRAFT - submitting...")
            try:
                bom_doc = frappe.get_doc("BOM", bom_0705.name)
                bom_doc.is_active = 1
                bom_doc.is_default = 1
                bom_doc.submit()
                frappe.db.commit()
                print(f"  ✅ Submitted {bom_0705.name}")
                results['successful'] += 1
            except Exception as e:
                print(f"  ✗ Failed to submit: {str(e)}")
                results['failed'] += 1
                return results
        
        else:
            print(f"  ✅ BOM-0705 is already active and submitted")
    
    else:
        print(f"  ⚠️  No BOM found for 0705 - creating...")
        result_0705 = regenerate_bom("0705")
        
        if result_0705['success']:
            print(f"  ✅ Created {result_0705['bom']} (${result_0705['cost']:,.2f})")
            results['successful'] += 1
        else:
            print(f"  ✗ Failed to create 0705: {result_0705.get('error')}")
            results['failed'] += 1
            return results
    
    # ============================================================================
    # STEP 2: Fix BOM-0307 (spray dried powder - needed by 04XX and 06XX)
    # ============================================================================
    print("\n📦 Checking BOM-0307...")
    
    bom_0307 = frappe.db.get_value("BOM",
        {"item": "0307"},
        ["name", "docstatus", "is_active", "is_default"],
        as_dict=True
    )
    
    if bom_0307:
        print(f"  Found: {bom_0307.name}")
        print(f"  Status: docstatus={bom_0307.docstatus}, is_active={bom_0307.is_active}")
        
        # If cancelled, handle dependencies
        if bom_0307.docstatus == 2:
            print(f"  ⚠️  BOM is CANCELLED - handling dependencies...")
            
            # Find all BOMs that use 0307
            children_0307 = frappe.db.sql("""
                SELECT DISTINCT b.name, b.item
                FROM `tabBOM` b
                JOIN `tabBOM Item` bi ON bi.parent = b.name
                WHERE bi.item_code = '0307'
                AND b.docstatus IN (0, 1)
            """, as_dict=True)
            
            print(f"  Found {len(children_0307)} BOMs depending on 0307:")
            for child in children_0307:
                print(f"    - {child.name} (Item: {child.item})")
            
            # Cancel and delete children first
            cancelled_items = []
            for child in children_0307:
                try:
                    child_doc = frappe.get_doc("BOM", child.name)
                    if child_doc.docstatus == 1:
                        child_doc.cancel()
                        frappe.db.commit()
                    frappe.delete_doc("BOM", child.name, force=1)
                    frappe.db.commit()
                    print(f"    ✓ Deleted {child.name}")
                    cancelled_items.append(child.item)
                except Exception as e:
                    print(f"    ✗ Failed to delete {child.name}: {str(e)}")
            
            # Delete cancelled BOM-0307
            try:
                frappe.delete_doc("BOM", bom_0307.name, force=1)
                frappe.db.commit()
                print(f"  ✓ Deleted cancelled {bom_0307.name}")
            except Exception as e:
                print(f"  ✗ Failed to delete {bom_0307.name}: {str(e)}")
                results['failed'] += 1
                return results
            
            # Create new BOM-0307
            print(f"  🔨 Creating new BOM for 0307...")
            result_0307 = regenerate_bom("0307")
            
            if result_0307['success']:
                print(f"  ✅ Created {result_0307['bom']} (${result_0307['cost']:,.2f})")
                results['successful'] += 1
            else:
                print(f"  ✗ Failed to create 0307: {result_0307.get('error')}")
                results['failed'] += 1
                return results
            
            # Recreate children
            print(f"\n  🔨 Recreating {len(cancelled_items)} child BOMs...")
            for item_code in cancelled_items:
                print(f"    Recreating BOM for {item_code}...")
                result_child = regenerate_bom(item_code)
                
                if result_child['success']:
                    print(f"      ✓ Created {result_child['bom']} (${result_child['cost']:,.2f})")
                    results['successful'] += 1
                else:
                    print(f"      ✗ Failed: {result_child.get('error')}")
                    results['failed'] += 1
        
        # If inactive but submitted, just reactivate
        elif bom_0307.docstatus == 1 and not bom_0307.is_active:
            print(f"  ⚠️  BOM is INACTIVE - reactivating...")
            try:
                bom_doc = frappe.get_doc("BOM", bom_0307.name)
                bom_doc.is_active = 1
                bom_doc.is_default = 1
                bom_doc.save()
                frappe.db.commit()
                print(f"  ✅ Reactivated {bom_0307.name}")
                results['successful'] += 1
            except Exception as e:
                print(f"  ✗ Failed to reactivate: {str(e)}")
                results['failed'] += 1
                return results
        
        # If draft, submit it
        elif bom_0307.docstatus == 0:
            print(f"  ⚠️  BOM is DRAFT - submitting...")
            try:
                bom_doc = frappe.get_doc("BOM", bom_0307.name)
                bom_doc.is_active = 1
                bom_doc.is_default = 1
                bom_doc.submit()
                frappe.db.commit()
                print(f"  ✅ Submitted {bom_0307.name}")
                results['successful'] += 1
            except Exception as e:
                print(f"  ✗ Failed to submit: {str(e)}")
                results['failed'] += 1
                return results
        
        else:
            print(f"  ✅ BOM-0307 is already active and submitted")
    
    else:
        print(f"  ⚠️  No BOM found for 0307 - creating...")
        result_0307 = regenerate_bom("0307")
        
        if result_0307['success']:
            print(f"  ✅ Created {result_0307['bom']} (${result_0307['cost']:,.2f})")
            results['successful'] += 1
        else:
            print(f"  ✗ Failed to create 0307: {result_0307.get('error')}")
            results['failed'] += 1
            return results
    
    # ============================================================================
    # PHASE 1: Independent products (don't use 0307)
    # ============================================================================
    print("\n" + "=" * 80)
    print("PHASE 1: REGENERATING INDEPENDENT PRODUCTS")
    print("=" * 80)
    
    for code in phase_1_independent:
        if code not in web_codes:
            continue
        
        print(f"\n📦 Processing: {code}")
        
        # Delete existing BOM if exists
        delete_result = cancel_and_delete_bom(code)
        if delete_result.get('deleted'):
            print(f"  ✓ Deleted old BOM: {delete_result['deleted']}")
        
        # Regenerate
        result = regenerate_bom(code)
        
        if result['success']:
            results['successful'] += 1
            print(f"  ✅ {code}: {result['bom']} (${result['cost']:,.2f}, {result['components']} components)")
        else:
            results['failed'] += 1
            print(f"  ✗ {code}: {result.get('error', 'Unknown error')}")
        
        results['details'].append(result)
    
    # ============================================================================
    # PHASE 2: Dependent products (use 0307)
    # ============================================================================
    print("\n" + "=" * 80)
    print("PHASE 2: REGENERATING DEPENDENT PRODUCTS")
    print("=" * 80)
    
    for code in phase_2_dependent:
        if code not in web_codes:
            continue
        
        print(f"\n📦 Processing: {code}")
        
        # Delete existing BOM if exists
        delete_result = cancel_and_delete_bom(code)
        if delete_result.get('deleted'):
            print(f"  ✓ Deleted old BOM: {delete_result['deleted']}")
        
        # Regenerate
        result = regenerate_bom(code)
        
        if result['success']:
            results['successful'] += 1
            print(f"  ✅ {code}: {result['bom']} (${result['cost']:,.2f}, {result['components']} components)")
        else:
            results['failed'] += 1
            print(f"  ✗ {code}: {result.get('error', 'Unknown error')}")
        
        results['details'].append(result)
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("REGENERATION SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {results['successful']}")
    print(f"✗ Failed: {results['failed']}")
    print(f"⊘ Skipped: {results['skipped']}")
    print(f"Total processed: {results['successful'] + results['failed']}")
    
    if results['failed'] > 0:
        print("\n" + "=" * 80)
        print("FAILED ITEMS:")
        print("=" * 80)
        for detail in results['details']:
            if not detail.get('success'):
                print(f"  ✗ {detail.get('error', 'Unknown error')}")
    
    return results

def force_activate_bom(bom_name):
    """
    Force activate a BOM regardless of its current state
    
    Args:
        bom_name (str): BOM name to activate
        
    Returns:
        dict: Result with success status and new BOM name
    """
    import frappe
    
    try:
        bom = frappe.get_doc("BOM", bom_name)
        
        print(f"\n🔍 Checking {bom_name}...")
        print(f"  Current: docstatus={bom.docstatus}, is_active={bom.is_active}")
        
        # Case 1: Cancelled (docstatus = 2)
        if bom.docstatus == 2:
            print(f"  ⚠️  BOM is cancelled - creating amended version")
            
            # Create amended version
            amended_bom = frappe.copy_doc(bom)
            amended_bom.docstatus = 0
            amended_bom.is_active = 1
            amended_bom.is_default = 1
            amended_bom.amended_from = bom.name
            
            # Clear the name to allow auto-naming
            amended_bom.name = None
            
            amended_bom.insert()
            amended_bom.submit()
            frappe.db.commit()
            
            print(f"  ✓ Created and submitted: {amended_bom.name}")
            
            return {
                'success': True,
                'bom_name': amended_bom.name,
                'action': 'amended'
            }
        
        # Case 2: Draft or Submitted but inactive
        elif not bom.is_active:
            print(f"  ℹ️  BOM is inactive - activating")
            
            bom.is_active = 1
            bom.is_default = 1
            
            # If draft, submit it
            if bom.docstatus == 0:
                bom.submit()
            else:
                bom.save()
            
            frappe.db.commit()
            
            print(f"  ✓ Activated: {bom.name}")
            
            return {
                'success': True,
                'bom_name': bom.name,
                'action': 'activated'
            }
        
        # Case 3: Already active
        else:
            print(f"  ✓ Already active")
            return {
                'success': True,
                'bom_name': bom.name,
                'action': 'already_active'
            }
            
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
