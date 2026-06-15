"""
T137 / v14_3_11 — Decommission legacy COA AMB Client Scripts.

Place at: amb_w_tds/amb_w_tds/patches/v14_3_11/decommission_legacy_coa_client_scripts.py
(create amb_w_tds/amb_w_tds/patches/v14_3_11/__init__.py too)

Register in patches.txt under [post_model_sync]:
    amb_w_tds.patches.v14_3_11.decommission_legacy_coa_client_scripts

WHY a patch (not just removing from the fixture): fixtures never DELETE records
that were removed from the fixture file, so sites that already have these legacy
Client Scripts (vpt, vpp) need an explicit delete. Removing them from the fixture
(via re-export after this patch runs on the dev site) stops fixture-sync from
re-creating them; this patch removes the ones that already exist elsewhere.

The COA audit logic now lives in app code (public/js/coa_common.js, loaded via
doctype_js for COA AMB + COA AMB2), and the doctype controllers already handle
TDS load + validation. So all of the scripts below are obsolete.

KEEP: `custom_naming_series` (naming logic; not superseded by code).
Idempotent: only deletes names that still exist AND target a COA doctype.
"""

import frappe

OBSOLETE = [
    "load_tds_parameters_1",              # buggy audit_tds_compliance (false-FAIL) — superseded by coa_common.js
    "custom_naming_series_1",             # exact duplicate of custom_naming_series
    "hello_world_test",                   # test cruft
    "load_tds_parameters_best_practice",  # superseded loader
    "load_tds_parameters",                # superseded loader (Client Script; the Server Script of same name is kept)
    "Load TDS Parameters",                # superseded loader
    "coa_amb_validate",                   # interim T130 hotfix — audit now in code (coa_common.js)
]

KEEP = {"custom_naming_series"}
COA_DTS = {"COA AMB", "COA AMB2"}


def execute():
    deleted, missing, skipped = [], [], []
    for name in OBSOLETE:
        if name in KEEP:
            continue
        if not frappe.db.exists("Client Script", name):
            missing.append(name)
            continue
        dt = frappe.db.get_value("Client Script", name, "dt")
        if dt in COA_DTS:
            frappe.delete_doc("Client Script", name, force=True,
                              ignore_missing=True, ignore_permissions=True)
            deleted.append(name)
        else:
            skipped.append((name, dt))

    frappe.db.commit()
    print(f"[v14_3_11] deleted: {deleted}")
    if missing:
        print(f"[v14_3_11] already absent: {missing}")
    if skipped:
        print(f"[v14_3_11] SKIPPED (dt not COA): {skipped}")
    print("[v14_3_11] enabled COA Client Scripts remaining:",
          frappe.get_all("Client Script", filters={"dt": ["in", list(COA_DTS)], "enabled": 1}, pluck="name"))
