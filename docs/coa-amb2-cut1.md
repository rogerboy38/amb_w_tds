# COA AMB2, Cut 1 (13.12.0)

Three defect-level fixes so the internal certificate (COA AMB2) is usable by Quality before the first LORAND run.

## Permissions
COA AMB2 is governed by **Custom DocPerm rows** on every site (the three non-test rows equal the DocType JSON).
Frappe does not apply a standard DocType's JSON permissions while Custom DocPerm rows exist, so the new rows ship in
`amb_w_tds/fixtures/custom_docperm.json` (imported by every migrate; hooks.py `or_filters`: parent = BOM Formula, or
name in the six COA AMB2 rows, so a re-export drags in nothing else). Six roles are added, one row each, exactly as in the table below. Quality User needs `submit` because the workflow's "Submit for
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

## The six rows shipped
One row per role (COA AMB's duplicate rows are not copied: Quality User and Stock User each have two differing rows
there, and ship as one row holding their union). A cell is the flag value; the flags `select`, `import`, `mask`,
`impersonate` and `if_owner` are 0 and the permission level is 0 on every row. A test compares this table with
`fixtures/custom_docperm.json`.

| role | read | write | create | delete | submit | cancel | amend | report | export | print | email | share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Quality Engineer | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| Quality User | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 |
| RND Manager | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Manufacturing User | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 |
| Sales Manager CRM | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 |
| Stock User | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 |

# COA AMB2, Cut 2a (13.12.1)

## Batch step on submit
`COAAMB2.update_batch_status()` (called by `on_submit`) wrote `Batch AMB.coa_reference`, which is a Link to COA AMB: Frappe's
link validation refused a COA AMB2 name, and `quality_status` was set to "Pass" (its options are Pending / Passed / Failed /
Hold). The call has never succeeded and logged "COA AMB2 - Batch Update" on every submit that carried a `batch_reference`.
Now `_batch_link_holds_this_doctype()` reads the Link field's options from the meta; when it does not point at COA AMB2 the
write is skipped (one Info comment on the COA AMB2), and `quality_status` is never written. The cancel path, `coa_amb.py` and
the other DocTypes are untouched (the same code, with the same defects, remains in `coa_amb.py` at 556, 628, 637, 663, 679
and in `coa_amb2.py` at the cancel call and at the `batch.last_coa_date` line). Cut 2b decides the real Batch AMB link.
