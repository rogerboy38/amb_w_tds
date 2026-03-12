# Technical Report: Data Quality Scanner Integration Issue

## Executive Summary

This document tracks the integration issues with the Data Quality Scanner skill into the Raven AI Agent routing system. Multiple attempts have been made to route scan/validate commands to the scanner skill, but all attempts have failed due to a fundamental routing architecture problem.

---

## 1. What We're Trying to Achieve

**Goal:** Route `@ai scan SO-XXXXX` commands to the Data Quality Scanner skill instead of the default `RaymondLucyAgent`.

**Expected Behavior:**
```
User: @ai scan SO-00767-BARENTZ Italia
Bot:  🔍 Data Quality Scan for SO-00767-BARENTZ Italia
     ✅ Customer Address: Valid
     ✅ Receivable Account: Configured
     ⚠️  MX CFDI: Missing fields
```

**Actual Behavior:**
```
User: @ai scan SO-00767-BARENTZ Italia
Bot:  [CONFIDENCE: HIGH] Here are the details for Sales Order SO-00767-BARENTZ...
     (This is the generic RaymondLucyAgent response)
```

---

## 2. Architecture Overview

### Current Flow
```
handle_raven_message()
    ↓
@ai detected → Extract query
    ↓
Keyword Routing (bot_name assignment)
    ↓
if bot_name == "sales_order_follow_up" → Sales Agent
elif bot_name == "payment_bot" → Payment Agent
elif bot_name == None → SkillRouter.route()
    ↓
SkillRouter.route() → Match triggers/patterns → skill.handle()
    ↓
Return response
```

### Key Files Involved

| File | Purpose |
|------|---------|
| `api/agent.py` | Main routing logic (700+ lines) |
| `skills/router.py` | SkillRouter class that matches and dispatches to skills |
| `skills/data_quality_scanner/skill.py` | The scanner skill implementation |
| `skills/framework.py` | SkillBase class that skills inherit from |

---

## 3. All Attempts Made

### Attempt 1: SkillRouter Integration (Initial Implementation)
- **Date:** Initial implementation
- **Method:** Added scanner to `SkillRouter._load_skills()`
- **Result:** Failed - queries never reached SkillRouter

### Attempt 2: Scanner Keywords Before SO Check
- **Date:** Previous session
- **Method:** Added scanner_keywords check BEFORE the SO-XXXXX pattern match
- **Code:**
  ```python
  scanner_keywords = ["scan ", "validate ", ...]
  if any(kw in q_lower for kw in scanner_keywords):
      bot_name = None  # Route to SkillRouter
  elif re.search(r'SO-\d+', q_lower):
      bot_name = "sales_order_follow_up"
  ```
- **Result:** Failed - still routing to sales_order_follow_up

### Attempt 3: Direct SkillRouter Call in Else Block
- **Method:** Added direct call to DataQualityScannerSkill in the else block
- **Result:** Failed - skill returned but result was ignored

### Attempt 4: Debug Logging Added
- **Method:** Added extensive logging to trace execution
- **Result:** Logs not visible - possibly not reaching the code

### Attempt 5: Syntax Error Fix
- **Date:** Last session
- **Method:** Fixed broken if/elif chain
- **Result:** Send button worked again

### Attempt 6: Pre-Processor Pattern (Current)
- **Method:** Run scanner BEFORE routing, bypass all complexity
- **Code Location:** Lines 371-401 in agent.py
- **Status:** Pushed but not tested after user stopped

---

## 4. Root Cause Analysis

### The Core Problem

The issue is NOT in the routing logic itself. The issue is that:

1. **The skill's `handle()` method is likely raising an exception** or returning in a way that causes the fall-through

2. **We don't have visibility** into what's happening inside the skill

3. **We're guessing** instead of systematically debugging

### Evidence

When `@ai scan SO-00767-BARENTZ Italia` is sent:
- Response shows `[CONFIDENCE: HIGH]` - this format is ONLY from `RaymondLucyAgent`
- This means: Either SkillRouter returned None, OR the skill raised an exception

### Possible Causes

| # | Possible Cause | Likelihood |
|---|---------------|------------|
| 1 | Skill throws exception during handle() | HIGH |
| 2 | Skill returns None instead of dict | MEDIUM |
| 3 | Skill imports fail silently | MEDIUM |
| 4 | Frappe context not available in skill | HIGH |

---

## 5. Immediate Next Steps (Before Coding)

### Step 1: Test the Skill Directly
Create a simple test to call the scanner skill directly:
```python
# In frappe bench
from raven_ai_agent.skills.data_quality_scanner.skill import DataQualityScannerSkill
scanner = DataQualityScannerSkill()
result = scanner.handle("scan SO-00767-BARENTZ Italia", {})
print(result)
```

### Step 2: Add Exception Handling in Skill
Wrap the entire handle() method in try/except to see errors:
```python
def handle(self, query, context=None):
    try:
        # existing code
    except Exception as e:
        frappe.log_error(f"Scanner error: {e}")
        return {"handled": True, "response": f"Error: {e}"}
```

### Step 3: Verify Imports Work
The skill imports from `raven_ai_agent.skills.framework`. Verify this module exists and is importable.

---

## 6. Proposed Solution (When Root Cause Confirmed)

Once we know the actual error, we can implement a proper fix. Options:

### Option A: Fix the Skill (If skill has bugs)
- Add proper error handling in the skill
- Ensure it returns correct format

### Option B: Dedicated Route (If we want permanent solution)
Add a dedicated `@ai scan` command handler:
```python
elif query.lower().startswith("scan "):
    # Direct scan handler
```

### Option C: Hybrid
- Keep pre-processor for scan/validate
- Fix skill for other cases

---

## 7. Code Locations (Current State)

### Pre-Processor (Lines 371-401)
```python
# ==================== PRE-PROCESSOR: Data Quality Scanner ====================
if plain_text.lower().startswith("@ai"):
    query = plain_text[3:].strip()
    q_lower = query.lower()
    
    scanner_precheck = ["scan", "validate", "check data", "pre-flight", "preflight", "diagnose"]
    if any(kw in q_lower for kw in scanner_precheck):
        # Run scanner and return directly
```

### SkillRouter (skills/router.py)
- Loads skills in `_load_skills()`
- Matches in `route()` method
- Returns skill.handle() result

### Scanner Skill (skills/data_quality_scanner/skill.py)
- `triggers = ["scan", "validate", ...]`
- `handle()` method does validation

---

## 8. What We Need From You

To proceed, please:

1. **Deploy the latest code** (has pre-processor)
2. **Test in Raven:** `@ai scan SO-00767-BARENTZ Italia`
3. **Check logs:** Look for any errors in bench.log

Or alternatively, run this test command on the server:
```bash
docker exec -it erpnext-backend-1 bash -c "cd /home/frappe/frappe-bench && bench console"
# Then in console:
from raven_ai_agent.skills.data_quality_scanner.skill import DataQualityScannerSkill
s = DataQualityScannerSkill()
print(s.handle("scan SO-00767-BARENTZ Italia", {}))
```

---

## 9. Lessons Learned

1. **Don't bypass - debug first**: We tried multiple workarounds without knowing the actual error
2. **Pre-processors are valid**: Running certain commands before routing is a legitimate pattern
3. **Need visibility**: Without logs, we're blind
4. **Test in isolation**: The skill should work independently before integrating

---

**Document Status:** In Progress
**Last Updated:** 2026-03-12
**Author:** AI Development Team
