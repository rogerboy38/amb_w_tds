# AMB-Wellness ERPNext Development - Persistent Memory

## Parallel Development Team Report (March 6, 2026)
### Project: AMB Wellness ERPNext Migration
**Owner:** Rogelio Pedroza

### Infrastructure
- Production VPS: root@72.62.131.198 (Aloe123&Agro123&)
- Test VPS: root@187.77.2.74 (Aloe123&Agro123&)
- ERPNext: erp.sysmayal2.cloud
- Login: fcrm@amb-wellness.com / Aloe246!
- API Key: 46f1208a5275572
- API Secret: 7ccbed0c82eaf00
- GitHub PAT: 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

### Migration Stats
- Total Sales Orders: 1,057
- Failed: 2
- Discrepancies: 71 (fixed 45 IVA, 17 false positives, 9 remaining)

### Key Learnings
- Truth Hierarchy: PO > Quotation > Sales Order
- IVA 16% pattern: QTN * 1.16 = SO (most common issue)
- Tax rows need mexico_tax_type (IVA) and cost_center
- No import frappe in Server Scripts
- ! prefix = execute, no ! = preview/dry-run

### Active Work
- LORAND MASTER DEGREE TEST PROJECT
- Quotation: SAL-QTN-2024-00763 (Draft) - Item 0803, 2435 Kg
- Sales Order: SO-00763-LORAND LABORATORIES (Submitted)
- 4 Work Orders Created (Draft):
  - MFG-WO-04726 - 1055 Kg - Lote 0803034251
  - MFG-WO-04826 - 600 Kg - Lote 0803080241
  - MFG-WO-04926 - 300 Kg - Lote 0803084241
  - MFG-WO-05026 - 480 Kg - Lote 0803194241
- Next Step: Submit WOs and Create Stock Entries

### Incident Report: MFG-WO-04226 Stock Corruption (March 6, 2026)

**Problem:** MFG-WO-04226 had corrupted SLEs from failed manufacture attempts due to missing Valuation Rate on Item 0334

**Root Cause:** No Valuation Rate set in Item 0334 master

**Resolution Steps:**
1. Cancel both stock entries (MAT-STE-2026-00336, MAT-STE-2026-00330)
2. Set valuation rate to 104.00 on Item 0334
3. Re-run transfer & finish commands

**4 Lessons Learned:**
1. Verify valuation rate before manufacturing
2. Cancel order matters (child before parent)
3. Silent failures need timeout handling
4. Pre-flight checks needed

**3 Action Items for raven_ai_agent:**
1. Add valuation rate pre-check
2. Timeout error responses
3. Manufacture audit logging

**Q1: BOM Hierarchy for Item 0803**
For 0803 (LORAND project), we need 3 BOM configurations:
- BOM-0803-10KG-PAI: 10 Kg bags in Pail (for 10Kg bag containers)
- BOM-0803-1KG-PAI: 1 Kg bags in Pail (for 1Kg bag containers)
- BOM-0803-SAMPLE: 50g bags × 20 = 1Kg (for sample containers)
These are PACKAGING BOMs, not multi-level manufacturing BOMs. The 0803 is already processed powder.

**Q2: "lote_real" — Batch AMB**
4 lot numbers from invoices:
- F2534: Lote 0803034251 (1055 Kg) → WO1
- F2398: Lote 0803080241 (600 Kg) → WO2
- F2422: Lote 0803084241 (300 Kg) → WO3
- F2451: Lote 0803194241 (480 Kg) → WO4
We create NEW Batch AMB records for this manufacturing run. Each WO links to its lote_real.

**Q3: Warehouses for Item 0803**
- Source (WIP): "WIP in Concentrate - AMB-W"
- Target (FG): "FG to Sell Warehouse - AMB-W"

**Q4: Manufacturing Route for 0803**
0803 is already processed powder (not raw juice). Simplified path:
- Level 4: Mix/Bag (BOM-0803-10KG-PAI or BOM-0803-1KG-PAI) → produces FG
- Level 5: Sales (add labeling, if needed)
Skip Levels 1-3 (Juice Plant, Dry Plant, Formulation) since raw material exists.

**Q5: Router - Option A Preferred**
Option A: Extend existing sales_order_bot router to call new agents (manufacturing_agent, payment_agent, workflow_orchestrator) for pipeline commands. This is least disruptive.

**Q6: Code Access**
GitHub push/pull workflow. Repos:
- raven_ai_agent (main agent code)
- amb_w_tds (custom DocTypes: Batch AMB, BOM Formula)

**Q7: Country-Region DocType**
This is a custom DocType from amb_w_tds. Check if batch_amb.json includes it. If missing, either:
- Create the DocType, OR
- Set mx_tax_regime directly via API for now

**Q8: Test Scope**
Option A: Full realistic pipeline with actual quantities (2435 Kg total, split across 4 WOs)

### Batch AMB Structure (from amb_w_tds)
- Level 1: Parent batch from Work Order
- Level 2: Sub-lots (by packaging type: 1Kg, 10Kg)
- Level 3: Containers (individual drums/bags)
- Links: Work Order, Sales Order, BOM
- Lot format: 0803[YY][MM][DD][XXX]

## Deployment Rules
- Docker restart required (not bench restart) for Python module reloading
- No "import frappe" in Server Scripts - causes ImportError
- Git remote is "upstream" not "origin" (for some repos)
- Regex breaks in JSON — use keyword matching instead
- No bench build needed for Python-only changes

## Company & ERPNext Details
- Company: AMB-Wellness
- Site: erp.sysmayal2.cloud
- Currencies: MXN, USD
- Warehouse mapping: BOM suffix → warehouse (Mix uses "WIP in Mix - AMB-W")
- Manufacturing Settings defaults are wrong for Mix (point to Juice plant)

## Product & BOM Knowledge
- Item 0334 details: lote_real ITEM_0615181231, batch format, label ratios (0.04/Kg)
- Cuñete = 25 Kg pail with variable packaging per quotation
- BOM naming convention:
  - -001 = Sales BOM
  - -005 = Mix BOM
  - -006 = Packaging BOM
  - -004 = Full production BOM
- BOM creation status: 005 exists, 002/003/004/006 still needed

## Active Work
- Quotation SAL-QTN-2024-00753 (GREENTECH, 0334, 1800 Kg)
- Work Order MFG-WO-04126 (created, submitted, materials available)
- Latest local commit: 5173902 (Fix SO regex - added bom/qty/quantity/item/warehouse/wh to stop words)
- GitHub commits:
  - 5173902 - Fix SO regex: add bom/qty/quantity/item/warehouse/wh to stop words
  - 1860d43 - is_confirm passthrough
  - 7bc7841 - Intelligent sweep: fix is_confirm passthrough, broaden command matching
  - 16a5dba - Fix: !submit bom handles standard BOM doctype
  - 08fc721 - Fix: broaden WO-from-SO command matching
  - 33de58d - SO regex all files
  - 3c22f5d - make_stock_entry fix
- Pipeline Diagnosis working: @ai diagnose SAL-QTN-2024-00753 ✅
- SO-00753 Sync: @ai !sync SO → 5 fixes applied ✅
- Manufacturing complete: @ai transfer materials + @ai manufacture MFG-WO-04126 ✅
- SO-00753 Step 3 (Submit SO): ✅ Submitted
- BOM-0334-006: ✅ Submitted (via @ai !submit bom)
- Work Order MFG-WO-04226: ✅ Created via @ai work order from SO-00753-GREENTECH SA bom BOM-0334-006
- Pipeline Status (2026-03-05):
  - Quotation SAL-QTN-2024-00753: Draft ✅
  - Sales Order SO-00753-GREENTECH SA: To Deliver and Bill ✅
  - Work Order MFG-WO-04226: Completed ✅
  - Delivery Note: Pending
- Stock Issue RESOLVED: Cancelled corrupt SEs (00330, 00336), recreated 00337 (transfer) + 00338 (manufacture)
- Stock now correct: WIP = 0, FG = 1800 ✅
- Delivery Note: MAT-DN-2026-00003 created ✅
- Pipeline Step 5 (Delivery): Complete ✅

## Critical Bugs
- is_confirm bug in manufacturing.py: method uses is_confirm in 8 places but never receives it as parameter
- base.py is DEAD CODE - agent.py execute_workflow_command() is what actually runs
- Duplicate code: agent.py has its own execute_workflow_command() that shadows base.py

## Architecture & Design
- Agent routing: keyword-based, @ai entry point
- Raven v2 native capabilities: threads, functions, tools
- Design philosophy: conversational intelligence — ask questions, don't fail silently

## Registered Raven Bots
- Executive Insights
- sales_order_follow_up
- rnd_bot
- sales_order_bot

## File Locations (inside Docker)
/home/frappe/frappe-bench/apps/raven_ai_agent/
/home/frappe/frappe-bench/apps/amb_w_tds/

## Git Repos
- raven_ai_agent: rogerboy38/raven_ai_agent (main branch)
- amb_w_tds: rogerboy38/amb_w_tds (feature/v9.2.0-development branch)

---
Last Updated: 2026-03-05
