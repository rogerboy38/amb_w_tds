# Changelog

## 13.12.20 — 2026-11

**Code only (`api/certificate.py`, `certificate_rules.py`).** No DocType JSON, fixture, patch or hook: **no `bench migrate` for this version by itself**; backend restart (web + workers) + `bench clear-cache`. Deploy with 13.12.16–13.12.19 and amb_w_spc's pair, as before.

### The certificate type follows the Item's "Allow Sales" check (TASKS-385, decision 320)
- **The rule.** `certificate_type_for_item(item)` reads the Item's own `is_sales_item` (label "Allow Sales"): on → COA AMB (customer certificate), off → COA AMB2 (internal certificate). It reads that Item's row only, so a variant's own value decides, not its template's. No item, or an Item that does not exist → no type, as before.
- **Removed.** `CERTIFICATE_TYPE_BY_ITEM_GROUP` (it shipped empty) and the walk up the Item Groups. The function keeps its name and place; its three callers are unchanged.
- **Messages.** The "Certificate" action refuses only a product that is not an Item, and says so: the type follows the "Allow Sales" check on the Item. The wrong-type refusal names the check and its value on that Item, so the user knows where to look.
- **When the type is judged is unchanged:** on a new certificate and in the save that changes its product. A stored certificate whose product stays is not judged again; changing the check on an Item later does not stop the workflow of certificates already made.
- Tests: `tests/test_certificate_links_b2.py` (the tests that pinned the empty table are replaced; a test reads ERPNext's own Item DocType for the label).
## 13.12.19 — 2026-11

**Code and two DocType JSONs (`coa_amb.json`, `coa_amb2.json`: `approved_by` and `approval_date` marked "no copy").** **`bench migrate` is needed** (the two DocTypes are synced; no new column), then a backend restart (web + workers) and `bench --site <site> clear-cache`. No workflow fixture, no fixture, no patch, no data change. Deploy with amb_w_spc, as 13.12.18.

### Findings of the review of 13.12.16–13.12.18 (TASKS-384 review, findings 1, 2, 4, 6 and the missing test)
- **A COA AMB is submitted only from the stored state Approved (finding 1, blocker).** A Draft, Validated or Pending Supervisor COA AMB could be submitted directly (the form's Submit, `frappe.client.submit`, a save carrying docstatus 1): the lock looked only at certificates that were Approved, and the framework named the submitted document by the first submitted state of the workflow, "Certificate Shared". Such a certificate then stood for its lot, so one Quality Manager could make a second certificate, submit it alone, Reject the properly approved certificate of a Failed lot, and the lot became Passed. Now every move of a COA AMB from docstatus 0 to 1 is refused unless the state **in the database** is Approved (the workflow's own "Submit for Sales Approval"), for every role, with its own message, in `before_validate` (which the framework runs also for a save that skips `validate`) and again in `validate`. A new document is never inserted as submitted. A certificate that is already submitted is not touched. COA AMB2 is unchanged (nothing of that type is submitted).
- **A new certificate carries no approver.** On a new certificate that is not becoming Approved the server empties `approved_by` and `approval_date`, whatever the caller sent; `approved_by`, `approval_date` (and, already, `filled_by`) are marked "no copy", so a Duplicate does not carry them. The form's **Amend copies every field, the "no copy" ones included**, so for an amendment it is the server that empties them. The amendment of a cancelled COA AMB is a new draft: no approver, its amender as `filled_by` (the rows are inserted by that person), approval by another person, and only then the share.
- **Which certificate still stands for a lot.** When a certificate is rejected or cancelled, another certificate of the lot counts only if, beside its state, docstatus and result, it records who approved it and who filled it and the two differ. **Effect to know:** a certificate approved or shared before 13.12.16 has no `filled_by` and does not stand; when the other certificate of its lot is taken back, the lot goes to Pending and not to that older certificate's status.
- **What counts as a change of the results (finding 2).** `filled_by` followed the `result` cell only, so an approver could change a limit, approve the certificate as Pass and not be its filler. A change of any field of a test row that the evaluation reads now counts: `result`, `specification`, `value`, `min_value`, `max_value`, `numeric`, `formula_based_criteria`, `acceptance_formula`, `custom_is_title_row`, `parameter_name`; so does a row added or removed, with or without a result. The same rule holds for a row saved, inserted or deleted by itself, and for the share of an Approved COA AMB (nothing of this may change in that save). The same row read from the database and sent back by the form is not a change (text without the spaces around it, the limits as numbers, the checks as 0/1). **Effect to know:** whoever makes a certificate with rows is its `filled_by` from the first save, results or not; whoever fills the results after that replaces it.
- **No certificate for a record below the sub-lot (finding 6).** `make_certificate_for_lot` and the `validate` of both certificates (in the save that sets or changes the lot) refuse a lot record whose level is not 1 or 2, with a message that says to choose the lot or the sub-lot; an empty level is level 1. Both sets of the lot picker carry the same term. On a site whose Batch AMB has no `custom_batch_level` field nothing is read, refused or filtered. A stored certificate that already names a container is not judged again by its saves; its approval is refused by amb_w_spc, as before.
- **The refusal for a certificate with no recorded filler says what to do (finding 4, wording only).** A certificate filled before 13.12.16 has no `filled_by` and cannot be approved. The message now says so and says what works: saving it again unchanged records nobody; whoever fills the certificate changes a result and saves (to keep the same value: change it, save, set it back, save again); then another person approves. **No backfill and no bypass were added**; certificates already Approved before 13.12.18 still do not release their lot (a ruling is needed).
- **A test across the two apps.** `tests/test_lot_release_with_spc.py` runs this app's real path from a certificate's save to the lot against amb_w_spc's real `certificate_approved` and `certificate_withdrawn`, over a lot table in memory (amb_w_spc's own seam): an approval writes the lot, its sub-lot and its container; a Reject returns them to Pending; a Reject with a certificate that still stands gives them that one's status; a certificate no second person approved does not stand. Skipped when amb_w_spc is not importable; run with both apps on `PYTHONPATH`.
- Not changed: the classification table of `api/certificate.py` (still empty); how amb_w_spc is called and what happens when it is absent (finding 5: deploy the two apps together); the workflow fixtures.
- Tests: `tests/test_certificate_rules_b1.py` (the test that pinned the direct submit as allowed is replaced), `tests/test_certificate_links_b2.py`, `tests/test_release_at_approved_b3.py`, `tests/test_batch_picker_13_12_2.py`, `tests/test_lot_release_with_spc.py` (new).
## 13.12.18 — 2026-11

**Code only (`certificate_rules.py`, both controllers, `batch_picker.py`).** No DocType JSON, fixture, patch or hook of this app: **no `bench migrate` for this version by itself**; backend restart (web + workers) + `bench --site <site> clear-cache`. **It must be deployed together with the amb_w_spc version that has `amb_w_spc/sfc_manufacturing/lot_quality.py`** (`certificate_approved`, `certificate_withdrawn`): from this version on, the approval of a certificate that names a lot calls that module, and fails with a message when it is not there.

### The lot is released at "Approved" (TASKS-384 B3; decisions 303, 315)
- **Approved → the lot is written.** When the state of a COA AMB or a COA AMB2 becomes Approved, this app calls amb_w_spc's `certificate_approved(doctype, name, lot, result)` with the result derived in that save (Pass, Fail or Partial). amb_w_spc maps it and is the only writer of the lot's status.
- **Reject and Cancel → the release is taken back.** When an Approved certificate goes back to Draft, or a shared COA AMB is cancelled, this app calls `certificate_withdrawn(doctype, name, lot, standing)`. `standing` is another certificate of the same lot record, of either type, that still stands (Approved and not submitted, or a COA AMB that is Certificate Shared and not cancelled, with a result that maps); when several stand, the one approved last. With none, the lot goes back to Pending.
- **How.** Decided in `validate` (the state before the save against the state now), carried out in `on_update` (the cancel: `on_cancel`), after the certificate's own write and in the same transaction. **Nothing is caught around the call**: if the lot cannot be written, the approval fails and the user sees why. The other app is looked up at the moment of the call; this app still imports without it. A certificate that names no lot calls nothing.
- **Removed.** COA AMB's `update_batch_status`: at submit it wrote the certificate's own word ("Pass") into the lot's `quality_status`, with `coa_reference`, `coa_generated`, `last_coa_date` and `coa_details`, and at cancel "COA Cancelled", all inside a `try/except` that logged and went on. COA AMB2's `update_batch_status`, a guarded no-op, with `_batch_link_holds_this_doctype`, `BATCH_COA_FIELD` and their comments. This app writes no field of a lot any more.
- **Not changed, and said here on purpose:** the other three after-submit steps of COA AMB (`notify_quality_team`, `create_quality_audit`, `update_product_quality_status`) are exactly as they were and fail as before; they are a later task.
- **The lot picker of both certificate forms** also offers a record whose `status_source` is "Inherited" (a sub-lot under a released lot can still get its own certificate), beside Pending, Hold and not yet set. On a site whose Batch AMB has no `status_source` field the picker is what it was.
- Tests: `tests/test_release_at_approved_b3.py`; `tests/test_coa_amb2_cut2a.py` lost the eleven tests of the removed no-op and pins its absence; `tests/test_batch_picker_13_12_2.py` runs its cases as a site without the new field.
## 13.12.17 — 2026-11

**Code, two DocType JSONs (`coa_amb.json`, `coa_amb2.json`: new field `work_order`) and one fixture (`client_script.json`, one Client Script disabled).** **`bench migrate` is needed** (one new column on each certificate; the fixture), then a backend restart (web + workers) and `bench --site <site> clear-cache`. No workflow fixture, no patch, no data change. The other halves of this item are in amb_w_spc (the lot's `coa_amb2` field and the "Certificate" action on the lot) and in rnd_warehouse_management (the action on the Work Order).

### Certificate ↔ Work Order ↔ lot, and creation from a lot (TASKS-384 B2; decisions 312, 317)
- **`work_order`** (new, Link → Work Order, both certificates): written by the server on every save from the lot's `work_order_ref`; a lot without a Work Order leaves the field as it is. Read-only on the form once it has a value.
- **The product decides the type.** `amb_w_tds/api/certificate.py` has one function, `certificate_type_for_item`, with its classification table at the top: an item takes the certificate type of the nearest Item Group of its ancestry that the table names. **The table ships empty**: no rule separating finished from semi-finished products could be read from the code or the fixtures (the Item Groups named there class a product by its form, and a powder is both sold and used as an input). With the table empty every item is unclassed and nothing below refuses.
- **The wrong type is refused** by the certificate's `validate`, when the certificate is made and when its product changes, for a classed product only. A stored certificate whose product stays is not judged again.
- **`make_certificate_for_lot(lot)`** (whitelisted; called by the lot form and, through the lot, by the Work Order form): inserts a Draft certificate of the product's type with lot, Work Order, product and specification filled, and returns its DocType and name. The product is the specification's product when the lot names a specification, else the lot's item. An unclassed product is refused with a message; so is a lot with neither.
- **The customers list of a COA AMB is filled on the server** when the certificate is created (`before_insert`, any creation path), from the specification's customers table, else the Item's. A list that already has rows is left alone. The browser's own prefill is unchanged.
- **Repaired on the way.** The lot-change handler of both forms set two fields the certificate does not have (`production_date`, `batch_quantity`) and overwrote the product with the lot's item: it now shows the lot's Work Order, fills the product only when it is empty and says so when the two differ. On the server a difference between the lot's item and the product is shown once, not refused (the two sit at different levels of the Item tree on purpose). The Client Script `custom_naming_series`, which emptied the naming series of a new COA AMB, is disabled and its body removed.
- Not changed: the workflow fixtures; the lot picker; `sync_from_tds`.
- Tests: `tests/test_certificate_links_b2.py`.
## 13.12.16 — 2026-11

**Code, hooks and two DocType JSONs (`coa_amb.json`, `coa_amb2.json`: new field `filled_by`; `approved_by` and `approval_date` read-only).** **`bench migrate` is needed** (one new column on each certificate), then a backend restart (web + workers) and `bench --site <site> clear-cache` (the hooks are read from the cache). No workflow fixture, no patch, no data change.

### Lock and derive, on both certificates (TASKS-384 B1; decisions 303, 312, 313)
- **One vocabulary.** `amb_w_tds/quality_vocabulary.py` holds the lot status list, the certificate result list, the map Pass → Passed, Fail → Failed, Partial → Hold, and the status sources. `tests/test_quality_vocabulary.py` fails when a list drifts from the option lists of this app's DocTypes, and compares with amb_w_spc's module when that app can be imported.
- **COA AMB derives on every save.** Its `validate` returned before the evaluation for a Draft, so a typed result and compliance stayed. It now derives result, compliance, percentages, the failing names and each row's status from the rows on every save, as COA AMB2 does since 13.12.12; a row whose result was removed is Pending again; no rows gives "No Tests" with compliance Pending. The old comment feared a timeout: the evaluation is arithmetic over rows already in memory and makes no query. The row checks that refuse an out-of-range numeric result still run at submit only.
- **"Validate All Tests" says that it saved** (both certificates) and no longer catches the server's error: a refused save reaches the user as the server's message, instead of an `{"error": …}` the form never showed.
- **COA AMB has the Approved lock of COA AMB2, by the same functions** (`ApprovedLock` and the three module functions in `coa_amb2.py`, over the state field of each type). An Approved COA AMB cannot be saved, renamed, merged into or deleted, by any role; its rows cannot be changed, added, removed or taken by another document. The workflow's own moves pass: Reject (to Draft) and, for COA AMB, "Submit for Sales Approval" (to Certificate Shared, a submit) — in which the results may not change. Every other submit of an Approved COA AMB is refused. COA AMB2 is unchanged: nothing of that type is submitted.
- **`filled_by`** (new, read-only, both certificates): the user who last changed a test result, written by the server on a save of the certificate and on a save, insert or delete of a result row by itself. A value sent by the caller is not kept.
- **"May this be approved"** runs when the state becomes Approved, each refusal with its own message: a specification is linked; test rows exist; the result is Pass, Fail or Partial; it is recorded who filled; the approver is not that person; for COA AMB a signature and at least one customer; no submitted Quality Inspection with status Rejected on the lot's Batches; no Non Conformance of those Batches that is not closed. No role and no user is exempt. On approval the server writes `approved_by` and `approval_date` (now read-only); a Reject empties them; any other save keeps the stored values.
- **Removed:** the early return of COA AMB's `validate` for a Draft; the form script (both certificates) that set the approver when a date was typed; the `try/except` of both `validate_all_tests`.
- **Effect to know before deploying:** a certificate whose results were entered before this version has no `filled_by`, and cannot be approved until a result is saved once more by whoever fills it. The Quality Manager signs a COA AMB **before** pressing Approve (sign, save, approve).
- Not changed: the workflow fixtures and who may press each transition; the scoring of a row; COA AMB's four after-submit steps; `set_approval_info` (it still fills an empty approver at a submit).
- Tests: `tests/test_certificate_rules_b1.py`, `tests/test_quality_vocabulary.py`; `tests/test_coa_amb2_approved_lock.py` and `tests/test_13_12_12.py` adjusted for the shared lock.
## 13.12.15 — 2026-11

**Code, hooks and one DocType JSON (`coa_quality_test_parameter.json`, round 9c).** The lock itself is code and hooks: it is in force after a backend restart (web + workers) **and** `bench --site <site> clear-cache` (not optional: the hooks are read from the cache). **`bench migrate` is needed for one thing only, the `_seen` repair below**; without it the lock is complete and the old database error on a result row saved by itself stays.

### An Approved COA AMB2 cannot be saved again (TASKS-335 D-12)
- All six states of the COA AMB2 workflow are docstatus 0 and the state's `allow_edit` is applied by the browser only, so an Approved certificate kept its Save button and accepted writes. `validate` now refuses a save of a document that was Approved before the save and still is. A workflow transition changes the state, so Approve and Reject (Approved → Draft) still pass. **Effect:** an Approved certificate cannot be saved again, including by "Validate All Tests", until a Quality Manager rejects it to Draft.
- Not changed: who may press each transition, the workflow fixture, scoring.
- Tests: `tests/test_coa_amb2_approved_lock.py`.

### The lock reaches the certificate's rows, and deletion (TASKS-361 decision 115)
- A result row of an Approved certificate saved, inserted or deleted **by itself** never passed through the certificate's `validate`, so `frappe.client.save` of one row changed it. Both child tables of COA AMB2 (`COA Quality Test Parameter`, `SPC Batch Parameter`) now carry a `doc_events` hook (`before_validate`, `on_trash`) that refuses when the row's parent is an Approved, not submitted COA AMB2. Rows of any other parent are not judged. A save of the certificate itself (the workflow's Reject and Approve) does not run row events and is unchanged.
- An Approved certificate cannot be deleted (`COAAMB2.on_trash`); a Draft can.
- **Still code and hooks only: no `bench migrate`; restart + `clear-cache`** (the hooks are read from the cache).
- Not changed: the "Auto Approved" state stays unlocked (pending list); `db_set` and SQL run no event.

### The lock also refuses a submit, a row taken away and a rename (TASKS-365 decision 128)
- **Submit (VM3 D12-6).** During a submit the document is already at docstatus 1 and the lock returned at once, so `frappe.client.submit` with a signature in the call changed an Approved certificate in place and submitted it. Since 13.12.6 no path of the workflow submits a COA AMB2 (Approved, at docstatus 0, is its end), so **an Approved certificate is not submitted at all**, changed or not, with or without a signature. The lock now also runs in `before_validate` (it runs under `ignore_validate` too). A submit from any other state is outside this lock and as it was.
- **A row taken away (VM3 D12-4).** A row is judged by the parent it **has in the database** as well as by the parent the caller sends: `parent` or `parenttype` changed in the same save no longer takes it out of an Approved certificate, for any role. And a document saved with the **name** of such a row in its own table is refused in its `before_validate`: another COA AMB2 by its controller, and COA AMB, Batch AMB and SPC Batch Record (the other DocTypes that carry `COA Quality Test Parameter` / `SPC Batch Parameter`) by `doc_events` registered here. Nothing else of those documents is judged; rows under any other parent are not judged.
- **Rename (VM3 D12-5).** `COAAMB2.before_rename` refuses the rename of an Approved certificate (API and the form's title) and a merge of another certificate into it. `allow_rename` stays on for the type: a Draft is renamed as before.
- Not changed: who may press each transition; "Auto Approved"; `db_set` and SQL run no event.

### No COA AMB2 is submitted, in any state (TASKS-366 decision 129)
- Round 9c refused the submit of an Approved certificate only; a Draft, Validated or Pending Supervisor one could still be submitted directly by a role that holds submit, past the workflow. `COAAMB2.refuse_submit` (first in `before_validate`, which runs under `ignore_validate` too, and in `validate`) now refuses every move of a certificate from docstatus 0 to 1, for every role, with one message: the certificate ends at Quality approval.
- A certificate that is already submitted on a site is not touched: update after submit, cancel and its print code behave as before. An amended copy of a cancelled one is a new draft and, like any draft, cannot be submitted.
- Not changed: the fixture's permission rows (two roles still hold the submit right, now without effect); the submit-time code in the controller, which no new document can reach any more.
- **Code only: no `bench migrate` added by this change;** restart + `clear-cache`.

### The result-row DocType no longer declares "track seen" (TASKS-365, T-1) — **this part needs `bench migrate`**
- `COA Quality Test Parameter` had `track_seen` = 1 and its table has no `_seen` column, so every save of an existing result row by itself ended in a database error (HTTP 500) before any handler ran. `track_seen` has no meaning for a child table and is removed from the DocType JSON. No column is added or dropped; the migrate only re-reads the DocType. After it, a result row of a Draft certificate can be saved by itself, and a result row of an Approved one is refused by the lock (which is why this repair comes after the lock on moved rows).
## 13.12.14 — 2026-11

**Code only — `amb_w_tds/formulation/propuestas.py` (`pick_headline`, new `_SPECIFIC_TOKENS`).** No DocType JSON, fixture, patch or hook: **no `bench migrate`**; backend restart (web + workers) + `bench --site <site> clear-cache`.

### The Propuesta's Acemannan column reads the NMR row when the TDS has one (TASKS-335 D-11)
- `pick_headline` chose the Acemannan column by a substring match on the TDS parameter names and then the first match in TDS order; with several Acemannan rows (O-acetyl method, NMR, ortho-acetyl) the first one won, not the NMR value Calidad uses. A name carrying `nmr` now wins inside the Acemannan family, before the "total / content" preference; a TDS without such a row keeps the old first-match behaviour. The column label and the Aloína and Arsénico columns are unchanged.
- Not changed: how a range or an ND is read (the engine's `_lead_num`), the other headline columns, any choice of parameter per proposal (waits for Calidad).
- Tests: three new cases in `tests/test_propuestas_formulacion.py`.

## 13.12.13 — 2026-11

**Code only — `amb_w_tds/doctype/bom_formula/bom_formula.py` (`_row_key`, new `_raw_text`) and `amb_w_tds/formulation/propuestas.py` (`_coa_values`).** No DocType JSON, fixture, patch or hook: **no `bench migrate`**; backend restart (web + workers) + `bench --site <site> clear-cache`.

### The Propuestas report reads a COA row the way the BOM Formula reader does (TASKS-298)
- `propuestas._coa_values` filtered `specification in (…)`, returned `{specification: …}` and read `value` before `result`. On real COA rows `specification` and `value` hold the acceptance text, so the report showed the limit's text ("NMT 100 CFU/ML", "3.5-5.0") as the lot's value, or nothing. It now files a row through the reader's `_row_key` (`parameter_name` first, `specification` only when it names a parameter) and reads the cell with the reader's `_raw_text` (`result` first, else `value`): one definition each, imported, not copied. The first row of a parameter still wins. The report and the print format only read; nothing is saved.
- **Blank rule for the cell (TASKS-301, Hugh's ruling):** a lot's cell is `result` when it is not empty; when `result` is empty it is `value` only if `value` is a pure non-zero number (the reader's own float-strict `_num`, imported as `_reader_num`), otherwise empty (`None`). The acceptance text that old-shape rows keep in `value` ("NMT 8%", "3.5 - 5.0", "FINE HOMOGENEOUS POWDER") is never shown as a lot's value. Report only: `_raw_text`, `_build_lots`, `_lot_value` and every saved prediction are unchanged.
### The reader's QIP fallback is case-sensitive (TASKS-298)
- `_row_key` asked `frappe.db.exists("Quality Inspection Parameter", spec)`, which MariaDB's collation answers case-insensitively (the literal `NONE` found the parameter `None`) and answers with the STORED name. The fallback now takes `specification` only when the stored name equals it exactly; still one query per distinct specification (cached). Acceptance text that equals a parameter name only by case is not taken as that parameter.
- Tests: `tests/test_13_12_13.py`; two existing mocks (`test_13_12_7`, `test_coa_amb2_cut1`) now answer `exists` with the name, as frappe does.

## 13.12.12 — 2026-11

**Code only — `amb_w_tds/doctype/coa_amb2/coa_amb2.py`.** No DocType JSON, fixture or patch: **no `bench migrate`**; backend restart (web + workers) + `bench --site <site> clear-cache`.

### COA AMB2: the totals follow the rows, and an empty failure list is written (TASKS-291)
- **A.** `validate()` returned early for a Draft, before `evaluate_overall_result`, so a single-cell edit (a save of the parent) left `pass_percentage`, `tested_percentage`, `overall_result`, `compliance_status`, `failed_parameters` and the rows' `status` as the last "Validate All Tests" left them. A Draft save now runs the evaluation after its three light checks. Nothing else of the Draft path changes; the submit path is untouched.
- **B.** `failed_parameters` was written only when something failed, so a re-score with 0 failures kept the old text (COA2-26-0004: Pass / 100 % with the names of an earlier Fail). It is now written on every evaluation: the failing parameters' names, or empty.
- Not changed: the scoring of a row (13.12.8: ND and "<"/LOQ without a number = N/A), who may edit a cell and when, the workflow, the BOM Formula reader, `missing_data_policy`.
- Tests: `tests/test_13_12_12.py`.

## 13.12.11 — 2026-11

**Code only — `amb_w_tds/doctype/bom_formula/bom_formula.py` (`_build_lots` + a new helper `_row_key`).** No DocType JSON, fixture or patch changes, so **no `bench migrate`**: backend restart (web and workers) + `bench --site <site> clear-cache`.

### The BOM Formula blend reads real COA rows (TASKS-289)
- `_build_lots` filed every COA row under `specification` and typed it by `kinds.get(specification)`. On real COA AMB2 documents `specification` holds the **acceptance text** ('NMT 40%', '3.5 - 5.0', 'NONE') and the parameter is in `parameter_name` (a Link to Quality Inspection Parameter), so the measured pH of the real submitted COAs read NO DATA and the blend was empty. The rows built in the sandbox for 1.96 and 2.584 had the name in `specification`, which is why they passed.
- Now the row is filed under `parameter_name` whenever it is set (it wins even if `specification` happens to be another parameter's name); only when `parameter_name` is blank is `specification` taken, and only if it names a parameter (one the TDS defines or an existing Quality Inspection Parameter). Acceptance text with a blank `parameter_name` stays unkeyed: NO DATA, never guessed. `kinds` and the limits copied for the "TDS upper limit" policy are keyed the same way. The query also fetches `parameter_name` (a column of `COA Quality Test Parameter`, shared by COA AMB and COA AMB2).
- Kept: the measured number from `result` first; NO DATA is never 0; both `missing_data_policy` values; the output keys `no_data`, `assumed_at_limit`, `missing_data_policy`. COA AMB (v1) scoring and the docstatus-1 guard are untouched.
- Tests: `tests/test_13_12_11.py`; the source pin in `test_13_12_6` follows the renamed call.

## 13.12.10 — 2026-11

**Data only — `fixtures/property_setter.json`, one record. No code, no patch, no schema change.** Needs `bench migrate` (fixture sync) and `bench --site <site> clear-cache`; no restart beyond the migrate's own.

### The Sales Invoice field order stops reverting at migrate (TASKS-287, Part A)
- `Sales Invoice-main-field_order` now carries **prod's 273-entry list** (stored text 5,622 B, `json.dumps` default separators, no trailing newline, sha256 `55195716b2fd7b23b13c88234f0eb7b150cbb60ee05e5194d0aa95eaddb17b65`) instead of the 231-entry list of 2026-04-20. The record's own `modified` is prod's current stamp for the row (`2026-11-02 17:31:32.188396`, the Customize Form save), so the imported row equals prod's. This fixture is the **only writer** of that row at a migrate; before this, every migrate put 231 entries back and Customize Form's 273 were lost. The 224 names common to both lists keep their relative order; 49 names are new (31 core ERPNext 16.17 fields, 18 ERPNext Mexico Compliance custom fields), 7 stale names dropped.
- The other 328 records of the file are byte-identical to 13.12.9. The four rounded-total records already carry `1` and are right; they lost at migrate only because the Mexico-EInvoice fork's `custom/sales_invoice.json` is applied after every fixture (its four values are fixed in the fork, TASKS-287 Part B).
- Tests: `tests/test_13_12_10.py`.

## 13.12.9 — 2026-11 (built as 13.12.7; renumbered after 13.12.8 shipped first)

**Code + one DocType field** (`BOM Formula.missing_data_policy`, TASKS-282 Part B — a schema change): needs **`bench migrate`**, then `bench --site <site> clear-cache` and a restart of the web/worker processes.

### BOM Formula: missing-data policy — "No data" (default) or "TDS upper limit" (TASKS-282 Part B)
- New Select **`missing_data_policy`** on BOM Formula (after Target TDS): **"No data"** (default — what TASKS-281 built: a lot without a usable number is left out of that parameter's estimate and named with its mass) or **"TDS upper limit"**: for every NUMERIC parameter, a lot with no usable number (blank, ND, text) is **assumed at the limit copied onto its own COA row** — `max_value` for a parameter the TDS caps (NMT), `min_value` for one it floors (NLT) — so the estimate is conservative, and the result says so: `simulate_blend` returns `assumed_at_limit` = {parameter: {value, bound, lots, mass_kg}} (one entry per assumed value, `parameter@value` when lots carry different limits) and `missing_data_policy`; the row note carries "ASSUMED at TDS limit 3 (max on the COA row) for X (300 kg) — policy …"; `no_data` stays empty for those lots. Never assumed, kept NO DATA and still named: a row without the needed bound, a two-sided TDS range (the engine does not know which side is worse), every qualitative (all_pass) parameter; pH (`hplus_avg`) and worst-case parameters follow the same rule without exception paths.
- `engine.py`: `Lot.limits` {specification: (min, max)}; `assume_at_limit(lots, parameters)`; constants `MISSING_NO_DATA` / `MISSING_TDS_LIMIT`. `bom_formula.py`: `_build_lots` reads `min_value` / `max_value` with each COA row and fills `Lot.limits`; `simulate_blend` applies the policy between `_build_lots` and `engine.blend`. Tests: `tests/test_13_12_7_missing_data_policy.py` (Hugh's 1.7 + blank under both policies: 1.7 with the blank lot named, or (100·1.7 + 300·3.0)/400 = 2.675 with the note).

### BOM Formula: the blend uses the measured number; no number is not 0 (TASKS-281)
- **Why.** `_build_lots` read a COA row as `float(value)` first and fell back to the Pass-token test of `result`: on the sandbox not one of 514 COA AMB rows delivered a number that way (every `value` string fails `float()`), 466 became `False` and averaged as **0**, and a measured `2.22` never reached a blend (REPLY-TASKS-280 A3). Hugh's two rulings (2026-11-03): (1) a lot whose OWN number is over its limit still enters a blend — only the blend is judged; (2) a lot with no usable number is **NO DATA**, never 0.
- **`bom_formula.py`** — `_lead_num` (the leading number, as `coa_amb2._num` reads it: `'<10 CFU/G'` → 10, `'23.5%'` → 23.5, `ND`/`<LOQ`/text → none); `_lot_value(row, kind)`: by the parameter's kind from the engine's own `Parameter` (`_parameter_kinds`: all_pass → qualitative, `numeric` → numeric, else descriptive) — numeric: `result`'s leading number, else `value` only when it is a **pure non-zero number** (`float()` strict — on COA AMB rows `value` carries the acceptance text, `NMT 1 PPM` / `3.5 - 5.0` / `Specification`, whose digits are a limit, never a measurement; the form fills "0" by default, so 0 there is unset), else NO DATA; qualitative: the Pass-token test of `result` (ND / free text is not a pass — today's per-lot rejection stays), an empty result is NO DATA; descriptive: nothing (the words stay in `_raw_by_lot`). `_build_lots(params=None)` takes the parameters; `simulate_blend` builds them first and passes them (direct callers without params get content-typed rows as before). Class-1 rows with no number anywhere read **NO DATA** (status "", neither Pass nor Fail; `predicted_value` stays the column's 0 and is never read); the row note names the lots left out and their mass; the return carries `no_data` ({parameter: lots, mass_kg, lots_used, mass_used_kg}) and `no_data_estimate`.
- **`formulation/engine.py`** — `Lot.values` may hold `None`/absent = NO DATA; `_mass_avg`, `_ph_hplus`, `_worst_case` read only the lots with a real number (`_is_number`: never a bool), `_all_pass` only the lots with a bool; `_within_spec(None, …)` → None; `BlendResult` gains `lots_used`, `lots_no_data`, `mass_used_kg`, `mass_no_data_kg`, and its note names the lots without data. The arithmetic for lots that have data is unchanged (the EXAMPLE CUSTOMER A F-2886-26 lock and the self-test values hold).
- **Not changed:** the qualitative per-lot rule, `_per_lot_pass` / `_all_pass_state` / `_descriptive_text`, `_num` (float-strict, still used by `_descriptive_text` and `_release_from_measured`), the form, the solver, the Raven reader, `coa_amb2.py` scoring, ND semantics (TASKS-282), the COA AMB2 workflow. `propuestas._coa_values` (the report's per-lot cell) still reads `value` before `result` — reported, not touched.
- Tests: `tests/test_13_12_7.py` (Hugh's 1.7/2.22 → 1.96 example against NMT 3 and NMT 2, 70/30 masses, over-limit blend, NO DATA naming, pH/worst-case with a lot without data, qualitative unchanged, the reader's precedence table, the preview's return shape).
## 13.12.8 — 2026-11

**Code only — no fixture, no patch, no schema change.** `bench --site <site> clear-cache` and a restart; no `migrate`. (Branched from main after 13.12.6; `version.txt` / `__init__.py` will conflict trivially with 13.12.7's bump when the second of the two PRs is merged — take the higher number.)

### COA AMB2: ND / "not analysed" is N/A, never Fail (TASKS-282 Part A)
- **Why.** A COA AMB2 on a pure-powder lot is the analytical INPUT of a formulation, not a verdict against a TDS (Hugh, 2026-11-03): the verdict belongs to the new mix. Today `ND` scored Fail against any NMT / range / NEGATIVE specification (`check_parameter_compliance` → `_num("ND")` is None → False), and a lot with 34 ND cells read "Quality: Fail".
- **`coa_amb2.py`** — `_NA_TOKENS` / `_is_na()`: a result that is exactly (case-insensitive, whitespace-collapsed, trailing dot stripped) one of `ND`, `N/D`, `N.D`, `N D`, `NOT DETECTED`, `NO DETECTADO/A`, `NOT DETECTABLE`, `NO DETECTABLE`, `NO DISPONIBLE`, `NOT AVAILABLE`, `NOT ANALYZED`, `NOT ANALYSED`, `NO ANALIZADO/A`, `NOT TESTED`, `N/A`, `N.A`, `NA`, `-`, `—`, `–` → row `status` **N/A**. `evaluate_overall_result`: N/A rows are set before the Pending test and leave `total`, so `pass_percentage` / `tested_percentage` speak of the rows that can be scored (all-N/A → 0 / 0, overall **Pending**); Fail only for a measured number outside its non-zero bound or a qualitative Fail; scored rows all Pass with N/A rows beside them → **Pass / Compliant**; Pending rows (blank) with passes and no fails → **Partial / Under Review** as before, N/A rows not counted as pending. `get_test_summary` adds `na` and `na_parameters` (`total` excludes N/A); *Validate All Tests* says "… ; n N/A (no data, not scored): names". `calculate_child_table_status` mirrors the rule.
- **TASKS-282a (Hugh, 2026-11-03):** a "below the limit" cell that carries **no number** — `<LOQ`, `< LOQ`, `<LOD`, `<MDL`, `<DL`, `≤LOQ`, `BLQ`, `BDL`, `BELOW LOQ` / `LOD` / `DETECTION LIMIT` / `QUANTIFICATION LIMIT`, their Spanish spellings — is **N/A** too (rule: starts with `<` / `≤` and holds no digit, or is one of the listed words); the BOM Formula reader already read them as NO DATA, so the two agree. A `<` followed by a digit is never N/A.
- **Unchanged:** `<10`, `< 10`, `<10 CFU/G`, `<0.021 PPM` keep their number (Pass vs NMT 100 as today); NEGATIVE / NONE / descriptive text against presence or qualitative specifications keep today's result; `validate_numeric_result` / `validate_test_parameters` (the submit-time guard) untouched; COA AMB (v1) untouched — its own `_num` / `check_parameter_compliance` are a separate copy. No patch rewrites stored statuses: a Draft is re-scored by *Validate All Tests* as before.
- Tests: `tests/test_13_12_8.py`.

## 13.12.6 — 2026-11

**Fixture only — no code, no patch, no schema change.** Needs `bench migrate` (fixture sync re-imports the Workflow record); `clear-cache` as before (the Workflow is cached with the DocType meta).

### COA AMB2: Quality's approval is the end of the workflow (TASKS-280 / 280c)
- A COA AMB2 carrying a real out-of-limit result could never finish: the last step, *Submit for Sales Approval → Certificate Shared*, submits the document, and `validate_numeric_result` (correctly) refuses an out-of-limit value on submit — so Quality's only way out was to falsify the number or leave the certificate open. Hugh's ruling (REPLY-TASKS-280, 2026-11-03): Quality approval is the end; the measured value is kept as measured.
- `fixtures/workflow.json`, record `submit_and_start_workflow` (COA AMB2) only: the two **`Submit for Sales Approval`** transitions (Quality User, Quality Manager), the **`Certificate Shared`** state (docstatus 1) and — because only that state could reach it (Frappe refuses a draft → cancelled transition) — the 13.12.4.1 **`Cancel`** transition and the **`Cancelled`** state (docstatus 2) are removed. **`Approved` stays docstatus 0 and is the final state**; *Approve* (Quality Manager, no self-approval) is the last forward transition; both *Reject* rows stay. Six states, seven transitions, every state docstatus 0. Texts, roles and flags of every remaining row unchanged; the COA AMB twin (`submit_and_start_workflow_1`), the TDS and BOM Formula workflows, `workflow_state.json`, `workflow_action_master.json` and the hooks filter untouched (other workflows still link `Certificate Shared`, `Cancel` and `Cancelled`).
- **No guard change, no code change.** The out-of-limit guard, the result evaluator and the BOM Formula reader are as in 13.12.5. Row Pass/Fail and `overall_result` are computed by *Actions → Validate All Tests* (`validate_all_tests`) at docstatus 0 — the workflow itself does not evaluate; a result edited after the button is pressed is stale until it is pressed again.
- **Cost of docstatus 0 as the end:** nothing a submit used to do happens at Approved — no `on_submit` (PDF, batch status, quality e-mail, audit row, Item quality status), no `approval_date` / `approved_by` (set only at docstatus 1), no signature requirement, no Cancel/Amend (Frappe cancels submitted documents only — Reject → Draft is the correction path). `get_batch_quality_data` (`docstatus: 1`, no caller in any app) keeps returning no COA AMB2. A document already in `Certificate Shared` or `Cancelled` would be refused on its next save ("not a valid Workflow State") — none exists on prod per TASKS-280c (COA2-26-0001 Draft, 0002 Approved, 0003 Draft); check before the cut: `SELECT name, workflow_state, docstatus FROM \`tabCOA AMB2\` WHERE workflow_state IN ('Certificate Shared','Cancelled') OR docstatus != 0`.
- **Open Workflow Action rows:** the fixture import deletes and re-inserts the Workflow; the Open row a document holds for its current state is untouched and stays Open (Frappe closes it only on the next state change, Reject here). On prod the Open `Approved` row of COA2-26-0002 remains; its only live action is Reject.
- **Rollback** (older image + migrate): the previous fixture re-imports the eight states / ten transitions; a COA left in `Approved` is still `Approved` and may then be pushed to `Certificate Shared` again — subject to the submit guard.
- **Not in this release — task (c):** the BOM Formula reader change (`_build_lots` reading `result` before `value`), without which the measured number never reaches a blend. Tests: `tests/test_13_12_6.py` (fixture shape, Frappe's own transition rules, nothing else moved, no code rode along); `test_coa_amb2_cut1.py` updated to the seven rows / six states.

## 13.12.5 — 2026-11

**Fixture only — no code, no patch.** Needs `bench migrate` (fixture sync).

### Quality Manager may cancel and amend a TDS (TASKS-270b)
- `fixtures/custom_docperm.json`: Custom DocPerm **TDS Product Specification · Quality Manager · level 0 · every permission** (select, read, write, create, delete, submit, cancel, amend, report, export, import, share, print, email, mask; `if_owner` 0) — the row Hugh saved in Role Permission Manager on prod on 2026-11-02, so that after 13.12.4.1's `Approved → Cancel → Cancelled` a Quality Manager also gets Frappe's **Amend** on the cancelled TDS (the role had `amend` 0 / `cancel` 0 / `submit` 0 there). Name `tds-l0-quality-mgr` (explicit, as the BOM Formula rows); the name joins the hooks export filter.
- **Read before the cut:** prod's Desk-made row carries its own hash name. Fixture sync upserts by `name` and never deletes, so this row lands **beside** prod's (two identical rows for the same DocType / role / level; permissions are the union, so nothing changes functionally) until the fixture carries prod's name — then they are one. The 13.12.4 / 13.12.4.1 migrates carry no TDS Custom DocPerm row at all (filter: BOM Formula rows + six COA AMB2 rows by name) and therefore cannot touch prod's Desk-made row.

## 13.12.4.1 — 2026-11

**Fixtures only — no code, no patch, no schema change.** Needs `bench migrate` (fixture sync) like 13.12.4; `clear-cache` as before.

### `fixtures/property_setter.json` is prod's own export (TASKS-270 item 1)
- The 13.12.4 migrate would have re-imported the file's 300 Property Setters over the 81 rows a System Manager saved in Customize Form on 2026-10-28/10-30 (Item, 8 transaction DocTypes, 5 stock DocTypes), setting 32 values back: `base_rounded_total-hidden`, `rounded_total-hidden`, `rounded_total-print_hide`, `disable_rounded_total-default` 1 → 0 on Delivery Note, Purchase Invoice, Purchase Order, Purchase Receipt, Quotation, Sales Invoice, Sales Order, Supplier Quotation. The file is now prod's export of 2026-11-02 (Frappe's own serialisation, main's filter; REPLY-TASKS-269a, sha256 `c1fe57b8…2b31` before the repo's trailing newline): **329 records** = main's 300 + 29 prod UI customisations made after the last export, 102 records updated (the 32 values, 60 `module`, 11 `is_system_generated`, `modified` on 102).
- **Caveat (Hugh's default, not solved here):** the four **Sales Invoice** rounded-total values are also shipped by mexico_einvoice's `custom/sales_invoice.json` with value 0, and `sync_customizations` runs after `sync_fixtures`, so they revert on the cut and are re-applied in Customize Form afterwards. The 43 exported rows that other apps also ship (42 mexico_einvoice, 1 erpnext_mexico_compliance) were already in the file and stay as they are.

### Three workflows: `Cancelled` state + `Cancel` transition (Quality Manager), as Desk 2026-11-02 (TASKS-270 / 270a item 2)
- An approved TDS (or a shared COA) could not be corrected: none of the three workflows had a transition to a docstatus-2 state, so Frappe hid Cancel/Amend. `fixtures/workflow.json` now carries, exactly as saved in Desk on prod on 2026-11-02, one state **Cancelled** (doc_status 2, allow_edit Quality Manager) and one transition to it, allowed **Quality Manager** only, on each of: *TDS Approval Workflow* (TDS Product Specification: **Approved → Cancel → Cancelled**; 8 states / 7 transitions), *submit_and_start_workflow* (COA AMB2: **Certificate Shared → Cancel → Cancelled**; 8 / 10), *submit_and_start_workflow_1* (COA AMB: **Certificate Shared → Cancel → Cancelled**; 8 / 9). No other row changes; no System Manager row, no Amended state, no Reopen from Cancelled.
- The state and action are Links; a fresh site has neither master, so `Cancelled` joins `workflow_state.json` and `Cancel` joins `workflow_action_master.json`, and both names join the hooks export filter (the hooks block's own rule since 2026-08-06).

## 13.12.4 — 2026-11

**Needs `bench migrate`** (fixture sync: one Client Script record changes; no patch, no schema change). Also one form script, so `bench --site <site> clear-cache` after the image swap as in 13.12.3.

### TDS form: the dead `your_app.*` calls are gone (C18, TASKS-266 item 1)
- **Fixed: every Item change on a TDS raised red dialogs.** `tds_product_specification.js` called `your_app.quality.doctype.tds_product_specification.tds_product_specification.get_item_details` / `get_latest_tds_version` (and `create_new_version` behind *Create New Version*, `get_latest_tds_version` again behind *Copy from Latest*) — a module that was never part of this app; each answered HTTP 417 "App your_app is not installed" and the callbacks never ran. The four functions and the two buttons that only reached them are removed; nothing is resurrected. `item_code` is still set on Item change by the *TDS Version* Client Script; the naming-series rewrite rule (`update_naming_series`) is unchanged.
- **Not changed here:** four scripts that 404 on every desk page (`warehouse_temperature.js`, `sales_order_upload.js`, `sales_invoice_upload.js`, `documents_panel.js`) are `app_include_js` entries of **other apps** (`raven_ai_agent/hooks.py:13-15`, written as `raven_ai_agent/public/js/…` instead of `/assets/raven_ai_agent/js/…`, one file missing; `rnd_warehouse_management/hooks.py:38`, file missing) — not amb_w_tds's to fix.

### *TDS Version* Client Script: never writes TDS Settings; *Generate Version* sets `custom_version` (TASKS-266 item 2)
- **Fixed: the second red dialog on every Item change and on every new TDS** ("Naming series must start with the prefix: TDS-SET"). The script tried to keep one TDS Settings record per item (`frappe.client.get_list` by `item_code`, then `frappe.client.insert` / `set_value` of `last_sequence_used`) — but TDS Settings is a **Single**, the server refused every insert and nothing was ever written. The script no longer touches TDS Settings; the sequence suggestion now reads the highest `tds_sequence` among the same item's TDS records and fills `tds_sequence` only when it is empty.
- **Fixed: `custom_version` was never updated by anything.** *Generate Version* now writes the generated string (`V1.<item>-Date:yy/mm/dd*NNNN`) into `custom_version`, and still into `tds_version` as before (so the naming-series rewrite keeps behaving as it did).
- Fixture record only (`fixtures/client_script.json`): **this is what makes the cut need `bench migrate`.**

### Fixture export filter + 13.12.3 wording (TASKS-266 item 3)
- `AMB Cost Factors` and `Quotation Item Escalated` (custom DocTypes that exist only on production) are out of `_AMB_W_TDS_DOCTYPES` (new `_PRODUCTION_ONLY_DOCTYPES`, import-time assert). Measured on the sandbox: `bench export-fixtures` on main pulled 5 of their records into the base files (1 Custom Field, 1 Property Setter, 2 Client Scripts, 1 Server Script); on this branch 0.
- The 13.12.3 entry, README row and the comment above `sc5v2_fetchCAVMap` said nginx answered the long request line; measured on prod (REPLY-263) it is gunicorn's default `limit_request_line` (4,094 bytes) — corrected.

### Sub-lot titles (G1, TASKS-266 item 4)
- `auto_set_title` lives in **amb_w_spc** (`sfc_manufacturing/doctype/batch_amb/batch_amb.py`), not in this app, so the fix is an amb_w_spc change delivered as its own branch/PR (`fix/g1-sublot-title-stable`: the stored title of a level-2/3/4 sub-lot stays unless the record is new, has no title, or its parent/level changed; no data patch, existing titles untouched). This entry only records that the two ship together as 13.12.4.

## 13.12.3 — 2026-11

**Code only** (no patch, no fixture, no DocType JSON change, nothing `bench migrate` would write). The file is a `doctype_js` script: Frappe hands it to the browser inside the DocType meta (`getdoctype` → `__js`), and that meta is cached server-side, so the change takes effect with the new image, a container recreate **and `bench --site <site> clear-cache`** (no `bench build`; a browser hard reload alone is not enough while the old meta is cached — measured in the sandbox).

### TDS "Parameter Selection" picker: the Customer-Specific Specification lookup no longer times out (TASKS-261)
- **Fixed: on every TDS that has a TDS Customers row the tab showed "Catalog load timed out (10s)" on load and on *Reload picker*.** `sc5v2_fetchCAVMap` in `phase_1c_tab_v2.js` asked for the customers' Customer-Specific Specification rows with `frappe.db.get_list`, which Frappe sends as a **GET** with the filters in the query string, and that filter carried **every parameter name the picker renders** (`parameter in [...]`, 174 names for a powder item, ~4.4 KB of query string in the sandbox, ~8 KB measured on prod). on prod, gunicorn refuses a request line longer than its default `limit_request_line` (4,094 bytes) with a 400 before Frappe sees it — nginx/traefik only relay that page (wording corrected in 13.12.4; measured on prod, REPLY-263); the picker awaited that promise and the watchdog fired. A TDS with no customer row never made the call, which is why the tab worked there.
- **Now:** the same lookup is one **POST** (`frappe.call` → `frappe.client.get_list`, the arguments travel in the body) that asks only for `customer in [...]`, `status = Approved`, `is_active = 1`, same fields, `limit_page_length = 0`; the rows are then matched against the rendered parameter names in the browser (a `Set`). Same map comes out, so the 🎯 CSS badges, the header count and *Add Selected* behave as before. The query string of the request is now 0 bytes regardless of catalog size.
- **Not changed:** the per-selection lookup inside *Add Selected* (one parameter name per request, ~530 bytes, well under the limit) is still a GET; `api/picker.py`; everything else in the file. The `your_app.*` calls in `tds_product_specification.js` are reported separately, not touched.

## 13.12.2 — 2026-10

**Code and docs only** (no patch, no fixture, no DocType JSON change, nothing `bench migrate` would write; the change takes effect with the new image and a container recreate plus a cache clear, because it is a Python module and two form scripts).

### One Batch Reference picker for COA AMB and COA AMB2 (TASKS-238/239)
- **Fixed: the COA AMB2 Batch Reference dropdown listed nothing.** It asked `docstatus = 1`, but Batch AMB is not submittable (its rows are always `docstatus 0`), so no batch could ever match; the COA AMB copy had been relaxed in June and the COA AMB2 copy was never updated. Both forms now call **one** whitelisted query, `amb_w_tds.amb_w_tds.api.batch_picker.search_batches`; neither carries a filter of its own any more (a unit test fails if one comes back).
- **The rule:** every Batch AMB whose `batch_status` is not Cancelled and whose `quality_status` is Pending, Hold or not yet set. **No item filter**: the product on a COA and the item on a batch sit at different levels of the Item tree, so each dropdown line shows the batch id, the batch's item and `quality status / batch status`, and the person chooses. Search text matches the batch id, title, golden number and item; newest first; paged; the user's Batch AMB read permission applies as for any Link search.
- **Fixed: the BOM Formula gate no longer takes a COA AMB2 for a batch's certificate through `batch_reference` alone.** `BOMFormula._resolve_coa` step 3 now counts only a submitted COA AMB. Nothing compared a COA AMB2's product with the batch's item, so with the picker open a COA AMB2 linked to the wrong batch would have satisfied the gate for that batch, and a newer one would have beaten an older correct COA AMB. **Accepted trade-off, until Cut 2b: a COA AMB2 satisfies the gate only through the explicit line link (`source_coa_amb2` + `source_coa_doctype`), not through the batch.** No existing result changes: there is no submitted COA AMB2 on the sandbox, and prod has one draft, none used.
- **Finding, not changed: `Formulation Settings.default_coa_source` is read by no code.** It is only stored (two patches write it, the Select defines it); the gate behaves the same under "COA AMB" and "COA AMB2". Whether it should work is a separate ruling.
- **Not changed:** COA AMB's submit and cancel (their invalid `quality_status` writes and Error Log rows stay as reported in REPLY-TASKS-237), `coa_amb.py`, `coa_amb2.py`, the Cut 2a guard, the item match, every Cut 2b item.

## 13.12.1 — 2026-10

**Requires `bench migrate`** (no patch, no schema change; the change is code only).

### COA AMB2, Cut 2a (TASKS-233)
- **Fixed: a COA AMB2 submit that carries a `batch_reference` still wrote one Error Log row, "COA AMB2 - Batch Update".**
  `update_batch_status` handed the COA AMB2 name to `Batch AMB.coa_reference`, a Link to COA AMB, so Frappe's link
  validation refused it (and `quality_status` was set to "Pass", which is not one of its options Pending / Passed /
  Failed / Hold). That update has never succeeded, so skipping it changes no data. Now the Batch AMB write is skipped
  when the field cannot hold a COA AMB2 name (read from the meta, so the same code writes once Cut 2b makes the field
  point at COA AMB2), `quality_status` is no longer written, and one Info comment on the COA AMB2 says "Batch not
  updated: link to COA AMB2 not available yet". Any other failure of the batch step is still logged.
- **Fixed: the same for the cancel.** Cancelling a batch-linked COA AMB2 wrote `quality_status = "COA Cancelled"`
  (not one of the field's options) and logged one more Error Log row, and because the batch was saved, the Batch AMB
  controller (`amb_w_spc`) also tried to announce a quality-status change that could never stick (a second row where
  the outgoing mail account fails, and a real e-mail where it works). The cancel now uses the same guard: when the
  Link cannot hold a COA AMB2 name the batch is not touched and one Info comment on the COA AMB2 says "Batch not updated
  on cancel: link to COA AMB2 not available yet"; when it can (Cut 2b), `quality_status` is still never written, a note
  is left on the batch and nothing is saved. What a cancelled COA should do to a batch is Cut 2b. `coa_amb.py` and every
  other DocType are untouched.
- **Corrected the 13.12.0 wording of the six new permission rows** (CHANGELOG, `docs/coa-amb2-cut1.md`): each row is
  now listed as shipped. The rows themselves did not change, and a test now compares the table in the docs with the
  rows in `fixtures/custom_docperm.json`.

## 13.12.0 — 2026-10

**Requires `bench migrate`** (no patch; the new permission rows and the workflow row arrive through the existing fixture sync).

### COA AMB2, Cut 1 (TASKS-227)
- **Permissions mirrored from COA AMB.** COA AMB2 gains six Custom DocPerm rows, one per role, exactly as follows
  (every flag not named is 0): **Quality Engineer** read / write / create / report / print;
  **Quality User** read / write / create / delete / submit / report / export / print / email / share;
  **RND Manager** all twelve (read, write, create, delete, submit, cancel, amend, report, export, print, email, share);
  **Manufacturing User**, **Sales Manager CRM** and **Stock User** read / report / export / print / email / share.
  Quality Inspector, Quality Manager and System Manager keep the rows they have; COA AMB's duplicate rows are not copied (a role with two differing rows becomes one row holding
  their union). Marketing Manager is not added: COA AMB has no row for it. The rows ship in
  `fixtures/custom_docperm.json`; the `hooks.py` Custom DocPerm fixture entry now also names the six COA AMB2 rows, besides
  `BOM Formula`, selecting the six COA AMB2 rows by name, so a re-export keeps them and drags in nothing else. No patch, no data change.
  Why a fixture: COA AMB2 already runs on Custom DocPerm rows on every site, and a standard DocType's JSON
  permissions are not applied while Custom DocPerm rows exist, so editing `coa_amb2.json` would change nothing.
- **Workflow.** Quality Manager may now press "Submit for Sales Approval" (Approved -> Certificate Shared, the real
  submit) on COA AMB2's workflow `submit_and_start_workflow`; Quality User stays allowed. One transition row is added to
  `fixtures/workflow.json`; the other seven transitions, the states and the COA AMB twin workflow are unchanged. The
  workflow is delivered by the fixture (every migrate re-imports it), so no patch is needed. A user who holds both
  roles sees the action twice in the Actions menu (Frappe lists one entry per allowed role); both do the same thing.
- **Submit email.** `notify_quality_team` now links to `/app/coa-amb2/<name>` (it pointed at `/app/coa-amb/`, the other
  DocType) and tells only the enabled Quality Managers plus the owner and `approved_by` (de-duplicated; never
  Administrator or Guest). Quality Inspector, Quality Analyst and the batch production manager are no longer notified.
- **Three Error Log rows no longer written on every COA AMB2 submit** (COA AMB2 only; `coa_amb.py` is untouched):
  the product update and its revert write the Item fields `last_coa_date`, `last_coa_result`, `last_coa_reference`
  only when the site has them (no site does, and no field is added); the quality-audit step is skipped when the
  `Quality Audit` DocType is absent (Frappe 16 has none, and none is added); the "Notification sent" note is added as
  comment type `Info` (Frappe 16 refuses `Email`), still after the mail has gone. Any other failure still goes to `log_error`.
- **Gate warning.** `BOM Formula.simulate_blend` still builds the blend from the lines that resolve a COA, and the
  acceptance rule is unchanged. A line skipped because it has no COA is now named (row number and item code) in an
  orange message and in two new result fields, `skipped_no_coa` and `warning`. No computed number changes.
- Not in this release: `Formulation Settings.default_coa_source` (stays COA AMB), any patch, the real/authorized pair,
  remark field, Batch AMB link, creation path and labels (Cut 2).

## 13.11.3 — 2026-10

**Requires `bench migrate`** (no patch; the change is what a migrate no longer does).

### Removed: the FMIX/MEMCAL sample formula fixtures
- Remove the FMIX/MEMCAL sample formula fixtures so a fresh install/migrate creates **no demo
  formulas** (prod stays clean). The file `amb_w_tds/fixtures/bom_formula.json` shipped seven
  sample BOM Formula records (`MEMCAL-T1` … `MEMCAL-T6` and `FMIX-0307-STEP1` with its four Mix
  Input lines). It was never listed under `fixtures` in `hooks.py`; Frappe imported it only because
  it sat in the fixtures folder, and re-imported it on every migrate.
- **Existing sample records on systems that already have them are left in place (no deletion);
  they are simply no longer re-imported or reset.** No patch touches them and no Workflow Action
  is generated for them.
- No code, schema, workflow, role, report, Print Format or release-logic change. The fixture
  mechanism for the real doctypes (Custom Fields, Custom DocPerms, Workflow, Mixing Equipment,
  Formulation Settings defaults, Print Format) is unchanged.
- Nothing in code, reports, Print Formats, JS or tests referenced the samples by name.

## 13.11.2 — 2026-10

**Requires `bench migrate`** (one patch; a BOM hook).

### Fixed: "Liberar a producción" crashed with "Duplicate Name: BOM BOM-0307-006 already exists"
- **Cause:** ERPNext's `BOM.autoname` picks the next `BOM-<item>-NNN` while **skipping amended
  BOMs**. On this site, amendments are named "Default Naming", so they take plain numbers
  (e.g. `BOM-0307-006` is an amendment of `-005`). The picker therefore re-proposes an existing
  name.
- **Release:** the release now names its BOM explicitly, **`BOM-<item>-NNN` counting amended BOMs**
  (here `BOM-0307-007`), with one retry. There is no new prefix: the released BOM is identified by
  `bom_formula`.
- **Every BOM creation path, including the manual "New BOM" dialog:** a BOM `autoname` hook runs
  after ERPNext's and moves the name to the next free number **only when the proposed name already
  exists**. Names that would not collide are untouched, and no existing BOM is renamed.

### BOM amendments use "Amend Counter"
- Patch `v13_11_2_bom_amend_counter`: in Document Naming Settings it sets **only** the BOM
  amendment override to **Amend Counter**. The global setting and all other rows are untouched,
  and it is idempotent.
- **Future** BOM amendments are named `BOM-<item>-NNN-1` instead of taking the next plain number.
  It renames nothing.
- ⚠ Amending one of the **existing** amendments that already took a plain number (e.g.
  `BOM-0307-006`) gives Frappe's counter name `BOM-0307-7`. This is Frappe's Amend Counter
  rule; the BOM hook above still keeps new BOMs collision-free.

### Liberar makes the released BOM the item's default ("first plan")
- **Changes the 13.11.0 behaviour (`is_default = 0`).** The released BOM is created with
  `is_default = 1`, and ERPNext's own `manage_default_bom` unticks the previous default on submit.
  Exactly one default remains, which is asserted.
- **The demotion is logged** as a comment on the BOM Formula and on the new BOM, naming the
  previous default, so a planner can tick it back.
- **A re-release (reuse of "BOM liberada") never touches defaults.** Existing Work Orders keep
  their own BOM.

## 13.11.1 — 2026-10

**Requires `bench migrate`** (the workflow fixture changed). No data or schema change.

### Fixed: the approval workflow was hard to see on the BOM Formula form
- The workflow state badge did not show, because the workflow had `override_status` = 1
  ("Don't Override Status"), which keeps Frappe from using the workflow state as the form's
  indicator. It is now 0, so the badge shows Borrador, En Revisión, Autorizado, Liberado or
  Rechazado.
- Every state stays at docstatus 0, so BOM Formula remains non-submittable and the migrate
  changes no document.
- The role-gated transitions were always offered, in Frappe's **Acciones** menu. The
  "Propuesta" buttons did not suppress them.
- **New line at the top of the form:** "Estado: <estado> · Siguiente acción: <acciones>
  (menú Acciones)", or "Sin acción disponible para su rol". It is built from the same
  transitions Frappe offers the user, so the next step is obvious.

## 13.11.0 — 2026-10

**Requires `bench migrate`.** After it, verify that the workflow "BOM Formula Aprobación"
imported and that each role can make its transitions.

### BOM Formula approval workflow
- Workflow **"BOM Formula Aprobación"** on BOM Formula: Borrador → En Revisión →
  Autorizado → **Liberado** / Rechazado. It ships as a fixture, together with its 5
  Workflow States and 6 Actions.
- **BOM Formula stays non-submittable.** The workflow runs on a new `workflow_state`
  field, and every state is a draft (docstatus 0).
- Transitions, each limited to one role:

  | from | action | to | role |
  |---|---|---|---|
  | Borrador | Enviar a revisión | En Revisión | Quality Engineer |
  | En Revisión | Autorizar | Autorizado | Quality Manager |
  | En Revisión | Devolver | Borrador | Quality Manager |
  | Autorizado | Liberar a producción | Liberado | Marketing Manager (Dirección) |
  | Autorizado | Rechazar | Rechazado | Marketing Manager |
  | Autorizado | Devolver a Calidad | Borrador | Marketing Manager |

- Who can edit in each state:
  - **Borrador:** Quality Engineer, Quality Manager, RND Manager, Manufacturing Manager,
    Manufacturing User, System Manager;
  - **En Revisión:** Quality Manager;
  - **Autorizado, Liberado, Rechazado:** Marketing Manager.
- **The state drives `cost_approval`**, so the two never disagree: Autorizado and Liberado
  mean approved, Rechazado means rejected, En Revisión means requested, and returning to
  Borrador withdraws an approval or rejection.
  - The 13.10.0 stamps follow: *Autorizado por* is the user who authorized, and *Fecha de
    autorización* is when.
  - With the workflow active, cost authorization is given by the "Autorizar" transition,
    not by setting the field by hand.
- **Existing records** without a state are set to Borrador when the workflow is installed,
  by Frappe's own workflow default.

### Liberar a producción builds a standard BOM
- New `amb_w_tds/formulation/release.py`, a small builder on ERPNext's native BOM. It does
  not reuse `BOMService.create_standard_bom` (an MRP-BOM copy tied to a Batch AMB, with
  `is_default` forced to 1 and its own commit).
- The BOM is built for the formula's product:
  - `quantity` = the Mix Input total (kg);
  - one item per Mix Input row: the row's Item (else its Batch AMB sublot's item), with
    qty = kg and uom Kg;
  - `bom_formula` = the source formula;
  - `is_active` 1, **submitted**, so a Work Order can use it.
- **Nothing is written unless every row resolves.** The release fails if any Mix Input row
  has no resolvable Item or a kg ≤ 0, or if the product's stock UOM is not Kg, and the
  message names the rows.
- **Default BOM:** `is_default` is requested as 0. ERPNext still makes the BOM the item's
  default when the item has no default BOM at all; it never takes the default away from an
  existing BOM.
- **Back-reference:** a new read-only **"BOM liberada"** field on BOM Formula.
- **Idempotent on that field:** if the released BOM is still submitted and active, it is
  reused. Other BOMs that merely carry `bom_formula` (some were tagged by hand) are never
  searched or touched.
- The BOM is built server-side, bypassing permission checks only on the Autorizado →
  Liberado transition. **No role gets a general right to create or submit BOMs.**

### Access
- **Marketing Manager** (Dirección): read, write and report on BOM Formula (level 0), and
  access to the "Propuestas de Formulación" report.

### Note
- The 7 fixture sample formulas (`FMIX-*`, `MEMCAL-*`) are re-created at every migrate, so
  they return to Borrador each time. They are not meant to be released.

## 13.10.0 — 2026-10

**Requires `bench migrate`** (doctype and Custom DocPerm changes).

### BOM Formula: Propuesta actions on the form
- A **"Propuesta"** button group on BOM Formula (`bom_formula.js`), shown only to users
  who can run the "Propuestas de Formulación" report:
  - **Generar PDF y Excel** renders the Propuestas PDF (the Print Format) and Excel (the
    report's own export) for the record's product and Sales Order, and attaches both to
    the record as private files.
  - **Compartir** opens Frappe's share dialog, for users with the share right.
  - **Enviar a Dirección** is a supporting action. It asks for confirmation, then emails
    both files to the configured Dirección recipients. With none configured it sends
    nothing and says where to set them.
- Server methods are in `amb_w_tds/formulation/propuesta_actions.py`. Each call is checked
  against the report's own rule: its roles, plus the "report" right on BOM Formula, plus
  read on the record. Recipients never come from the caller.

### Formulation Settings: "Destinatarios de Dirección"
- A table of Users who receive "Enviar a Dirección", empty by default. The administrator
  fills it in on each site; no address ships in the app.

### Permissions on BOM Formula (cost stays visible to Calidad)
- **Quality Manager** and **Quality Engineer**: read, write, create, report, print, email
  and export, at permission level 0. Calidad prepares and authorizes, and sees cost. No
  delete, submit or cancel: release to production stays with the existing authority.
- **report = 1** for Manufacturing Manager, Manufacturing User and RND Manager.
  Previously only System Manager could run reports on BOM Formula, so these roles hit
  "You don't have permission to get a report on: BOM Formula".
- "Propuestas de Formulación" report roles gain Quality Manager and Quality Engineer.

### Calidad authorization
- Recorded in the existing fields: **Autorización de Costo** (`cost_approval` =
  approved) and **Autorizado por** (`cost_approved_by`).
- `cost_approved_by` was read-only and nothing ever set it. It is now stamped with the
  user, together with a new read-only **Fecha de autorización** (`cost_approved_on`),
  when the approval becomes "approved", and both are cleared when it is withdrawn.
- `cost_approved_on` is the only new field; no change history was kept on BOM Formula.
- The formal approval Workflow (Borrador → Autorizado Calidad → Dirección → Liberado)
  is a separate, later task.

## 13.9.1 — 2026-10

**Requires `bench migrate`** (the Print Format fixture changed).

### Fixed: Propuestas de Formulación judged nothing on real data
- Without a TDS filter, the report looked the TDS up by an exact match of
  `TDS Product Specification.product_item` to the proposal's `product_sku`. Production
  TDS name a longer descriptive Item, so every proposal showed "SIN TDS".
- Now, per proposal: the explicit TDS filter if given, else **the proposal's own
  `target_tds`**, else "SIN TDS". The Item-name lookup is gone.
- A draft TDS judges, as the gate's Simular already does, but every verdict on it is
  labelled "TDS en borrador" and counted apart. A cancelled or missing TDS is refused
  ("TDS CANCELADA" / "TDS NO EXISTE"), with no pass/fail.
- Report, Excel and PDF use the one resolution. The "PDF para Dirección" button now passes
  the report's `tds` and `pedido` filters; an empty Pedido means all orders. Before, the
  PDF could judge and scope differently from the screen.
- Each verdict shows its basis:
  - a "TDS aplicada" column in the report and Excel;
  - "TDS aplicada" and the bounds per proposal in the PDF;
  - one spec header only when every proposal used the same TDS with the same status.
- The headline columns (Acemannan, Aloína, Arsénico) take each proposal's own parameter
  from its own TDS. A column carries a UOM in its header only when all proposals agree;
  otherwise each value names its parameter and UOM.
- The report's TDS filter offers any approved or draft TDS. It used to offer only TDS of
  the product's exact Item, the same miss.

## 13.9.0 — 2026-10

**Requires `bench migrate` on every site.**

### BOM Formula formulation form onto `main` (phase-g `a2b6d8c`)
- `phase-g/g0b-2a` (`a2b6d8c`) merged into `main` with no conflicts. `main`'s own
  work since `3a8d1c5` (CI, README, the COA AMB `log_error` fix and its test) is kept.
- BOM Formula: 104 fields, 10 Tab Breaks (Pedido, Base, Selección de lotes, Mix,
  Predicción y puerta, Costo y autorización, Memoria de Cálculo, Ejecución, Juice,
  Trazabilidad). Mix and Juice are exclusive by `formula_type`, so a document shows 9.
- The `simulate_blend` gate (estimate → lab measures → release on the measured value),
  with COA resolution per Mix line.
- Child doctypes: BOM Formula Authorized Value, Candidate Lot, Memoria Line, Spec Filter;
  Formulation Settings; Mixing Equipment. Print Format "Materiales para formulación".
- Existing BOM Formula records keep their data: every field of the previous form
  survives with the same type; `formula_type` gains the option `Base`.

### Also carried by the phase-g line
- COA AMB2: COA AMB's fixed compliance methods ported.
- LOOP-1 lot identity resolver (`amb_lot_identity`).
- BUG208 customs valuation (`valuation.py`, `valuation_jinja.py`).
- Role home-page cleanup (`clear_stale_role_home_page`).

### New: report "Propuestas de Formulación"
- Script Report (BOM Formula) for one product and optionally one Sales Order. It lists
  the draft Mix proposals and, per proposal, shows the lot lines, the gate's weighted
  TOTAL and the compliance of that total against the product's TDS. A comparison row per
  proposal comes first. Export: Excel/CSV.
- Print Format "Propuestas de Formulación" (BOM Formula, Jinja), with a TDS header box,
  per-proposal tables, the comparison and Dirección's decision and signature block.
  Exports to PDF. The report's "PDF para Dirección" button opens it.
- The Script Report ships as a standard module file
  (`report/propuestas_de_formulación/`); a standard Report without a module file is
  deleted by `remove_orphan_entities()` at every migrate. The Print Format ships as a
  name-filtered fixture. Read-only: the report writes nothing.

### Transport note
- The migrate runs two patches new to production (`g1a_formulation_settings_defaults`,
  `g0b2a_source_coa_doctype`).
- Production's orphan table `tabBOM Formula Item` (3 rows, its DocType long deleted)
  is not touched by a migrate. Export it before the production migrate.
