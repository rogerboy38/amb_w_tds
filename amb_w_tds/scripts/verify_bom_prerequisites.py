"""
Verify all prerequisites for BOM generation
Execute: bench --site [sitename] execute amb_w_tds.scripts.verify_bom_prerequisites.run
"""

import frappe

def run():
    """Verify system is ready for BOM generation"""
    print("\n" + "="*80)
    print("BOM GENERATION PREREQUISITES VERIFICATION")
    print("="*80 + "\n")
    
    checks = []
    
    # Check 1: Web product items exist
    print("Checking web product items...")
    web_codes = [
        '0307', '0323', '0401', '0417', '0433', '0449', '0465',
        '0501', '0517', '0533', '0549', '0565', '0581',
        '0601', '0602', '0603', '0604', '0605', '0606',
        '0607', '0608', '0609', '0610', '0611',
        '0701', '0702', '0703', '0704', '0705', '0706', '0707', '0708'
    ]
    
    missing_items = []
    for code in web_codes:
        if not frappe.db.exists("Item", code):
            missing_items.append(code)
    
    if missing_items:
        checks.append({
            "name": "Web Product Items",
            "status": "FAIL",
            "message": f"Missing items: {', '.join(missing_items)}"
        })
    else:
        checks.append({
            "name": "Web Product Items",
            "status": "PASS",
            "message": f"All {len(web_codes)} items exist"
        })
    
    # Check 2: Utility items exist
    print("Checking utility items...")
    utility_items = ['WATER-UTILITY', 'ELECTRICITY-UTILITY', 'GAS-UTILITY', 'LABOR-COST']
    missing_utilities = []
    
    for utility in utility_items:
        if not frappe.db.exists("Item", utility):
            missing_utilities.append(utility)
    
    if missing_utilities:
        checks.append({
            "name": "Utility Items",
            "status": "FAIL",
            "message": f"Missing utilities: {', '.join(missing_utilities)}"
        })
    else:
        checks.append({
            "name": "Utility Items",
            "status": "PASS",
            "message": "All utility items exist"
        })
    
    # Check 3: Base component items
    print("Checking base component items...")
    base_items = ['0307', '0302', '0705', 'MALTODEXTRIN', 'ACTIVATED-CARBON', 
                  'CITRIC-ACID', 'POTASSIUM-SORBATE', 'ALOE-LEAF-FRESH']
    missing_base = []
    
    for item in base_items:
        if not frappe.db.exists("Item", item):
            missing_base.append(item)
    
    if missing_base:
        checks.append({
            "name": "Base Component Items",
            "status": "WARN",
            "message": f"Missing components: {', '.join(missing_base)}"
        })
    else:
        checks.append({
            "name": "Base Component Items",
            "status": "PASS",
            "message": "All base components exist"
        })
    
    # Check 4: Check if Items table is accessible
    print("Checking database access...")
    try:
        item_count = frappe.db.count("Item")
        checks.append({
            "name": "Database Access",
            "status": "PASS",
            "message": f"Items table accessible ({item_count} items)"
        })
    except Exception as e:
        checks.append({
            "name": "Database Access",
            "status": "FAIL",
            "message": f"Database error: {str(e)}"
        })
    
    # Check 5: BOM DocType accessible
    print("Checking BOM DocType...")
    try:
        bom_meta = frappe.get_meta("BOM")
        checks.append({
            "name": "BOM DocType",
            "status": "PASS",
            "message": f"BOM DocType accessible ({len(bom_meta.fields)} fields)"
        })
    except Exception as e:
        checks.append({
            "name": "BOM DocType",
            "status": "FAIL",
            "message": f"BOM DocType error: {str(e)}"
        })
    
    # Print results
    print("\n" + "="*80)
    print("VERIFICATION RESULTS")
    print("="*80 + "\n")
    
    passed = sum(1 for c in checks if c['status'] == 'PASS')
    warned = sum(1 for c in checks if c['status'] == 'WARN')
    failed = sum(1 for c in checks if c['status'] == 'FAIL')
    
    for check in checks:
        status_symbol = {
            'PASS': '✓',
            'WARN': '⚠',
            'FAIL': '✗'
        }[check['status']]
        
        print(f"{status_symbol} {check['name']}: {check['message']}")
    
    print("\n" + "="*80)
    print(f"Summary: {passed} passed, {warned} warnings, {failed} failed")
    print("="*80 + "\n")
    
    if failed > 0:
        print("⚠ CRITICAL: Cannot proceed with BOM generation until failures are resolved.\n")
        return False
    elif warned > 0:
        print("⚠ WARNING: BOM generation may proceed with warnings, but review recommended.\n")
        return True
    else:
        print("✓ ALL CHECKS PASSED: System ready for BOM generation.\n")
        return True

if __name__ == "__main__":
    run()
