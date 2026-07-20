"""Synthetic proof for vm3 advisories A-1 and A-2 on the Agromayal cleanup.

Dev's phantom is already cleaned, so a plain re-run is an idempotent no-op and
proves nothing about the new guards. This harness injects synthetic rows, asserts
the guard reacts, and ROLLS BACK — nothing is committed, no document is created
through the ORM, and the live data is untouched.

Run:  env/bin/python apps/amb_w_tds/scripts/agromayal/test_guards_a1_a2.py --site v2.sysmayal.cloud
"""

import importlib.util
import sys

import frappe

HERE = "/home/frappe/frappe-bench/apps/amb_w_tds/scripts/agromayal/cleanup_agromayal_phantom_so.py"
spec = importlib.util.spec_from_file_location("cleanup", HERE)
cleanup = importlib.util.module_from_spec(spec)
sys.modules["cleanup"] = cleanup

RESULTS = []


def check(name, passed, detail=""):
    RESULTS.append((name, passed, detail))
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def sql(q, v=()):
    return frappe.db.sql(q, v, as_dict=True)


def mk_wo(name, qty, bom, sales_order=None, docstatus=0, produced=0):
    frappe.db.sql(
        """INSERT INTO `tabWork Order`
           (name, creation, modified, owner, modified_by, docstatus, production_item,
            qty, produced_qty, bom_no, sales_order, company, status)
           VALUES (%s, NOW(), NOW(), 'Administrator', 'Administrator', %s, '0307',
                   %s, %s, %s, %s, (SELECT name FROM `tabCompany` LIMIT 1), 'Draft')""",
        (name, docstatus, qty, produced, bom, sales_order))


def main():
    spec.loader.exec_module(cleanup)
    so_row = sql("""SELECT name, docstatus FROM `tabSales Order`
                    WHERE customer LIKE %s AND docstatus IN (1,2)
                      AND name IN (SELECT parent FROM `tabSales Order Item` WHERE item_code='0307')""",
                 ("%AGROMAYAL%",))
    so = so_row[0]["name"]
    print(f"target SO: {so} (docstatus {so_row[0]['docstatus']})\n")

    # =================================================================== A-1
    print("A-1 — downstream link enumeration must cover Dynamic Link, not just Link")
    mk_wo("WO-TEST-A1", 6000, "BOM-0307-FG-FINAL")

    # (1) regression: static Link (the Batch AMB.work_order_ref case from dev)
    frappe.db.sql("""INSERT INTO `tabBatch AMB` (name, creation, modified, owner, modified_by,
                     docstatus, work_order_ref) VALUES ('BATCH-TEST-A1', NOW(), NOW(),
                     'Administrator','Administrator',0,'WO-TEST-A1')""")
    links = cleanup.downstream_links(["WO-TEST-A1"])
    hit = [l for l in links if l["doctype"] == "Batch AMB"]
    check("static Link (Batch AMB.work_order_ref) detected", bool(hit), str(hit[:1]))

    # (2) the actual advisory: a Dynamic Link reference must be seen
    frappe.db.sql("""INSERT INTO `tabDynamic Link` (name, creation, modified, owner, modified_by,
                     docstatus, parent, parenttype, parentfield, idx, link_doctype, link_name)
                     VALUES ('DL-TEST-A1', NOW(), NOW(),'Administrator','Administrator',0,
                     'TEST-CONTACT','Contact','links',1,'Work Order','WO-TEST-A1')""")
    links = cleanup.downstream_links(["WO-TEST-A1"])
    dl = [l for l in links if l["doctype"] == "Dynamic Link"]
    check("DYNAMIC Link (link_doctype='Work Order') detected", bool(dl),
          dl[0]["kind"] if dl else "NOT SEEN — advisory would still be open")

    # (3) a submitted downstream doc must HALT outright
    frappe.db.sql("UPDATE `tabDynamic Link` SET docstatus=1 WHERE name='DL-TEST-A1'")
    t = {"draft_wos": [], "orphan_wos": [{"name": "WO-TEST-A1", "docstatus": 0}],
         "projects": [], "sres": [], "so": so, "so_docstatus": 2}
    try:
        cleanup.execute(t, apply_it=False, unlink_ok=True)
        check("submitted dynamic-link ref halts even with unlink flag", False, "no Halt raised")
    except cleanup.Halt as e:
        check("submitted dynamic-link ref halts even with unlink flag", "SUBMITTED" in str(e).upper())

    # (4) draft refs halt WITHOUT the flag, proceed WITH it
    frappe.db.sql("UPDATE `tabDynamic Link` SET docstatus=0 WHERE name='DL-TEST-A1'")
    try:
        cleanup.execute(t, apply_it=False, unlink_ok=False)
        check("draft dynamic-link ref halts without unlink flag", False, "no Halt raised")
    except cleanup.Halt:
        check("draft dynamic-link ref halts without unlink flag", True)
    try:
        cleanup.execute(t, apply_it=False, unlink_ok=True)
        check("draft dynamic-link ref proceeds with unlink flag", True)
    except cleanup.Halt as e:
        check("draft dynamic-link ref proceeds with unlink flag", False, str(e))

    # (5) system chatter must be reported, never blocking
    frappe.db.sql("""INSERT INTO `tabComment` (name, creation, modified, owner, modified_by,
                     docstatus, comment_type, reference_doctype, reference_name)
                     VALUES ('CMT-TEST-A1', NOW(), NOW(),'Administrator','Administrator',0,
                     'Comment','Work Order','WO-TEST-A1')""")
    links = cleanup.downstream_links(["WO-TEST-A1"])
    cm = [l for l in links if l["doctype"] == "Comment"]
    check("Comment seen but classified as non-blocking chatter",
          bool(cm) and all(c["chatter"] for c in cm))

    # =================================================================== A-2
    print("\nA-2 — orphan resolver must fail LOUD, never green while an orphan remains")
    frappe.db.sql("DELETE FROM `tabDynamic Link` WHERE name='DL-TEST-A1'")
    frappe.db.sql("DELETE FROM `tabBatch AMB` WHERE name='BATCH-TEST-A1'")
    frappe.db.sql("DELETE FROM `tabComment` WHERE name='CMT-TEST-A1'")
    frappe.db.sql("DELETE FROM `tabWork Order` WHERE name='WO-TEST-A1'")
    frappe.db.sql("UPDATE `tabSales Order` SET docstatus=1 WHERE name=%s", so)  # pretend un-cleaned

    # (6) perturbed qty + BOM: the OLD predicate would miss it silently
    mk_wo("WO-TEST-A2", 5500, "BOM-0307-SOMETHING-ELSE")
    try:
        cleanup.resolve()
        check("perturbed-qty orphan: halts instead of false green", False, "resolve() returned green")
    except cleanup.Halt as e:
        check("perturbed-qty orphan: halts instead of false green",
              "NO orphan" in str(e), str(e)[:110])
    frappe.db.sql("DELETE FROM `tabWork Order` WHERE name='WO-TEST-A2'")

    # (7) orphan whose BOM differs but qty matches the SO -> found, BOM only reported
    mk_wo("WO-TEST-A2B", 6000, "BOM-0307-DIFFERENT")
    try:
        t2 = cleanup.resolve()
        found = [o["name"] for o in t2["orphan_wos"]]
        check("orphan found by SO qty even with an unexpected BOM", found == ["WO-TEST-A2B"], str(found))
    except cleanup.Halt as e:
        check("orphan found by SO qty even with an unexpected BOM", False, str(e)[:110])

    # (8) two candidates -> ambiguous, must halt
    mk_wo("WO-TEST-A2C", 6000, "BOM-0307-FG-FINAL")
    try:
        cleanup.resolve()
        check("two orphan candidates: halts as ambiguous", False, "resolve() returned green")
    except cleanup.Halt as e:
        check("two orphan candidates: halts as ambiguous", "ambiguous" in str(e), str(e)[:90])
    frappe.db.sql("DELETE FROM `tabWork Order` WHERE name IN ('WO-TEST-A2B','WO-TEST-A2C')")

    # (9) idempotent resting state: SO already cancelled + zero orphans is OK
    frappe.db.sql("UPDATE `tabSales Order` SET docstatus=2 WHERE name=%s", so)
    try:
        t3 = cleanup.resolve()
        check("cleaned env (SO cancelled, 0 orphans) stays green", t3["orphan_wos"] == [])
    except cleanup.Halt as e:
        check("cleaned env (SO cancelled, 0 orphans) stays green", False, str(e)[:110])

    print("\n" + "=" * 62)
    ok = all(p for _, p, _ in RESULTS)
    print(f"{sum(1 for _, p, _ in RESULTS if p)}/{len(RESULTS)} checks passed — "
          f"{'ALL GREEN' if ok else 'FAILURES PRESENT'}")
    return ok


if __name__ == "__main__":
    site = sys.argv[sys.argv.index("--site") + 1]
    frappe.init(site=site, sites_path="sites")
    frappe.connect()
    try:
        ok = main()
    finally:
        frappe.db.rollback()          # nothing synthetic is ever committed
        print("rolled back — no synthetic row persisted")
        frappe.destroy()
    sys.exit(0 if ok else 1)
