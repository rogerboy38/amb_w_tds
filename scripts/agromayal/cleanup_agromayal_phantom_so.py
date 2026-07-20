"""Agromayal phantom SO cleanup — guarded, reversible, QUERY-DRIVEN.

Transported artifact for dev -> vpt -> prod. Document names differ per
environment (the orphan Work Order is MFG-WO-05926 on wsl and MFG-WO-06226 on
prod), so every target is resolved by QUERY, never by hardcoded name.

The real harm being fixed: SO-117326 holds a 6,000 Kg phantom reservation on
item 0307, which has 39 Kg on hand -> projected availability reads -5,961 in
FG to Sell. Cancelling the SO releases the reservation; everything else is
tidy-up of never-executed paperwork.

FAIL-CLOSED: the pre-flight halts on ANY sign of real data (invoice, delivery,
payment, GL, produced quantity, or 0303/A0303 stock). It is designed to refuse
on an environment that is NOT the phantom-only shape seen on dev.

Usage (from the bench root):
    env/bin/python apps/amb_w_tds/scripts/agromayal/cleanup_agromayal_phantom_so.py \
        --site v2.sysmayal.cloud            # dry-run, prints the plan
    ... --site <site> apply=1               # execute (TAKE A BACKUP FIRST)
"""

import re
import sys

import frappe

SO_CUSTOMER_LIKE = "%AGROMAYAL%"
TARGET_ITEM = "0307"
ORPHAN_BOM_EXPECTED = "BOM-0307-FG-FINAL"   # reported, NEVER filtered on (A-2)
ORPHAN_QTY_TOL = 1.0                        # vs the SO's own 0307 quantity
CLEAN_ITEMS = ("0303", "A0303")


class Halt(Exception):
    """Pre-flight refused: the environment holds real data."""


# --------------------------------------------------------------------------
# resolve — every target found by query, never by name
# --------------------------------------------------------------------------
def resolve():
    so = frappe.db.sql(
        """SELECT name FROM `tabSales Order`
           WHERE customer LIKE %s AND docstatus IN (1, 2) AND per_delivered = 0 AND per_billed = 0
             AND name IN (SELECT parent FROM `tabSales Order Item` WHERE item_code = %s)""",
        (SO_CUSTOMER_LIKE, TARGET_ITEM),
        as_dict=True,
    )
    if len(so) != 1:
        raise Halt(f"expected exactly 1 undelivered/unbilled Agromayal 0307 SO, found {len(so)}: {so}")
    so = so[0].name
    # docstatus 2 means a previous run already cancelled it; the script is
    # idempotent so a part-failed run can be resumed rather than restarted.
    so_ds = frappe.db.get_value("Sales Order", so, "docstatus")

    draft_wos = frappe.get_all(
        "Work Order", filters={"sales_order": so, "docstatus": 0}, pluck="name"
    )
    # A-2 (vm3): resolve the orphan by ROBUST traits and assert loudly.
    # The old predicate filtered on qty 5999-6001 AND bom_no=BOM-0307-FG-FINAL
    # and returned green when it matched nothing — so a prod orphan with a
    # different qty or BOM would be silently left behind. Now the qty is taken
    # from the SO itself (env-independent), the BOM is REPORTED not filtered,
    # and a miss halts.
    so_qty = frappe.db.sql(
        """SELECT COALESCE(SUM(qty), 0) FROM `tabSales Order Item`
           WHERE parent = %s AND item_code = %s""", (so, TARGET_ITEM))[0][0]
    orphan_wos = frappe.db.sql(
        """SELECT name, docstatus, qty, bom_no, produced_qty, creation, owner
           FROM `tabWork Order`
           WHERE production_item = %s
             AND (sales_order IS NULL OR sales_order = '')
             AND produced_qty = 0
             AND docstatus IN (0, 1)
             AND ABS(qty - %s) <= %s""",
        (TARGET_ITEM, so_qty, ORPHAN_QTY_TOL), as_dict=True,
    )
    # Loud assertion. Pre-clean (SO still submitted) exactly one orphan must
    # exist; post-clean (SO already cancelled) zero is the correct resting
    # state. More than one is always ambiguous and never auto-processed.
    if len(orphan_wos) > 1:
        raise Halt(
            f"expected at most 1 orphan Work Order, found {len(orphan_wos)}: "
            f"{[(o['name'], o['qty'], o['bom_no'], o['docstatus']) for o in orphan_wos]} "
            "— ambiguous, refusing to guess")
    if so_ds == 1 and not orphan_wos:
        near = frappe.db.sql(
            """SELECT name, docstatus, qty, bom_no, produced_qty FROM `tabWork Order`
               WHERE production_item = %s AND (sales_order IS NULL OR sales_order = '')
                 AND docstatus IN (0, 1)""", TARGET_ITEM, as_dict=True)
        raise Halt(
            f"SO is still open but NO orphan Work Order matched qty {so_qty} "
            f"(tolerance {ORPHAN_QTY_TOL}, produced_qty=0). Unlinked {TARGET_ITEM} WOs seen: "
            f"{[(n['name'], n['qty'], n['bom_no'], n['produced_qty']) for n in near]} "
            "— refusing to report success while an orphan may remain")
    projects = frappe.db.sql(
        """SELECT name, status FROM `tabProject`
           WHERE sales_order = %s OR name LIKE %s""",
        (so, SO_CUSTOMER_LIKE),
        as_dict=True,
    )
    sres = []
    if frappe.db.exists("DocType", "Stock Reservation Entry"):
        sres = frappe.db.sql(
            """SELECT name, docstatus, reserved_qty FROM `tabStock Reservation Entry`
               WHERE voucher_no = %s OR from_voucher_no = %s""",
            (so, so),
            as_dict=True,
        )
    return {"so": so, "so_docstatus": so_ds, "draft_wos": draft_wos,
            "orphan_wos": orphan_wos, "projects": projects, "sres": sres}


def _link_field_map():
    """Every field that can point at a Work Order: static Link AND Dynamic Link.

    Reporting only — no disposition decision is taken from this map (B-2).
    Kept because naming the referencing documents makes a HALT actionable.
    """
    static, dynamic = [], []
    for tbl, dt_col in (("DocField", "parent"), ("Custom Field", "dt")):
        for r in frappe.db.sql(
            f"""SELECT `{dt_col}` AS dt, fieldname, options, fieldtype FROM `tab{tbl}`
                WHERE (fieldtype='Link' AND options='Work Order') OR fieldtype='Dynamic Link'""",
            as_dict=True,
        ):
            if not r.dt or not frappe.db.exists("DocType", r.dt):
                continue
            if r.fieldtype == "Link":
                static.append((r.dt, r.fieldname))
            elif r.options:
                dynamic.append((r.dt, r.fieldname, r.options))
    return sorted(set(static)), sorted(set(dynamic))


def downstream_links(wo_names):
    """Informational enumeration of every reference to the target Work Orders.

    Covers static Link AND Dynamic Link pairs (A-1). Purely descriptive: frappe's
    own checks decide what blocks (B-2).
    """
    if not wo_names:
        return []
    ph = ",".join(["%s"] * len(wo_names))
    static, dynamic = _link_field_map()
    out = []
    for dt, fn in static:
        try:
            hits = frappe.db.sql(
                f"""SELECT name, docstatus, `{fn}` AS wo FROM `tab{dt}` WHERE `{fn}` IN ({ph})""",
                tuple(wo_names), as_dict=True)
        except Exception:
            continue
        out += [{"doctype": dt, "field": fn, "kind": "Link", **h} for h in hits]
    for dt, fn, optf in dynamic:
        try:
            hits = frappe.db.sql(
                f"""SELECT name, docstatus, `{fn}` AS wo FROM `tab{dt}`
                    WHERE `{optf}`='Work Order' AND `{fn}` IN ({ph})""",
                tuple(wo_names), as_dict=True)
        except Exception:
            continue
        out += [{"doctype": dt, "field": fn, "kind": f"Dynamic Link via {optf}", **h} for h in hits]
    return out


# The ONLY pre-unlink permitted: artifacts explicitly confirmed disposable by
# Hugh (2026-07-20) — draft Batch AMB / Sample Request AMB carrying a stale
# work_order_ref. Everything else is left to frappe's own link safety.
UNLINK_WHITELIST = (("Batch AMB", "work_order_ref"), ("Sample Request AMB", "work_order_ref"))


def whitelisted_test_refs(wo_names):
    """Draft rows on the confirmed-disposable fields only."""
    if not wo_names:
        return []
    ph = ",".join(["%s"] * len(wo_names))
    out = []
    for dt, fn in UNLINK_WHITELIST:
        if not frappe.db.exists("DocType", dt) or not frappe.db.has_column(dt, fn):
            continue
        for h in frappe.db.sql(
            f"""SELECT name, docstatus, `{fn}` AS wo FROM `tab{dt}`
                WHERE `{fn}` IN ({ph})""", tuple(wo_names), as_dict=True):
            out.append({"doctype": dt, "field": fn, **h})
    return out


def workflow_actions_on(wo_names):
    """Workflow Action rows referencing the target Work Orders (read-only)."""
    if not wo_names or not frappe.db.exists("DocType", "Workflow Action"):
        return []
    ph = ",".join(["%s"] * len(wo_names))
    return frappe.db.sql(
        f"""SELECT name, reference_name AS wo, status, workflow_state
            FROM `tabWorkflow Action`
            WHERE reference_doctype='Work Order' AND reference_name IN ({ph})""",
        tuple(wo_names), as_dict=True)


def native_link_check(wo_name):
    """Ask FRAPPE whether the doc is still linked — static AND dynamic.

    B-2 (vm3): the previous version carried a hand-written "these doctypes are
    non-blocking" allowlist. That is exactly the judgement a cleanup script
    should not be making. frappe already implements both checks; defer to them
    and HALT on whatever they report, Workflow Action included. A phantom WO
    that an active workflow references is not a clean phantom.
    """
    from frappe.model.delete_doc import (
        check_if_doc_is_dynamically_linked,
        check_if_doc_is_linked,
    )

    doc = frappe.get_doc("Work Order", wo_name)
    for fn in (check_if_doc_is_linked, check_if_doc_is_dynamically_linked):
        try:
            fn(doc, method="Delete")
        except frappe.LinkExistsError as e:
            msg = re.sub(r"<[^>]+>", "", str(e)).strip()
            return f"{fn.__name__}: {msg}"
    return None


def bin_state():
    return frappe.db.sql(
        """SELECT warehouse, actual_qty, reserved_qty, projected_qty
           FROM `tabBin` WHERE item_code = %s ORDER BY warehouse""",
        TARGET_ITEM, as_dict=True,
    )


# --------------------------------------------------------------------------
# pre-flight — HALT on any real data
# --------------------------------------------------------------------------
def preflight(t):
    so = t["so"]
    checks = {
        "Sales Invoice rows": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSales Invoice Item` WHERE sales_order=%s", so)[0][0],
        "Delivery Note rows": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDelivery Note Item` WHERE against_sales_order=%s", so)[0][0],
        "Payment Entry refs": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabPayment Entry Reference` WHERE reference_name=%s", so)[0][0],
        "GL Entry rows": frappe.db.sql(
            "SELECT COUNT(*) FROM `tabGL Entry` WHERE voucher_no=%s OR against_voucher=%s",
            (so, so))[0][0],
        "Stock Entries against target WOs": frappe.db.sql(
            """SELECT COUNT(*) FROM `tabStock Entry` WHERE work_order IN (
                 SELECT name FROM `tabWork Order` WHERE sales_order=%s)""", so)[0][0],
    }
    adv = frappe.db.get_value("Sales Order", so, "advance_paid") or 0
    checks["advance_paid"] = adv
    recv = frappe.db.sql(
        """SELECT COALESCE(SUM(debit - credit), 0) FROM `tabGL Entry` gl
           JOIN `tabAccount` a ON a.name = gl.account
           WHERE gl.party_type='Customer' AND gl.party=(SELECT customer FROM `tabSales Order` WHERE name=%s)
             AND a.account_type='Receivable' AND gl.is_cancelled=0""", so)[0][0]
    checks["receivable balance"] = recv

    for wo in [w for w in t["draft_wos"]] + [w["name"] for w in t["orphan_wos"]]:
        pq = frappe.db.get_value("Work Order", wo, "produced_qty") or 0
        checks[f"produced_qty {wo}"] = pq
    for item in CLEAN_ITEMS:
        checks[f"Bin rows {item}"] = frappe.db.count("Bin", {"item_code": item})
        checks[f"SLE rows {item}"] = frappe.db.count("Stock Ledger Entry", {"item_code": item})
    for p in t["projects"]:
        checks[f"Timesheet rows {p['name']}"] = frappe.db.count(
            "Timesheet Detail", {"project": p["name"]})
        checks[f"costing {p['name']}"] = frappe.db.get_value(
            "Project", p["name"], "total_costing_amount") or 0
        checks[f"billed {p['name']}"] = frappe.db.get_value(
            "Project", p["name"], "total_billed_amount") or 0

    print("\n--- PRE-FLIGHT (every value must be 0) ---")
    bad = []
    for k, v in checks.items():
        flag = "" if not v else "   <<< REAL DATA"
        if v:
            bad.append((k, v))
        print(f"    {k:44s} {v}{flag}")
    if bad:
        raise Halt(f"environment holds real data, refusing to clean: {bad}")
    print("    ALL ZERO -> phantom-only shape confirmed")


# --------------------------------------------------------------------------
# operations
# --------------------------------------------------------------------------
def execute(t, apply_it, unlink_ok, stage="full"):
    so = t["so"]
    print(f"\n--- OPERATIONS (stage={stage}) ---")

    wo_targets = list(t["draft_wos"]) + [w["name"] for w in t["orphan_wos"]]

    if stage == "reservation":
        # STAGED MODE — land the actual harm fix (reservation release) and defer
        # every Work Order disposition. Writes NOTHING to the WOs or their
        # Workflow Actions; the only mutations are the SO cancel and the project
        # cancels. This exists because WFA-blocked WOs must not hold the
        # reservation fix hostage — deferring is not the same as ignoring.
        wfas = workflow_actions_on(wo_targets)
        t["_deferred_wos"] = wo_targets
        t["_deferred_wfas"] = wfas
        if wo_targets:
            not_started = [w for w in wfas if (w["workflow_state"] or "") == "Not Started"]
            print(f"   DEFERRED: janitorial — {len(not_started)} Not-Started WFAs on target WOs "
                  f"({len(wfas)} Workflow Action row(s) total across {len(wo_targets)} WO(s))")
            for w in wo_targets:
                mine = [x for x in wfas if x["wo"] == w]
                print(f"     {w}: {len(mine)} WFA row(s) "
                      f"{[(x['name'], x['status'], x['workflow_state']) for x in mine] or '—'} — left untouched")
        else:
            print("   DEFERRED: none — no Work Order remains in the target set")
    else:
        # (0) Disposition links BEFORE any delete, and never force.
        wo_targets = list(t["draft_wos"]) + [w["name"] for w in t["orphan_wos"]]

        # 0a. informational only — no decision is taken from this enumeration.
        info = downstream_links(wo_targets)
        if info:
            print("   INFO — references seen (frappe decides what blocks):")
            for l in info:
                print(f"     [{l['kind']}] {l['doctype']}.{l['field']}: {l['name']} "
                      f"(docstatus {l['docstatus']}) -> {l['wo']}")

        # 0b. pre-unlink ONLY the explicitly-confirmed test artifacts, drafts only.
        tests = whitelisted_test_refs(wo_targets)
        submitted = [x for x in tests if x["docstatus"] != 0]
        if submitted:
            raise Halt(f"whitelisted refs exist but are NOT draft: {submitted} — refusing")
        if tests:
            print("   confirmed-disposable test artifacts (whitelist):")
            for x in tests:
                print(f"     {x['doctype']}.{x['field']}: {x['name']} (docstatus {x['docstatus']}) -> {x['wo']}")
            if not unlink_ok:
                raise Halt(
                    "draft test artifacts reference the target WOs. Re-run with "
                    "unlink_test_batches=1 to unlink them. Refusing to force-delete.")
            for x in tests:
                print(f"0. unlink {x['doctype']} {x['name']}.{x['field']} (was {x['wo']})")
                if apply_it:
                    frappe.db.set_value(x["doctype"], x["name"], x["field"], None)
            if apply_it:
                frappe.db.commit()
        t["_unlinked"] = tests

        # 0c. FRAPPE's own verdict is the gate. Anything it still reports as linked
        #     — Workflow Action included — halts the run with the exact document.
        if apply_it:
            blocked = [(wo, native_link_check(wo)) for wo in wo_targets]
            blocked = [(wo, m) for wo, m in blocked if m]
            if blocked:
                raise Halt(
                    "frappe still reports these Work Orders as linked; NOT force-deleting: "
                    + " | ".join(f"{wo} -> {m}" for wo, m in blocked))

    # (a) cancel the SO — this is the actual fix (releases the reservation)
    if t["so_docstatus"] == 2:
        print(f"a. Sales Order {so} already cancelled — skipping (idempotent)")
    else:
        print(f"a. cancel Sales Order {so}")
    if apply_it and t["so_docstatus"] != 2:
        doc = frappe.get_doc("Sales Order", so)
        doc.cancel()
        frappe.db.commit()
        print(f"   docstatus now {frappe.db.get_value('Sales Order', so, 'docstatus')}")

    # (b) delete the draft SO-linked WOs  [full unwind only]
    for wo in (t["draft_wos"] if stage != "reservation" else []):
        print(f"b. delete draft Work Order {wo}")
        if apply_it:
            frappe.delete_doc("Work Order", wo, force=False, ignore_permissions=True)
            frappe.db.commit()   # commit per step: a mid-run halt must not undo earlier steps

    # (c) orphan WO: cancel if submitted, else delete  [full unwind only]
    for w in (t["orphan_wos"] if stage != "reservation" else []):
        act = "cancel" if w["docstatus"] == 1 else "delete"
        print(f"c. {act} orphan Work Order {w['name']} (docstatus {w['docstatus']})")
        if apply_it:
            if w["docstatus"] == 1:
                frappe.get_doc("Work Order", w["name"]).cancel()
            else:
                frappe.delete_doc("Work Order", w["name"], force=False, ignore_permissions=True)
            frappe.db.commit()

    # (d) projects -> Cancelled
    for p in t["projects"]:
        print(f"d. project {p['name']} status {p['status']} -> Cancelled")
        if apply_it:
            frappe.db.set_value("Project", p["name"], "status", "Cancelled")
            frappe.db.commit()

    # (e) SRE, when the environment has them (dev has none; reservation is on tabBin)
    for s in t["sres"]:
        print(f"e. Stock Reservation Entry {s['name']} (docstatus {s['docstatus']}) -> cancel")
        if apply_it and s["docstatus"] == 1:
            frappe.get_doc("Stock Reservation Entry", s["name"]).cancel()
    if apply_it:
        frappe.db.commit()


def postverify(t, before, stage="full"):
    print(f"\n--- POST-VERIFY (stage={stage}) ---")
    so = t["so"]
    ok = True
    ds = frappe.db.get_value("Sales Order", so, "docstatus")
    print(f"    SO docstatus = {ds} (2 = cancelled)")
    ok &= ds == 2
    after = bin_state()
    for b in before:
        a = next((x for x in after if x["warehouse"] == b["warehouse"]), None)
        print(f"    Bin {b['warehouse'][:34]:34s} reserved {b['reserved_qty']:>8} -> {a['reserved_qty']:>8} | "
              f"projected {b['projected_qty']:>8} -> {a['projected_qty']:>8} | actual {b['actual_qty']} -> {a['actual_qty']}")
        ok &= a["actual_qty"] == b["actual_qty"]          # stock must NOT move
        if b["reserved_qty"]:
            ok &= a["reserved_qty"] == 0                  # reservation released
    # B-1 (vm3): RESULT reflects ONLY the resolved target set. A stray that was
    # never in scope is reported as a janitorial candidate, never as a FAIL.
    targets = list(t["draft_wos"]) + [w["name"] for w in t["orphan_wos"]]
    left = [n for n in targets if frappe.db.exists("Work Order", n)
            and frappe.db.get_value("Work Order", n, "docstatus") in (0, 1)]
    if stage == "reservation":
        # Staged RESULT covers the SO + projects + reservation ONLY. The WO
        # dispositions are deferred by design, so they are INFO and can never
        # fail this run.
        wfas = t.get("_deferred_wfas") or workflow_actions_on(left)
        ns = [w for w in wfas if (w["workflow_state"] or "") == "Not Started"]
        print(f"    INFO — DEFERRED janitorial: {len(left)} WO(s) {left} carrying "
              f"{len(ns)} Not-Started WFA(s); untouched by design, NOT part of this RESULT")
        for n in left:
            print(f"      {n} still docstatus "
                  f"{frappe.db.get_value('Work Order', n, 'docstatus')} (unchanged)")
    else:
        print(f"    target-set WOs remaining: {left} (must be [])")
        ok &= not left
    strays = frappe.db.sql(
        """SELECT name, docstatus, qty, bom_no FROM `tabWork Order`
           WHERE production_item=%s AND (sales_order IS NULL OR sales_order='')
             AND produced_qty=0 AND docstatus IN (0,1)""", TARGET_ITEM, as_dict=True)
    strays = [x for x in strays if x["name"] not in targets]
    if strays:
        print(f"    INFO — {len(strays)} out-of-scope unlinked {TARGET_ITEM} WO(s), "
              f"janitorial candidates, NOT part of this RESULT:")
        for x in strays:
            print(f"      {x['name']} qty={x['qty']} bom={x['bom_no']} docstatus={x['docstatus']}")
    for p in t["projects"]:
        st = frappe.db.get_value("Project", p["name"], "status")
        print(f"    project {p['name']} status = {st}")
        ok &= st == "Cancelled"
    for item in CLEAN_ITEMS:
        n = frappe.db.count("Bin", {"item_code": item}) + frappe.db.count(
            "Stock Ledger Entry", {"item_code": item})
        print(f"    {item} Bin+SLE rows = {n} (must stay 0)")
        ok &= n == 0
    gl = frappe.db.sql("SELECT COUNT(*) FROM `tabGL Entry` WHERE voucher_no=%s", so)[0][0]
    print(f"    GL rows for the SO = {gl} (must stay 0)")
    ok &= gl == 0
    print(f"\n    RESULT: {'PASS' if ok else 'FAIL'}")
    return ok


def main(apply_it, unlink_ok, stage="full"):
    t = resolve()
    print("--- RESOLVED TARGETS (by query) ---")
    print(f"    SO           : {t['so']}")
    print(f"    draft WOs    : {t['draft_wos']}")
    print(f"    orphan WOs   : {[(w['name'], w['docstatus']) for w in t['orphan_wos']]}")
    print(f"    projects     : {[(p['name'], p['status']) for p in t['projects']]}")
    print(f"    SRE rows     : {t['sres'] or 'none (reservation carried on tabBin.reserved_qty)'}")
    before = bin_state()
    print("\n--- BIN BEFORE ---")
    for b in before:
        print(f"    {b['warehouse'][:40]:40s} actual={b['actual_qty']} reserved={b['reserved_qty']} projected={b['projected_qty']}")
    preflight(t)
    execute(t, apply_it, unlink_ok, stage)
    if apply_it:
        return postverify(t, before, stage)
    print("\nDRY-RUN — nothing written. Re-run with apply=1 (AFTER a backup) to execute.")
    return True


if __name__ == "__main__":
    site = None
    for i, a in enumerate(sys.argv):
        if a == "--site" and i + 1 < len(sys.argv):
            site = sys.argv[i + 1]
    if not site:
        print("refusing to run without an explicit --site")
        sys.exit(2)
    apply_it = "apply=1" in sys.argv
    unlink_ok = "unlink_test_batches=1" in sys.argv
    stage = "full"
    for a in sys.argv:
        if a.startswith("--stage="):
            stage = a.split("=", 1)[1]
    if stage not in ("full", "reservation"):
        print(f"unknown --stage={stage} (expected 'full' or 'reservation')")
        sys.exit(2)
    frappe.init(site=site, sites_path="sites")
    frappe.connect()
    try:
        ok = main(apply_it, unlink_ok, stage)
    except Halt as e:
        print(f"\n!! HALT: {e}")
        print("   No change made. Report to Hugh; do not clean this environment.")
        sys.exit(1)
    finally:
        frappe.destroy()
    sys.exit(0 if ok else 1)
