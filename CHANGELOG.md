# Changelog

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
