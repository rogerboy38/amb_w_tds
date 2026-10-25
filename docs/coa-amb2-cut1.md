# COA AMB2, Cut 1 (13.12.0)

Three defect-level fixes so the internal certificate (COA AMB2) is usable by Quality before the first LORAND run.

## Permissions
COA AMB2 is governed by **Custom DocPerm rows** on every site (the three non-test rows equal the DocType JSON).
Frappe does not apply a standard DocType's JSON permissions while Custom DocPerm rows exist, so the new rows ship in
`amb_w_tds/fixtures/custom_docperm.json` (imported by every migrate; hooks.py `or_filters`: parent = BOM Formula, or
name in the six COA AMB2 rows, so a re-export drags in nothing else). Roles added: Quality User, Manufacturing User, RND Manager, Sales Manager CRM,
Stock User, Quality Engineer (read, write, create, report, print). Quality User needs `submit` because the workflow's "Submit for
Sales Approval" (Approved → Certificate Shared, docstatus 1) is allowed to that role.

## Submit email
`COAAMB2.notify_quality_team` → recipients from `_notification_recipients()` (enabled Quality Managers, owner,
`approved_by`; de-duplicated; never Administrator or Guest), link `/app/coa-amb2/<name>`.

## Gate
`BOM Formula._build_lots` collects `_skipped_no_coa`; `simulate_blend` shows `_skip_warning()` with
`frappe.msgprint(..., indicator="orange")` and returns `skipped_no_coa` and `warning`. The set of lines that feed the
blend is unchanged.

## Workflow
`submit_and_start_workflow` (COA AMB2) lives in `amb_w_tds/fixtures/workflow.json`, which every migrate re-imports
(delete and insert of the whole workflow document), so a fixture edit reaches every site without a patch. One transition
row is added: Approved -> "Submit for Sales Approval" -> Certificate Shared, allowed role **Quality Manager** (the Quality
User row stays). The other seven transitions, the seven states and the COA AMB twin (`submit_and_start_workflow_1`) are
unchanged. Existing COA AMB2 records keep their `workflow_state` (it is a field on the record, not on the workflow).

## Error Log
Three rows were written by every COA AMB2 submit, from `coa_amb2.py` only (the same code also sits in `coa_amb.py`,
which this release does not touch): the Item fields `last_coa_*` that no site has (now written only if the Item meta has
them), the `Quality Audit` DocType that Frappe 16 does not ship (step skipped when absent), and the "Notification sent"
comment of type `Email` (now `Info`). Other failures are still logged.
