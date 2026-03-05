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
- Latest deployed commit: 1bb7360 (task_validator sync/fix ready)
- GitHub commits: 50e33b2 (task_validator), 1bb7360 (sync keywords)
- Pipeline Diagnosis working: @ai diagnose SAL-QTN-2024-00753 ✅

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
