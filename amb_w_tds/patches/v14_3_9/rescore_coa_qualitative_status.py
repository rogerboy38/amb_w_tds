"""
V14.3.9 (2026-06-24) - Re-score submitted COA AMB status after the compliance fix.

Commits f2f6758 + 2258416 corrected check_parameter_compliance(): flt() was
collapsing unit-suffixed results to 0 (acemannan '23.5%', micro '<10 CFU/G'
wrongly Fail) and the qualitative branch was over-strict (Appearance/Odor/
Color/Taste). Submitted COAs keep the old wrong status because submitted docs
cannot be re-validated through the UI.

This patch recomputes status for every SUBMITTED COA with the corrected logic
and writes it via db.set_value (status fields only - it does NOT touch results,
certificate content, or what a customer received). Idempotent.

Standing rule (Hugh, 2026-06-23): the DB re-score must run on every transport.
A tracked Frappe patch satisfies this - it runs once per environment during
that env's migrate (vpt, prod).
"""

import frappe


def execute():
    names = frappe.get_all("COA AMB", filters={"docstatus": 1}, pluck="name")
    fixed = 0
    for name in names:
        try:
            doc = frappe.get_doc("COA AMB", name)
            failed = passed = pending = 0
            for row in doc.coa_quality_test_parameter:
                if doc._is_header_row(row):
                    continue
                if not (row.result or "").strip():
                    pending += 1
                    continue
                ok = doc.check_parameter_compliance(row)
                new = "Pass" if ok else "Fail"
                if ok:
                    passed += 1
                else:
                    failed += 1
                if row.status != new:
                    frappe.db.set_value("COA Quality Test Parameter", row.name,
                                        "status", new, update_modified=False)
            overall = ("Fail" if failed else
                       "Pass" if passed and not pending else
                       "Partial" if passed else "Pending")
            if doc.overall_result != overall:
                frappe.db.set_value("COA AMB", name, "overall_result",
                                    overall, update_modified=False)
                fixed += 1
        except Exception:
            frappe.log_error(message=f"rescore failed for {name}: {frappe.get_traceback()}",
                             title="COA rescore patch v14_3_9")
    frappe.db.commit()
    print(f"COA rescore v14_3_9: {fixed} overall_result corrected of {len(names)} submitted COAs")
