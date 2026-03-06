# AMB-Wellness ERPNext Development - Persistent Memory

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
