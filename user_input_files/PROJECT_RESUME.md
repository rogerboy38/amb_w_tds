# Raven AI Agent Project — Complete Resume (v3)
**Updated**: March 5, 2026, 9:28 AM CST | **Site**: erp.sysmayal2.cloud | **Company**: AMB-Wellness

---

## 1. What We Built

A multi-agent system inside **Raven Chat** (ERPNext's chat app) that responds to `@ai` mentions and routes to specialized agents for a full Sales-to-Payment pipeline.

| Agent/Handler | File | What It Does |
|---------------|------|-------------|
| **RaymondLucyAgent** | `agent.py` | Default fallback — sales commands, quotation ops, AI memory, web search |
| **TaskValidatorMixin** | `handlers/task_validator.py` | Diagnose pipelines, validate SO vs QTN, intelligent sync |
| **SalesMixin** | `handlers/sales.py` | Submit SO, create DN, create SI |
| **QuotationMixin** | `handlers/quotation.py` | Fix/submit/update quotations |
| **ManufacturingMixin** | `handlers/manufacturing.py` | WO, transfer materials, manufacture |
| **ManufacturingAgent** | `agents/manufacturing_agent.py` | Standalone MFG agent (WO + stock entries) |
| **PaymentAgent** | `agents/payment_agent.py` | Payment entries, reconciliation |
| **WorkflowOrchestrator** | `agents/workflow_orchestrator.py` | Multi-step pipeline SO→WO→DN→SI→PE |
| **SalesOrderFollowUpAgent** | `agents/sales_order_followup_agent.py` | Follow ups, reminders |
| **RouterPatch** | `router_patch.py` | Patches Raven's router for custom bot routes |

**Entry point**: `raven_ai_agent.api.agent.handle_raven_message` (hooks.py)

---

## 2. GitHub Repository

**Repo**: `rogerboy38/raven_ai_agent` | **Branch**: `main`
**PAT**: `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`

### Full Commit History (chronological):
| # | Hash | Description | Deployed? |
|---|------|-------------|-----------|
| 1 | `6bd7286` | Initial push: all agent files + test plan | ✅ |
| 2 | `c5963ab` | Fix: `RndAgent` → `RnDAgent` class name | ✅ |
| 3 | `3c48191` | Add `@manufacturing`/`@payment`/`@workflow` routing | ✅ |
| 4 | `8528ee8` | Add intent detection using regex (BROKEN) | ✅ |
| 5 | `bff8e33` | Fix: replace regex with keyword matching | ✅ |
| 6 | `77a53f0` | Fix: smart warehouse resolution in manufacturing_agent | ✅ |
| 7 | `50e33b2` | Upgrade task_validator: intelligent actions + sync SO | ✅ |
| 8 | `1bb7360` | Add sync/fix keywords to agent.py routing | ✅ |
| 9 | `cba3330` | Fix SO regex in task_validator.py (spaces in names) | ✅ |
| 10 | `3c22f5d` | Fix make_stock_entry: returns _dict not Document in ERPNext v16 | ✅ |
| 11 | `8ac34ad` | Fix SO regex in sales.py | ✅ |
| 12 | `de15fb4` | Fix SO regex in base.py | ✅ |
| 13 | `2e4e990` | Fix SO regex in manufacturing_agent.py | ✅ |
| 14 | `6ce91b7` | Fix SO regex in workflow_orchestrator.py | ✅ |
| 15 | `33de58d` | Fix SO regex in agent.py execute_workflow_command | **❌ NOT DEPLOYED** |

---

## 3. Routing Architecture

```
User sends "@ai <message>" in Raven Chat
         │
         ▼
agent.py handle_raven_message()  ← hooks.py entry point
         │
         ├─ validator_keywords? ──→ task_validator.py (TaskValidatorMixin)
         │   diagnose, validate, sync, fix, audit, check payment, !sync, !fix
         │
         ├─ orch_keywords? ──→ workflow_orchestrator.py (WorkflowOrchestrator)
         │   pipeline status, run full cycle, dry run
         │
         ├─ mfg_keywords? ──→ manufacturing_agent.py (ManufacturingAgent)
         │   work order, manufacture, transfer material, mfg-wo
         │
         ├─ pay_keywords? ──→ payment_agent.py (PaymentAgent)
         │   payment, outstanding, unpaid, reconcile
         │
         └─ default ──→ RaymondLucyAgent (sales_order_bot)
             quotation commands, sales commands, submit SO, etc.
```

**CRITICAL LESSON**: `agent.py` has its OWN `execute_workflow_command()` (line ~862) that **OVERRIDES** `base.py`'s version. Any fix to base.py routing/regex MUST also be applied to agent.py. This is the "duplicate code" problem that caused the SO submit bug.

---

## 4. Deployment Details

### Docker Containers (ALL must be restarted together):
```bash
docker restart erpnext-backend-1 erpnext-queue-short-1 erpnext-queue-long-1 erpnext-scheduler-1 erpnext-websocket-1
```

### Git Pull (inside Docker):
```bash
docker exec erpnext-backend-1 bash -c "cd /home/frappe/frappe-bench/apps/raven_ai_agent && git pull upstream main"
# Then from HOST:
docker restart erpnext-backend-1 erpnext-queue-short-1 erpnext-queue-long-1 erpnext-scheduler-1 erpnext-websocket-1
```

### Key Rules:
- `bench restart` does NOT reload Python → must use `docker restart`
- Git remote is `upstream` (not `origin`) → `git pull upstream main`
- No `bench build` needed for Python-only changes (only for JS/CSS)
- Server Script sandbox blocks `subprocess`, `os`, `import` → cannot deploy via Server Scripts

---

## 5. ERPNext Credentials

| Field | Value |
|-------|-------|
| **Site** | erp.sysmayal2.cloud |
| **Login** | fcrm@amb-wellness.com |
| **Password** | Aloe246! |
| **Company** | AMB-Wellness |
| **Currencies** | MXN (local), USD (export sales) |

---

## 6. SO-00753 GREENTECH Pipeline — Current State

### The Complete 8-Step Pipeline:

| Step | Action | Document | Status |
|------|--------|----------|--------|
| 0 | Quotation (Truth Source) | SAL-QTN-2024-00753 | 📝 Draft — GREENTECH S.A, 0334, 1800 Kg, USD 187,200 |
| 1 | Manufacturing WO (Mix) | MFG-WO-04126 | ✅ **Completed** — Materials transferred + Manufactured |
| 2 | Stock Entry (Manufacture) | MAT-STE-2026-00328 (transfer) + MAT-STE-2026-00329 (manufacture) | ✅ **Completed** — 1800 Kg of 0334 produced |
| **3** | **Submit Sales Order** | **SO-00753-GREENTECH SA** | **📝 Draft — ✅ 0 issues (synced) — NEEDS SUBMIT** |
| 4 | Sales WO from SO (Labeling) | — | ⏳ Pending (blocked by Step 3) |
| 5 | Stock Entry (Sales Manufacture) | — | ⏳ Pending |
| 6 | Delivery Note | — | ⏳ Pending |
| 7 | Sales Invoice | — | ⏳ Pending |
| 8 | Payment Entry | — | ⏳ Pending |

### What's Been Accomplished (Steps 0-2):
1. ✅ Diagnosed quotation → found 6 issues between QTN and SO
2. ✅ Synced SO from quotation → 5 changes applied (payment terms, delivery, item rate, total, taxes)
3. ✅ Re-diagnosed → 0 issues, all checks passed
4. ✅ Transferred materials to WO (MAT-STE-2026-00328)
5. ✅ Manufactured 1800 Kg of 0334 (MAT-STE-2026-00329)

### Immediate Next Action:
1. **Deploy commit `33de58d`**: `git pull upstream main` + `docker restart` (fixes SO regex in agent.py)
2. **Test**: `@ai !submit sales order SO-00753-GREENTECH SA`
3. Continue Steps 4-8

---

## 7. Agent/Handler Coverage Map

| Step | Pipeline Stage | Handler | @ai Command | Status |
|------|---------------|---------|-------------|--------|
| 0 | Quotation | `quotation.py` | `@ai !fix quotation`, `@ai !submit quotation` | ✅ Working |
| 0→3 | QTN → SO Creation | `sales.py` | `@ai !sales order SAL-QTN-XXXX` | ✅ Working |
| 0→3 | QTN → SO Validation | `task_validator.py` | `@ai diagnose SAL-QTN-XXXX` | ✅ Deployed |
| 0→3 | SO Sync from QTN | `task_validator.py` | `@ai !sync SO XXX from quotation` | ✅ Deployed |
| 1 | Create MFG WO | `manufacturing.py` | `@ai create work order for ITEM qty QTY` | ✅ Working |
| 2 | Transfer Materials | `manufacturing.py` | `@ai transfer materials MFG-WO-XXXXX` | ✅ Working |
| 2 | Finish Manufacture | `manufacturing.py` | `@ai finish work order MFG-WO-XXXXX` | ✅ Working |
| 3 | Submit SO | `sales.py` via `agent.py` | `@ai !submit sales order SO-XXXXX` | 🔧 Fix pushed, NOT deployed |
| 4 | Sales WO from SO | `workflow_orchestrator.py` | via `@ai run SO-XXXXX` | ⚠️ Orchestrator only |
| 5 | SE Manufacture (Sales) | `workflow_orchestrator.py` | via `@ai run SO-XXXXX` | ⚠️ Orchestrator only |
| 6 | Delivery Note | `sales.py` | `@ai !delivery SO-XXXXX` | ✅ Working |
| 7 | Sales Invoice | `sales.py` | `@ai !invoice SO-XXXXX` | ✅ Working |
| 8 | Payment Entry | `payment_agent.py` | `@ai create payment ACC-SINV-XXXX` | ⚠️ Exists, not recently tested |

### Cross-Cutting Intelligence:
| Tool | Command | Status |
|------|---------|--------|
| Pipeline Diagnosis | `@ai diagnose SAL-QTN-XXXX` / `@ai diagnose SO-XXXXX` | ✅ Deployed |
| SO Validation | `@ai validate SO-XXXXX` | ✅ Deployed |
| Payment Check | `@ai check payments SAL-QTN-XXXX` | ✅ Deployed |
| Pipeline Dashboard | `@ai pipeline status SO-XXXXX` | ✅ Working |
| Full Cycle Run | `@ai run full cycle SO-XXXXX` | ⚠️ Needs BOM intelligence |
| SO Sync/Fix | `@ai !sync SO XXX from quotation` | ✅ Deployed |

---

## 8. Critical Bugs Fixed (Lessons Learned)

### Bug 1: SO Names with Spaces
**Problem**: SO names like `SO-00753-GREENTECH SA` contain spaces. Regex `SO-[\w\-]+` only matched `SO-00753-GREENTECH`, missing ` SA`.
**Fix**: Applied across ALL 6 files: `r'(SO-[\w\-]+(?:\s+(?!from\b|to\b|pipeline\b|status\b|check\b|audit\b|validate\b|diagnose\b)[\w\.]+)*|SAL-ORD-\d+-\d+)'`
**Files fixed**: agent.py, base.py, sales.py, task_validator.py, manufacturing_agent.py, workflow_orchestrator.py

### Bug 2: ERPNext v16 make_stock_entry Returns _dict
**Problem**: `make_stock_entry()` returns `frappe._dict` (not a Document) in ERPNext v16. Calling `.submit()` on it fails with `'NoneType' object is not callable`.
**Fix**: Wrap with `frappe.get_doc("Stock Entry", result.get("name"))` to get a proper Document before calling `.insert()` and `.submit()`.
**File**: `manufacturing_agent.py`

### Bug 3: Duplicate execute_workflow_command()
**Problem**: `agent.py` line ~862 has its own `execute_workflow_command()` that **shadows** `base.py`'s version. Fixing regex in base.py alone doesn't work — must also fix agent.py's copy.
**Lesson**: Always check ALL files for the same function/pattern before declaring a fix complete.

### Bug 4: No `import frappe` in Server Scripts
ERPNext Server Script sandbox pre-injects `frappe` but blocks explicit `import frappe`. Also blocks `subprocess`, `os`, `shutil`, etc.

### Bug 5: Regex in JSON Double-Escaping
JSON payloads double-escape `\d` → `\\d`, breaking regex patterns. Solution: use keyword matching instead of regex for intent detection.

---

## 9. BOM Structure (Documented for All Migrations)

Standard hierarchy per finished item (e.g., 0334):

| BOM Suffix | Level | Status | Default | Qty | Purpose |
|-----------|-------|--------|---------|-----|---------|
| -001 | Sales | Draft | YES | 25 Kg | Quotation / SO — what sales sees |
| -004 | Full Production | Draft→Submit | No | 1 Kg | Complete 40+ item BOM |
| -005 | Mix Manufacturing | Submitted | YES | 1 Kg | WO for Mix plant |
| -006 | Sales Packaging | Draft→Submit | No | 25 Kg | Packaging WO (submittable version of 001) |

### Item 0334 BOM Status:
| BOM | Status | Default | Used By |
|-----|--------|---------|---------|
| BOM-0334-001 | Draft, Active | YES | Sales quotations |
| BOM-0334-004 | Draft, Active | No | Full costing |
| BOM-0334-005 | **Submitted**, Active | YES | MFG-WO-04126 (completed) |
| BOM-0334-006 | Draft, Active | No | Sales WO (Step 4) |

Full guide: `/home/user/workspace/BOM_MIGRATION_GUIDE.md`

---

## 10. RaymondLucyAgent — Complete Architecture & Features

Located in `agent.py` lines 242-1162. This is the **core intelligence engine** — a sophisticated AI agent with persistent memory, anti-hallucination protocols, dynamic ERPNext context, web search, and an autonomy slider. All specialized agents (manufacturing, payment, etc.) route through it as the default fallback.

### 10.1 Class Hierarchy & Mixins
```python
class RaymondLucyAgent(
    ManufacturingMixin,      # handlers/manufacturing.py — WO, stock entries, SOP (606 lines)
    BOMMixin,                # handlers/bom.py — BOM commands, label fixer, cancel (267 lines)
    WebSearchMixin,          # handlers/web_search.py — Direct web search (53 lines)
    SalesMixin,              # handlers/sales.py — Sales-to-Purchase cycle (477 lines)
    QuotationMixin,          # handlers/quotation.py — Quotation fix/update/TDS (415 lines)
):
```
The agent inherits from 5 handler mixins, giving it access to all domain-specific commands.

### 10.2 Named Protocols (Core Design Philosophy)

| Protocol | Name | Purpose | Implementation |
|----------|------|---------|----------------|
| **Raymond Protocol** | Anti-Hallucination | NEVER fabricate ERPNext data — always query DB, cite document names, express confidence (HIGH/MEDIUM/LOW/UNCERTAIN) | `get_erpnext_context()` — fetches verified data before every LLM call |
| **Memento Protocol** | Persistent Memory | Store important facts as "memory tattoos" that survive across sessions | `tattoo_fact()` → writes to AI Memory doctype with optional vector embeddings |
| **Lucy Protocol** | Context Continuity | Load user context at session start, generate session summaries at end | `get_morning_briefing()` + `end_session()` |
| **Karpathy Protocol** | Autonomy Slider | Graduated permission levels: L1=read-only, L2=modify with confirm, L3=dangerous ops | `determine_autonomy()` — auto-detects level from keywords |

### 10.3 Settings & Configuration (lines 261-308)
```python
def __init__(self, user):
    self.user = user
    self.settings = self._get_settings()      # Tries 3 sources
    self.client = OpenAI(api_key=...)          # GPT-4o-mini
    self.autonomy_level = 1                    # Default COPILOT
```
**Settings cascade** (tries in order):
1. `AI Agent Settings` doctype → `get_password("openai_api_key")`
2. `Raven Settings` doctype → `get_password("openai_api_key")`
3. `frappe.conf` (site_config.json) → `openai_api_key`

**Configurable fields**: `openai_api_key`, `model` (default: gpt-4o-mini), `max_tokens` (default: 2000), `confidence_threshold` (default: 0.7)

### 10.4 Morning Briefing — Lucy Protocol (lines 310-340)
```python
def get_morning_briefing(self) -> str:
```
- Loads top 10 **Critical/High** importance memories from `AI Memory` doctype
- Loads latest **Session Summary** (generated at previous session end)
- Returns formatted briefing injected into system prompt
- Purpose: Agent "remembers" what happened in previous sessions

### 10.5 Vector Memory Search — RAG (lines 342-367)
```python
def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
```
- **Primary**: Vector similarity search via `VectorStore` class (cosine similarity with configurable threshold)
- **Fallback**: Keyword `LIKE` search on AI Memory doctype
- Uses `VECTOR_SEARCH_ENABLED` flag (True if `raven_ai_agent.utils.vector_store` imports successfully)
- Returns relevant memories injected into LLM context for every query

### 10.6 Memento Protocol — tattoo_fact (lines 369-394)
```python
def tattoo_fact(self, content: str, importance: str = "Normal", source: str = None):
```
- Stores a fact to **AI Memory** doctype with:
  - `user`: Current user
  - `content`: The fact text
  - `importance`: Critical / High / Normal
  - `memory_type`: "Fact"
  - `source`: "Conversation" (default) or custom
- **Primary**: Stores with vector embedding via `VectorStore.store_memory_with_embedding()`
- **Fallback**: Stores without embedding (keyword-searchable only)
- These "tattoos" persist across sessions — the agent's long-term memory

### 10.7 Dynamic Doctype Detection (lines 396-493)
```python
DOCTYPE_KEYWORDS = {  # 23 doctypes, bilingual EN/ES
    "Sales Invoice": ["invoice", "factura", "billing", "invoiced"],
    "Sales Order": ["sales order", "orden de venta", "so-", "pedido"],
    "Purchase Order": ["purchase order", "orden de compra", "po-"],
    "Quotation": ["quotation", "quote", "cotización"],
    "Customer": ["customer", "client", "cliente"],
    "Item": ["item", "product", "artículo", "producto"],
    "Work Order": ["work order", "manufacturing", "production", "producción"],
    "BOM": ["bom", "bill of material", "lista de materiales"],
    "Quality Inspection": ["quality", "inspection", "qc", "calidad"],
    "Batch": ["batch", "lote"],
    "Payment Entry": ["payment", "pago"],
    # ... + 12 more (Supplier, Stock Entry, DN, PR, MR, Lead, Opportunity, Address, Contact, Employee, Warehouse, Serial No, Journal Entry)
}
```
- `detect_doctype_from_query()`: Scans message for keywords → returns list of matching doctypes
- `query_doctype_with_permissions()`: Queries each detected doctype WITH permission check, adds clickable links
- `get_available_doctypes()`: Lists all 23 doctypes user has read access to
- **Key insight**: Agent auto-discovers what data is relevant without hardcoded routes

### 10.8 ERPNext Context Builder — Raymond Protocol (lines 609-845)
```python
def get_erpnext_context(self, query: str) -> str:
```
This is the **anti-hallucination engine**. Before every LLM call, it:

1. **URL Detection**: If query contains a URL → fetches and extracts content (tables, lists, addresses)
2. **Web Search Intent**: Detects keywords like "search", "buscar", "find" → runs DuckDuckGo search
3. **Market Research Detection**: Detects "who are the players in..." type questions → web search
4. **Dynamic Doctype Query**: Runs `detect_doctype_from_query()` → queries each matching doctype
5. **Keyword-specific queries** (backward compatibility):
   - Invoices, customers, items, purchase orders, quotations, sales orders, work orders, delivery notes
   - Quality inspections, TDS/tax data, best-selling items
6. **Customer-specific reports**: Recognizes customer names (barentz, legosan, lorand) → fetches their sales data

All context is injected into the LLM system prompt so GPT-4o-mini answers from **verified data**, not imagination.

### 10.9 DuckDuckGo Web Search (lines 495-607)
```python
def duckduckgo_search(self, query: str, max_results: int = 5) -> str:
def search_web(self, query: str, url: str = None) -> str:
```
- **duckduckgo_search()**: Parses HTML results from `html.duckduckgo.com` — no API key required
- **search_web()**: Two modes:
  - With URL: Fetches page, extracts tables/lists/addresses/contact info via BeautifulSoup
  - Without URL: Falls back to DuckDuckGo search
- Extracts: Tables (max 3, 20 rows each), lists (max 5, 15 items each), address/contact divs
- Returns structured text injected as `⭐ WEB SEARCH RESULTS` or `⭐ EXTERNAL WEB DATA`

### 10.10 Autonomy Slider — Karpathy Protocol (lines 847-860)
```python
def determine_autonomy(self, query: str) -> int:
```
| Level | Type | Trigger Keywords | Behavior |
|-------|------|-----------------|----------|
| 1 | COPILOT (default) | Read-only queries | Suggest, explain, query data |
| 2 | COMMAND | update, change, modify, create, convert, confirm | Execute with confirmation |
| 3 | AGENT | delete, cancel, submit, create invoice, payment | Dangerous ops — requires explicit permission |

- `!` prefix = Force mode (auto-confirms, like sudo)
- Privileged roles (Sales Manager, Manufacturing Manager, Stock Manager, Accounts Manager, System Manager) = auto-confirm

### 10.11 Main Processing Flow — process_query() (lines 1029-1126)
```
User Message
    │
    ▼
1. Help/capabilities check → return CAPABILITIES_LIST
    │
    ▼
2. determine_autonomy() → Level 1/2/3
    │
    ▼
3. execute_workflow_command() → try direct command execution
    │  (submit SO, create WO, delivery, invoice, BOM, batch...)
    │  If matched → return result immediately (no LLM call)
    │
    ▼ (if no workflow match)
4. Build rich context:
    │  a. get_morning_briefing() → session history + key memories
    │  b. get_erpnext_context() → verified DB data + web results
    │  c. search_memories() → RAG on AI Memory
    │
    ▼
5. Call OpenAI GPT-4o-mini:
    │  System: SYSTEM_PROMPT (Raymond-Lucy Protocol v2.0)
    │  System: Context (briefing + ERPNext data + memories)
    │  User: conversation_history[-10:] + current query + autonomy warning
    │  Temperature: 0.3 (low for accuracy)
    │
    ▼
6. Return response with confidence tag + autonomy level
```

### 10.12 Session Summary — end_session() (lines 1128-1162)
```python
def end_session(self, conversation: List[Dict]):
```
- Takes last 20 messages of conversation
- Asks GPT-4o-mini to summarize in 2-3 sentences (key decisions + info shared)
- Stores summary as `AI Memory` with `importance: High`, `memory_type: Summary`
- This summary is loaded by `get_morning_briefing()` at next session start → continuity

### 10.13 Custom Doctypes Used

| Doctype | Purpose | Key Fields |
|---------|---------|------------|
| **AI Memory** | Persistent memory store | user, content, importance (Critical/High/Normal), memory_type (Fact/Summary), source, creation |
| **AI Agent Settings** | Agent configuration | openai_api_key (password), model, max_tokens, confidence_threshold |

### 10.14 SYSTEM_PROMPT — The Agent's DNA (lines 46-117)
The full system prompt defines:
- **LLM OS Model**: Context Window = RAM, Vector DB = Hard Drive, Tools = ERPNext APIs
- **Raymond Protocol**: Never fabricate data, always cite sources, express confidence
- **Memento Protocol**: Store critical/high/normal facts about user
- **Lucy Protocol**: Morning briefing, session summaries, reference past conversations
- **Karpathy Protocol**: 3-level autonomy slider
- **Rules**: Verify doctypes exist, check permissions, format currency/dates by locale
- **Response format**: `[CONFIDENCE: X] [AUTONOMY: LEVEL Y]` prefix on every response
- **Critical rules**: Never say "hold on" or "let me check" — search is already done before LLM sees the query

### 10.15 CAPABILITIES_LIST — What Agent Advertises (lines 119-237)
When user says `@ai help`, returns a comprehensive capabilities menu:
- ERPNext Data Access (quotations, deliveries, best sellers, TDS)
- Web Research (search, find suppliers, extract from URL, market research)
- Create ERPNext Records (suppliers with web-researched addresses)
- Workflows (quotation→SO, WO, stock entry, DN, SI)
- Manufacturing SOP (full WO lifecycle: create→submit→issue materials→job cards→complete→FG)
- Sales-to-Purchase Cycle (opportunity→MR→RFQ→SQ→PO→PR→PI→DN→SI)
- BOM Management (show, cancel, revert, check labels, fix labels, force fix)
- BOM Creator (show, submit, validate, create from TDS, create for batch)
- Document Actions (submit, unlink, fix, update)

### 10.16 Key Takeaways for Our Agents

**What we should adopt in specialized agents:**
1. **Persistent Memory** (AI Memory doctype + tattoo_fact) — agents remember across sessions
2. **Anti-Hallucination** (always query DB first, express confidence) — never guess
3. **Morning Briefing** — agents start with context from last session
4. **Session Summary** — agents save what happened for next time
5. **Dynamic Context** — auto-detect relevant doctypes instead of hardcoding
6. **Bilingual Keywords** — EN/ES detection for Mexican company
7. **Autonomy Slider** — graduated permissions with `!` force mode
8. **Web Search** — DuckDuckGo fallback when question is outside ERPNext

**What could be improved:**
1. Vector search is optional (falls back to keyword LIKE) — should ensure VectorStore is always available
2. `execute_workflow_command()` is duplicated in agent.py AND base.py — needs consolidation
3. Temperature 0.3 is good for accuracy but may limit creative responses
4. No conversation threading yet — each message is somewhat standalone
5. Memory extraction from LLM responses (`[Stored:]` pattern) is stubbed but not implemented

---

## 11. Workspace Files

| File | Purpose |
|------|---------|
| `/home/user/workspace/raven_current/api/agent.py` | Main entry point (fixed SO regex + sync keywords) |
| `/home/user/workspace/raven_current/api/handlers/task_validator.py` | Intelligent sync + diagnose |
| `/home/user/workspace/raven_current/api/handlers/sales.py` | SO/DN/SI operations (fixed regex) |
| `/home/user/workspace/raven_current/api/handlers/base.py` | Base handler (fixed regex) |
| `/home/user/workspace/raven_current/agents/manufacturing_agent.py` | MFG agent (fixed make_stock_entry + regex) |
| `/home/user/workspace/raven_current/agents/workflow_orchestrator.py` | Pipeline orchestrator (fixed regex) |
| `/home/user/workspace/PROJECT_RESUME.md` | **This file** |
| `/home/user/workspace/PIPELINE_COVERAGE_REVIEW.md` | Full pipeline gap analysis |
| `/home/user/workspace/BOM_MIGRATION_GUIDE.md` | Standard BOM structure for migrations |

---

## 12. Known Gaps (Remaining Work)

### Blocking (for SO-00753):
1. **Deploy commit `33de58d`** — agent.py SO regex fix — user must run `git pull + docker restart`

### Medium Priority:
2. **No standalone "Sales WO from SO" command** — Steps 4-5 only via orchestrator `run full cycle`
3. **Quality Inspection handling** — DN creation may require QI for certain items
4. **CFDI/E-Invoice fields** — SI doesn't auto-populate SAT fields (G03, PPD, Wire Transfer)
5. **Payment Entry not fully tested** — PaymentAgent exists but not exercised recently

### Low Priority / Enhancement:
6. **No Step 0 in Orchestrator** — Pipeline dashboard starts from SO, misses Quotation pre-conditions
7. **`is_confirm` bug** — In old `execute_workflow_command()` line ~874, `NameError` if code path is hit
8. **Apply RaymondLucyAgent features** — Persistent memory, anti-hallucination, dynamic context to all agents

---

## 13. Important Rules (Hard-Won Knowledge)

1. **No `import frappe` in Server Scripts** — causes ImportError
2. **`bench restart` doesn't reload Python** — must use `docker restart` from host
3. **Git remote is `upstream`** not `origin` — use `git pull upstream main`
4. **Regex breaks in JSON** — double-escaping kills patterns; use keyword matching instead
5. **No `bench build` needed** for Python-only changes
6. **All bots use `@ai`** — single entry point, internal routing by keywords
7. **ERPNext v16**: `make_stock_entry()` returns `_dict` not Document — wrap with `frappe.get_doc()`
8. **Duplicate code**: `agent.py` execute_workflow_command() overrides base.py — fix BOTH
9. **SO regex**: Must handle spaces in names — use negative lookahead pattern
10. **Quotation is truth source** — SO must be validated/synced against QTN, especially payment terms

---

## 14. Reference Pipeline (SO-00752 LEGOSAN — Completed)

| Step | Document | Status |
|------|----------|--------|
| 0 | SAL-QTN-2024-00752 | ✅ Submitted |
| 1 | MFG-WO-03726 | ✅ Completed |
| 2 | MAT-STE-2026-00327 | ✅ Submitted |
| 3 | SO-00752-LEGOSAN AB | ✅ Submitted (To Bill) |
| 4 | Sales WO | ⏳ Pending |
| 5 | Sales SE | ⏳ Pending |
| 6 | MAT-DN-2026-00002 | ✅ Submitted |
| 7 | ACC-SINV-2026-00001 | ✅ Submitted (Unpaid) |
| 8 | Payment Entry | ⏳ Pending (preview tested) |

---

*This document is the complete state of the project as of March 5, 2026, 9:28 AM CST.*
*For BOM migration details, see: `/home/user/workspace/BOM_MIGRATION_GUIDE.md`*
*For pipeline gap analysis, see: `/home/user/workspace/PIPELINE_COVERAGE_REVIEW.md`*
