# BOM Agent Development - Session Handout

**Date:** 2026-02-19  
**Branch:** `feature/v9.2.0-development`  
**Latest Commit:** `6878869`  
**Repository:** https://github.com/rogerboy38/amb_w_tds.git

---

## Project Summary

AI-powered Bill of Materials (BOM) creation agent for AMB Wellness, an Aloe Vera products manufacturer. The agent parses natural language requests and generates multi-level BOMs in ERPNext/Frappe.

---

## Completed Phases This Session

### Phase 3: Flavor → Variant Refactor ✅
- Renamed `flavor` field to `variant` across entire codebase
- Updated `ParsedSpec` dataclass, engine, parser, templates
- Commit: `eb44fb0`

### Phase 3B: Documentation Cleanup ✅
- Updated `naming_conventions.md` with real product codes
- Removed MANGO/PLAIN examples, replaced with 30X/HIGHPOL
- Commit: `64122f6`

### Phase 4: Variant Parsing Logic ✅
- Added `RATIO_PATTERNS` for parsing concentration ratios (30:1 → 30X)
- Added `valid_variants` and `default_concentration` to `PRODUCT_FAMILIES`
- Implemented `_extract_variant()` method
- Commits: `840235d`, `a068c67`

### Phase 5: Certification/Attribute Parsing ✅
- Added `CERTIFICATION_MAP` with all AMB Wellness certifications
- Implemented `_extract_certification()` method
- Fixed FG naming pattern: `{FAMILY}-{ATTRIBUTE}-{VARIANT}-{PACKAGING}`
- Commit: `6878869`

---

## Current FG Naming Pattern

```
{FAMILY}-{ATTRIBUTE}-{VARIANT}-{PACKAGING}
```

Examples:
- `0227-FT-30X-1000L-IBC` (Fair Trade, 30:1 concentrate in IBC)
- `0227-ORG-10X-1000L-IBC` (Organic, 10:1 concentrate)
- `0307-KOS-200X-25KG-BAG` (Kosher, 200:1 powder)
- `0307-KOS-ORG-200X-25KG-BAG` (Kosher Organic, powder)

---

## Key Files

| File | Purpose |
|------|---------|
| `ai_bom_agent/parser.py` | Request parsing, variant/certification extraction |
| `ai_bom_agent/engine.py` | BOM generation logic, FG item naming |
| `ai_bom_agent/data_contracts.py` | ParsedSpec dataclass |
| `ai_bom_agent/api.py` | API entry point |
| `ai_bom_agent/templates/` | Business rules, naming conventions |

---

## Certification Codes

| Input | Code |
|-------|------|
| ORGANIC | ORG |
| CONVENTIONAL | CONV |
| KOSHER | KOS |
| KOSHER ORGANIC | KOS-ORG |
| FAIR TRADE | FT (default) |
| HALAL | HALAL |
| IASC | IASC |
| FSSC | FSSC |
| COSMOS | COSMOS |

---

## Product Families

| Family | Type | Default Variant | Valid Variants |
|--------|------|-----------------|----------------|
| 0227 | Gel Concentrate | 30X | 1X, 10X, 20X, 30X |
| 0307 | Spray Dried Powder | 200X | 100X, 200X |
| 0303 | Normal Powder | 200X | (none) |
| 0301 | Powder Base | 200X | (none) |

---

## Test Command Template

```bash
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0227 organic 10:1", "dry_run": True}'
```

---

## Sandbox Access

- **Frappe Site:** v2.sysmayal.cloud
- **GitHub PAT:** Configured in secrets
- **SSH:** Available on sandbox

---

## Potential Next Steps

1. **Phase 6:** Mesh size parsing for powder products
2. **Phase 7:** Customer-specific naming patterns
3. **Phase 8:** Batch/lot tracking integration
4. **Phase 9:** Frappe UI for variant selection
