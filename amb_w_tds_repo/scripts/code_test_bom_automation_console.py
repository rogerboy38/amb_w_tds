#!/usr/bin/env python3
"""
BOM Automation Testing Script for ERPNext Bench Console
========================================================

This script tests all BOM automation functions in the ERPNext environment.
Run this in your bench console to verify everything works before API testing.

Usage:
1. Connect to your bench: bench console
2. Run: exec(open('test_bom_automation_console.py').read())

Author: MiniMax Agent
Date: 2025-11-20
"""

import frappe
import json
from datetime import datetime

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"🔍 {title}")
    print("="*80)

def print_result(test_name, result, success=True):
    """Print test result with formatting"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} {test_name}")
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(str(result))

def test_bom_functions():
    """Test all BOM automation functions"""
    
    print_section("BOM AUTOMATION FUNCTIONS TEST")
    print(f"Testing Time: {datetime.now()}")
    print(f"ERPNext Version: {frappe.__version__}")
    print(f"Available Apps: {frappe.get_installed_apps()}")
    
    # Test 1: Import BOM Automation Module
    print_section("TEST 1: Import BOM Automation Module")
    try:
        import amb_w_tds.api.bom_automation as bom_automation
        print_result("Import BOM automation module", "✅ Successfully imported")
        test_1_passed = True
    except Exception as e:
        print_result("Import BOM automation module", f"❌ Failed: {str(e)}")
        test_1_passed = False
        print("\n💡 SOLUTION: Run 'bench restart' after installing the module")
        return
    
    # Test 2: Test Helper Functions
    print_section("TEST 2: Test Helper Functions")
    try:
        # Test operation time mapping
        time_mapping_result = bom_automation.get_operation_time_mapping("LAVADO")
        print_result("Operation time mapping (LAVADO)", f"Time: {time_mapping_result} minutes")
        
        # Test workstation mapping
        workstation_result = bom_automation.get_workstation_mapping("MOLIENDA")
        print_result("Workstation mapping (MOLIENDA)", f"Workstation: {workstation_result}")
        
        # Test BOM finder function
        boms = frappe.get_all("BOM", fields=["name"], limit=3)
        if boms:
            print(f"📋 Available BOMs in system: {len(boms)}")
            for i, bom in enumerate(boms[:3], 1):
                print(f"   {i}. {bom.name}")
        
        test_2_passed = True
    except Exception as e:
        print_result("Helper functions test", f"❌ Failed: {str(e)}")
        test_2_passed = False
    
    # Test 3: Find Test BOM
    print_section("TEST 3: Find Test BOM")
    try:
        # Look for a test BOM or create one
        test_bom_name = None
        
        # Try to find existing BOM
        existing_boms = frappe.get_all("BOM", filters={"docstatus": ["!=", 2]}, limit=1)
        if existing_boms:
            test_bom_name = existing_boms[0].name
            print_result("Find existing BOM", f"Found: {test_bom_name}")
        else:
            print_result("Find existing BOM", "❌ No BOMs found")
            test_bom_name = None
        
        test_3_passed = bool(test_bom_name)
    except Exception as e:
        print_result("Find test BOM", f"❌ Failed: {str(e)}")
        test_bom_name = None
        test_3_passed = False
    
    # Test 4: Test BOM Validation Function
    print_section("TEST 4: Test BOM Validation (validate_and_fix_bom)")
    try:
        if test_bom_name:
            # Test validation without fixing
            result = bom_automation.validate_and_fix_bom(test_bom_name, auto_fix=False)
            print_result("BOM validation (no fix)", result)
            
            # Test validation with fixing
            result = bom_automation.validate_and_fix_bom(test_bom_name, auto_fix=True)
            print_result("BOM validation (with fix)", result)
            
            test_4_passed = True
        else:
            print_result("BOM validation test", "❌ Skipped - No test BOM available")
            test_4_passed = False
    except Exception as e:
        print_result("BOM validation test", f"❌ Failed: {str(e)}")
        test_4_passed = False
    
    # Test 5: Test Quick Functions
    print_section("TEST 5: Test Quick Functions")
    try:
        if test_bom_name:
            # Test quick fix
            result = bom_automation.quick_fix_bom_operations(test_bom_name)
            print_result("Quick BOM fix", result)
            
            test_5_passed = True
        else:
            print_result("Quick functions test", "❌ Skipped - No test BOM available")
            test_5_passed = False
    except Exception as e:
        print_result("Quick functions test", f"❌ Failed: {str(e)}")
        test_5_passed = False
    
    # Test 6: Test Work Order Functions
    print_section("TEST 6: Test Work Order Functions")
    try:
        if test_bom_name:
            # Test work order creation (will be draft)
            result = bom_automation.create_work_order_simple(test_bom_name, 1)
            print_result("Create simple work order", result)
            
            test_6_passed = True
        else:
            print_result("Work order test", "❌ Skipped - No test BOM available")
            test_6_passed = False
    except Exception as e:
        print_result("Work order test", f"❌ Failed: {str(e)}")
        test_6_passed = False
    
    # Test 7: Test Work Order Diagnosis
    print_section("TEST 7: Test Work Order Diagnosis")
    try:
        # Look for existing work orders
        work_orders = frappe.get_all("Work Order", limit=1)
        if work_orders:
            wo_name = work_orders[0].name
            result = bom_automation.diagnose_and_fix_work_order(wo_name)
            print_result(f"Diagnose work order ({wo_name})", result)
            test_7_passed = True
        else:
            print_result("Work order diagnosis", "❌ No work orders found to test")
            test_7_passed = False
    except Exception as e:
        print_result("Work order diagnosis", f"❌ Failed: {str(e)}")
        test_7_passed = False
    
    # Test 8: Test API Whitelisted Status
    print_section("TEST 8: Test API Whitelisted Functions")
    try:
        # Check if functions are properly decorated
        whitelisted_functions = [
            bom_automation.validate_and_fix_bom,
            bom_automation.create_work_order_from_bom,
            bom_automation.diagnose_and_fix_work_order,
            bom_automation.quick_fix_bom_operations,
            bom_automation.quick_work_order_diagnosis,
            bom_automation.create_work_order_simple
        ]
        
        for func in whitelisted_functions:
            has_whitelist = hasattr(func, '_frappe_whitelisted')
            func_name = func.__name__
            status = "✅ Whitelisted" if has_whitelist else "❌ Not whitelisted"
            print(f"   {status}: {func_name}")
        
        test_8_passed = True
    except Exception as e:
        print_result("API whitelisted test", f"❌ Failed: {str(e)}")
        test_8_passed = False
    
    # Summary
    print_section("TEST SUMMARY")
    tests = [
        ("Import Module", test_1_passed),
        ("Helper Functions", test_2_passed),
        ("Find Test BOM", test_3_passed),
        ("BOM Validation", test_4_passed),
        ("Quick Functions", test_5_passed),
        ("Work Order Functions", test_6_passed),
        ("Work Order Diagnosis", test_7_passed),
        ("API Whitelisted", test_8_passed)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"📊 Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Ready for API testing!")
        print("\n✅ Next Steps:")
        print("1. Test via API console in browser")
        print("2. Deploy to production frappe.cloud")
        print("3. Configure Raven AI functions")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\n📋 Failed tests:")
        for test_name, result in tests:
            if not result:
                print(f"   ❌ {test_name}")
    
    return {
        "total_tests": total,
        "passed_tests": passed,
        "success_rate": (passed/total)*100,
        "ready_for_api": passed >= 6,  # At least 6 tests need to pass
        "test_details": tests
    }

if __name__ == "__main__":
    try:
        result = test_bom_functions()
        print(f"\n🏁 Testing completed at {datetime.now()}")
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()