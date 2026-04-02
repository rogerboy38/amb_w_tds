"""
PH12.4 Validation Script - Weight Capture System
Run with: bench execute amb_w_tds.scripts.validate_ph12_4.validate
"""
import frappe
import json
import inspect

def validate():
    results = []

    def log_test(test_id, name, passed, details=""):
        status = "PASS" if passed else "FAIL"
        results.append((test_id, status))
        print(f"  [{status}] {test_id}: {name}" + (f" | {details}" if details else ""))

    print("=" * 60)
    print("PH12.4 VALIDATION - Weight Capture System")
    print("=" * 60)

    from amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb import BatchAMB

    # T4.1 - calculate_weight method exists
    log_test("T4.1", "calculate_weight method exists", hasattr(BatchAMB, "calculate_weight"))

    # T4.2 - validate_barrel_weight method exists
    log_test("T4.2", "validate_barrel_weight method exists", hasattr(BatchAMB, "validate_barrel_weight"))

    # T4.3 - Tara weight field exists on Container Barrels
    meta = frappe.get_meta("Container Barrels")
    tara = meta.get_field("tara_weight")
    log_test("T4.3", "tara_weight field on Container Barrels", tara is not None)

    # T4.4 - net_weight field exists
    net = meta.get_field("net_weight")
    log_test("T4.4", "net_weight field on Container Barrels", net is not None)

    # T4.5 - weight_validated field exists
    wv = meta.get_field("weight_validated")
    log_test("T4.5", "weight_validated field on Container Barrels", wv is not None)

    # T4.6 - gross_weight field exists
    gw = meta.get_field("gross_weight")
    log_test("T4.6", "gross_weight field on Container Barrels", gw is not None)

    # T4.7 - receive_weight API endpoint discoverable
    try:
        fn = frappe.get_attr("amb_w_tds.api.batch_api.receive_weight")
        log_test("T4.7", "receive_weight API endpoint discoverable", callable(fn))
    except Exception as e:
        log_test("T4.7", "receive_weight API endpoint discoverable", False, str(e))

    # T4.8 - receive_weight is whitelisted (STRICT VERSION)
    try:
        fn = frappe.get_attr("amb_w_tds.api.batch_api.receive_weight")
        
        # Check source code for decorator
        try:
            source = inspect.getsource(fn)
            source_has_decorator = (
                "@frappe.whitelist()" in source or
                "@frappe.whitelist(" in source
            )
        except Exception:
            source_has_decorator = False
        
        # Check runtime metadata
        runtime_flag = getattr(fn, "whitelisted", None)
        
        # STRICT: Only pass if decorator in source OR runtime_flag is explicitly True
        is_whitelisted = bool(source_has_decorator or runtime_flag is True)
        
        log_test(
            "T4.8",
            "receive_weight is @frappe.whitelist",
            is_whitelisted,
            f"source={source_has_decorator}, runtime={runtime_flag}"
        )
    except Exception as e:
        log_test("T4.8", "receive_weight is @frappe.whitelist", False, str(e))

    # T4.9 - Batch AMB loads with weight methods
    batches = frappe.get_all("Batch AMB", filters={"custom_batch_level": "3"}, limit=1, pluck="name")
    if batches:
        doc = frappe.get_doc("Batch AMB", batches[0])
        has_calc = hasattr(doc, "calculate_weight")
        has_val = hasattr(doc, "validate_barrel_weight")
        log_test("T4.9", f"L3 batch {batches[0]} has weight methods", has_calc and has_val)
    else:
        batches = frappe.get_all("Batch AMB", limit=1, pluck="name")
        if batches:
            doc = frappe.get_doc("Batch AMB", batches[0])
            has_calc = hasattr(doc, "calculate_weight")
            log_test("T4.9", f"Batch {batches[0]} has calculate_weight", has_calc)
        else:
            log_test("T4.9", "Batch weight methods on instance", False, "No batches found")

    # T4.10 - calculate_totals still works (backward compat)
    log_test("T4.10", "calculate_totals backward compatible", hasattr(BatchAMB, "calculate_totals"))

    # Summary
    passed = sum(1 for r in results if r[1] == "PASS")
    total = len(results)
    print("=" * 60)
    print(f"PASSED: {passed}/{total} FAILED: {total - passed}/{total}")
    print(f"RESULT: {'PASS' if passed == total else 'FAIL'}")
    print("=" * 60)
    return results

if __name__ == "__main__":
    validate()
