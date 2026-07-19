"""F-S12-2 item 3: collapse Module Def casing split onto canonical 'Amb W Tds'.

DB truth before this patch (vpt 2026-07-19): two Module Def rows for app amb_w_tds —
'Amb W Tds' (canonical, matches modules.txt) and 'AMB_W_TDS' (orphan, no file source) —
plus module values stored with app-name casing ('amb_w_tds') on rows shipped by
workspace json. Data columns compare case-insensitively, so lookups worked; the split
is a literal-casing/orphan-row problem, which is why every comparison here is BINARY.
Idempotent: re-running is a no-op once normalized.
"""
import frappe

CANON = "Amb W Tds"
APP = "amb_w_tds"
TABLES = ["DocType", "Report", "Page", "Print Format", "Notification",
          "Dashboard Chart", "Number Card", "Workspace", "Custom Field",
          "Property Setter", "Server Script", "Client Script"]


def execute():
    if not frappe.db.exists("Module Def", CANON):
        frappe.get_doc({"doctype": "Module Def", "module_name": CANON,
                        "app_name": APP, "custom": 0}).insert(ignore_permissions=True)

    for dt in TABLES:
        try:
            frappe.db.sql(
                """update `tab{0}` set module=%s
                   where module is not null
                     and lower(module) in (%s, %s)
                     and BINARY module != %s""".format(dt),
                (CANON, CANON.lower(), APP, CANON))
        except Exception:
            # table absent on this site (app subset installs) — nothing to normalize
            continue

    for row in frappe.db.sql(
            "select name from `tabModule Def` where lower(name) in (%s, %s) "
            "and BINARY name != %s", (CANON.lower(), APP, CANON)):
        frappe.delete_doc("Module Def", row[0], force=True,
                          ignore_permissions=True, delete_permanently=True)

    frappe.clear_cache()
