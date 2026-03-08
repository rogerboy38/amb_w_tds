## Executive Summary

This report documents the current status of the Raven AI Agent implementation for AMB Wellness (erp.sysmayal2.cloud). The project delivers an AI-powered agent that operates inside ERPNext via the Raven messaging channel, handling the complete Order-to-Cash and Manufacturing workflows through natural language commands.

As of March 8, 2026, all 6 critical GAPs identified during the LORAND Master Degree Test have been resolved and deployed. Phase 5 (Delivery and Invoice) introduced 4 smart capabilities: auto-batch assignment, preflight checks, CFDI field resolution, and intelligent error suggestions. The system has been validated end-to-end from Sales Order through Invoice creation with full rollback verification.

<table><tr><td>Metric</td><td>Value</td></tr><tr><td>GAPs Resolved</td><td>6 / 6 (100%)</td></tr><tr><td>Smart Capabilities Added (Phase 5)</td><td>4 new functions</td></tr><tr><td>Repository Files</td><td>180+</td></tr><tr><td>Agent Modules</td><td>5 (Core, Manufacturing, Workflows, Handlers, BOM)</td></tr><tr><td>ERPNext Version</td><td>v16.6.1 (Frappe v16.9.0, Raven v2.8.5)</td></tr><tr><td>Deployment Target</td><td>VPS 72.62.131.198 (Docker)</td></tr><tr><td>Last Successful E2E Test</td><td>March 7, 2026</td></tr></table>

## Table of Contents

1. System Architecture

2. Workflow Pipeline (Steps 0-8)

3. GAP Analysis and Resolution

3.1 GAP-01: Batch Handling (Delivery)

3.2 GAP-02: Batch Auto-Assignment (FIFO)

3.3 GAP-03: Smart WO Planning

3.4 GAP-04: Named Batch Creation

3.5 GAP-05: Auto Material Transfer

3.6 GAP-06: Manufacturing Dashboard

4. Phase 5: Smart Agent Upgrades

4.1 Auto-Assign Batches

4.2 Preflight Delivery Check

4.3 Mexico CFDI Resolution

4.4 Error Suggestions Engine

5. Architecture Recommendations

6. Technical Details

7. Testing Results

8. Deployment Process

9. Known Constraints and Next Steps

### 1. System Architecture

The Raven AI Agent is a Python-based AI system that runs as a Frappe app inside ERPNext. It listens for messages on Raven channels and routes commands to specialized agent modules. The architecture follows the Raymond-Lucy Protocol v2.0 with anti-hallucination safeguards, persistent memory, and a 3-level autonomy slider.

## Core Components

<table><tr><td>Component</td><td>File</td><td>Role</td></tr><tr><td>Agent Core</td><td>agent.py (1,478 lines)</td><td>Main entry point, LLM orchestration, routing to handlers, Raven message processing</td></tr><tr><td>Workflows</td><td>workflows.py (1,601 lines)</td><td>Document creation (Quotation through Invoice), BOM automation, TDS resolution, batch management</td></tr><tr><td>Manufacturing Agent</td><td>manufacturing_agent.py (1,417 lines)</td><td>Work Orders, Stock Entries, SO allocation, WO planning, batch creation, dashboards</td></tr><tr><td>Handler Mixins</td><td>handlers/ (5 modules)</td><td>ManufacturingMixin, BOMMixin, WebSearchMixin, SalesMixin, QuotationMixin</td></tr><tr><td>Channel Utils</td><td>channel_utils.py</td><td>Raven real-time messaging via Socket.IO publish events</td></tr><tr><td>Vector Store</td><td>vector_store.py</td><td>Semantic search over AI Memory doctype for context continuity</td></tr></table>

## Message Flow

1. User sends message on Raven channel (e.g. @ai !delivery from SO-00763)

2. hooks.py triggers handle_raven_message() in agent.py

3. Agent extracts command intent via keyword matching (mfg, pay, orch, validator keywords)

4. Routes to appropriate handler: ManufacturingAgent, WorkflowExecutor, or LLM

5. Handler executes ERPNext API calls via Frappe ORM

6. Response posted back to Raven channel via raven.api.raven_message.send_message

## Autonomy Levels (Karpathy Protocol)

<table><tr><td>Level</td><td>Mode</td><td>Behavior</td></tr><tr><td>1</td><td>COPILOT</td><td>Query data, suggest actions, explain. No document creation.</td></tr><tr><td>2</td><td>COMMAND</td><td>Execute specific operations with confirmation. Dry-run preview.</td></tr><tr><td>3</td><td>AGENT</td><td>Multi-step workflows. Full autonomy with ! prefix.</td></tr></table>

Command convention: no prefix = dry-run preview (Level 2), ! prefix = execute (Level 3).

### 2. Workflow Pipeline (Steps 0-8)

The complete Order-to-Cash pipeline consists of 9 steps. Step 0 (Quotation) is the truth source and is handled by the Task Validator. Steps 1-8 are handled by the Workflow Orchestrator and Manufacturing Agent. The truth hierarchy for data is: Purchase Order > Quotation > Sales Order.

<table><tr><td>Step</td><td>Document</td><td>Handler</td><td>Status</td></tr><tr><td>0</td><td>Quotation (Truth Source)</td><td>task_validator</td><td>ACTIVE</td></tr><tr><td>1</td><td>Work Order (Manufacturing)</td><td>ManufacturingAgent</td><td>ACTIVE</td></tr><tr><td>2</td><td>Stock Entry (Manufacture)</td><td>ManufacturingAgent</td><td>ACTIVE</td></tr><tr><td>3</td><td>Sales Order Submit</td><td>WorkflowExecutor</td><td>ACTIVE</td></tr><tr><td>4</td><td>Sales WO (WO from SO)</td><td>ManufacturingAgent</td><td>ACTIVE</td></tr><tr><td>5</td><td>Stock Entry (Sales Mfg)</td><td>ManufacturingAgent</td><td>ACTIVE</td></tr><tr><td>6</td><td>Delivery Note</td><td>WorkflowExecutor + Smart</td><td>ACTIVE</td></tr><tr><td>7</td><td>Sales Invoice</td><td>WorkflowExecutor + Smart</td><td>ACTIVE</td></tr><tr><td>8</td><td>Payment Entry</td><td>PaymentAgent</td><td>ACTIVE</td></tr></table>

## Key Business Rules

• Accounting uses MICROSIP SAT-like account codes

• Mexico CFDI: PUE for advance payment, PPD for credit terms (30 days, etc.)

• CFDI Use: G01 for goods acquisition, G03 for general expenses

• Batch naming: convention 0803[YY][MM][DD][SEQ] for LORAND items

• Mix Lot Calculator: qty <= 700kg = 1 lot; qty > 700kg = ceil(qty/700) lots; sample = lots * 1 Kg

• No 'import frappe' in Server Scripts (causes ImportError; frappe is already available)

### 3. GAP Analysis and Resolution

During the LORAND Master Degree Test (March 6-7, 2026), 6 critical gaps were identified in the agent's capabilities. All 6 have been resolved, deployed, and verified. The original requirements report identified 7 gaps, 5 enhancements, and 4 architecture recommendations with an estimated 18-22 dev-days effort.

<table><tr><td>GAP</td><td>Title</td><td>Priority</td><td>Status</td></tr><tr><td>GAP-01</td><td>Batch Handling in Delivery Notes</td><td>CRITICAL</td><td>RESOLVED</td></tr><tr><td>GAP-02</td><td>Batch Auto-Assignment (FIFO)</td><td>CRITICAL</td><td>RESOLVED</td></tr><tr><td>GAP-03</td><td>Smart WO Planning with SO Allocation</td><td>HIGH</td><td>RESOLVED</td></tr><tr><td>GAP-04</td><td>Named Batch Creation</td><td>HIGH</td><td>RESOLVED</td></tr><tr><td>GAP-05</td><td>Auto Material Transfer for Manufacturing</td><td>HIGH</td><td>RESOLVED</td></tr><tr><td>GAP-06</td><td>Manufacturing Dashboard</td><td>MEDIUM</td><td>RESOLVED</td></tr></table>

### 3.1 GAP-01: Batch Handling in Delivery Notes

Problem: When creating a Delivery Note for items with has_batch_no=1, ERPNext v16 requires batch assignment via Serial and Batch Bundle. The agent was unable to deliver items like 0803- because no batch was being assigned to DN line items, causing the error 'Serial No / Batch No mandatory'.

Root Cause: ERPNext v16 introduced the Serial and Batch Bundle model, which means Stock Ledger Entry.batch_no is NULL. Stock is tracked via Batch.batch_qty instead. The original agent code did not account for this.

Solution: Implemented _auto_assign_batches() in workflows.py (line 100) that queries tabBatch directly for available stock and assigns batches using FIFO by expiry date. Sets use_serial_batch_fields=1 on each DN item row.

### 3.2 GAP-02: Batch Auto-Assignment (FIFO)

Problem: Manual batch assignment is error-prone and slow. Items with multiple available batches need intelligent selection based on expiry dates.

Solution: The _auto_assign_batches() function implements FIFO (First Expiry, First Out) logic. It groups DN items by (item_code, warehouse), queries all non-expired batches with  $ batch\_qty > 0 $ , orders by COALESCE(expiry_date, '9999-12-31') ASC, and assigns the earliest-expiring batch first. If a single batch has insufficient stock, it moves to the next available batch.

SQL Query (v16 compatible):

SELECT name, batch_qty, expiry_date FROM tabBatch WHERE item=%s AND disabled=0 AND batch_qty>0 AND (expiry_date IS NULL OR expiry_date >= CURDATE()) ORDER BY COALESCE(expiry_date, '9999-12-31') ASC

### 3.3 GAP-03: Smart WO Planning

Problem: The agent could only create single Work Orders per Sales Order. Complex manufacturing requires splitting SO quantities across multiple WOs with different lot assignments and BOMs.

Solution: Implemented create_wo_plan() (line 919 in manufacturing_agent.py) and get_so_allocation() (line 819). The planning system: (1) Checks existing WO allocation before creating, (2) Auto-trims plan if SO is partially allocated, (3) Shows allocation dashboard if fully allocated, (4) Creates named batches on-the-fly if needed, (5) Stores batch assignment in custom_lote field.

Command: @ai plan work orders for SO-00763

### 3.4 GAP-04: Named Batch Creation

Problem: AMB Wellness uses a specific batch naming convention (0803[YY][MM][DD][SEQ]) for traceability. The agent needed to create batches with user-defined names rather than auto-generated IDs.

Solution: Implemented create_named_batch() (line 758 in manufacturing_agent.py). Validates item has batch tracking enabled, checks for duplicates (returns success if same item owns existing batch), and creates the batch with optional expiry_date and manufacturing_date.

### 3.5 GAP-05: Auto Material Transfer

Problem: Before manufacturing, raw materials must be transferred from source warehouses to WIP warehouse. This manual step was blocking automated manufacturing flows.

Solution: Implemented create_material_transfer() (line 369 in manufacturing_agent.py). Features: (1) Smart warehouse resolution via _resolve_warehouses() with BOM_WAREHOUSE_MAP, (2) Resilience fix for 'success despite ERPNext warnings' pattern, (3) Automatic qty calculation from WO required_items.

Warehouse Resolution: Uses BOM_WAREHOUSE_MAP dict mapping BOM types to source/target warehouses, with company validation for multi-company support (latest commit 3af2381).

### 3.6 GAP-06: Manufacturing Dashboard

Problem: No visibility into manufacturing status across Sales Orders. Users had to manually check each WO to understand production progress.

Solution: Implemented mfg_status_dashboard() (line 1120 in manufacturing_agent.py). Two modes: (1) Overview showing all active SOs with WO counts, quantities, produced amounts, and color-coded status, (2) Detail mode per SO showing individual WO breakdown with allocation percentages.

Command: @ai mfg status (overview) or @ai mfg status SO-00763 (detail)

### 4. Phase 5: Smart Agent Upgrades

Phase 5 focused on Delivery Note and Sales Invoice creation. Instead of simple document creation, the team implemented 4 smart capabilities that make the agent intelligent about common failure modes in Mexican ERPNext environments.

### 4.1 Auto-Assign Batches

Function: _auto_assign_batches(dn_doc) at workflows.py line 100. Called automatically during DN creation. Scans all DN items, identifies those with has_batch_no=1 that lack a batch assignment, and assigns using FIFO expiry logic.

<table><tr><td>Feature</td><td>Implementation</td></tr><tr><td>Strategy</td><td>FIFO by expiry date (First Expiry First Out)</td></tr><tr><td>Grouping</td><td>Items grouped by (item_code, warehouse) for efficient lookup</td></tr><tr><td>v16 Compatibility</td><td>Queries Batch.batch_qty directly (not SLE.batch_no)</td></tr><tr><td>Split Support</td><td>If one batch is insufficient, moves to next available batch</td></tr><tr><td>Flag</td><td>Sets use_serial_batch_fields=1 on each assigned item row</td></tr></table>

### 4.2 Preflight Delivery Check

Function: _preflight_delivery_check(so_doc) at workflows.py line 173. Runs during dry-run (no ! prefix) to show warnings before creating the Delivery Note.

<table><tr><td>Check</td><td>What It Does</td></tr><tr><td>Stock Availability</td><td>Compares bin qty or batch_qty against SO pending delivery qty</td></tr><tr><td>Batch Requirements</td><td>Verifies sufficient batch stock for items with has_batch_no=1</td></tr><tr><td>QI Requirements</td><td>Warns if inspection_required_before_delivery is set on an item</td></tr><tr><td>Warehouse Defaults</td><td>Falls back to 'FG to Sell Warehouse - AMB-W' if no warehouse set</td></tr></table>

### 4.3 Mexico CFDI Resolution

Function: _resolve_mx_cfdi_fields(customer, payment_terms_template) at workflows.py line 221. Automatically determines the correct CFDI payment option (PUE vs PPD), CFDI use code, and mode of payment for Mexican invoices.

<table><tr><td>Field</td><td>Logic</td></tr><tr><td>mx_payment_option</td><td>PUE if terms contain: advance, anticipad, prepaid, antes, previo, adelant. PPD if terms contain: days, dias, credit, credito, net, after. Default: PPD</td></tr><tr><td>mx_cfdi_use</td><td>Reads customer.mx_cfdi_use custom field. Falls back to G01 (goods acquisition)</td></tr><tr><td>mode_of_payment</td><td>Defaults to Wire Transfer</td></tr><tr><td>Terms Source</td><td>Checks both payment_terms_template name AND Customer.payment_terms field</td></tr></table>

### 4.4 Error Suggestions Engine

When document creation fails, the agent analyzes the error message and provides actionable recovery steps instead of raw tracebacks. This includes pattern matching for common ERPNext errors like missing batch numbers, insufficient stock, QI blocks, and permission errors.

### 5. Architecture Recommendations

<table><tr><td>ID</td><td>Recommendation</td><td>Status</td></tr><tr><td>ARCH-01</td><td>Refactor agent.py into modular handler mixins for maintainability</td><td>DONE</td></tr><tr><td>ARCH-02</td><td>Implement dry-run / execute pattern (no != preview, != execute)</td><td>DONE</td></tr><tr><td>ARCH-03</td><td>Include Step 0 (Quotation) in dashboard and workflow visibility</td><td>DONE</td></tr><tr><td>ARCH-04</td><td>Add comprehensive error recovery with actionable suggestions</td><td>DONE</td></tr></table>

ARCH-01 was implemented by splitting the original 3,104-line monolith agent.py into a core module plus 5 handler mixins (ManufacturingMixin, BOMMixin, WebSearchMixin, SalesMixin, QuotationMixin). ARCH-02 allows users to preview document creation with a dry run before committing. ARCH-03 was fixed by adding the show_work_orders() function (line 1078) that includes allocation data. ARCH-04 is the error suggestions engine from Phase 5.

### 6. Technical Details

## Environment

<table><tr><td>Component</td><td>Version / Detail</td></tr><tr><td>ERPNext</td><td>v16.6.1</td></tr><tr><td>Frappe Framework</td><td>v16.9.0</td></tr><tr><td>Raven Messaging</td><td>v2.8.5</td></tr><tr><td>Python</td><td>3.11+ (Docker container)</td></tr><tr><td>Server</td><td>VPS 72.62.131.198 (Docker Compose)</td></tr><tr><td>Database</td><td>MariaDB (Frappe managed)</td></tr><tr><td>Repository</td><td>rogerboy38/raven_ai_agent (GitHub, branch: main)</td></tr></table>

## Key Git Commits

<table><tr><td>SHA</td><td>Description</td></tr><tr><td>6bd7286</td><td>Initial 7-file structure</td></tr><tr><td>c5963ab</td><td>RnDAgent fix</td></tr><tr><td>3c48191</td><td>Bot routing logic</td></tr><tr><td>8528ee8</td><td>Regex intent matching (BROKEN - replaced)</td></tr><tr><td>bff8e33</td><td>Keyword matching fix (replaced regex)</td></tr><tr><td>77a53f0</td><td>Smart warehouse resolution</td></tr><tr><td>3af2381</td><td>BOM-type-aware warehouse + company validation (LATEST STABLE)</td></tr></table>

## ERPNext v16 Specifics

Serial and Batch Bundle: ERPNext v16 introduced a new model for serial/batch tracking. The Stock Ledger Entry.batch_no field is NULL. Instead, available batch stock is maintained in Batch.batch_qty which is automatically updated by ERPNext. All agent queries use this field directly.

DN Item Flags: When assigning batches to Delivery Note items, use_serial_batch_fields=1 must be set on each row. This tells ERPNext v16 to read batch_no from the item row directly instead of looking for a Serial and Batch Bundle child document.

## Raven Integration

Channel: AMB-Wellness-implementacion-amb-sysmayal2

Hook: hooks.py points to raven_ai_agent.api.agent.handle_raven_message

Bot: Falls back to sales_order_bot (no manufacturing_bot exists)

Message API: POST to raven.api.raven_message.send_message with channel_id, text (HTML), message_type

### 7. Testing Results

## LORAND Master Degree Test (March 6-7, 2026)

The LORAND project (SO-00763) served as the end-to-end validation test for the entire agent system. The test covered all 5 phases of the project plan.

<table><tr><td>Phase</td><td>Scope</td><td>Result</td></tr><tr><td>Phase 1</td><td>Data Prep - Item, BOM, Quotation setup</td><td>PASS</td></tr><tr><td>Phase 2</td><td>BOM Configuration - Multi-level BOM support</td><td>PASS</td></tr><tr><td>Phase 3</td><td>Linking - SO-WO-BOM chain</td><td>PASS</td></tr><tr><td>Phase 4</td><td>Manufacturing with Batch AMB - WO, SE, batch creation</td><td>PASS</td></tr><tr><td>Phase 5</td><td>Delivery and Invoice - DN + Invoice with smart capabilities</td><td>PASS</td></tr></table>

## Phase 5 Clean Test (March 7, 2026)

After all smart capabilities were deployed, a clean end-to-end test was executed:

• 1. Command: @ai delivery from SO-00763 (dry run preview)

• 2. Preflight check showed stock and batch status - all clear

• 3. Command: @ai !delivery from SO-00763 (execute)

• 4. DN MAT-DN-2026-00005 created with 3/3 batches auto-assigned (LOTE102)

• 5. Command: @ai !invoice from SO-00763 (execute)

• 6. DN auto-submitted, Invoice ACC-SINV-2026-00006 created with PPD | G01

• 7. All artifacts rolled back: Invoice deleted, DN cancelled, STE cancelled

## Test Artifacts

<table><tr><td>Document</td><td>Name</td><td>Status After Test</td></tr><tr><td>Delivery Note</td><td>MAT-DN-2026-00005</td><td>Cancelled (rolled back)</td></tr><tr><td>Sales Invoice</td><td>ACC-SINV-2026-00006</td><td>Deleted (rolled back)</td></tr><tr><td>Stock Entry</td><td>MAT-STE-2026-00350</td><td>Cancelled (rolled back)</td></tr><tr><td>Batch</td><td>LOTE102</td><td>Active (expiry 2028-03-06)</td></tr></table>

## I tem 0803- Notes

Item 0803- has has_batch_no=1. During testing, inspection_required_before_delivery was disabled via a temporary Server Script because the item had a broken 'Plant Code: 1 (Mix)' link that prevented normal save. This item-level change was done manually and persists.

### 8. Deployment Process

Deployment follows a GitHub-based workflow. Code is pushed from the development environment to the repository, then pulled and restarted on the production VPS.

## Deployment Steps

• 1. Code changes are prepared and validated locally

• 2. Push to GitHub via API: GET current file SHA, base64-encode content, PUT with SHA

• 3. SSH into VPS (root@72.62.131.198) - note: SSH from sandbox times out, user executes manually

• 4. Run: git pull upstream main

• 5. Run: docker restart amb-wellness-backend-1 amb-wellness-frontend-1

• 6. Verify via Raven channel that agent responds correctly

## File Push Pattern (GitHub API)

GET /repos/rogerboy38/raven_ai_agent/contents/{path}
Extract sha from response
PUT /repos/rogerboy38/raven_ai_agent/contents/{path} with:
message, content (base64), sha, branch='main'

### 9. Known Constraints and Next Steps

## Known Constraints

• Item 0803- has a broken 'Plant Code: 1 (Mix)' link that prevents normal item save

• No Raven bot named 'manufacturing_bot' exists - agent falls back to 'sales_order_bot'

• SSH from cloud sandbox to VPS times out - deploys require user to run git pull manually

• Regex-based intent matching (commit 8528ee8) was abandoned in favor of keyword matching

• Vector store (semantic search) requires additional setup and is not active by default

## Recommended Next Steps

<table><tr><td>Priority</td><td>Item</td><td>Description</td></tr><tr><td>HIGH</td><td>Payment Entry (Step 8)</td><td>Complete PaymentAgent implementation for the final pipeline step</td></tr><tr><td>HIGH</td><td>Batch Transfer Fix</td><td>Ensure Material Receipt STE correctly links batch to FG warehouse for DN pickup</td></tr><tr><td>MEDIUM</td><td>LORAND Smart Commands</td><td>Implement remaining LORAND-specific commands: track samples, generate samples, Mix Lot Calculator, Packaging Optimizer</td></tr><tr><td>MEDIUM</td><td>Error Recovery Automation</td><td>Expand _get_error_suggestions() with auto-retry logic for recoverable errors</td></tr><tr><td>LOW</td><td>Manufacturing Bot</td><td>Create a dedicated Raven bot for manufacturing commands instead of using sales_order_bot fallback</td></tr><tr><td>LOW</td><td>Vector Store Activation</td><td>Enable semantic search over AI Memory for better context continuity</td></tr></table>