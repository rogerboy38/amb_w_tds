# COA AMB2, Cut 1 (13.12.0)

Three defect-level fixes so the internal certificate (COA AMB2) is usable by Quality before the first LORAND run.

## Permissions
COA AMB2 is governed by **Custom DocPerm rows** on every site (the three non-test rows equal the DocType JSON).
Frappe does not apply a standard DocType's JSON permissions while Custom DocPerm rows exist, so the new rows ship in
`amb_w_tds/fixtures/custom_docperm.json` (imported by every migrate; hooks.py `or_filters`: parent = BOM Formula, or
name in the six COA AMB2 rows, so a re-export drags in nothing else). Roles added: Quality User, Manufacturing User, RND Manager, Sales Manager CRM,
Stock User, Quality Engineer (read, write, create). Quality User needs `submit` because the workflow's "Submit for
Sales Approval" (Approved → Certificate Shared, docstatus 1) is allowed to that role.

## Submit email
`COAAMB2.notify_quality_team` → recipients from `_notification_recipients()` (enabled Quality Managers, owner,
`approved_by`; de-duplicated; never Administrator or Guest), link `/app/coa-amb2/<name>`.

## Gate
`BOM Formula._build_lots` collects `_skipped_no_coa`; `simulate_blend` shows `_skip_warning()` with
`frappe.msgprint(..., indicator="orange")` and returns `skipped_no_coa` and `warning`. The set of lines that feed the
blend is unchanged.
