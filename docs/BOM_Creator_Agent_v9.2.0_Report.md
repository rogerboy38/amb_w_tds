# BOM Creator Agent v9.2.0 - Technical Report

**Date:** 2026-02-18  
**Version:** v9.2.0  
**Status:** ✅ Production Ready  
**Branch:** `feature/v9.2.0-development`

---

## Executive Summary

The BOM Creator Agent v9.2.0 has been successfully refactored to work with real production data from the AMB-Wellness ERP system. The agent now correctly creates multi-level Bill of Materials (BOM) hierarchies with proper item naming conventions that match existing ERPNext item variants.

### Key Achievements
- ✅ Agent aligned with real production items (0307, 0227)
- ✅ Item naming follows ERPNext variant pattern (e.g., `0307- Fair Trade-25KG-BAG`)
- ✅ Multi-level BOM creation with sub-assembly reuse
- ✅ Dry-run mode for safe testing
- ✅ Full integration with ERPNext ItemAndBOMService

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (api.py)                        │
│  create_multi_level_bom_from_spec() - Main Entry Point       │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Parser (parser.py)                          │
│  ProductSpecificationParser - Parses "0307" → ParsedSpec     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│               Core Engine (engine.py)                        │
│  AgentCoreEngine - Orchestrates BOM generation               │
│  ├── _plan_hierarchy() - Plans items & BOMs                  │
│  ├── _generate_fg_item() - Creates FG naming                 │
│  ├── _create_items() - Creates items in ERPNext              │
│  └── _create_boms() - Creates BOMs in ERPNext                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Templates (templates/)                          │
│  template_0307_master.json - Spray Drying process            │
│  template_0227_master.json - Liquid Concentrate process      │
└─────────────────────────────────────────────────────────────┘
```

---

## API Reference

### Main Endpoint

```python
@frappe.whitelist()
def create_multi_level_bom_from_spec(
    request_text: str,
    dry_run: bool = False,
    company: str = "AMB-Wellness"
) -> dict
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `request_text` | str | required | Product family code (e.g., "0307") |
| `dry_run` | bool | False | If True, plans but doesn't create documents |
| `company` | str | "AMB-Wellness" | ERPNext company for document creation |

**Returns:**
```json
{
    "success": true,
    "spec": { "family": "0307", "packaging": "25KG-BAG", ... },
    "items_created": ["0307- Fair Trade-25KG-BAG"],
    "items_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
    "boms_created": ["0307- Fair Trade-25KG-BAG"],
    "boms_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
    "errors": [],
    "warnings": [],
    "dry_run": false,
    "execution_time_seconds": 0.53
}
```

### Usage Examples

```bash
# Dry-run (preview only)
bench --site v2.sysmayal.cloud execute \
    amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
    --kwargs '{"request_text": "0307", "dry_run": True}'

# Live execution (creates documents)
bench --site v2.sysmayal.cloud execute \
    amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
    --kwargs '{"request_text": "0307", "dry_run": False}'
```

---

## Item Naming Convention

The agent generates item codes matching ERPNext variant patterns:

### Finished Goods (FG)
**Pattern:** `{FAMILY}- {CERTIFICATION}-{PACKAGING}`

**Examples:**
- `0307- Fair Trade-25KG-BAG`
- `0227-30X- Fair Trade-220L-BRRL`

### Semi-Finished Goods (SFG)
**Pattern:** `SFG-{FAMILY}-STEP{N}-{PROCESS}`

**Examples:**
- `SFG-0307-STEP1-SPRAY-DRYING`
- `SFG-0227-STEP1-CONCENTRATION`

---

## Files Modified

| File | Changes |
|------|---------|
| `api.py` | Added `company` parameter with default "AMB-Wellness" |
| `engine.py` | Rewrote `_generate_fg_item()` for variant-aware naming; Fixed `_resolve_item_pattern()` for None handling |
| `template_0307_master.json` | Aligned with production structure (steps, input_items) |
| `template_0227_master.json` | Verified and aligned |
| `test_v9.2.0_phase3_mrp.sh` | Updated to use real item codes |

---

## Commit History

| Commit | Message |
|--------|---------|
| `e5b7b5e` | v9.2.0: Align BOM Creator with real production data |
| `88f51f7` | Fix test script: Python True/False and heredoc issues |
| `f480086` | Fix template: Add missing 'steps' key to 0307 template |
| `c05c9ea` | Fix API: Add company parameter to prevent 'Company' error |
| `9c3e28e` | Fix template: Use input_items/item_pattern structure |
| `03aed74` | Fix engine: Handle None values in pattern resolution |
| `aef1b75` | Implement variant-aware FG naming with certification |
| `c9a0679` | Fix naming: Add leading space for certification match |

---

## Test Results

### Dry-Run Test (2026-02-18)
```json
{
    "success": true,
    "items_created": ["0307- Fair Trade-25KG-BAG"],
    "items_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
    "boms_created": ["0307- Fair Trade-25KG-BAG"],
    "boms_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
    "errors": [],
    "dry_run": true
}
```

### Live Test (2026-02-18)
```json
{
    "success": true,
    "items_created": ["0307- Fair Trade-25KG-BAG"],
    "items_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
    "boms_created": ["0307- Fair Trade-25KG-BAG"],
    "boms_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
    "errors": [],
    "dry_run": false,
    "execution_time_seconds": 0.53
}
```

---

## Known Limitations

1. **Sub-assembly BOM linking:** The `bom_no` field for sub-assemblies is not yet automatically looked up and linked in the FG BOM.

2. **Single certification:** Currently defaults to "Fair Trade" when no certification is specified. Future versions may support multiple certifications.

3. **Template-dependent:** Each product family requires a master template. New families need templates to be added.

---

## Next Steps for Orchestrator Integration

The BOM Creator Agent is ready to be integrated with the Orchestrator Agent. The recommended integration approach:

```python
# Orchestrator can call the agent via frappe.call
result = frappe.call(
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec",
    request_text="0307",  # Product family from user request
    dry_run=False,
    company="AMB-Wellness"
)

if result.get("success"):
    # BOM created successfully
    items = result.get("items_created", [])
    boms = result.get("boms_created", [])
else:
    # Handle errors
    errors = result.get("errors", [])
```

---

## Production Deployment

To deploy to production:

```bash
# On production server
cd ~/frappe-bench/apps/amb_w_tds
git fetch origin
git checkout feature/v9.2.0-development
git pull origin feature/v9.2.0-development
bench --site production.site migrate
```

---

**Report Generated:** 2026-02-18  
**Author:** Matrix Agent
