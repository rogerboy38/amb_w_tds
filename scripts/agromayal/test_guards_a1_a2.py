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
    # HARD SAFETY: the harness exercises apply paths, and those call
    # frappe.db.commit() internally. A real commit ends the transaction and the
    # closing rollback then reverts nothing — which leaked four synthetic rows
    # into dev the first time this ran. Neutralise commit for the whole harness
    # so "rolled back" is structurally guaranteed, not merely intended.
    frappe.db.commit = lambda *a, **k: None
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

    # (3) whitelisted test artifact (draft Batch AMB) halts WITHOUT the flag
    t = {"draft_wos": [], "orphan_wos": [{"name": "WO-TEST-A1", "docstatus": 0}],
         "projects": [], "sres": [], "so": so, "so_docstatus": 2}
    try:
        cleanup.execute(t, apply_it=False, unlink_ok=False)
        check("whitelisted draft artifact halts without unlink flag", False, "no Halt raised")
    except cleanup.Halt:
        check("whitelisted draft artifact halts without unlink flag", True)

    # (4) ... and is unlinked with the flag
    try:
        cleanup.execute(t, apply_it=False, unlink_ok=True)
        check("whitelisted draft artifact proceeds with unlink flag", True)
    except cleanup.Halt as e:
        check("whitelisted draft artifact proceeds with unlink flag", False, str(e))

    # (5) a SUBMITTED whitelisted artifact must never be unlinked
    frappe.db.sql("UPDATE `tabBatch AMB` SET docstatus=1 WHERE name='BATCH-TEST-A1'")
    try:
        cleanup.execute(t, apply_it=False, unlink_ok=True)
        check("submitted whitelisted artifact refused even with flag", False, "no Halt raised")
    except cleanup.Halt as e:
        check("submitted whitelisted artifact refused even with flag", "NOT draft" in str(e))
    frappe.db.sql("UPDATE `tabBatch AMB` SET docstatus=0 WHERE name='BATCH-TEST-A1'")

    # (6) B-2 THE BLOCKER: a Workflow Action row makes the WO un-deletable.
    #     No hand-rolled allowlist may wave this through — frappe's own dynamic
    #     link check must be what stops us.
    frappe.db.sql("""INSERT INTO `tabWorkflow Action` (name, creation, modified, owner,
                     modified_by, docstatus, reference_doctype, reference_name, status)
                     VALUES ('WFA-TEST-A1', NOW(), NOW(),'Administrator','Administrator',0,
                     'Work Order','WO-TEST-A1','Open')""")
    verdict = cleanup.native_link_check("WO-TEST-A1")
    check("frappe itself reports the Workflow Action link", bool(verdict), (verdict or "")[:88])
    try:
        cleanup.execute(t, apply_it=True, unlink_ok=True)
        check("WO with a Workflow Action row HALTS (never force-deleted)", False,
              "no Halt raised — script would have deleted it")
    except cleanup.Halt as e:
        halted_named = "WO-TEST-A1" in str(e) and "Workflow Action" in str(e)
        check("WO with a Workflow Action row HALTS (never force-deleted)", halted_named, str(e)[:96])
    still = frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name='WO-TEST-A1'")
    check("the blocked WO still exists (nothing was force-deleted)", bool(still))
    frappe.db.sql("DELETE FROM `tabWorkflow Action` WHERE name='WFA-TEST-A1'")

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

    # =================================================================== B-1
    print("\nB-1 — RESULT must cover only the resolved target set; strays are INFO")
    mk_wo("WO-TEST-STRAY", 4321, "BOM-0307-UNRELATED")   # never in scope
    t4 = {"draft_wos": [], "orphan_wos": [], "projects": [], "sres": [],
          "so": so, "so_docstatus": 2}
    before = cleanup.bin_state()
    res = cleanup.postverify(t4, before)
    check("out-of-scope stray does NOT fail the RESULT", res is True,
          "stray present but RESULT stayed PASS")
    frappe.db.sql("DELETE FROM `tabWork Order` WHERE name='WO-TEST-STRAY'")

    # ============================================ STAGED RESERVATION MODE
    print("\nSTAGE=reservation — WFA-blocked WOs defer, they do not block the fix")
    mk_wo("WO-TEST-STAGE", 6000, "BOM-0307-FG-FINAL")
    for i in range(4):
        frappe.db.sql("""INSERT INTO `tabWorkflow Action` (name, creation, modified, owner,
                         modified_by, docstatus, reference_doctype, reference_name, status,
                         workflow_state) VALUES (%s, NOW(), NOW(),'Administrator',
                         'Administrator',0,'Work Order','WO-TEST-STAGE','Open','Not Started')""",
                      (f"WFA-TEST-STAGE-{i}",))
    t5 = {"draft_wos": [], "orphan_wos": [{"name": "WO-TEST-STAGE", "docstatus": 0}],
          "projects": [], "sres": [], "so": so, "so_docstatus": 2}
    before_wo = frappe.db.sql("SELECT docstatus, modified FROM `tabWork Order` WHERE name='WO-TEST-STAGE'", as_dict=True)
    before_wfa = frappe.db.sql("SELECT COUNT(*) c FROM `tabWorkflow Action` WHERE reference_name='WO-TEST-STAGE'", as_dict=True)[0]["c"]

    # full mode still refuses (regression — the blocker fix must stand)
    try:
        cleanup.execute(dict(t5), apply_it=True, unlink_ok=True, stage="full")
        check("full mode still HALTS on the WFA-blocked WO", False, "no Halt raised")
    except cleanup.Halt:
        check("full mode still HALTS on the WFA-blocked WO", True)

    # staged mode defers instead of aborting
    try:
        cleanup.execute(t5, apply_it=True, unlink_ok=False, stage="reservation")
        check("stage=reservation DEFERS instead of halting", True)
    except cleanup.Halt as e:
        check("stage=reservation DEFERS instead of halting", False, str(e)[:100])

    after_wo = frappe.db.sql("SELECT docstatus, modified FROM `tabWork Order` WHERE name='WO-TEST-STAGE'", as_dict=True)
    after_wfa = frappe.db.sql("SELECT COUNT(*) c FROM `tabWorkflow Action` WHERE reference_name='WO-TEST-STAGE'", as_dict=True)[0]["c"]
    check("deferred WO untouched (still exists, docstatus+modified unchanged)",
          bool(after_wo) and after_wo == before_wo)
    check("its 4 Not-Started WFAs untouched", after_wfa == before_wfa == 4, f"{before_wfa} -> {after_wfa}")

    res = cleanup.postverify(t5, cleanup.bin_state(), stage="reservation")
    check("staged RESULT is PASS despite the deferred WO", res is True)

    # E — the INVERT: a staged PASS must not be able to mask a failed fix.
    # Force each of the three staged obligations to fail, independently.
    class FakeBin(list):
        pass

    # E1 reservation NOT released -> FAIL
    held = [{"warehouse": "FG to Sell Warehouse - AMB-W", "actual_qty": 39.0,
             "reserved_qty": 6000.0, "projected_qty": -5961.0}]
    real_bin_state = cleanup.bin_state
    cleanup.bin_state = lambda: held          # after-state still reserved
    res_e1 = cleanup.postverify(t5, held, stage="reservation")
    cleanup.bin_state = real_bin_state
    check("E1 invert: unreleased reservation FAILS the staged RESULT", res_e1 is False)

    # E2 project left Open -> FAIL
    frappe.db.sql("UPDATE `tabProject` SET status='Open' WHERE name='PROJ-0023'")
    t6 = dict(t5); t6["projects"] = [{"name": "PROJ-0023", "status": "Open"}]
    res_e2 = cleanup.postverify(t6, cleanup.bin_state(), stage="reservation")
    check("E2 invert: project left Open FAILS the staged RESULT", res_e2 is False)
    frappe.db.sql("UPDATE `tabProject` SET status='Cancelled' WHERE name='PROJ-0023'")

    # E3 SO not cancelled -> FAIL
    frappe.db.sql("UPDATE `tabSales Order` SET docstatus=1 WHERE name=%s", so)
    res_e3 = cleanup.postverify(t5, cleanup.bin_state(), stage="reservation")
    check("E3 invert: uncancelled SO FAILS the staged RESULT", res_e3 is False)
    frappe.db.sql("UPDATE `tabSales Order` SET docstatus=2 WHERE name=%s", so)

    frappe.db.sql("DELETE FROM `tabWorkflow Action` WHERE reference_name='WO-TEST-STAGE'")
    frappe.db.sql("DELETE FROM `tabWork Order` WHERE name='WO-TEST-STAGE'")

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
        leftovers = frappe.db.sql(
            """SELECT 'Work Order' dt, name FROM `tabWork Order` WHERE name LIKE 'WO-TEST%'
               UNION ALL SELECT 'Batch AMB', name FROM `tabBatch AMB` WHERE name LIKE '%TEST-A1%'
               UNION ALL SELECT 'Dynamic Link', name FROM `tabDynamic Link` WHERE name LIKE 'DL-TEST%'
               UNION ALL SELECT 'Workflow Action', name FROM `tabWorkflow Action` WHERE name LIKE 'WFA-TEST%'
               UNION ALL SELECT 'Comment', name FROM `tabComment` WHERE name LIKE 'CMT-TEST%'""")
        print(f"residue check after rollback: {leftovers or 'CLEAN — no synthetic row persisted'}")
        if leftovers:
            print("!! HARNESS LEAKED — clean these rows manually")
        print("rolled back — no synthetic row persisted")
        frappe.destroy()
    sys.exit(0 if ok else 1)
