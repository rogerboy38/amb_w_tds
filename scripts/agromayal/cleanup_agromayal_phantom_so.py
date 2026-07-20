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


# Frappe removes this chatter itself when a document is deleted, so a hit here
# is reported but must not block the run (blocking on Comment would refuse
# everywhere — 43 Comment rows already point at Work Orders on dev).
SYSTEM_CHATTER = {
    "Comment", "Version", "Activity Log", "Access Log", "View Log", "Route History",
    "Document Follow", "Email Queue", "Email Queue Recipient", "Notification Log",
    "Workflow Action", "Workflow Action Permitted Role", "ToDo", "Assignment Rule",
    "Energy Point Log", "Document Share Key", "Notification Settings",
}


def _link_field_map():
    """Every field that can point at a Work Order: static Link AND Dynamic Link.

    A-1 (vm3): the first version only scanned fieldtype='Link'. The bench has
    133 Dynamic Link fields, so a doc referencing a Work Order via
    reference_doctype='Work Order' + reference_name was invisible to the guard
    and would reproduce the same LinkExistsError the guard exists to prevent.
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
            elif r.options:  # options names the sibling field holding the doctype
                dynamic.append((r.dt, r.fieldname, r.options))
    return sorted(set(static)), sorted(set(dynamic))


def downstream_links(wo_names):
    """Docs outside the target set that point at these Work Orders.

    Found the hard way on dev: the orphan WO carried two draft Batch AMB records
    on `work_order_ref`, so the delete threw LinkExistsError mid-run. Prod will
    have the same shape with different names, so the artifact has to see them —
    through static Link fields AND Dynamic Link pairs.
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
        for h in hits:
            out.append({"doctype": dt, "field": fn, "kind": "Link",
                        "chatter": dt in SYSTEM_CHATTER, **h})
    for dt, fn, optf in dynamic:
        try:
            hits = frappe.db.sql(
                f"""SELECT name, docstatus, `{fn}` AS wo FROM `tab{dt}`
                    WHERE `{optf}`='Work Order' AND `{fn}` IN ({ph})""",
                tuple(wo_names), as_dict=True)
        except Exception:
            continue
        for h in hits:
            out.append({"doctype": dt, "field": fn, "kind": f"Dynamic Link via {optf}",
                        "chatter": dt in SYSTEM_CHATTER, **h})
    return out


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
def execute(t, apply_it, unlink_ok):
    so = t["so"]
    print("\n--- OPERATIONS ---")

    # (0) downstream links must be dispositioned BEFORE any delete, never forced.
    wo_targets = list(t["draft_wos"]) + [w["name"] for w in t["orphan_wos"]]
    links = downstream_links(wo_targets)
    chatter = [l for l in links if l["chatter"]]
    links = [l for l in links if not l["chatter"]]
    if chatter:
        print(f"   {len(chatter)} system-chatter reference(s) (auto-removed by frappe, not blocking): "
              f"{sorted({c['doctype'] for c in chatter})}")
    if links:
        print("   downstream links found (outside the target set):")
        for l in links:
            print(f"     [{l['kind']}] {l['doctype']}.{l['field']}: {l['name']} "
                  f"(docstatus {l['docstatus']}) -> {l['wo']}")
        submitted = [l for l in links if l["docstatus"] == 1]
        if submitted:
            raise Halt(f"downstream SUBMITTED docs link the target WOs: {submitted}")
        if not unlink_ok:
            raise Halt(
                "draft downstream docs link the target WOs. Confirm they are disposable "
                "(on dev these were test Batch AMB records, per Hugh 2026-07-20) and re-run "
                "with unlink_test_batches=1. Refusing to force-delete.")
        for l in links:
            print(f"0. unlink {l['doctype']} {l['name']}.{l['field']} (was {l['wo']})")
            if apply_it:
                frappe.db.set_value(l["doctype"], l["name"], l["field"], None)
        if apply_it:
            frappe.db.commit()
    t["_unlinked"] = links

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

    # (b) delete the draft SO-linked WOs
    for wo in t["draft_wos"]:
        print(f"b. delete draft Work Order {wo}")
        if apply_it:
            frappe.delete_doc("Work Order", wo, force=False, ignore_permissions=True)
            frappe.db.commit()   # commit per step: a mid-run halt must not undo earlier steps

    # (c) orphan WO: cancel if submitted, else delete
    for w in t["orphan_wos"]:
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


def postverify(t, before):
    print("\n--- POST-VERIFY ---")
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
    left = frappe.db.sql(
        """SELECT name, docstatus FROM `tabWork Order`
           WHERE (sales_order=%s AND docstatus=0)
              OR (production_item=%s AND (sales_order IS NULL OR sales_order='')
                  AND produced_qty=0 AND docstatus IN (0,1))""",
        (so, TARGET_ITEM), as_dict=True)
    print(f"    phantom WOs remaining: {left}")
    ok &= not left
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


def main(apply_it, unlink_ok):
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
    execute(t, apply_it, unlink_ok)
    if apply_it:
        return postverify(t, before)
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
    frappe.init(site=site, sites_path="sites")
    frappe.connect()
    try:
        ok = main(apply_it, unlink_ok)
    except Halt as e:
        print(f"\n!! HALT: {e}")
        print("   No change made. Report to Hugh; do not clean this environment.")
        sys.exit(1)
    finally:
        frappe.destroy()
    sys.exit(0 if ok else 1)
