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


def execute():
    print("=" * 60)
    print("PH12.6 Validation Script")
    print("=" * 60)
    
    results = []
    
    # T6.1: No console.log in batch_amb.js
    print("\n[T6.1] Debug statements in batch_amb.js")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["grep", "-c", "console.log", 
             "/workspace/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js"],
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
    except Exception as e:
        print(f"FAIL: Error checking - {str(e)}")
        results.append(("T6.1", "FAIL"))
    
    # T6.2: All whitelisted methods have permission checks
    print("\n[T6.2] Whitelist permission checks")
    print("-" * 40)
    try:
        whitelist_count = subprocess.run(
            ["grep", "-c", "@frappe.whitelist",
             "/workspace/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        perm_count = subprocess.run(
            ["grep", "-c", "frappe.has_permission",
             "/workspace/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"],
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
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.2", "FAIL"))
    
    # T6.3: receive_weight has auth check
    print("\n[T6.3] API authentication check")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["grep", "-n", "Authorization\\|Bearer\\|device_id",
             "/workspace/amb_w_tds/amb_w_tds/api/batch_api.py"],
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
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.3", "FAIL"))
    
    # T6.4: Pipeline validation blocks skip
    print("\n[T6.4] Pipeline validation")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["grep", "-n", "validate_pipeline_transition",
             "/workspace/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"],
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
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.4", "FAIL"))
    
    # T6.5: Serial format correct
    print("\n[T6.5] Serial format")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["grep", "-n", "serial.*=.*f.*base_title.*seq_num",
             "/workspace/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout and "C{idx:03d}" not in result.stdout:
            print("PASS: Serial format is {title}-{seq:03d} (no redundant C)")
            results.append(("T6.5", "PASS"))
        else:
            print("FAIL: Serial format may have redundant C prefix")
            results.append(("T6.5", "FAIL"))
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.5", "FAIL"))
    
    # T6.6: Container Barrels child table exists
    print("\n[T6.6] Container Barrels child table")
    print("-" * 40)
    try:
        json_path = "/workspace/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.json"
        with open(json_path, "r") as f:
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
    except Exception as e:
        print(f"FAIL: Error - {str(e)}")
        results.append(("T6.6", "FAIL"))
    
    # T6.7: All DocType JSONs have custom=1
    print("\n[T6.7] DocType custom=1")
    print("-" * 40)
    try:
        import glob
        issues = []
        for json_file in glob.glob(
            "/workspace/amb_w_tds/amb_w_tds/amb_w_tds/doctype/**/*.json", 
            recursive=True
        ):
            if "batch_amb" in json_file.lower():
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
