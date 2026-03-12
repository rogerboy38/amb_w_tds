# Data Quality Scanner - Test Plan
## Phase 1: Implementation Validation

---

## 🎯 Test Objective

Validate that the Data Quality Scanner correctly detects issues before they cause errors in the Raven channel operations.

---

## ✅ Completion Criteria

### Must Pass (Go/No-Go)

| # | Criterion | Test Method | Target |
|---|-----------|--------------|--------|
| 1 | Scanner loads without errors | Check bench console import | No ImportError |
| 2 | Detects missing customer address | Test on SO with no address | HIGH issue detected |
| 3 | Detects broken address link | Test on SO with invalid address | CRITICAL issue detected |
| 4 | Detects group account | Test on SO with group receivable | CRITICAL issue detected |
| 5 | Detects currency mismatch | Test on USD invoice in MXN company | HIGH issue detected |
| 6 | Detects missing MX fields | Test on SI without CFDI fields | HIGH issue detected |
| 7 | Detects group cost center | Test on SO with group CC | CRITICAL issue detected |
| 8 | Raven channel responds | Send `@ai scan SO-XXXXX` | Response displayed |

### Should Pass (Quality)

| # | Criterion | Test Method | Target |
|---|-----------|--------------|--------|
| 9 | Confidence score accurate | Compare to actual issues | ±15% accuracy |
| 10 | Auto-fix suggestions shown | Check response | All issues show fix |
| 11 | Memory integration works | Check AI Memory created | Memory stored |
| 12 | Works on Sales Invoice | Test on ACC-SINV-XXXXX | Correct detection |
| 13 | Works on Quotation | Test on SAL-QTN-XXXXX | Correct detection |

---

## 🧪 Test Cases

### Test Case 1: Basic Import
```python
# bench console
from raven_ai_agent.skills.data_quality_scanner.skill import DataQualityScannerSkill
scanner = DataQualityScannerSkill()
print("✅ Loaded successfully")
```
**Expected:** No errors, object created

---

### Test Case 2: Scan Clean Document
```python
# Find a known good SO
result = scanner.scan_sales_order("SO-00767-BARENTZ Italia S.p.A")
print(result["confidence"])  # Should be > 0.9
print(result["can_proceed"])  # Should be True
```
**Expected:** HIGH confidence, can proceed

---

### Test Case 3: Scan Document with Issues (from Raven history)

Based on the Raven conversation, these SOs had issues:
- SO-00769-COSMETILAB 18 - had address issues
- SO-XXXXX with missing MX fields

```python
result = scanner.scan_sales_order("SO-00769-COSMETILAB 18")
print(f"Issues found: {result['total_issues']}")
print(f"Confidence: {result['confidence']}")
for issue in result["issues"]:
    print(f"  - {issue['type']}: {issue['message']}")
```
**Expected:** Multiple issues detected, confidence < 0.8

---

### Test Case 4: Sales Invoice Scan

```python
# Test on known invoice from batch
result = scanner.scan_sales_invoice("ACC-SINV-2026-00070")
print(f"Issues found: {result['total_issues']}")
```
**Expected:** Issues related to accounts, CFDI fields

---

### Test Case 5: Quotation Scan

```python
result = scanner.scan_quotation("SAL-QTN-2024-00763")
print(f"Issues: {result['total_issues']}")
print(f"Can proceed: {result['can_proceed']}")
```
**Expected:** Detects missing fields if any

---

### Test Case 6: Raven Channel Integration

**Steps:**
1. Open Raven channel: https://erp.sysmayal2.cloud/raven/AMB-Wellness/AMB-Wellness-implementacion-amb-sysmayal2
2. Send: `@ai scan SO-00767-BARENTZ Italia`
3. Bot should respond with scan results

**Expected Response Format:**
```
## 🔍 Data Quality Scan: SO-00767-...

🟢 HIGH CONFIDENCE: 95%

✅ No issues found! Document is ready for processing.
```

---

### Test Case 7: Raven Channel with Issues

**Steps:**
1. Send: `@ai scan SO-00769-COSMETILAB 18`
2. Bot should show issues

**Expected Response Format:**
```
## 🔍 Data Quality Scan: SO-00769-...

🟡 MEDIUM CONFIDENCE: 75%

### 🔴 Critical Issues (1)
- Address '...' does not exist
  - Field: `customer_address`
  - Auto-fix: resolve_from_customer (90% confidence)

---

**Summary:** 3 issues, 2 auto-fixable

✅ Can proceed - Minor issues can be auto-fixed during execution.
```

---

## 📋 Test Execution Script

Run this in bench console:

```python
# ============================================================
# DATA QUALITY SCANNER - TEST SCRIPT
# ============================================================

import frappe
from raven_ai_agent.skills.data_quality_scanner.skill import DataQualityScannerSkill

scanner = DataQualityScannerSkill()

print("=" * 60)
print("TEST 1: Import")
print("=" * 60)
print("✅ Scanner loaded successfully")

print("\n" + "=" * 60)
print("TEST 2: Scan Clean Document")
print("=" * 60)
result = scanner.scan_sales_order("SO-00767-BARENTZ Italia S.p.A")
print(f"Document: {result.get('document_name')}")
print(f"Customer: {result.get('customer')}")
print(f"Issues: {result.get('total_issues')}")
print(f"Confidence: {result.get('confidence')}")
print(f"Can Proceed: {result.get('can_proceed')}")
if result.get('issues'):
    for issue in result['issues']:
        print(f"  - {issue['type']}: {issue['message']}")

print("\n" + "=" * 60)
print("TEST 3: Scan Document with Issues")
print("=" * 60)
# Try other SOs that might have issues
sos_to_test = [
    "SO-00769-COSMETILAB 18",
    "SO-00753-GREENTECH SA",
    "SO-00752-LEGOSAN AB"
]
for so_name in sos_to_test:
    try:
        result = scanner.scan_sales_order(so_name)
        print(f"\n{so_name}:")
        print(f"  Issues: {result.get('total_issues')}")
        print(f"  Confidence: {result.get('confidence')}")
        if result.get('issues'):
            for issue in result['issues'][:3]:  # Show first 3
                print(f"    - {issue['type']}: {issue['message'][:50]}")
    except Exception as e:
        print(f"\n{so_name}: ERROR - {e}")

print("\n" + "=" * 60)
print("TEST 4: Sales Invoice")
print("=" * 60)
try:
    result = scanner.scan_sales_invoice("ACC-SINV-2026-00070")
    print(f"Issues: {result.get('total_issues')}")
    print(f"Confidence: {result.get('confidence')}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("Tests completed. Check results above.")
```

---

## 🚀 Raven Channel Test Commands

Test these commands in the Raven channel:

| # | Command | Expected |
|---|---------|----------|
| 1 | `@ai scan SO-00767-BARENTZ Italia` | Clean scan, HIGH confidence |
| 2 | `@ai validate SO-00769-COSMETILAB 18` | Issues found |
| 3 | `@ai check data SAL-QTN-2024-00763` | Quotation scan |
| 4 | `@ai scan ACC-SINV-2026-00070` | Invoice scan |
| 5 | `@ai help scan` | Show help |

---

## 📊 Success Metrics

### Quantitative Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Detection Rate | >95% | Issues found / Known issues |
| False Positive Rate | <5% | Clean docs marked as issues |
| Response Time | <2 seconds | Time to scan |
| Raven Integration | 100% | Commands respond |

### Qualitative Targets

- [ ] All 8 Raven commands return valid responses
- [ ] Confidence score matches actual issue severity
- [ ] Auto-fix suggestions are accurate
- [ ] Memory integration works (AI Memory created)

---

## 🐛 Bug Reporting Template

If issues found, document:

```markdown
## Bug Report: Data Quality Scanner

**Date:** 
**Test Case:** #
**Command:** 
**Expected:** 
**Actual:** 
**Severity:** 

**Steps to Reproduce:**
1. 
2. 
3. 

**Error Message:**
```

---

## ✅ Sign-off Checklist

- [ ] All Must Pass criteria met (8/8)
- [ ] At least 10 Should Pass criteria met (10/13)
- [ ] No critical bugs blocking production
- [ ] Documentation updated
- [ ] Memory integration verified
- [ ] Raven channel commands working

**Status:** 🟢 READY FOR PRODUCTION / 🔴 NEEDS FIXES
