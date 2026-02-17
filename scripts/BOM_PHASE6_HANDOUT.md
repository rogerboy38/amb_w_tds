# Phase 6 Handout - BOM Hooks Integration & Repo Cleanup

## Session Status: IN PROGRESS

**Branch:** `feature/v9.1.0-development`
**Last Commit:** `a0cec28` (Phase 5 complete)
**Date:** 2026-02-17

---

## COMPLETED IN THIS SESSION

### Task 1: Raven AI Agent BOM Integration ✅
- Created `amb_w_tds/amb_w_tds/raven/bom_tracking_agent.py`
  - Commands: `bom health`, `bom inspect <BOM>`, `bom status <ITEM>`, `bom issues`
  - Integrates with `bom_status_manager.run_health_check()`
  - Reads from `bom_known_issues.json`
- Updated `amb_w_tds/amb_w_tds/raven/config.py` to register both agents
- Updated `amb_w_tds/amb_w_tds/raven/__init__.py`

### Task 2: Repo Cleanup - Junk Files Staged for Deletion ✅
Files staged for `git rm`:
- Root: `===`, `FETCH_HEAD`, `FILTER`, `KEEP`, `phase_a_git_push.sh`, `phase_b_git_push.sh`, `push_to_git_plus.sh`
- App: `hooks.py.backup`, `hooks.py.bakup.20251220_153025`, `test_agent.py`
- Raven: `config.py.backup`, `serial_tracking_agent.py.full`, `serial_tracking_agent_simple.py`

**NOTE:** Kept `serial_minimal_working.py` - it's the working serial agent used by config.py

---

## REMAINING TASKS

### Task 3: Update Version & README
1. Update `version.txt` to `9.1.0`
2. Verify `__init__.py` has version 9.1.0
3. Update `README.md`:
   - Version badge: v7.0.0 → v9.1.0
   - Title: "Version 9.1.0 - BOM Hierarchy & AI Agent Release"
   - Add "What's New in v9.1.0" section
   - Update scripts section
4. Create `v9.1.0_RELEASE_NOTES.md`

### Task 4: Verify hooks.py
- Confirm BOM doc_events registered
- Confirm scheduler_events for weekly health check
- Ensure app_version = 9.1.0

### Task 5: Final Verification (on production)
```bash
bench --site v2.sysmayal.cloud execute amb_w_tds.scripts.bom_status_manager.run_health_check_dry
bench --site v2.sysmayal.cloud execute amb_w_tds.scripts.scheduled_bom_health.run
bench --site v2.sysmayal.cloud console
>>> import amb_w_tds
>>> import amb_w_tds.raven.bom_tracking_agent
```

### Task 6: Create Final Report
- `BOM_PHASE6_FINAL_REPORT.md` with full project summary

### Task 7: Update Raven AI Agent Help Table
- User reminder at end of Phase 6

---

## GIT STATUS (as of session end)

```
Staged deletions: 13 junk/backup files
Modified (unstaged): 
  - amb_w_tds/raven/__init__.py
  - amb_w_tds/raven/config.py
Untracked:
  - amb_w_tds/raven/bom_tracking_agent.py
```

---

## NEXT SESSION START COMMAND

```bash
cd /workspace/amb_w_tds && git status
```

Then continue with Task 3 (version & README updates).
