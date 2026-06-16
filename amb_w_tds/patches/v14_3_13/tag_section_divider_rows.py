"""
T140-B / v14_3_13 — Tag untagged COA section-divider rows.

Place at:  amb_w_tds/amb_w_tds/patches/v14_3_13/tag_section_divider_rows.py
           (+ amb_w_tds/amb_w_tds/patches/v14_3_13/__init__.py)
Register in PACKAGE patches.txt under [post_model_sync]:
           amb_w_tds.patches.v14_3_13.tag_section_divider_rows

WHY: some section dividers (e.g. "Physicochemical") were stored WITHOUT
custom_is_title_row but with the placeholder acceptance "Specification", so the
server scored them as tests (inflated counts, spurious status). The controllers now
treat such rows as headers at runtime (_is_header_row), but this patch fixes the
STORED data so existing COAs — including the ~5,850 migrated certs — read correctly
without a per-doc revalidation: flag them custom_is_title_row=1 and set status='Title'.

Shared child doctype 'COA Quality Test Parameter' (both COA AMB + COA AMB2).
Set-based UPDATE (not ORM): tens of thousands of child rows; per-doc load/save would
be needlessly slow and would bump parent modified timestamps. Touches only the two
columns on divider rows.

Idempotent: only rows not already flagged are updated; re-runs affect 0 rows.
"""

import frappe


def execute():
    before = frappe.db.sql(
        """
        SELECT COUNT(*) FROM `tabCOA Quality Test Parameter`
        WHERE (custom_is_title_row IS NULL OR custom_is_title_row = 0)
          AND LOWER(TRIM(COALESCE(NULLIF(TRIM(`value`), ''), `specification`, ''))) = 'specification'
        """
    )[0][0]

    frappe.db.sql(
        """
        UPDATE `tabCOA Quality Test Parameter`
        SET `custom_is_title_row` = 1, `status` = 'Title'
        WHERE (custom_is_title_row IS NULL OR custom_is_title_row = 0)
          AND LOWER(TRIM(COALESCE(NULLIF(TRIM(`value`), ''), `specification`, ''))) = 'specification'
        """
    )
    frappe.db.commit()

    remaining = frappe.db.sql(
        """
        SELECT COUNT(*) FROM `tabCOA Quality Test Parameter`
        WHERE (custom_is_title_row IS NULL OR custom_is_title_row = 0)
          AND LOWER(TRIM(COALESCE(NULLIF(TRIM(`value`), ''), `specification`, ''))) = 'specification'
        """
    )[0][0]
    print(f"[v14_3_13] section dividers tagged custom_is_title_row=1: {before} updated; remaining untagged: {remaining}")
    # expected: remaining == 0
