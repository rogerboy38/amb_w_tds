# Implementation Roadmap: Intelligent Pre-flight System
## 3-Week Sprint Plan

---

## 🗓️ WEEK 1: Data Quality Scanner

### Day 1-2: Core Scanner Skill
**File:** `raven_ai_agent/skills/data_quality_scanner/skill.py`

**Deliverables:**
```python
class DataQualityScannerSkill:
    name = "data_quality_scanner"
    description = "Pre-flight validation for ERPNext operations"
    triggers = ["scan", "validate", "check data"]
    
    def handle(self, query, context):
        # Implementation
        pass
```

**Validation Rules to Implement:**
- [x] Customer Address validation (8 types from commit history)
- [x] Account configuration validation (6 types)
- [x] MX CFDI field validation (3 types)
- [x] Cost Center group detection
- [x] Currency mismatch detection
- [x] Inventory availability check

### Day 3-4: Integration with BatchOrchestrator
**File:** `raven_ai_agent/agents/batch_orchestrator.py`

**Changes:**
```python
# Before execution
scan_result = self.scanner.scan_sales_order(so_name)
if scan_result["issues"]:
    report += f"\n⚠️ Found {len(scan_result['issues'])} issues"
    # Continue with current behavior for now
```

### Day 5: Testing & Deployment
- [ ] Test scanner against 20 historical bug cases
- [ ] Verify 95% detection rate
- [ ] Deploy to production with monitoring
- [ ] Git commit + deployment command

**Deployment Command:**
```bash
cd raven_ai_agent
git add skills/data_quality_scanner/
git commit -m "Add: Pre-flight data quality scanner skill"
git push origin main

# VPS deployment
docker exec -it erpnext-backend-1 bash -c "cd /home/frappe/frappe-bench/apps/raven_ai_agent && git pull origin main"
docker restart erpnext-backend-1
```

---

## 🗓️ WEEK 2: Self-Healing Fixer

### Day 1-2: Core Fixer Skill
**File:** `raven_ai_agent/skills/self_healing_fixer/skill.py`

**Auto-fix Capabilities:**
```python
class SelfHealingFixerSkill:
    AUTO_FIX_PATTERNS = {
        "missing_address": {
            "method": "_create_address_from_customer",
            "confidence": 0.90,
            "priority": "HIGH"
        },
        "account_mismatch": {
            "method": "_set_default_receivable_account",
            "confidence": 0.95,
            "priority": "HIGH"
        },
        "missing_mx_fields": {
            "method": "_set_cfdi_defaults",
            "confidence": 0.85,
            "priority": "MEDIUM"
        },
        "group_cost_center": {
            "method": "_find_leaf_cost_center",
            "confidence": 0.80,
            "priority": "MEDIUM"
        },
        "currency_mismatch": {
            "method": "_enforce_mxn_account",
            "confidence": 0.88,
            "priority": "HIGH"
        }
    }
```

### Day 3: Integration with Scanner
**Enhanced flow:**
```python
# Integrated pipeline
scan_result = scanner.scan(doc)
if scan_result["issues"]:
    fix_result = fixer.auto_fix(doc, scan_result["issues"])
    
    # Report to user
    message = f"""
    🔍 Scanned: {doc.name}
    ⚠️ Found: {len(scan_result["issues"])} issues
    ✅ Fixed: {len(fix_result["fixed"])} automatically
    ⏸️ Manual: {len(fix_result["failed"])} require attention
    """
```

### Day 4-5: Testing & Learning Database
- [ ] Test auto-fix on 15 historical cases
- [ ] Build fix pattern database (JSON)
- [ ] Add learning loop (successful fixes → new patterns)
- [ ] Deploy to production

**Learning Database Schema:**
```json
{
  "fix_patterns": [
    {
      "issue_type": "missing_address",
      "detection_pattern": "customer_address field is empty",
      "fix_method": "create_from_customer",
      "success_rate": 0.92,
      "total_attempts": 25,
      "last_updated": "2026-03-15"
    }
  ]
}
```

---

## 🗓️ WEEK 3: Confidence-Aware Execution

### Day 1-2: Confidence Scoring Engine
**File:** `raven_ai_agent/api/confidence_engine.py`

**Algorithm:**
```python
class ConfidenceEngine:
    def calculate_confidence(self, scan_result, fix_result):
        """
        Calculate operation confidence score (0-1)
        
        Factors:
        - Data quality score (40%)
        - Auto-fix success rate (30%)
        - Historical success rate (20%)
        - User override history (10%)
        """
        base_score = 1.0
        
        # Deduct for unfixed issues
        critical_issues = [i for i in scan_result["issues"] if i["severity"] == "HIGH"]
        base_score -= len(critical_issues) * 0.15
        
        # Deduct for failed fixes
        base_score -= len(fix_result["failed"]) * 0.10
        
        # Add for successful fixes
        base_score += len(fix_result["fixed"]) * 0.05
        
        return max(0.0, min(1.0, base_score))
```

### Day 3: Enhanced Command Router
**File:** `raven_ai_agent/api/command_router.py`

**Changes:**
```python
def execute_workflow_command_v2(self, query, channel_id, confirm=False):
    """Enhanced execution with pre-flight validation"""
    
    # Step 1: Parse command
    cmd = self._parse_command(query)
    
    # Step 2: Pre-flight scan
    scan = self.scanner.scan(cmd.target_doc)
    
    # Step 3: Calculate confidence
    confidence = self.confidence_engine.calculate(scan, fix_result={})
    
    # Step 4: Report if low confidence
    if confidence < 0.7 and not confirm:
        return self._request_confirmation(scan, confidence)
    
    # Step 5: Auto-fix
    if scan["issues"]:
        fix_result = self.fixer.auto_fix(cmd.target_doc, scan["issues"])
    
    # Step 6: Execute
    result = self._execute_command(cmd)
    
    # Step 7: Enhanced report
    return self._format_result(result, confidence, scan, fix_result)
```

### Day 4: User Experience Updates
**Raven channel response templates:**

```python
# Template: Low confidence warning
LOW_CONFIDENCE_TEMPLATE = """
⚠️ [CONFIDENCE: LOW - {confidence}%]

Pre-flight scan found {issue_count} issues:
{issue_list}

I can auto-fix {fixable_count} of them.
{manual_count} require your attention:
{manual_list}

Proceed anyway? Type 'yes' to confirm.
"""

# Template: Success with fixes
SUCCESS_WITH_FIXES_TEMPLATE = """
✅ [CONFIDENCE: {level} - {confidence}%]

{operation} completed successfully!
📊 Auto-fixed {fixed_count} issues:
{fixed_list}

{result_details}
"""
```

### Day 5: Testing & Deployment
- [ ] End-to-end testing with real Raven channel
- [ ] User acceptance testing (UAT)
- [ ] Performance monitoring
- [ ] Full production deployment

---

## 📋 TESTING CHECKLIST

### Regression Tests (Historical Bugs)
- [ ] Test case 1: Missing customer address → Auto-create
- [ ] Test case 2: Group account in invoice → Find leaf account
- [ ] Test case 3: MX CFDI fields missing → Set defaults
- [ ] Test case 4: Currency mismatch USD/MXN → Enforce MXN account
- [ ] Test case 5: Cost center group → Find leaf center
- [ ] Test case 6: Broken address link → Resolve from customer
- [ ] Test case 7: Multiple issues → Fix all, report unfixable
- [ ] Test case 8: High confidence path → Execute without user prompt

### New Scenarios
- [ ] Batch operation with 20 orders (mixed quality)
- [ ] Single invoice with perfect data (confidence = 100%)
- [ ] Order with unfixable issues (require manual intervention)
- [ ] Confidence scoring accuracy (±5% of actual success rate)

---

## 🎯 SUCCESS METRICS (Weekly Tracking)

### Week 1 Targets
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Scanner detection rate | >95% | ___ | ⏳ |
| False positives | <5% | ___ | ⏳ |
| Scan time per document | <200ms | ___ | ⏳ |
| Integration with batch | 100% | ___ | ⏳ |

### Week 2 Targets
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Auto-fix success rate | >70% | ___ | ⏳ |
| Time to fix (avg) | <5 sec | ___ | ⏳ |
| Fix pattern database | 15+ patterns | ___ | ⏳ |
| Zero regressions | 0 bugs | ___ | ⏳ |

### Week 3 Targets
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Confidence accuracy | ±10% | ___ | ⏳ |
| User intervention reduction | -70% | ___ | ⏳ |
| Bug rate reduction | -80% | ___ | ⏳ |
| Development velocity | +100% | ___ | ⏳ |

---

## 🔄 DEPLOYMENT PROCESS (Per Week)

### Standard Deployment Flow
```bash
# 1. Local development & testing
cd /workspace/raven_ai_agent
pytest tests/test_[feature].py

# 2. Commit to Git
git add .
git commit -m "[Week X] Feature: [description]"
git push origin main

# 3. Deploy to VPS Production
ssh root@72.62.131.198

# Inside VPS:
docker exec -it erpnext-backend-1 bash
cd /home/frappe/frappe-bench/apps/raven_ai_agent
git pull origin main
exit

docker restart erpnext-backend-1

# 4. Monitor logs
docker logs -f erpnext-backend-1 | grep "AI Agent"

# 5. Test in Raven channel
# Navigate to: https://erp.sysmayal2.cloud/raven/...
# Run test commands
```

---

## 📝 DOCUMENTATION UPDATES

### Files to Update
- [x] `/docs/intelligent_development_proposal.md` - DONE
- [x] `/docs/implementation_roadmap.md` - THIS FILE
- [ ] `README.md` - Add new capabilities section
- [ ] `raven_ai_agent/skills/AGENTS.md` - Document new skills
- [ ] `/memories/raven_ai_agent_status.md` - Update progress

### User Guide Sections
- [ ] "How to interpret confidence scores"
- [ ] "Understanding pre-flight scan results"
- [ ] "When to override low confidence warnings"
- [ ] "Auto-fix pattern database"

---

## 🚨 RISK MITIGATION

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scanner false positives | MEDIUM | LOW | Extensive testing, user override option |
| Auto-fix corrupts data | HIGH | LOW | Dry-run mode, rollback capability |
| Performance degradation | LOW | MEDIUM | Async scanning, caching |
| User confusion | MEDIUM | MEDIUM | Clear messaging, gradual rollout |

---

## ✅ COMPLETION CRITERIA

### Phase Complete When:
1. All unit tests pass (>95% coverage)
2. Zero critical bugs in production
3. User feedback positive (>80% satisfaction)
4. Metrics meet targets
5. Documentation complete
6. Team training complete

**Sign-off Required From:**
- [ ] Technical Lead (Rogelio)
- [ ] QA Team
- [ ] End Users (Administrator Technical, Liliana)

---

**Document Status:** Draft v1.0  
**Last Updated:** 2026-03-12  
**Next Review:** After Week 1 completion
