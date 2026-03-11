# Development Report: BUG28 Fix & Sales Invoice Creation Issues

**Date:** March 11, 2026  
**Issue:** BUG28 - Payment Agent incorrectly intercepts Sales Invoice creation commands  
**Status:** In Progress

---

## Executive Summary

This report documents the development cycle for fixing BUG28, where the Payment Agent was incorrectly intercepting commands meant for the Sales Order Follow-Up Agent. Multiple issues were discovered and fixed during this cycle.

---

## Issues Found & Fixed

### 1. BUG28: Router Logic Failure (PRIMARY ISSUE)

**Problem:** Commands like `@ai !create sales invoice from SO-00775-ALBAFLOR` were being routed to `payment_bot` instead of `sales_order_follow_up`, causing the Payment Agent help text to be displayed instead of creating the invoice.

**Root Cause:** Two locations had routing logic:
- `raven_ai_agent/api/handlers/router.py` - Fixed
- `raven_ai_agent/api/agent.py` - **THIS WAS THE ACTIVE FILE** - Not fixed initially

**Fixes Applied:**
1. Added SO-priority routing in `agent.py` (line ~419) to check for `SO-\d+` pattern before payment keywords
2. Added `import re` to agent.py (was missing)
3. Commit: `b356ee2` - Added SO-priority routing in agent.py
4. Commit: `3203e4e` - Added missing import re

**Status:** ✅ FIXED - Routing now correctly goes to sales_order_follow_up

---

### 2. Mode of Payment Not Set (CFDI Compliance)

**Problem:** `Error creating Sales Invoice: [Sales Invoice, ACC-SINV-2026-00048]: mxpaymentoption, modeofpayment`

**Fixes Applied:**
1. Added logic to set `mode_of_payment` from Customer's custom field
2. Fallback to dynamically query first available Mode of Payment from system
3. Commit: `be66439` - Add default mode_of_payment
4. Commit: `ab69c3e` - Dynamically get available Mode of Payment
5. Commit: `d129ebf` - Remove invalid fields from query (is_active doesn't exist)

**Status:** ✅ FIXED

---

### 3. mxpaymentoption Field Missing (CFDI Compliance)

**Problem:** `Error creating Sales Invoice: [Sales Invoice, ACC-SINV-2026-00049]: mxpaymentoption`

**Fixes Applied:**
1. First attempted hardcoded mapping based on payment method name
2. Then changed to dynamically query "SAT Payment Option" doctype
3. Commit: `80116a0` - Add mxpaymentoption field handling
4. Commit: `bbf9374` - Dynamically get SAT Payment Options from system

**Status:** ✅ Pushed - Awaiting production test

---

## Git Commits Summary

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

## Production Deployment Commands

```bash
# Pull latest code
docker exec -it erpnext-backend-1 bash -c "cd /home/frappe/frappe-bench/apps/raven_ai_agent && git pull upstream main"

# Restart all containers
docker restart erpnext-queue-short-1 erpnext-queue-long-1 erpnext-backend-1 erpnext-scheduler-1 erpnext-websocket-1
```

---

## Testing

**Test Command:**
```
@ai !create sales invoice from SO-00775-ALBAFLOR
```

**Expected Behavior:** Routes to `sales_order_follow_up` and creates Sales Invoice

---

## Lessons Learned

1. **Multiple routing locations:** The codebase has multiple files with routing logic (`agent.py`, `handlers/router.py`, `api/router.py`). Need to ensure fixes are applied to the ACTIVE file.

2. **Import statements:** Always verify required imports (`re` module) are present

3. **Field validation:** ERPNext field names differ between versions. Always verify field existence (`is_active` doesn't exist in Mode of Payment)

4. **Mexican CFDI compliance:** Requires multiple fields: `mode_of_payment`, `mxpaymentoption`, `mx_cfdi_use`

5. **Dynamic vs Hardcoded:** Prefer dynamically querying system doctypes instead of hardcoding values

---

## Next Steps

1. Test the latest fix on production
2. If SAT Payment Option doctype doesn't exist, create default value
3. Monitor for any other missing CFDI fields
4. Consider adding more comprehensive Mexican localization handling

---

**Report Generated:** March 11, 2026  
**Author:** MiniMax Agent
