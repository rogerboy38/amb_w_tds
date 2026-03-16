# BOM Phase 5 Completion Handout

## Phase 5: BOM Hooks Integration & Scheduled Health Checks

**Status:** ✅ COMPLETE  
**Date:** 2026-02-17  
**Branch:** `feature/v9.1.0-development`  
**Site:** v2.sysmayal.cloud

---

## Summary

Phase 5 transforms the BOM health system from manual scripts into an **automated monitoring system** integrated with Frappe's event hooks and scheduler.

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `amb_w_tds/amb_w_tds/bom_hooks.py` | BOM document event hooks (on_submit, on_update) |
| `amb_w_tds/amb_w_tds/scripts/scheduled_bom_health.py` | Weekly scheduled health check entry point |
| `amb_w_tds/amb_w_tds/scripts/bom_known_issues.json` | Tracked known issues (skip in reports) |

### Modified Files

| File | Changes |
|------|---------|
| `amb_w_tds/amb_w_tds/hooks.py` | Added BOM doc_events and scheduler_events |
| `amb_w_tds/amb_w_tds/scripts/bom_fixer.py` | Enhanced post_to_raven() to accept channel names |

---

## 1. BOM Event Hooks (bom_hooks.py)

### Triggered Events

| Event | Hook | Function |
|-------|------|----------|
| BOM Submit | `on_submit` | Validates structure, posts warnings to Raven |
| BOM Update | `on_update` | Lightweight checks for critical issues |

### Validation Checks

- **Self-reference detection** - BOM referencing itself
- **Circular dependency detection** - BOM hierarchy loops
- **Flat structure warning** - Large BOMs with no sub-assemblies
- **Missing component detection** - Non-existent items
- **Inactive sub-BOM detection** - Draft or inactive sub-BOMs
- **Duplicate item detection** - Same item multiple times

### Behavior

- **NON-BLOCKING** - All validations post warnings but allow operations to proceed
- Posts to Raven channel: `bom-hierarchy-audit`
- Errors are logged, never block user operations

### Manual Validation

```bash
bench execute amb_w_tds.amb_w_tds.bom_hooks.validate_bom --kwargs '{"bom_name": "BOM-XXXX-XXX"}'
```

---

## 2. Scheduled Health Check (scheduled_bom_health.py)

### Scheduler Configuration

Added to `hooks.py`:

```python
scheduler_events = {
    "weekly": [
        "amb_w_tds.scripts.scheduled_bom_health.run",
    ],
}
```

### Features

- Runs comprehensive health check weekly
- Filters out known/tracked issues
- Posts summary report to Raven
- Configurable via parameters

### Manual Execution

```bash
# Standard run (posts to Raven)
bench execute amb_w_tds.scripts.scheduled_bom_health.run

# Silent run (no Raven post)
bench execute amb_w_tds.scripts.scheduled_bom_health.run_silent

# Include known issues in report
bench execute amb_w_tds.scripts.scheduled_bom_health.run_full
```

---

## 3. Known Issues Tracking (bom_known_issues.json)

### Purpose

Track issues that cannot be auto-fixed but are acknowledged. These are filtered from weekly reports to reduce noise.

### Initial Tracked Issues

| BOM/Item | Reason |
|----------|--------|
| BOM-0301-001 | 0227 variant - expected cost difference |
| BOM-0303-005 | Cost-only BOM for pricing reference |
| 0302 | Missing item - pending master data |
| 0803-KOSHER-ORGANIC | Missing item - pending supplier confirmation |

### Management Commands

```bash
# List known issues
bench execute amb_w_tds.scripts.scheduled_bom_health.list_known_issues

# Add known issue
bench execute amb_w_tds.scripts.scheduled_bom_health.add_known_issue \
  --kwargs '{"bom": "BOM-XXXX-XXX", "reason": "Description"}'

# Remove known issue
bench execute amb_w_tds.scripts.scheduled_bom_health.remove_known_issue \
  --kwargs '{"bom": "BOM-XXXX-XXX"}'
```

---

## 4. Services Integration

### bom_service.py

- **Status:** Compatible - no changes needed
- Creates BOMs with proper structure
- Uses hierarchical cost calculation

### cost_calculation_service.py

- **Status:** Compatible - no changes needed
- Calculates hierarchical BOM costs
- Handles sub-assembly costs correctly

Both services work with the corrected BOM structures from Phase 4.

---

## 5. Testing Checklist

### Hook Testing

```bash
# 1. Validate an existing BOM manually
bench execute amb_w_tds.amb_w_tds.bom_hooks.validate_bom --kwargs '{"bom_name": "BOM-0308-001"}'

# 2. Create a test BOM in bench console to trigger hooks
bench --site v2.sysmayal.cloud console
# > bom = frappe.new_doc("BOM")
# > bom.item = "TEST-ITEM"
# > bom.quantity = 1
# > bom.save()  # Triggers on_update hook
```

### Scheduler Testing

```bash
# Test the scheduled job entry point
bench execute amb_w_tds.scripts.scheduled_bom_health.run

# Verify Raven notification received in 'bom-hierarchy-audit' channel
```

### Raven Verification

1. Go to Raven app in ERPNext
2. Check `bom-hierarchy-audit` channel
3. Confirm health report messages appear

---

## 6. Git Commands

```bash
cd ~/frappe-bench/apps/amb_w_tds
git pull origin feature/v9.1.0-development
git status
```

---

## 7. Phase 6 Recommendations

### Deployment Checklist

1. **Migrate to production** - Merge `feature/v9.1.0-development` to main
2. **Clear scheduler cache** - `bench clear-cache` after deployment
3. **Verify scheduler** - Check `bench doctor` for scheduler status
4. **Monitor first week** - Watch Raven for hook notifications

### Cleanup Tasks

- Remove backup/duplicate files (*.bak, *.old)
- Archive Phase 1-5 handouts to docs/
- Update CHANGELOG.md

### Future Enhancements

- Add BOM cost recalculation on item rate changes
- Implement BOM approval workflow
- Add email notifications alongside Raven
- Dashboard for BOM health metrics

---

## Quick Reference

| Task | Command |
|------|---------|
| Run health check | `bench execute amb_w_tds.scripts.bom_status_manager.run_health_check` |
| Run auto-fix (dry) | `bench execute amb_w_tds.scripts.bom_status_manager.auto_fix` |
| Run auto-fix (live) | `bench execute amb_w_tds.scripts.bom_status_manager.auto_fix --kwargs '{"dry_run": False}'` |
| Validate single BOM | `bench execute amb_w_tds.amb_w_tds.bom_hooks.validate_bom --kwargs '{"bom_name": "BOM-XXX"}'` |
| Weekly health (manual) | `bench execute amb_w_tds.scripts.scheduled_bom_health.run` |
| List known issues | `bench execute amb_w_tds.scripts.scheduled_bom_health.list_known_issues` |

---

**Phase 5 Complete** ✅

The BOM health monitoring system is now automated and will run weekly, posting reports to Raven. All BOM submissions are validated with warnings posted for any structural issues.
