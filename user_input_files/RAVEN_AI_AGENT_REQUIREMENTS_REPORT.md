# Raven AI Agent — Manufacturing Intelligence Requirements Report

**Version:** 1.0  
**Date:** March 7, 2026  
**Author:** Computer (Perplexity) — Commissioned by Rogelio Pedroza  
**Test Case:** LORAND MASTER DEGREE TEST (SO-00763, Item 0803 Variant)  
**Repository:** `rogerboy38/raven_ai_agent` (branch: main)  
**Target Files:**
- `raven_ai_agent/api/handlers/manufacturing.py` (619 lines — ManufacturingMixin)
- `raven_ai_agent/agents/manufacturing_agent.py` (765 lines — ManufacturingAgent)
- `raven_ai_agent/agents/workflow_orchestrator.py` (692 lines — WorkflowOrchestrator)

---

## Executive Summary

During the LORAND MASTER DEGREE TEST (variant item `0803- KOSHER-ORGANIC-LAS3-HADS NMT 2 PPM-ACM 15/20` from SO-00763), we completed the full manufacturing cycle: 6 BOMs created (3 template + 3 variant), 4 Work Orders (MFG-WO-04726 through MFG-WO-05026) — all reaching Completed status. However, **critical gaps** were uncovered that prevented full Raven-native execution and required manual API intervention.

This report documents **7 critical gaps, 5 enhancements, and 4 architectural recommendations** for the parallel development team to implement.

---

## 1. CRITICAL GAPS (Blockers Found During Test)

### GAP-01: Batch/Lote Handling in Material Transfer & Manufacture

**Severity:** CRITICAL — Blocks `transfer materials` and `finish work order` for batch-tracked items  
**Files Affected:** `manufacturing_handler.py` (lines 280-306, 308-338), `manufacturing_agent.py` (lines 325-376, 262-323)  
**Error Observed:** `SerialNoRequiredError: "Serial No / Batch No are mandatory for Item [item_code]"`

**Current State:**
- `manufacturing_handler.py` lines 433-453 (Material Receipt) already has batch logic — it looks up existing batches or creates new ones.
- But `issue materials` (line 280) and `finish work order` (line 308) both call `make_stock_entry()` from ERPNext core and do NOT set `batch_no` on the resulting items.
- `manufacturing_agent.py` `create_material_transfer()` (line 325) and `create_stock_entry_manufacture()` (line 262) have the same omission.

**Required Changes:**

```python
# After calling make_stock_entry(), iterate over items and set batch_no:
se_dict = make_stock_entry(wo_name, purpose, qty)
se = frappe.get_doc(se_dict)

for item in se.items:
    if frappe.db.get_value("Item", item.item_code, "has_batch_no"):
        # Check if a specific batch was requested (from WO custom field or command parameter)
        requested_batch = get_requested_batch(wo_name, item.item_code)  # NEW
        if requested_batch:
            item.batch_no = requested_batch
        else:
            # Fallback: find existing batch with available qty
            batch = find_batch_with_qty(item.item_code, item.s_warehouse, item.qty)
            if batch:
                item.batch_no = batch
            else:
                # Auto-create batch if item.create_new_batch == 1
                if frappe.db.get_value("Item", item.item_code, "create_new_batch"):
                    new_batch = create_batch(item.item_code)
                    item.batch_no = new_batch
                # else: allow_negative_stock may still permit submission
```

**Acceptance Criteria:**
1. `@ai transfer materials MFG-WO-XXXXX` works for items with `has_batch_no=1`
2. `@ai !finish work order MFG-WO-XXXXX` correctly assigns batch on the FG item row
3. Both commands accept optional `batch [BATCH-NAME]` parameter
4. If no batch specified, auto-select most recent batch with available qty
5. If `create_new_batch=1` on item, auto-create a new batch

---

### GAP-02: Variant Item BOM Resolution

**Severity:** CRITICAL — Bot cannot find BOMs for variant items  
**Files Affected:** `manufacturing_handler.py` (line 57), `manufacturing_agent.py` (lines 72-80)

**Current State:**
- BOM lookup uses: `frappe.db.get_value("BOM", {"item": item_code, "is_active": 1, "is_default": 1}, "name")`
- For variant items (e.g. `0803- KOSHER-ORGANIC-LAS3-HADS NMT 2 PPM-ACM 15/20`), the default BOM must be set ON THE VARIANT specifically, not on the template `0803`.
- The current code does NOT fall back to the template item's BOM.

**Required Changes:**

```python
def resolve_bom(item_code):
    """Smart BOM resolution: variant → template fallback"""
    # 1. Try direct BOM on item
    bom = frappe.db.get_value("BOM",
        {"item": item_code, "is_active": 1, "is_default": 1, "docstatus": 1}, "name")
    if bom:
        return bom
    
    # 2. Try any active BOM on item (non-default)
    bom = frappe.db.get_value("BOM",
        {"item": item_code, "is_active": 1, "docstatus": 1}, "name")
    if bom:
        return bom
    
    # 3. If variant, try template item's BOM
    variant_of = frappe.db.get_value("Item", item_code, "variant_of")
    if variant_of:
        bom = frappe.db.get_value("BOM",
            {"item": variant_of, "is_active": 1, "is_default": 1, "docstatus": 1}, "name")
        if bom:
            return bom
    
    return None
```

**Acceptance Criteria:**
1. `@ai create work order for 0803-VARIANT qty 100` finds the template BOM if no variant BOM exists
2. If both template and variant BOMs exist, variant BOM takes priority
3. Response message indicates which BOM was used and whether it was inherited from template

---

### GAP-03: Multi-Work-Order Plan (Custom WO Split from SO)

**Severity:** CRITICAL — Cannot execute production plans with multiple WOs per SO line  
**Files Affected:** `manufacturing_agent.py` (lines 184-258), `manufacturing_handler.py` (lines 42-83)

**Current State:**
- `create_work_order_from_so()` creates exactly 1 WO per SO line item with the full SO qty.
- For SO-00763 (2096 Kg), it created one WO for 2096 Kg.
- AMB's production planning requires SPLITTING into multiple WOs with specific lote/batch assignments:
  - WO1: 1055 Kg — Lote 0803034251
  - WO2: 600 Kg — Lote 0803080241
  - WO3: 300 Kg — Lote 0803084241
  - WO4: 480 Kg — Lote 0803194241

**Required New Command:**

```
@ai create wo plan for SO-00763:
  WO1: qty 1055 lote 0803034251
  WO2: qty 600 lote 0803080241
  WO3: qty 300 lote 0803084241
  WO4: qty 480 lote 0803194241
```

**New Method Signature:**

```python
def create_wo_plan(self, so_name: str, plan: List[Dict]) -> Dict:
    """Create multiple Work Orders from a single SO line item.
    
    Args:
        so_name: Sales Order name
        plan: List of dicts, each with:
            - qty (float): Quantity for this WO
            - batch_name (str, optional): Lote/batch to assign
            - bom (str, optional): Override BOM
            - fg_warehouse (str, optional): Override FG warehouse
    
    Validation:
        - Sum of all plan qtys must equal SO line qty (or allow partial)
        - Each batch_name must be unique
        - Auto-create batches if they don't exist
    """
```

**Acceptance Criteria:**
1. New `@ai create wo plan for SO-XXXXX` command
2. Accepts multi-line or JSON format for WO specifications
3. Validates that sum of quantities matches SO (or warns on partial)
4. Creates named batches (lotes) as part of the plan
5. Links all WOs to the same SO
6. Returns a summary table showing all created WOs with lote assignments

---

### GAP-04: Batch/Lote Creation Command

**Severity:** CRITICAL — No way to create named batches via Raven  
**Files Affected:** None (new capability needed)

**Current State:**
- Material Receipt (line 448) can auto-create batches, but they get auto-generated names.
- AMB uses meaningful batch names like `0803034251` (format: ITEM + DATE + SEQUENCE).
- There is no Raven command to create a batch with a specific name.

**Required New Command:**

```
@ai create batch 0803034251 for item 0803-VARIANT
@ai create batch 0803034251 for item 0803-VARIANT expiry 2027-03-07
```

**New Method:**

```python
def create_named_batch(self, batch_name: str, item_code: str, 
                        expiry_date: str = None, 
                        manufacturing_date: str = None) -> Dict:
    """Create a batch with a user-defined name.
    
    Validation:
        - batch_name must be unique
        - item_code must exist and have has_batch_no=1
        - Optionally set expiry_date, manufacturing_date, description
    """
```

**Acceptance Criteria:**
1. `@ai create batch [NAME] for [ITEM]` creates batch with exact name specified
2. Supports optional `expiry [DATE]` and `mfg-date [DATE]` parameters
3. Validates item has `has_batch_no=1`
4. Returns confirmation with batch link

---

### GAP-05: `!finish` Bypasses Material Transfer

**Severity:** HIGH — Leaves `material_transferred_for_manufacturing=0` on completed WOs  
**Files Affected:** `manufacturing_handler.py` (lines 308-338)

**Current State:**
- `finish work order` directly calls `make_stock_entry(wo_name, "Manufacture", remaining)`.
- This creates a Manufacture stock entry without first checking if materials have been transferred.
- On WOs where `allow_negative_stock=1` (like the LORAND test), it succeeds but:
  - `material_transferred_for_manufacturing` remains 0
  - Costing may be incorrect (no WIP warehouse movement)
  - Audit trail is incomplete

**Required Changes:**

```python
# In _handle_finish_work_order:
wo = frappe.get_doc("Work Order", wo_name)

# Check if materials need to be transferred first
if wo.material_transferred_for_manufacturing < wo.qty:
    # Auto-transfer materials before manufacturing
    try:
        transfer_se = make_stock_entry(wo_name, "Material Transfer for Manufacture", 
                                        wo.qty - wo.material_transferred_for_manufacturing)
        transfer_doc = frappe.get_doc(transfer_se)
        # Set batch_no on transfer items (GAP-01)
        for item in transfer_doc.items:
            if needs_batch(item.item_code):
                item.batch_no = resolve_batch(item.item_code, item.s_warehouse, item.qty)
        transfer_doc.insert(ignore_permissions=True)
        transfer_doc.submit()
    except Exception as transfer_error:
        # Log warning but continue if allow_negative_stock
        frappe.log_error(f"Auto-transfer failed for {wo_name}: {transfer_error}")

# Then create manufacture entry
se_dict = make_stock_entry(wo_name, "Manufacture", remaining)
```

**Acceptance Criteria:**
1. `!finish work order` auto-transfers materials if not yet transferred
2. If transfer fails but `allow_negative_stock` is enabled, continue with a warning
3. After completion, `material_transferred_for_manufacturing` reflects the correct qty
4. Response message shows both transfer and manufacture stock entry names

---

### GAP-06: No Lote-Aware WO Status Display

**Severity:** MEDIUM — Production team can't see batch assignments at a glance  
**Files Affected:** `manufacturing_handler.py` (lines 19-40), `manufacturing_agent.py` (lines 380-440)

**Current State:**
- `show work orders` displays: WO name, product, progress, status, start date.
- Missing: lote/batch assignment, linked SO, linked stock entries.

**Required Enhancement:**

```
| Work Order | Product | Lote/Batch | Qty | SO | Status |
|------------|---------|------------|-----|----|--------|
| MFG-WO-04726 | 0803-VARIANT | 0803034251 | 1055 | SO-00763 | Completed |
| MFG-WO-04826 | 0803-VARIANT | 0803080241 | 600 | SO-00763 | Completed |
```

**Acceptance Criteria:**
1. `show work orders` includes batch/lote column
2. Shows linked Sales Order
3. Filter by SO: `@ai show work orders for SO-00763`
4. Filter by item: `@ai show work orders for 0803`

---

### GAP-07: WO from SO Creates Wrong Quantities

**Severity:** HIGH — Bot assumes 1:1 mapping between SO line qty and WO qty  
**Files Affected:** `manufacturing_agent.py` (lines 207-209), `workflow_orchestrator.py` (lines 79-84)

**Current State:**
```python
# manufacturing_agent.py line 207-209:
for item in so.items:
    item_code = item.item_code
    qty = item.qty  # Takes FULL SO qty (2096 Kg)
```

```python
# workflow_orchestrator.py line 79-84:
item = so.items[0] if so.items else None
item_code = item.item_code
qty = item.qty  # Takes FULL SO qty
```

Both assume the full SO line quantity goes into a single WO. This is incorrect for AMB's workflow where:
- Production is split across multiple batches/dates
- Different invoices may cover partial quantities
- Quality holds may require partial production

**Required Changes:**
- `create_work_order_from_so()` should accept optional `qty` override
- `run_full_cycle()` should accept a `wo_plan` parameter
- New command: `@ai create wo from SO-00763 qty 1055` (partial)

---

## 2. ENHANCEMENTS (Improvements for Smarter Agent)

### ENH-01: Orchestrator WO Plan Phase

**Priority:** HIGH  
**Description:** The workflow orchestrator's Steps 1-2 should support a "WO Plan" phase where multiple WOs are created, each with assigned lotes, and then executed sequentially or in parallel.

**Current Orchestrator Flow:**
```
Step 1: 1 Manufacturing WO → Submit
Step 2: 1 Stock Entry (Manufacture)
```

**Proposed Enhanced Flow:**
```
Step 1a: Create WO Plan (N Work Orders with lote assignments)
Step 1b: Submit all WOs
Step 2a: Transfer materials for each WO (with batch assignment)
Step 2b: Create manufacture entry for each WO
```

**New Command:**
```
@workflow run SO-00763 wo-plan [
  {qty: 1055, lote: "0803034251"},
  {qty: 600, lote: "0803080241"},
  {qty: 300, lote: "0803084241"},
  {qty: 480, lote: "0803194241"}
]
```

---

### ENH-02: Intelligent BOM Selection by Quantity

**Priority:** MEDIUM  
**Description:** AMB has multiple BOMs per item by pack size (10Kg, 1Kg, samples). Agent should auto-select BOM based on WO quantity.

**Context from LORAND test:**
- BOM-0803-002: 10Kg presentation
- BOM-0803-003: 1Kg presentation
- BOM-0803-004: 1Kg samples

**Logic:**
```python
def select_bom_by_qty(item_code, qty):
    """Select the best BOM based on quantity range."""
    boms = frappe.get_all("BOM",
        filters={"item": item_code, "is_active": 1, "docstatus": 1},
        fields=["name", "quantity", "is_default"],
        order_by="quantity desc")
    
    # Pick BOM whose quantity best divides into the WO qty
    # Or pick default BOM and let user override
```

---

### ENH-03: Post-WO Completion SO Status Check

**Priority:** MEDIUM  
**Description:** After all WOs complete, verify SO delivery/billing status and suggest next step.

**Observed Issue:** After completing 4 WOs for SO-00763, the SO still showed "To Deliver and Bill" with 0% delivered and 0% billed. Agent should automatically check and prompt:

```
✅ All 4 Work Orders completed for SO-00763.
📊 SO Status: To Deliver and Bill (0% delivered, 0% billed)
➡️ Next: Create Delivery Note? Use `@ai create DN from SO-00763`
```

---

### ENH-04: Bulk WO Operations

**Priority:** MEDIUM  
**Description:** Submit, transfer, or finish multiple WOs in one command.

```
@ai !submit all WOs for SO-00763
@ai !finish all WOs for SO-00763
@ai !transfer materials for all WOs for SO-00763
```

**Implementation:** Loop over all WOs linked to the SO and execute the operation on each.

---

### ENH-05: Stock Entry Cleanup Command

**Priority:** LOW  
**Description:** During LORAND test, orphan draft stock entries were created when commands failed. Need a cleanup command.

```
@ai cleanup draft stock entries for SO-00763
@ai cleanup draft SEs older than 7 days
```

---

## 3. ARCHITECTURAL RECOMMENDATIONS

### ARCH-01: Unified Batch Resolution Utility

Create a shared utility module used by ALL handlers:

```python
# raven_ai_agent/utils/batch_utils.py

class BatchResolver:
    """Centralized batch/lote handling for all stock operations."""
    
    @staticmethod
    def resolve_batch(item_code: str, warehouse: str = None, 
                      qty: float = None, preferred_batch: str = None) -> Optional[str]:
        """Find or create appropriate batch for a stock operation."""
        pass
    
    @staticmethod
    def create_named_batch(batch_name: str, item_code: str, **kwargs) -> str:
        """Create a batch with a specific name."""
        pass
    
    @staticmethod
    def get_batch_qty(batch_name: str, warehouse: str = None) -> float:
        """Get available quantity in a specific batch."""
        pass
    
    @staticmethod
    def set_batch_on_stock_entry(se_doc, batch_map: Dict = None):
        """Apply batch assignments to all items in a stock entry."""
        pass
```

### ARCH-02: WO Plan Data Model

Store WO plans as a linked document or JSON field on Work Orders:

```python
# Custom fields on Work Order:
# custom_wo_plan_id: Link to "WO Plan" (new doctype, or JSON in custom field)
# custom_lote: Data — the assigned lote/batch name for this WO
# custom_invoice_ref: Data — invoice or PO reference for this WO batch

# New Doctype: WO Plan
{
    "doctype": "WO Plan",
    "sales_order": "SO-00763",
    "item_code": "0803-VARIANT",
    "total_qty": 2096,
    "lines": [
        {"wo": "MFG-WO-04726", "qty": 1055, "lote": "0803034251", "status": "Completed"},
        {"wo": "MFG-WO-04826", "qty": 600, "lote": "0803080241", "status": "Completed"},
        ...
    ]
}
```

### ARCH-03: Handler/Agent Code Deduplication

**Problem:** `manufacturing_handler.py` (ManufacturingMixin) and `manufacturing_agent.py` (ManufacturingAgent) have DUPLICATE logic for:
- Creating Work Orders (handler line 42 vs agent line 50)
- Submitting Work Orders (handler line 122 vs agent line 143)
- Creating Manufacture entries (handler line 308 vs agent line 262)
- Material transfers (handler line 280 vs agent line 325)

**Recommendation:** The handler (Mixin) should delegate to the Agent class:

```python
# manufacturing_handler.py should become a thin command parser:
class ManufacturingMixin:
    def _handle_manufacturing_commands(self, query, query_lower, is_confirm):
        from raven_ai_agent.agents.manufacturing_agent import ManufacturingAgent
        agent = ManufacturingAgent()
        
        if "create work order" in query_lower:
            # Parse command → call agent.create_work_order()
        if "finish work order" in query_lower:
            # Parse command → call agent.create_stock_entry_manufacture()
```

This ensures batch handling, warehouse resolution, and all intelligence lives in ONE place.

### ARCH-04: Command Parsing Robustness

**Problem:** Commands rely on exact keyword matching with regex. During testing, slight variations failed silently.

**Examples that should work but currently don't:**
- `@ai transfer materials for MFG-WO-04726` (works)
- `@ai transfer MFG-WO-04726` (may not match — missing "materials" keyword)
- `@ai finish MFG-WO-04726` (works)
- `@ai complete MFG-WO-04726` (may not match in handler)

**Recommendation:** Use a scored intent matcher or at minimum add more aliases:

```python
COMMAND_ALIASES = {
    "transfer_materials": [
        "transfer materials", "transfer material", "issue materials",
        "emitir material", "transferir", "transfer"
    ],
    "finish_wo": [
        "finish work order", "complete production", "finalizar",
        "completar", "finish", "complete", "manufacture"
    ],
    "create_wo": [
        "create work order", "crear orden", "new wo", "create wo"
    ]
}
```

---

## 4. TEST CASE REFERENCE

### LORAND MASTER DEGREE TEST — Full Results

| Step | Action | Method | Result |
|------|--------|--------|--------|
| 1 | Create 3 template BOMs (0803) | API | ✅ BOM-0803-002, -003, -004 Submitted |
| 2 | Create 3 variant BOMs | API | ✅ BOM-variant-002, -003, -004 Submitted |
| 3 | Set default BOM on variant | API | ✅ BOM-variant-002 (10Kg) |
| 4 | Create WOs from SO via Raven | Raven `@ai create wo from SO-00763` | ⚠️ Created 3 auto-WOs with wrong qtys (2096/334/5) |
| 5 | Delete auto-WOs | API | ✅ Cancelled and deleted |
| 6 | Create 4 planned WOs | API | ✅ MFG-WO-04726 through -05026 |
| 7 | Submit 4 WOs | API | ✅ All submitted |
| 8 | Transfer materials via Raven | Raven `@ai !transfer materials` | ❌ FAILED — "Batch No mandatory" |
| 9 | Finish WOs via Raven | Raven `@ai !finish work order` | ✅ Worked (allow_negative_stock=1) |
| 10 | Cleanup orphan draft SEs | API | ✅ 4 drafts deleted |
| 11 | Verify completion | API | ✅ All 4 WOs Completed |

**Key Insight:** Steps 4, 8, and 10 required manual API intervention because Raven lacked the capabilities documented in GAP-01 through GAP-07.

---

## 5. IMPLEMENTATION PRIORITY

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| P0 | GAP-01: Batch handling in transfer/manufacture | 2-3 days | Unblocks batch-tracked items |
| P0 | GAP-04: Named batch creation | 1 day | Required by GAP-01 and GAP-03 |
| P0 | GAP-03: Multi-WO plan | 3-4 days | Core production planning |
| P1 | GAP-02: Variant BOM resolution | 1 day | Unblocks variant items |
| P1 | GAP-05: Auto-transfer on finish | 1 day | Data integrity |
| P1 | GAP-07: Partial qty WO from SO | 1 day | Flexible production |
| P1 | ARCH-01: Batch utility module | 2 days | Foundation for all batch work |
| P2 | GAP-06: Lote-aware status display | 0.5 day | Visibility |
| P2 | ARCH-03: Handler/Agent dedup | 2 days | Maintainability |
| P2 | ENH-01: Orchestrator WO plan phase | 2-3 days | End-to-end automation |
| P3 | ENH-02: BOM selection by qty | 1 day | Intelligence |
| P3 | ENH-03: Post-completion SO check | 0.5 day | UX |
| P3 | ENH-04: Bulk WO operations | 1 day | Productivity |
| P3 | ENH-05: Draft SE cleanup | 0.5 day | Housekeeping |
| P3 | ARCH-04: Command aliases | 1 day | Robustness |

**Estimated Total:** 18-22 developer-days

---

## 6. SUCCESS CRITERIA

After implementing P0 + P1 items, the following scenario must work end-to-end via Raven chat (no API intervention):

```
1. @ai create batch 0803034251 for 0803-VARIANT
2. @ai create batch 0803080241 for 0803-VARIANT
3. @ai create batch 0803084241 for 0803-VARIANT
4. @ai create batch 0803194241 for 0803-VARIANT
5. @ai create wo plan for SO-00763:
     WO1: qty 1055 lote 0803034251
     WO2: qty 600 lote 0803080241
     WO3: qty 300 lote 0803084241
     WO4: qty 480 lote 0803194241
6. @ai !submit all WOs for SO-00763
7. @ai !transfer materials for all WOs for SO-00763
8. @ai !finish all WOs for SO-00763
9. @ai show work orders for SO-00763
   → Shows all 4 WOs with lotes, all Completed
```

**All 9 steps must execute successfully without leaving the Raven chat.**

---

*End of Report*
