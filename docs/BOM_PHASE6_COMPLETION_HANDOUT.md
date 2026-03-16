# BOM Phase 6 Completion Handout

**Completed:** 2026-02-19  
**Branch:** feature/v9.2.0-development  
**Status:** ✅ COMPLETE

---

## Phase 6 Summary: Highpol & Acetypol Product Families + Organic Sub-Certifications

### Changes Made

#### 1. parser.py - New Product Families
Added HIGHPOL and ACETYPOL to `PRODUCT_FAMILIES`:
- **HIGHPOL:** High Polysaccharide Aloe Vera Powder
  - Valid variants: 10/15, 15/20, 20/25, 25/30, 30/35, 35/40
  - Default: 20/25
- **ACETYPOL:** High Acemannan Aloe Vera Powder
  - Valid variants: 10/15, 15/20, 20/25
  - Default: 15/20

#### 2. parser.py - Slash Ratio Patterns
Added `SLASH_RATIO_PATTERNS` for NN/NN format variants used by Highpol/Acetypol.

#### 3. parser.py - Updated _extract_variant()
Modified to check `SLASH_RATIO_PATTERNS` first for HIGHPOL/ACETYPOL families before standard `RATIO_PATTERNS`.

#### 4. parser.py - Updated _parse_natural_language()
Added keyword detection for "HIGHPOL" and "ACETYPOL" in natural language requests.

#### 5. parser.py - Updated ITEM_CODE_PATTERNS
Added patterns to match word-based family codes:
- `^(HIGHPOL|ACETYPOL)$`
- `^(HIGHPOL|ACETYPOL)-(.+)$`

#### 6. parser.py - Updated _parse_item_code()
Normalized family codes to uppercase to handle HIGHPOL/ACETYPOL case-insensitively.

#### 7. parser.py - Expanded CERTIFICATION_MAP
Added organic sub-certifications:
- EU ORGANIC → ORG-EU
- NOP USA ORGANIC → ORG-NOP
- KOREAN ORGANIC → ORG-KR

#### 8. engine.py - Updated cert_names
Added human-readable names for new organic sub-certifications.

#### 9. Template Files
Created master templates for new families:
- `templates/template_HIGHPOL_master.json`
- `templates/template_ACETYPOL_master.json`

---

## New FG Naming Examples

| Request | FG Item Code |
|---------|--------------|
| HIGHPOL | HIGHPOL-FT-20/25-25KG-BAG |
| HIGHPOL 30/35 organic | HIGHPOL-ORG-30/35-25KG-BAG |
| ACETYPOL 15/20 | ACETYPOL-FT-15/20-25KG-BAG |
| 0227 EU organic 30:1 | 0227-ORG-EU-30X-1000L-IBC |
| 0307 NOP USA organic | 0307-ORG-NOP-200X-25KG-BAG |

---

## Supported Families (Updated)

| Family | Type | Default Variant | Valid Variants |
|--------|------|-----------------|----------------|
| 0227 | Gel Concentrate | 30X | 1X, 10X, 20X, 30X |
| 0307 | Spray Dried Powder | 200X | 100X, 200X |
| 0303 | Normal Powder | 200X | (none) |
| 0301 | Powder Base | 200X | (none) |
| HIGHPOL | Highpol Powder | 20/25 | 10/15, 15/20, 20/25, 25/30, 30/35, 35/40 |
| ACETYPOL | Acetypol Powder | 15/20 | 10/15, 15/20, 20/25 |

---

## Certification Codes (Updated)

| Input | Code |
|-------|------|
| EU ORGANIC | ORG-EU |
| NOP USA ORGANIC | ORG-NOP |
| KOREAN ORGANIC | ORG-KR |
| ORGANIC | ORG (generic) |
| FAIR TRADE | FT (default) |
| KOSHER | KOS |
| KOSHER ORGANIC | KOS-ORG |
| CONVENTIONAL | CONV |
| HALAL | HALAL |
| COSMOS / ECOCERT | COSMOS |

---

## Test Commands

```bash
# Pull latest
cd /home/frappe/frappe-bench/apps/amb_w_tds
git pull origin feature/v9.2.0-development

# Test HIGHPOL default
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "HIGHPOL", "dry_run": True}'
# Expected: family=HIGHPOL, variant=20/25, FG=HIGHPOL-FT-20/25-25KG-BAG

# Test HIGHPOL with explicit variant
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "HIGHPOL 30/35 organic", "dry_run": True}'
# Expected: family=HIGHPOL, variant=30/35, attribute=ORG, FG=HIGHPOL-ORG-30/35-25KG-BAG

# Test ACETYPOL
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "ACETYPOL 15/20", "dry_run": True}'
# Expected: family=ACETYPOL, variant=15/20, FG=ACETYPOL-FT-15/20-25KG-BAG

# Test EU Organic
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0227 EU organic 30:1", "dry_run": True}'
# Expected: attribute=ORG-EU, FG=0227-ORG-EU-30X-1000L-IBC

# Test NOP USA Organic
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 NOP USA organic", "dry_run": True}'
# Expected: attribute=ORG-NOP, FG=0307-ORG-NOP-200X-25KG-BAG
```

---

## Files Modified

1. `amb_w_tds/ai_bom_agent/parser.py`
   - Added HIGHPOL and ACETYPOL to PRODUCT_FAMILIES
   - Added SLASH_RATIO_PATTERNS
   - Updated _extract_variant() for slash patterns
   - Updated _parse_natural_language() for new keywords
   - Updated ITEM_CODE_PATTERNS for word-based codes
   - Expanded CERTIFICATION_MAP with organic sub-types

2. `amb_w_tds/ai_bom_agent/engine.py`
   - Added ORG-EU, ORG-NOP, ORG-KR to cert_names

3. `amb_w_tds/ai_bom_agent/templates/template_HIGHPOL_master.json` (NEW)

4. `amb_w_tds/ai_bom_agent/templates/template_ACETYPOL_master.json` (NEW)

---

## Next Steps (Phase 7 - Future)

- Add mesh size parsing for powder products
- Implement customer-specific naming patterns
- Add batch/lot tracking integration
