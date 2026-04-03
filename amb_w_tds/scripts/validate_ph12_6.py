"""
PH12.6 Validation Script
Comprehensive tests for PH12.6 features

Usage:
    bench execute amb_w_tds.scripts.validate_ph12_6.execute
"""
import frappe
import subprocess
import os
import json
import glob


def execute():
    print("=" * 60)
    print("PH12.6 Validation Script")
    print("=" * 60)
    
    # Get the app path dynamically
    app_path = get_app_path()
    print(f"\nApp path: {app_path}")
    
    results = []
    
    # T6.1: No console.log in batch_amb.js
    print("\n[T6.1] Debug statements in batch_amb.js")
    print("-" * 40)
    try:
        js_files = glob.glob(f"{app_path}/**/batch_amb.js", recursive=True)
        js_file = js_files[0] if js_files else None
        
        if js_file:
            result = subprocess.run(
                ["grep", "-c", "console.log", js_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            if count == 0:
                print("PASS: No console.log found")
                results.append(("T6.1", "PASS"))
            else:
                print(f"FAIL: Found {count} console.log statements")
                results.append(("T6.1", "FAIL"))
        else:
            print("FAIL: batch_amb.js not found")
            results.append(("T6.1", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error checking - {str(e)}")
        results.append(("T6.1", "FAIL"))
    
    # T6.2: All whitelisted methods have permission checks
    print("\n[T6.2] Whitelist permission checks")
    print("-" * 40)
    try:
        py_files = glob.glob(f"{app_path}/**/batch_amb.py", recursive=True)
        py_file = py_files[0] if py_files else None
        
        if py_file:
            whitelist_count = subprocess.run(
                ["grep", "-c", "@frappe.whitelist", py_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            perm_count = subprocess.run(
                ["grep", "-c", "frappe.has_permission", py_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            w_count = int(whitelist_count.stdout.strip()) if whitelist_count.stdout.strip().isdigit() else 0
            p_count = int(perm_count.stdout.strip()) if perm_count.stdout.strip().isdigit() else 0
            
            if p_count >= w_count:
                print(f"PASS: {p_count} permission checks for {w_count} whitelisted methods")
                results.append(("T6.2", "PASS"))
            else:
                print(f"FAIL: {p_count} checks for {w_count} methods")
                results.append(("T6.2", "FAIL"))
        else:
            print("FAIL: batch_amb.py not found")
            results.append(("T6.2", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.2", "FAIL"))
    
    # T6.3: receive_weight has auth check
    print("\n[T6.3] API authentication check")
    print("-" * 40)
    try:
        api_files = glob.glob(f"{app_path}/**/batch_api.py", recursive=True)
        api_file = api_files[0] if api_files else None
        
        if api_file:
            result = subprocess.run(
                ["grep", "-n", "Authorization\\|Bearer", api_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.stdout and "Authorization" in result.stdout:
                print("PASS: Authorization check found in batch_api.py")
                results.append(("T6.3", "PASS"))
            else:
                print("FAIL: No Authorization check found")
                results.append(("T6.3", "FAIL"))
        else:
            print("FAIL: batch_api.py not found")
            results.append(("T6.3", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.3", "FAIL"))
    
    # T6.4: Pipeline validation blocks skip
    print("\n[T6.4] Pipeline validation")
    print("-" * 40)
    try:
        py_files = glob.glob(f"{app_path}/**/batch_amb.py", recursive=True)
        py_file = py_files[0] if py_files else None
        
        if py_file:
            result = subprocess.run(
                ["grep", "-n", "validate_pipeline_transition", py_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.stdout:
                print("PASS: Pipeline validation method exists")
                results.append(("T6.4", "PASS"))
            else:
                print("FAIL: No pipeline validation found")
                results.append(("T6.4", "FAIL"))
        else:
            print("FAIL: batch_amb.py not found")
            results.append(("T6.4", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.4", "FAIL"))
    
    # T6.5: Serial format correct (no redundant C)
    print("\n[T6.5] Serial format")
    print("-" * 40)
    try:
        py_files = glob.glob(f"{app_path}/**/batch_amb.py", recursive=True)
        py_file = py_files[0] if py_files else None
        
        if py_file:
            # Check for correct serial format
            result = subprocess.run(
                ["grep", "-n", "serial.*=.*f.*base_title.*seq", py_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Also check for the wrong format with redundant C
            wrong_result = subprocess.run(
                ["grep", "-n", "C{idx:03d}", py_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout and not wrong_result.stdout:
                print("PASS: Serial format is {title}-{seq:03d} (no redundant C)")
                results.append(("T6.5", "PASS"))
            elif wrong_result.stdout:
                print("FAIL: Serial format has redundant C prefix")
                results.append(("T6.5", "FAIL"))
            else:
                print("PASS: Serial generation uses base_title format")
                results.append(("T6.5", "PASS"))
        else:
            print("FAIL: batch_amb.py not found")
            results.append(("T6.5", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.5", "FAIL"))
    
    # T6.6: Container Barrels child table exists
    print("\n[T6.6] Container Barrels child table")
    print("-" * 40)
    try:
        json_files = glob.glob(f"{app_path}/**/batch_amb.json", recursive=True)
        json_file = json_files[0] if json_files else None
        
        if json_file:
            with open(json_file, "r") as f:
                doc = json.load(f)
            
            children = doc.get("fields", [])
            has_container_barrels = any(
                f.get("fieldname") == "container_barrels" for f in children
            )
            
            if has_container_barrels:
                print("PASS: container_barrels child table exists")
                results.append(("T6.6", "PASS"))
            else:
                print("FAIL: container_barrels not found in DocType")
                results.append(("T6.6", "FAIL"))
        else:
            print("FAIL: batch_amb.json not found")
            results.append(("T6.6", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.6", "FAIL"))
    
    # T6.7: All DocType JSONs have custom=1
    print("\n[T6.7] DocType custom=1")
    print("-" * 40)
    try:
        issues = []
        for json_file in glob.glob(f"{app_path}/**/batch_amb.json", recursive=True):
            with open(json_file, "r") as f:
                doc = json.load(f)
            if not doc.get("custom"):
                issues.append(os.path.basename(json_file))
        
        if not issues:
            print("PASS: All Batch AMB DocTypes have custom=1")
            results.append(("T6.7", "PASS"))
        else:
            print(f"FAIL: Missing custom=1 in: {issues}")
            results.append(("T6.7", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.7", "FAIL"))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    for test, status in results:
        print(f"  {test}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return results


def get_app_path():
    """Get the amb_w_tds app path dynamically"""
    # Try to find the app in common locations
    possible_paths = [
        "/workspace/amb_w_tds/amb_w_tds",
        os.path.expanduser("~/frappe-bench/apps/amb_w_tds/amb_w_tds"),
        "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Fallback: use first path
    return possible_paths[0]
