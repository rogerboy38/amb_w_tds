"""Rename TDS Settings.cav_block_on_mismatch -> css_block_on_mismatch.

Companion to amb_w_spc v15_4_0 rename of Customer Acceptable Value (CAV)
DocType -> Customer-Specific Specification (CSS). Field carries the same
semantic; rename keeps naming aligned with the doctype rename.

Idempotent + partial-failure safe: explicit NEW-row pre-check (tabSingles
has no UNIQUE constraint on (doctype, field) so ON DUPLICATE KEY UPDATE
would have no key to fire on; we check explicitly instead). OLD row
delete is conditional on existence via the "if not old: return" guard.

Rollback (if needed post vpt-docker failure):
    UPDATE `tabSingles` SET field='cav_block_on_mismatch'
        WHERE doctype='TDS Settings' AND field='css_block_on_mismatch';
or, equivalently, deploy a reverse-patch with the OLD/NEW swapped.

Brown-field VM3: this patch runs and migrates the existing tabSingles row.
Fresh-install vpt-docker: no tabSingles row exists yet; patch no-ops at
the "if not old: return" guard; schema_sync then creates the column from
the updated tds_settings.json fieldname (css_block_on_mismatch) directly.

Pre-flight discovery on VM3 (2026-06-03): frappe.db.sql parameter
binding requires a tuple/list, not a scalar — `(value,)` not `value`.
A scalar was silently no-op'd. Fixed by passing the explicit tuple.
"""
import frappe


def execute():
    if not frappe.db.table_exists("tabSingles"):
        return

    old = frappe.db.sql("""
        SELECT value FROM `tabSingles`
        WHERE doctype='TDS Settings' AND field='cav_block_on_mismatch'
    """, as_dict=True)

    if not old:
        return  # fresh install or already migrated

    # Defensive: if NEW already exists (partial prior run), skip INSERT and
    # just do the DELETE. tabSingles has no UNIQUE constraint on (doctype,
    # field), so a blind INSERT could create duplicate NEW rows on re-run.
    new_exists = frappe.db.sql("""
        SELECT 1 FROM `tabSingles`
        WHERE doctype='TDS Settings' AND field='css_block_on_mismatch'
    """)

    if not new_exists:
        # Parameter binding: tuple, not scalar. Scalar silently no-ops.
        frappe.db.sql("""
            INSERT INTO `tabSingles` (doctype, field, value)
            VALUES ('TDS Settings', 'css_block_on_mismatch', %s)
        """, (old[0].value,))

    frappe.db.sql("""
        DELETE FROM `tabSingles`
        WHERE doctype='TDS Settings' AND field='cav_block_on_mismatch'
    """)

    frappe.db.commit()
