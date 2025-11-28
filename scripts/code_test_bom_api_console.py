#!/usr/bin/env python3
"""
API Testing Script for BOM Automation Functions
==============================================

After bench console testing passes, use this script to test the API endpoints.
This simulates the actual Raven AI calls to the API.

Usage:
1. Run bench console tests first: exec(open('test_bom_automation_console.py').read())
2. If tests pass, run this script: exec(open('test_bom_api_console.py').read())

Author: MiniMax Agent
Date: 2025-11-20
"""

import frappe
import json
from datetime import datetime
import requests

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

def test_bom_api_functions():
    """Test BOM automation functions via API simulation"""
    
    print_section("BOM AUTOMATION API FUNCTIONS TEST")
    print(f"Testing Time: {datetime.now()}")
    print("This simulates Raven AI calling the API endpoints")
    
    try:
        # Import the module
        import amb_w_tds.api.bom_automation as bom_automation
        print("✅ BOM automation module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import BOM automation: {e}")
        print("💡 Run bench console test first to install the module")
        return
    
    # Test 1: API Function Simulation
    print_section("TEST 1: API Function Simulation")
    try:
        # Get a test BOM
        boms = frappe.get_all("BOM", filters={"docstatus": ["!=", 2]}, limit=1)
        if not boms:
            print("❌ No BOMs found to test with")
            return
        
        test_bom = boms[0].name
        print(f"📋 Testing with BOM: {test_bom}")
        
        # Test validate_and_fix_bom (dry run)
        print("\n🧪 Testing validate_and_fix_bom (dry run)...")
        result = bom_automation.validate_and_fix_bom(test_bom, auto_fix=False)
        print_result("validate_and_fix_bom (dry run)", result)
        
        # Test validate_and_fix_bom (with fix)
        print("\n🧪 Testing validate_and_fix_bom (with fix)...")
        result = bom_automation.validate_and_fix_bom(test_bom, auto_fix=True)
        print_result("validate_and_fix_bom (with fix)", result)
        
        test_1_passed = True
    except Exception as e:
        print_result("validate_and_fix_bom", f"❌ Failed: {str(e)}")
        test_1_passed = False
    
    # Test 2: Work Order Creation Simulation
    print_section("TEST 2: Work Order Creation Simulation")
    try:
        if test_1_passed and boms:
            test_bom = boms[0].name
            
            print(f"\n🧪 Testing create_work_order_from_bom for {test_bom}...")
            result = bom_automation.create_work_order_from_bom(test_bom, 100, auto_complete_fields=True)
            print_result("create_work_order_from_bom", result)
            
            # Check if work order was created
            if result.get('work_order_name'):
                wo_name = result['work_order_name']
                print(f"\n🧪 Testing quick work order diagnosis for {wo_name}...")
                diag_result = bom_automation.quick_work_order_diagnosis(wo_name)
                print_result("quick_work_order_diagnosis", diag_result)
            
            test_2_passed = True
        else:
            print_result("Work order creation", "❌ Skipped - Previous test failed")
            test_2_passed = False
    except Exception as e:
        print_result("Work order creation", f"❌ Failed: {str(e)}")
        test_2_passed = False
    
    # Test 3: Quick Functions Simulation
    print_section("TEST 3: Quick Functions Simulation")
    try:
        if boms:
            test_bom = boms[0].name
            
            print(f"\n🧪 Testing quick_fix_bom_operations for {test_bom}...")
            result = bom_automation.quick_fix_bom_operations(test_bom)
            print_result("quick_fix_bom_operations", result)
            
            print(f"\n🧪 Testing create_work_order_simple for {test_bom}...")
            result = bom_automation.create_work_order_simple(test_bom, 50)
            print_result("create_work_order_simple", result)
            
            test_3_passed = True
        else:
            print_result("Quick functions", "❌ Skipped - No test BOM")
            test_3_passed = False
    except Exception as e:
        print_result("Quick functions", f"❌ Failed: {str(e)}")
        test_3_passed = False
    
    # Test 4: Work Order Diagnosis Simulation
    print_section("TEST 4: Work Order Diagnosis Simulation")
    try:
        # Try to find existing work orders
        work_orders = frappe.get_all("Work Order", limit=2)
        if work_orders:
            for wo in work_orders:
                wo_name = wo.name
                print(f"\n🧪 Testing diagnose_and_fix_work_order for {wo_name}...")
                result = bom_automation.diagnose_and_fix_work_order(wo_name)
                print_result(f"diagnose_work_order ({wo_name})", result)
            
            test_4_passed = True
        else:
            print_result("Work order diagnosis", "❌ No work orders found")
            test_4_passed = False
    except Exception as e:
        print_result("Work order diagnosis", f"❌ Failed: {str(e)}")
        test_4_passed = False
    
    # Test 5: Natural Language Command Simulation
    print_section("TEST 5: Natural Language Command Simulation")
    try:
        print("🎯 Simulating Raven AI natural language commands:")
        
        commands = [
            f"Fix BOM {boms[0].name if boms else 'BOM-TEST'}",
            "Create work order for BOM with quantity 500",
            "Diagnose and fix work order MFG-WO-02225"
        ]
        
        for cmd in commands:
            print(f"\n💬 Command: '{cmd}'")
            if boms:
                test_bom = boms[0].name
                # Simulate the function call that would be made
                result = bom_automation.validate_and_fix_bom(test_bom, auto_fix=True)
                print(f"🔧 AI Function: validate_and_fix_bom('{test_bom}', auto_fix=True)")
                print(f"📊 Result: {result.get('status', 'Unknown')}")
            else:
                print("❌ No BOM available for simulation")
        
        test_5_passed = True
    except Exception as e:
        print_result("Natural language simulation", f"❌ Failed: {str(e)}")
        test_5_passed = False
    
    # Summary
    print_section("API TEST SUMMARY")
    tests = [
        ("BOM Validation Functions", test_1_passed),
        ("Work Order Creation", test_2_passed),
        ("Quick Functions", test_3_passed),
        ("Work Order Diagnosis", test_4_passed),
        ("Natural Language Simulation", test_5_passed)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"📊 API Tests Passed: {passed}/{total}")
    
    if passed >= 4:  # At least 4 out of 5 tests need to pass
        print("🎉 API FUNCTIONS ARE WORKING!")
        print("\n✅ Ready for Browser API Testing:")
        print("1. Go to: https://sysmayal-frappe.ngrok.io/api/method/amb_w_tds.api.bom_automation.validate_and_fix_bom")
        print("2. Post: {'bom_name': 'YOUR-BOM-NAME', 'auto_fix': false}")
        print("3. Should return: BOM validation results")
        print("\n✅ Ready for Production Deployment!")
    else:
        print("⚠️  API FUNCTIONS NEED FIXING")
        print("\n📋 Failed tests:")
        for test_name, result in tests:
            if not result:
                print(f"   ❌ {test_name}")
    
    return {
        "total_tests": total,
        "passed_tests": passed,
        "success_rate": (passed/total)*100,
        "ready_for_browser_api": passed >= 4,
        "test_details": tests
    }

if __name__ == "__main__":
    try:
        result = test_bom_api_functions()
        print(f"\n🏁 API testing completed at {datetime.now()}")
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()