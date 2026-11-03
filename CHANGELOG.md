# Changelog

## 13.12.7 — 2026-11

**Code only — no fixture, no patch, no schema change.** `bench --site <site> clear-cache` and a restart of the web/worker processes; no `migrate`.

### BOM Formula: the blend uses the measured number; no number is not 0 (TASKS-281)
- **Why.** `_build_lots` read a COA row as `float(value)` first and fell back to the Pass-token test of `result`: on the sandbox not one of 514 COA AMB rows delivered a number that way (every `value` string fails `float()`), 466 became `False` and averaged as **0**, and a measured `2.22` never reached a blend (REPLY-TASKS-280 A3). Hugh's two rulings (2026-11-03): (1) a lot whose OWN number is over its limit still enters a blend — only the blend is judged; (2) a lot with no usable number is **NO DATA**, never 0.
- **`bom_formula.py`** — `_lead_num` (the leading number, as `coa_amb2._num` reads it: `'<10 CFU/G'` → 10, `'23.5%'` → 23.5, `ND`/`<LOQ`/text → none); `_lot_value(row, kind)`: by the parameter's kind from the engine's own `Parameter` (`_parameter_kinds`: all_pass → qualitative, `numeric` → numeric, else descriptive) — numeric: `result`'s number, else a **non-zero** number in `value` (`value` is a Data column the form fills with "0"; 0 there is unset), else NO DATA; qualitative: the Pass-token test of `result` (ND / free text is not a pass — today's per-lot rejection stays), an empty result is NO DATA; descriptive: nothing (the words stay in `_raw_by_lot`). `_build_lots(params=None)` takes the parameters; `simulate_blend` builds them first and passes them (direct callers without params get content-typed rows as before). Class-1 rows with no number anywhere read **NO DATA** (status "", neither Pass nor Fail; `predicted_value` stays the column's 0 and is never read); the row note names the lots left out and their mass; the return carries `no_data` ({parameter: lots, mass_kg, lots_used, mass_used_kg}) and `no_data_estimate`.
- **`formulation/engine.py`** — `Lot.values` may hold `None`/absent = NO DATA; `_mass_avg`, `_ph_hplus`, `_worst_case` read only the lots with a real number (`_is_number`: never a bool), `_all_pass` only the lots with a bool; `_within_spec(None, …)` → None; `BlendResult` gains `lots_used`, `lots_no_data`, `mass_used_kg`, `mass_no_data_kg`, and its note names the lots without data. The arithmetic for lots that have data is unchanged (the LORAND F-2886-26 lock and the self-test values hold).
- **Not changed:** the qualitative per-lot rule, `_per_lot_pass` / `_all_pass_state` / `_descriptive_text`, `_num` (float-strict, still used by `_descriptive_text` and `_release_from_measured`), the form, the solver, the Raven reader, `coa_amb2.py` scoring, ND semantics (TASKS-282), the COA AMB2 workflow. `propuestas._coa_values` (the report's per-lot cell) still reads `value` before `result` — reported, not touched.
- Tests: `tests/test_13_12_7.py` (Hugh's 1.7/2.22 → 1.96 example against NMT 3 and NMT 2, 70/30 masses, over-limit blend, NO DATA naming, pH/worst-case with a lot without data, qualitative unchanged, the reader's precedence table, the preview's return shape).

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
