# Raven AI Agent - Formulation Orchestrator Handout

## Last Updated: 2026-02-14

## Project Overview
ERPNext Raven AI integration with formulation workflow capabilities.

**Repository:** https://github.com/rogerboy38/raven_ai_agent.git
**Latest Commit:** `b0ba0bc` - "Improve report clarity for missing COA and cost data"

## Completed Work

### 1. Skill-Based Routing (DONE)
- Modified `raven_ai_agent/api/agent.py` to integrate `SkillRouter`
- Queries with trigger words like "formulate" now route to `FormulationOrchestratorSkill`
- Falls back to default `RaymondLucyAgent` if no skill matches

### 2. Data Normalization Fix (DONE)
- Fixed field mismatch between `BatchSelectorAgent` (`qty_available`) and `CostCalculatorAgent` (`qty`)
- Added normalization step in `raven_ai_agent/skills/formulation_orchestrator/skill.py`

### 3. Report Clarity Improvements (DONE)
- **`tds_compliance.py`**: Now counts batches with missing COA data (`no_coa_count`)
- **`report_generator.py`**: 
  - Shows `⚠️ NO COA DATA` instead of confusing `❌ FAILED` with 0/0 counts
  - Recommendations now state "Compliance could not be verified due to missing COA records"

## Key Files
- `raven_ai_agent/api/agent.py` - Main message handler with skill routing
- `raven_ai_agent/skills/router.py` - SkillRouter class
- `raven_ai_agent/skills/formulation_orchestrator/skill.py` - Main orchestrator
- `raven_ai_agent/skills/formulation_orchestrator/agents/` - Sub-agents:
  - `batch_selector.py`
  - `tds_compliance.py`
  - `cost_calculator.py`
  - `report_generator.py`

## Test Command
```
@ai formulate 100kg of ITEM_0612185231
```

## Known Data Issues (Not Code Bugs)
- Test items may lack `valuation_rate` → Cost shows MXN 0.00
- Batches may lack COA records → Compliance shows "NO COA DATA"

## Next Steps / Potential Improvements
1. Test the refined report output with user
2. Consider adding more detailed cost breakdown when data is available
3. Could add support for specifying TDS parameters in the formulation request
