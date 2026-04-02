"""
<<<<<<< HEAD
PH12.2 Validation Script - UX Reengineering (Fixed)
Run with: bench execute amb_w_tds.scripts.validate_ph12_2.validate
"""
import frappe
import os
=======
PH12.2 Validation Script - UX Reengineering
Run with: bench execute amb_w_tds.scripts.validate_ph12_2.validate
"""
import frappe
import json
>>>>>>> 7d6863f (Update:)

def validate():
    results = []

    def log_test(test_id, name, passed, details=""):
        status = "PASS" if passed else "FAIL"
        results.append((test_id, status))
        print(f"  [{status}] {test_id}: {name}" + (f" | {details}" if details else ""))

    print("=" * 60)
<<<<<<< HEAD
    print("PH12.2 VALIDATION - UX Reengineering (Fixed)")
=======
    print("PH12.2 VALIDATION - UX Reengineering")
>>>>>>> 7d6863f (Update:)
    print("=" * 60)

    # T1: pipeline_status exists
    meta = frappe.get_meta("Batch AMB")
    ps = meta.get_field("pipeline_status")
    log_test("T1", "pipeline_status exists", ps is not None)

    if ps:
<<<<<<< HEAD
        # T2: All options present
        opts = [o.strip() for o in (ps.options or "").split('\n') if o.strip()]
        exp = ["Draft", "WO Linked", "In Production", "Weighing", "QI Pending", "QI Passed", "COA Ready", "Ready for Delivery", "Delivered", "Closed"]
        miss = [o for o in exp if o not in opts]
        log_test("T2", "All options present", len(miss) == 0, str(miss) if miss else "")

        # T3: Default is Draft
        log_test("T3", "Default Draft", ps.default_value == "Draft", ps.default_value)

        # T4: In list view
        log_test("T4", "In list view", ps.in_list_view == 1)

    else:
        log_test("T2", "All options present", False, "pipeline_status field missing")
        log_test("T3", "Default Draft", False, "pipeline_status field missing")
        log_test("T4", "In list view", False, "pipeline_status field missing")

    # T5: Batches load with pipeline_status
    batches = frappe.get_all("Batch AMB", limit=5, order_by="creation desc")
    if batches:
        details = []
        for b in batches:
            batch = frappe.get_doc("Batch AMB", b.name)
            title = batch.title or batch.name
            pipe = getattr(batch, "pipeline_status", "N/A")
            details.append(f"{b.name} L{batch.custom_batch_level} title={title} pipe={pipe}")
        log_test("T5", "Batches load", True, f"{len(batches)} batches found")
        for d in details:
            print(f"    {d}")
    else:
        log_test("T5", "Batches load", False, "No batches found")

    # T6: JS contains pipeline progress logic
    js_path = "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js"
    if os.path.exists(js_path):
        with open(js_path, 'r') as f:
            js_content = f.read()
            has_pipeline = "pipeline_status" in js_content and "render_pipeline_progress" in js_content
            log_test("T6", "JS pipeline", has_pipeline)
    else:
        log_test("T6", "JS pipeline", False, f"File not found: {js_path}")

    # T7: JS contains role-based button logic
    if os.path.exists(js_path):
        with open(js_path, 'r') as f:
            js_content = f.read()
            has_roles = "Manufacturing User" in js_content or "setup_role_based_buttons" in js_content
            log_test("T7", "JS roles", has_roles)
    else:
        log_test("T7", "JS roles", False, "JS file not found")

    # T8: JS has developer_mode guard
    if os.path.exists(js_path):
        with open(js_path, 'r') as f:
            js_content = f.read()
            has_guard = "developer_mode" in js_content
            log_test("T8", "JS debug guard", has_guard)
    else:
        log_test("T8", "JS debug guard", False, "JS file not found")

    # T9: DocType has multiple tab breaks (sections)
    try:
        doctype_json_path = "/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.json"
        if os.path.exists(doctype_json_path):
            import json
            with open(doctype_json_path, 'r') as f:
                doctype_data = json.load(f)
                tabs = [f.get("label") for f in doctype_data.get("fields", []) if f.get("fieldtype") == "Tab Break"]
                log_test("T9", "DocType tabs>=3", len(tabs) >= 3, str(tabs))
        else:
            log_test("T9", "DocType tabs>=3", False, "JSON file not found")
    except Exception as e:
        log_test("T9", "DocType tabs>=3", False, str(e))

    # T10: BatchAMB imports
=======
        # T2: All expected options present
        opts = [o.strip() for o in (ps.options or "").split('\n') if o.strip()]
        exp = ["Draft","WO Linked","In Production","Weighing","QI Pending","QI Passed","COA Ready","Ready for Delivery","Delivered","Closed"]
        miss = [o for o in exp if o not in opts]
        log_test("T2", "All options present", len(miss)==0, str(miss))
        
        # T3: Default Draft
        log_test("T3", "Default Draft", (ps.default or "").strip()=="Draft", str(ps.default))
        
        # T4: In list view
        log_test("T4", "In list view", bool(ps.in_list_view))
    else:
        log_test("T2", "All options present", False, "pipeline_status not found")
        log_test("T3", "Default Draft", False, "pipeline_status not found")
        log_test("T4", "In list view", False, "pipeline_status not found")

    # T5: Batches load
    try:
        batches = frappe.get_all("Batch AMB", fields=["name","title","custom_batch_level","pipeline_status"], limit=5)
        log_test("T5", "Batches load", True, f"{len(batches)} batches found")
        for b in batches:
            print(f"    {b.name} L{b.custom_batch_level} title={b.title} pipe={b.pipeline_status or 'NULL'}")
    except Exception as e:
        log_test("T5", "Batches load", False, str(e)[:100])

    # T6-8: JS file checks
    try:
        app_path = frappe.get_app_path("amb_w_tds")
        js_path = os.path.join(app_path, "amb_w_tds", "doctype", "batch_amb", "batch_amb.js")
        
        if os.path.exists(js_path):
            with open(js_path) as f:
                js = f.read().lower()
            log_test("T6", "JS pipeline", "pipeline" in js and "progress" in js)
            log_test("T7", "JS roles", any(x in js for x in ["user_roles", "manufacturing manager", "operator"]))
            log_test("T8", "JS debug guard", "developer_mode" in js)
        else:
            log_test("T6", "JS pipeline", False, "File not found")
            log_test("T7", "JS roles", False, "File not found")
            log_test("T8", "JS debug guard", False, "File not found")
    except Exception as e:
        log_test("T6", "JS pipeline", False, str(e)[:50])
        log_test("T7", "JS roles", False, str(e)[:50])
        log_test("T8", "JS debug guard", False, str(e)[:50])

    # T9: DocType tabs
    try:
        json_path = js_path.replace(".js", ".json")
        if os.path.exists(json_path):
            with open(json_path) as f:
                dt = json.load(f)
            tabs = [f.get("label","?") for f in dt.get("fields",[]) if f.get("fieldtype")=="Tab Break"]
            log_test("T9", "DocType tabs>=3", len(tabs)>=3, str(tabs))
        else:
            log_test("T9", "DocType tabs>=3", False, "JSON file not found")
    except Exception as e:
        log_test("T9", "DocType tabs>=3", False, str(e)[:100])

    # T10: Import test
>>>>>>> 7d6863f (Update:)
    try:
        from amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb import BatchAMB
        log_test("T10", "BatchAMB imports", True)
    except Exception as e:
<<<<<<< HEAD
        log_test("T10", "BatchAMB imports", False, str(e))
=======
        log_test("T10", "BatchAMB imports", False, str(e)[:100])
>>>>>>> 7d6863f (Update:)

    # Summary
    passed = sum(1 for r in results if r[1] == "PASS")
    total = len(results)
    print("=" * 60)
    print(f"PASSED: {passed}/{total} FAILED: {total - passed}/{total}")
    print(f"RESULT: {'PASS' if passed == total else 'FAIL'}")
    print("=" * 60)
    return results

<<<<<<< HEAD

=======
>>>>>>> 7d6863f (Update:)
if __name__ == "__main__":
    validate()
