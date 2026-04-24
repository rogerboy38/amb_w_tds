# -*- coding: utf-8 -*-
# ==========================================================
# amb_w_tds.patches.v13_6.p3_kill_patches.kill_migrated_server_scripts
# ==========================================================
# V13.6.0 P3 — Server Script migration kill-patch.
# Deletes Server Script DB rows whose logic has been migrated
# into in-code hooks (doctype_events / api / override_whitelisted_methods)
# OR archived verbatim under docs/legacy/.
#
# Runs automatically on `bench migrate` (listed in patches.txt).
# Pre-kill backups live under /tmp/p3-artifacts/ (full Frappe
# backup + server_scripts_full_dump.json + per-row body files).
# ==========================================================
import frappe


def execute():
    scripts_to_delete = [
        "test_wordpress_api",
        "Clear WordPress Post IDs",
        "fix_invoice_debit_to",
        "Fix SAT CFDI Permissions",
        "coa_amb",
        "coa_amb_tds_loader",
        "coa_amb_load_tds_parameters",
        "coa_amb_api",
        "test_script",
        "Triggers Script",
        "batch_naming_amb",
        "Fix CFDI Use Permission - Sales Invoice",
        "coa_amb_1",
        "coa_amb_tds_loader_1",
        "coa_amb_load_tds_parameters_1",
        "Force Customer Specific Account",
        "Set Customer Invoice Currency from Sales Order",
        "BOM Creator - Calculate Total Cost",
        "Fetch TDS Version Validation",
        "QuotationItemEscalated",
        "Quotation Item Escalated Server Script",
        "load_tds_parameters",
    ]

    deleted = 0
    missing = 0
    failed  = 0
    for script_name in scripts_to_delete:
        try:
            frappe.delete_doc("Server Script", script_name, force=True)
            frappe.db.commit()
            print(f"OK     deleted  : {script_name}")
            deleted += 1
        except frappe.DoesNotExistError:
            print(f"SKIP   not found : {script_name}")
            missing += 1
        except Exception as e:
            print(f"FAIL             : {script_name} -> {e}")
            failed += 1

    total = len(scripts_to_delete)
    print(f"P3 kill-patch (amb_w_tds): total={total} deleted={deleted} missing={missing} failed={failed}")
