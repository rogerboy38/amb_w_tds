# Raven AI Agent - Project Status

**Last Updated:** March 14, 2026

---

## Current Status

### ✅ Pipeline & Diagnosis Commands - FIXED (Team A)

Team A (first team) successfully fixed the pipeline routing issue:

- `@ai pipeline SAL-QTN-2024-00752` → ✅ Working
- `@ai diagnose SAL-QTN-2024-00752` → ✅ Working
- Full pipeline diagnosis now returns complete data including:
  - Quotation summary (customer, date, items, total, status)
  - Issues found (severity levels)
  - Pipeline status
  - Next steps

### Architecture

**Working Solution:**
1. `api/handlers/router.py` - Routes `pipeline SAL-QTN-*` to `task_validator`
2. `agents/task_validator.py` - NEW TaskValidator agent (NOT the mixin in handlers/)
3. `skills/data_quality_scanner/skill.py` - DataQualityScannerSkill processes the command

### Key Files

| File | Status | Notes |
|------|--------|-------|
| `agents/task_validator.py` | ✅ ACTIVE | Main TaskValidator implementation |
| `api/handlers/task_validator.py` | ⚠️ LEGACY | Old mixin - can be deprecated |
| `api/handlers/router.py` | ✅ ACTIVE | Routing logic |
| `skills/data_quality_scanner/skill.py` | ✅ ACTIVE | Scanner logic |

### Known Issues

- Backup files need cleanup (multiple .backup_* files created during development)
- There was a conflict between two development teams working in parallel:
  - Team A: Fixed pipeline/diagnosis (this is the working solution)
  - Team B: Worked on separate branch ("mundo paralelo")
  - Result: Duplicate files, conflicting approaches

---

## Test Commands

```
@ai pipeline SAL-QTN-2024-00752
@ai diagnose SAL-QTN-2024-00752  
@ai scan SAL-QTN-2024-00752
```

---

## Recent History

- 2026-03-13: Pipeline routing issue identified
- 2026-03-14: Team A fixed the issue - confirmed working via bench console test
- 2026-03-14: Pulled changes to workspace, audited the solution
- 2026-03-14: Added Team B bug fixes (BUG28 and CFDI compliance)

---

## Team B: Bug Fixes (BUG28 & Sales Invoice)

Team B (parallel team) fixed multiple issues:

### BUG28: Router Logic Failure
- **Problem:** `@ai !create sales invoice from SO-00775-ALBAFLOR` was routed to payment_bot instead of sales_order_follow_up
- **Root Cause:** Multiple routing files existed - `agent.py` was the active one, not `handlers/router.py`
- **Fix:** Added SO-priority routing in `agent.py` to check for SO-\d+ pattern before payment keywords
- **Commits:** `b356ee2`, `3203e4e`

### Fix 2: Mode of Payment (CFDI Compliance)
- **Problem:** Error: mxpaymentoption, modeofpayment
- **Fix:** Added logic to set mode_of_payment from Customer's custom field, with fallback to query available Mode of Payment
- **Commits:** `be66439`, `ab69c3e`, `d129ebf`

### Fix 3: mxpaymentoption Field (CFDI Compliance)
- **Problem:** Error: mxpaymentoption field missing
- **Fix:** Dynamically query SAT Payment Option doctype
- **Commits:** `80116a0`, `bbf9374`

### Git Commits Summary (Team B)
| Commit | Description |
|--------|-------------|
| `b356ee2` | fix(BUG28): Add SO-priority routing in agent.py |
| `3203e4e` | fix(BUG28): Add missing import re |
| `be66439` | fix: Add default mode_of_payment for Mexico CFDI |
| `ab69c3e` | fix: Dynamically get available Mode of Payment |
| `d129ebf` | fix: Remove invalid fields from Mode of Payment query |
| `80116a0` | fix: Add mxpaymentoption field for Mexico CFDI |
| `bbf9374` | fix: Dynamically get SAT Payment Options from system |

---

**Memory maintained by:** MiniMax Agent