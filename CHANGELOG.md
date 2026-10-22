# Changelog

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
