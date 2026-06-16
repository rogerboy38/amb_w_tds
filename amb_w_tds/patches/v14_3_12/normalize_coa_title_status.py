"""
T139 / v14_3_12 — Normalize stale status on COA title (section-header) rows.

Place at:
  amb_w_tds/amb_w_tds/patches/v14_3_12/normalize_coa_title_status.py
  (create amb_w_tds/amb_w_tds/patches/v14_3_12/__init__.py too)

Register in patches.txt under [post_model_sync]:
  amb_w_tds.patches.v14_3_12.normalize_coa_title_status

WHY:
Title rows (custom_is_title_row=1) must never carry a Pass/Fail/Pending status.
Older code left stale statuses on them, which (a) showed a spurious 'Fail' on a
section header ("Specification ... Fail") and (b) inflated get_test_summary
("Validated 20 tests: 22 passed, 1 failed, 1 pending"). evaluate_overall_result
now resets them to 'Title' on every validate; this patch fixes the rows already
stored in the DB so existing COAs (including the ~5,850 migrated certs) read
correctly WITHOUT needing a re-validate.

Shared child doctype 'COA Quality Test Parameter' is used by both COA AMB and
COA AMB2, so a single UPDATE covers both parents.

frappe.db.sql (not ORM): this is a set-based bulk normalization over tens of
thousands of child rows; per-doc ORM load/save would be needlessly slow and
would bump modified timestamps on the parent COAs. Direct UPDATE is the right
tool and touches only the child status column.

Idempotent: only rows whose status isn't already 'Title' are updated; re-runs
affect 0 rows.
"""

import frappe


def execute():
    before = frappe.db.count(
        "COA Quality Test Parameter",
        {"custom_is_title_row": 1, "status": ["!=", "Title"]},
    )

    frappe.db.sql(
        """
        UPDATE `tabCOA Quality Test Parameter`
        SET `status` = 'Title'
        WHERE `custom_is_title_row` = 1
          AND (`status` IS NULL OR `status` != 'Title')
        """
    )
    frappe.db.commit()

    remaining = frappe.db.count(
        "COA Quality Test Parameter",
        {"custom_is_title_row": 1, "status": ["!=", "Title"]},
    )
    print(f"[v14_3_12] title rows normalized to 'Title': {before} updated; remaining non-Title title rows: {remaining}")
    # expected: remaining == 0
