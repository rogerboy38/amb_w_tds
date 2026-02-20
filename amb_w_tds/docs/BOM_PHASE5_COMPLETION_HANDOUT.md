# BOM Phase 5 Completion Handout

**Completed:** 2026-02-19  
**Branch:** feature/v9.2.0-development  
**Status:** ✅ COMPLETE

---

## Phase 5 Summary: Certification/Attribute Parsing

### Changes Made

#### 1. parser.py - Certification Map & Extraction
- Added `CERTIFICATION_MAP` dictionary mapping input variants to standard codes:
  - ORGANIC/ORG → "ORG"
  - CONVENTIONAL/CONV → "CONV"
  - KOSHER/KOS → "KOS"
  - KOSHER ORGANIC/KOS-ORG → "KOS-ORG"
  - FAIR TRADE/FAIRTRADE/FT → "FT"
  - HALAL → "HALAL"
  - IASC → "IASC"
  - FSSC/FSSC 22000 → "FSSC"
  - COSMOS/ECOCERT → "COSMOS"

- Added `DEFAULT_CERTIFICATION = "FT"` (Fair Trade is default)

- Implemented `_extract_certification()` method:
  - Searches request text for certification keywords
  - Matches longest phrases first ("KOSHER ORGANIC" before "KOSHER")
  - Returns certification CODE (e.g., "ORG" not "ORGANIC")
  - Falls back to DEFAULT_CERTIFICATION if none found

#### 2. parser.py - Updated Parsing Methods
- `_parse_item_code()`: Now calls `_extract_certification()` and sets `spec.attribute`
- `_parse_natural_language()`: Now calls `_extract_certification()` and sets `spec.attribute`

#### 3. engine.py - Fixed FG Naming Pattern
- Updated `_generate_fg_item()` to use correct pattern: `{FAMILY}-{ATTRIBUTE}-{VARIANT}-{PACKAGING}`
- Removed hardcoded " Fair Trade" certification
- Added `cert_names` mapping for human-readable item names

### FG Naming Pattern

**Old (incorrect):** `0227-30X- Fair Trade-1000L-IBC`  
**New (correct):** `0227-FT-30X-1000L-IBC`

Pattern: `{FAMILY}-{ATTRIBUTE}-{VARIANT}-{PACKAGING}`
- FAMILY: Product family code (0227, 0307, etc.)
- ATTRIBUTE: Certification code (FT, ORG, KOS, etc.)
- VARIANT: Concentration ratio (30X, 200X, etc.)
- PACKAGING: Container format (1000L-IBC, 25KG-BAG, etc.)

### Test Commands

```bash
# Pull latest
cd /home/frappe/frappe-bench/apps/amb_w_tds
git pull origin feature/v9.2.0-development

# Test 1 - Default (Fair Trade)
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0227", "dry_run": True}'
# Expected: attribute=FT, variant=30X, FG=0227-FT-30X-1000L-IBC

# Test 2 - Explicit organic
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0227 organic 10:1 concentrate", "dry_run": True}'
# Expected: attribute=ORG, variant=10X, FG=0227-ORG-10X-1000L-IBC

# Test 3 - Kosher powder
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 kosher", "dry_run": True}'
# Expected: attribute=KOS, variant=200X, FG=0307-KOS-200X-25KG-BAG

# Test 4 - Explicit Fair Trade
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0227 fair trade 30:1", "dry_run": True}'
# Expected: attribute=FT, variant=30X, FG=0227-FT-30X-1000L-IBC

# Test 5 - Kosher Organic combo
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 kosher organic 200:1", "dry_run": True}'
# Expected: attribute=KOS-ORG, variant=200X, FG=0307-KOS-ORG-200X-25KG-BAG
```

### Grep Verification

```bash
# Should return 0 hardcoded Fair Trade (only in cert_names dict is OK)
grep -rn "Fair Trade" amb_w_tds/ai_bom_agent/engine.py
# Result: Line 316 in cert_names dict (acceptable)

# Should return matches
grep -rn "CERTIFICATION_MAP" amb_w_tds/ai_bom_agent/parser.py
grep -rn "_extract_certification" amb_w_tds/ai_bom_agent/parser.py
```

---

## Files Modified

1. `amb_w_tds/ai_bom_agent/parser.py`
   - Added `CERTIFICATION_MAP` dictionary
   - Added `DEFAULT_CERTIFICATION` constant
   - Added `_extract_certification()` method
   - Updated `_parse_item_code()` to extract certification
   - Updated `_parse_natural_language()` to extract certification

2. `amb_w_tds/ai_bom_agent/engine.py`
   - Updated `_generate_fg_item()` with correct naming pattern
   - Removed hardcoded " Fair Trade" certification
   - Added `cert_names` mapping for human-readable names

---

## Certification Codes Reference

| Input Variants | Code |
|----------------|------|
| ORGANIC, ORG | ORG |
| CONVENTIONAL, CONV | CONV |
| KOSHER, KOS | KOS |
| KOSHER ORGANIC, KOS-ORG | KOS-ORG |
| FAIR TRADE, FAIRTRADE, FT | FT |
| HALAL | HALAL |
| IASC | IASC |
| FSSC, FSSC 22000 | FSSC |
| COSMOS, ECOCERT | COSMOS |

---

## Next Steps (Phase 6 - Future)

- Add mesh size parsing for powder products
- Implement customer-specific naming patterns
- Add batch/lot tracking integration
