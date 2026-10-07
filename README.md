# AMB W TDS

[![Version](https://img.shields.io/badge/version-v14.0.0-blue.svg)](https://github.com/rogerboy38/amb_w_tds/releases/tag/v14.0.0)
[![Frappe](https://img.shields.io/badge/frappe-v16.17.5-orange.svg)](https://github.com/frappe/frappe/tree/v16.17.5)
[![Python](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](license.txt)

> Frappe / ERPNext app for AMB-Wellness: Technical Data Sheets (TDS), Certificates of
> Analysis (COA), BOM Formula and formulation, Sample Requests, Quotation AMB and the
> selling-side customizations that go with them.

---

## Current status (2026-10-06)

| Line | Commit | Date | What it is |
|------|--------|------|------------|
| `main` | `ceffabe` | 2026-08-16 | Trunk. CI runs on every push and pull request to `main`. |
| Production | `646ba26` (tag `prod-pin-646ba26`, "t9a") | 2026-09-10 | What production runs. Built from Phase E/F work plus the role home-page hotfix; not yet merged to `main`. |
| In flight | `phase-g/*` branches | 2026-09-08 → 09-11 | BOM Formula FoxPro-parity tabs and COA AMB2 compliance port. See [Work in progress](#work-in-progress-not-yet-on-main). |

**Version numbering.** The latest release tag is **v14.0.0**. The package itself still
reports `13.7.0` in `amb_w_tds/__init__.py`, and `version.txt` still reads `10.0.0`; neither
has been bumped since April 2026.

---

## Relationship with `amb_w_spc` (required)

AMB-Wellness runs two companion apps on the same site. **`amb_w_spc` must be installed
alongside `amb_w_tds`.** Several features here call into DocTypes and controllers that
live there.

| App | Owns |
|-----|------|
| **amb_w_tds** (this repo) | TDS, COA, BOM / BOM Formula, Formulation, Quotation, Sales, Customer, CRM, HR-light and Logistics DocTypes and customizations |
| **amb_w_spc** | QC, Manufacturing, SPC, Stock, Warehouse and Work Order DocTypes, including the **Batch AMB** controller and **Plant Configuration** |

Rules of thumb:

- A DocType override for anything migrated to `amb_w_spc` (Batch AMB, etc.) belongs in
  `amb_w_spc/hooks.py`, not here. `override_doctype_class` in this app is intentionally empty.
- Fixtures are filtered by DocType, not by module, using `_AMB_W_TDS_DOCTYPES` in
  `amb_w_tds/hooks.py`. Shared ERPNext DocTypes go to whichever app has the dominant use.
- Sample Request AMB callers that need Batch AMB data are routed to `amb_w_spc`.

---

## Functional areas

The app defines **49 DocTypes** in the `Amb W Tds` module (`amb_w_tds/amb_w_tds/doctype/`).

### Technical Data Sheets
- **TDS Product Specification** and **TDS Product Specification V2**, with **TDS Settings**,
  **TDS Default Parameter**, **TDS Preservative**.
- Server-side FoxPro-style TDS PDF generation.
- Shelf-life auto-fill gated by substrate, so powder specs never take liquid text (T62).
- Quality Inspection Parameter picker with a 3-level family / sub-group / parameter tree
  (Phase 1C tab).

### Certificates of Analysis
- **COA AMB** and **COA AMB2**, with **COA Quality Test Parameter** and **COA Preservative**.
- Numeric and qualitative compliance scoring; a bound of `0` means "no bound", so NLT / NMT
  specs score correctly.
- COA workflow with a Reopen path, corrected parameter table and muted workflow emails.
- Governance rules: no self-approval, explicit Reject, AMB2 mirroring.
- FoxPro-format COA PDF via the print pipeline; COA numbers derived from the unique name.

### BOM Formula and formulation
- **BOM Formula** with child tables for amino acids, juice inputs, mix inputs and predicted
  analytics; **BOM Template**, **BOM Version**, **BOM Enhancement**.
- Formulation engine (`amb_w_tds/formulation/engine.py`) driving the Mix and Juice tabs,
  with calibrated coefficients and scrap parameters.
- **Formulation** workspace and Frappe v16 sidebar for the BOM Formula lane.

### Sales and sampling
- **Quotation AMB** and **Quotation AMB Sales Partner**.
- **Sample Request AMB** with net / tare / gross weight model, AMB control numbers,
  golden-number auto-fetch from the linked COA, COA and TDS print buttons, and a 4-role
  permission model encoded in the DocType.
- **AMB Pack Plan Item** child table on Quotation and Sales Order
  (`amb_w_tds/selling_edge/pack_plan.py`).
- Proforma print format **proforma_amb_26**.

### Cost and KPI
- **Amb KPI Factors**, **AMB Cost Factors**, **KPI Cost Breakdown**.
- **AMB Cost & KPI Dashboard** desk page (`amb_cost_dashboard`).

### R&D, regulatory and market
- **Product Development Project**, **Animal Trial**, **Product Compliance**,
  **Country Regulation**, **Certification Document**, **Market Research**,
  **Market Entry Plan**, **Distribution Organization** / **Distribution Contact**,
  **Preservative System** / **Preservative Composition**.

### Containers and lots
- **Barrel**, **Container Selection**, **Container Type Rule**, **Container Sync Log**,
  **Lote AMB**, **Production Plant AMB**, **Juice Conversion Config**.

---

## Work in progress (not yet on `main`)

These lines are newer than `main`. Some of them already run in production through the
prod pins listed below.

### Production pins (tags)

| Tag | Production date | Contents |
|-----|-----------------|----------|
| `prod-pin-6da3edd` | 2026-09-06 | t7: E-1 Sprint 1.1 content (MEMCAL coefficients, FMIX L1 proposal) and E-3 Mix Input native fields |
| `prod-pin-a4cd188` | 2026-09-07 | t8: F-L1 RND Manager DocPerm on BOM Formula; F-L2 retire stale AmbAgent adapters |
| `prod-pin-deb28f0` | 2026-09-08 | t9: E-4 Producción rulings (line_class, pH mass-average, RC 0.85, shelf life 730 days) |
| `prod-pin-646ba26` | 2026-09-11 | t9a: clear nine pre-v16 `Role.home_page` routes that 404 at the site root |

### Open branches

| Branch | Tip | Topic |
|--------|-----|-------|
| `phase-g/g1a-tabs` | `4ad591a` (2026-09-09) | G-1a: BOM Formula FoxPro-parity tabs, controller re-pointed to native tables, 16 predicted analytic rows, blend engine locked to the LORAND F-2886-26 reference arithmetic |
| `phase-g/g0b1-coa-amb2-port` | `03a4400` (2026-09-09) | Port COA AMB's fixed compliance methods to COA AMB2, with scorer tests |
| `phase-g/g0b-2a` | `a2b6d8c` (2026-09-11) | Cut 2 of t10: resolve a Mix line to its lot's COA, real cost gate, plus G-0b-1 and the role home-page fix folded in |

Also carried on these branches and not yet on `main`:

- **bug208** (2026-08-20 → 21): customs value, weight and UoM on one valuation contract;
  currency bound to the field; zero-bag shipment warning.
- **loop1** (2026-08-24): `amb_lot_identity`, a single lot-identity resolver.

---

## Installation

### Prerequisites

| Component | Version |
|-----------|---------|
| Frappe Framework | v16.17.5 (what production runs) |
| ERPNext | v16 (this app customizes BOM, Quotation, Sales Order, Customer and other ERPNext DocTypes) |
| `amb_w_spc` | required, install first |
| Python | 3.14 (Frappe v16.17.5 requires `>=3.14,<3.15`) |
| Node.js | 24 or later |
| MariaDB | with `utf8mb4` / `utf8mb4_unicode_ci` |

### Install

```bash
# Companion app first
bench get-app https://github.com/rogerboy38/amb_w_spc.git
bench --site your-site.com install-app amb_w_spc

# This app
bench get-app https://github.com/rogerboy38/amb_w_tds.git --branch main
bench --site your-site.com install-app amb_w_tds

bench --site your-site.com migrate
bench build --app amb_w_tds
bench --site your-site.com clear-cache
bench restart
```

`migrate` runs the patches in `amb_w_tds/patches.txt`. Some of them are fail-closed and
abort rather than leave a site half-migrated; read the comment above a patch before
forcing it.

---

## Development

### Tests

```bash
bench --site your-site.com set-config allow_tests true
bench --site your-site.com run-tests --app amb_w_tds
```

### Continuous integration

| Workflow | What it does |
|----------|--------------|
| `ci.yml` | Builds a bench on Frappe v16.17.5, Python 3.14, Node 24 and MariaDB, installs the app on a fresh site and runs the server tests. Triggers on push and pull request to `main`. |
| `linter.yml` | Semgrep with the Frappe rule set, plus Python correctness rules. |
| `repo-hygiene.yml` | Fails on self-referential symlinks and module-name casing drift (the module is always `Amb W Tds`). |

### Fixtures

Export with `bench export-fixtures --app amb_w_tds`. The fixture list in `hooks.py`
covers Custom Fields, Property Setters, Client and Server Scripts, Workflows, Roles,
Print Formats, Reports, Workspaces and more, filtered by the DocTypes this app owns.

---

## Project structure

```
amb_w_tds/
├── amb_w_tds/
│   ├── amb_w_tds/            # Module "Amb W Tds"
│   │   ├── doctype/          # 49 DocTypes
│   │   ├── page/             # amb_cost_dashboard
│   │   ├── print_format/     # proforma_amb_26
│   │   └── workspace/        # Formulation
│   ├── api/                  # Whitelisted endpoints (batch, BOM, containers, quotation, picker, validate)
│   ├── formulation/          # Formulation / blend engine
│   ├── selling_edge/         # Pack Plan on Quotation and Sales Order
│   ├── services/             # BOM and cost-calculation services
│   ├── raven/                # Raven chat-agent commands
│   ├── fixtures/             # Exported customizations
│   ├── patches/              # Migration patches (see patches.txt)
│   ├── public/               # JS / CSS assets
│   ├── templates/, www/      # Web templates and pages
│   ├── workspace/            # ERPNext workspace overrides
│   └── hooks.py
├── docs/                     # SOPs, phase handouts, V13.5.0 reports
├── scripts/                  # Maintenance scripts
├── .github/workflows/        # CI, linter, repo hygiene
└── pyproject.toml
```

---

## Raven AI agent

The `amb_w_tds/raven/` module still provides `serial …` and `bom …` chat commands for
the Raven agent. The command reference lives in
[`amb_w_tds/raven/RAVEN_COMMANDS_HELP.md`](amb_w_tds/raven/RAVEN_COMMANDS_HELP.md).
The older HTTP agent twins under `api/agent*` that minted Batch AMB were deleted on
`main` in August 2026, and the dormant AmbAgent v14 adapters are retired on the
Phase F line.

---

## Release history

| Version | Date | Highlights |
|---------|------|------------|
| main (untagged) | 2026-05 → 08 | Sample Request AMB documents and permissions, COA compliance fixes, Pack Plan, Formulation workspace and Mix / Juice tabs, Cost & KPI dashboard, module-name cleanup, CI repaired and pinned to Frappe v16.17.5, agent twins removed |
| v14.0.0 | 2026-05-01 | Same commit as v13.8.1 |
| v13.8.1 | 2026-05-01 | Batch AMB dashboard override removed; `amb_w_spc` owns it |
| v13.8.0 | 2026-05-01 | Fixtures shipped, dashboard module |
| v13.7.0 | 2026-04-30 | Release bump to 13.7.0 |
| v13.6.0 | 2026-04-24 | Kill-patch for migrated Server Scripts |
| v13.5.0 | 2026-04-23 | Fixtures phase P2 certified |
| v10.0.0 | 2026-03-27 | — |
| v9.1.0 | 2026-02 | BOM hierarchy and Raven AI agent |
| v9.0.0 | 2026-01 | BOM Status Manager |

Older release notes: [`v8.6.0`](v8.6.0_RELEASE_NOTES.md), [`v8.7.0`](v8.7.0_RELEASE_NOTES.md),
[`v9.1.0`](v9.1.0_RELEASE_NOTES.md).

---

## License

MIT. See [license.txt](license.txt).

**Maintained by** the AMB-Wellness team · support@amb-wellness.com
