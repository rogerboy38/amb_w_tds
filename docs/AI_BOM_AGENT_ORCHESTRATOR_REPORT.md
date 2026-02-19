# AI BOM Agent - Orchestrator Team Report
## AMB Wellness ERP Integration Project
**Report Date:** 2026-02-19  
**Branch:** `feature/v9.2.0-development`  
**Latest Commit:** `1d29b75`

---

## 1. Executive Summary

The AI BOM Agent is a natural language-driven system for automated Bill of Materials (BOM) generation in ERPNext v16. It parses product requests (like "0227 organic 10:1 concentrate") and creates multi-level BOMs with proper item codes, certifications, and packaging configurations.

### Completed Phases
| Phase | Commit | Description |
|-------|--------|-------------|
| **Phase 4** | `840235d` | Variant/concentration parsing (10X, 30X, 200X from "10:1", "30:1") |
| **Phase 5** | `6878869` | Certification parsing (FT, ORG, KOS, HALAL, etc.) |
| **Phase 6** | `1d29b75` | New product families (HIGHPOL, ACETYPOL), slash ratios (10/15), organic sub-types (ORG-EU, ORG-NOP, ORG-KR) |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                              │
│  "0227 organic 10:1 concentrate in IBC containers"          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 ProductSpecificationParser                   │
│  parser.py                                                   │
│  - _parse_item_code() or _parse_natural_language()          │
│  - _extract_variant()    → 10X, 30X, 200X, 10/15           │
│  - _extract_certification() → FT, ORG, KOS-ORG, ORG-EU     │
│  - _extract_packaging()  → 1000L-IBC, 25KG-BAG             │
│  Returns: ParsedSpec dataclass                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AgentCoreEngine                           │
│  engine.py                                                   │
│  - Load master template (template_{FAMILY}_master.json)     │
│  - Plan item hierarchy (SFG steps → FG)                     │
│  - Validate against business_rules.json                     │
│  - _generate_fg_item() → {FAMILY}-{ATTR}-{VAR}-{PKG}       │
│  - Create/reuse items and BOMs in ERPNext                  │
│  Returns: GenerationReport                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      ERPNext v16                             │
│  erpnext_client.py                                          │
│  - ItemAndBOMService                                        │
│  - Creates Items (0227-ORG-10X-1000L-IBC)                  │
│  - Creates multi-level BOMs (SFG → SFG → FG)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Parser (`parser.py`)
- **PRODUCT_FAMILIES:** Dictionary defining product characteristics (0227, 0307, 0303, 0301, HIGHPOL, ACETYPOL)
- **RATIO_PATTERNS:** Regex for concentration parsing (`30:1` → `30X`)
- **SLASH_RATIO_PATTERNS:** Regex for polysaccharide ratios (`10/15`)
- **CERTIFICATION_MAP:** Maps user input to standard codes (17 certifications)

### 3.2 Engine (`engine.py`)
- **Multi-level BOM generation:** SFG-STEP1 → SFG-STEP2 → SFG-STEP3 → FG
- **Item code pattern:** `{FAMILY}-{ATTRIBUTE}-{VARIANT}-{PACKAGING}`
- **Dry-run support:** Plan without creating in database
- **Validation:** Business rules enforcement

### 3.3 Templates
- JSON templates for each product family
- Define item hierarchy and BOM structure
- Located in `amb_w_tds/ai_bom_agent/templates/`

---

## 4. Current Capabilities

### 4.1 Supported Product Families
| Family | Type | Variants | Default |
|--------|------|----------|---------|
| 0227 | SFG (Liquid) | 1X, 10X, 20X, 30X | 30X |
| 0307 | FG (Powder) | 100X, 200X | 200X |
| 0303 | SFG (Powder) | None | 200X |
| 0301 | SFG (Powder) | None | 200X |
| HIGHPOL | FG (Powder) | 10/15 to 35/40 | 20/25 |
| ACETYPOL | FG (Powder) | 10/15 to 20/25 | 15/20 |

### 4.2 Supported Certifications
| Code | Full Name |
|------|-----------|
| FT | Fair Trade (default) |
| ORG | Organic (generic) |
| ORG-EU | Organic EU |
| ORG-NOP | Organic NOP USA |
| ORG-KR | Organic Korean |
| KOS | Kosher |
| KOS-ORG | Kosher Organic |
| CONV | Conventional |
| HALAL | Halal |
| IASC | IASC Certified |
| FSSC | FSSC 22000 |
| COSMOS | COSMOS Ecocert |

### 4.3 Packaging Options
| Code | Container | Capacity |
|------|-----------|----------|
| 1000L-IBC | IBC Container | ~1080 Kg |
| 220L-BBL | 220L Barrel Blue | ~230 Kg |
| 25KG-BAG | 25 Kg Bag | 25 Kg |

---

## 5. Raven AI Integration

The existing `BOMTrackingAgent` (`raven/bom_tracking_agent.py`) provides:
- BOM health monitoring
- BOM inspection commands
- Issue tracking

---

## 6. Recommendations for `raven_ai_agent`

### 6.1 HIGH PRIORITY - Natural Language BOM Creation

**Feature:** Allow users to create BOMs via Raven chat.

```
User: @bom create 0227 organic 10:1 in IBC
Agent: ✅ Created BOM: 0227-ORG-10X-1000L-IBC
       - 3 SFG steps created
       - 1 FG item created
       - Total 4 BOMs linked
```

**Implementation:**
- Add `bom create <request>` command to BOMTrackingAgent
- Call `ai_bom_agent.api.create_multi_level_bom_from_spec()`
- Return formatted result with links to ERPNext

### 6.2 HIGH PRIORITY - Quotation-to-BOM Bridge

**Feature:** Auto-generate BOMs when sales quotes are created.

```
User: @bom quote 0227 organic 500kg for CustomerX
Agent: Created Quotation QUO-2026-0042
       BOM ready: 0227-ORG-30X-1000L-IBC
       Estimated cost: $X,XXX
```

**Why:** Currently, sales team creates quotes manually, then production team manually creates BOMs. This bridges the gap.

### 6.3 MEDIUM PRIORITY - Batch Tracking Integration

**Feature:** Link BOM execution with batch traceability.

```
User: @batch trace LOT-2026-0227-001
Agent: Batch: LOT-2026-0227-001
       Product: 0227-ORG-30X-1000L-IBC
       BOM: BOM-0227-ORG-30X-1000L-IBC-001
       Raw Materials:
       - Aloe Leaf: LOT-RM-001 (500kg)
       - Container: E011-001
       Status: In Production (Step 2/3)
```

### 6.4 MEDIUM PRIORITY - Cost Estimation

**Feature:** Quick cost estimation from natural language.

```
User: @bom cost 0227 organic 1000kg
Agent: Estimated cost breakdown:
       - Raw Materials: $X,XXX
       - Processing: $XXX
       - Packaging: $XXX
       - Total: $X,XXX per kg
```

### 6.5 LOW PRIORITY - Template Suggestions

**Feature:** Suggest similar products when request is ambiguous.

```
User: @bom create aloe powder
Agent: Multiple matches found:
       1. 0307 - Spray Dried Powder 200X
       2. 0303 - Normal Powder
       3. HIGHPOL - Highpol Powder (10/15)
       Reply with number to proceed.
```

### 6.6 LOW PRIORITY - Certification Document Generation

**Feature:** Generate certification documents from BOM data.

```
User: @bom cert 0227-ORG-30X-1000L-IBC
Agent: Generated documents:
       - Organic Certificate (EU)
       - Fair Trade Certificate
       - IASC Certificate
       Download: [link]
```

---

## 7. Technical Gaps to Address

### 7.1 Error Handling
- Current: Basic try/catch with string errors
- Needed: Structured error codes for Raven display

### 7.2 Async Support
- Current: Synchronous execution
- Needed: Background job queue for large BOM trees

### 7.3 Caching
- Current: No caching
- Needed: Template and validation rule caching

### 7.4 Audit Trail
- Current: Basic logging
- Needed: Full audit trail for compliance (who/what/when)

### 7.5 Multi-language
- Current: English only
- Needed: Spanish support (primary market is Mexico)

---

## 8. Files Reference

| File | Purpose |
|------|---------|
| `ai_bom_agent/parser.py` | Natural language parsing |
| `ai_bom_agent/engine.py` | BOM generation orchestration |
| `ai_bom_agent/api.py` | External API entry point |
| `ai_bom_agent/erpnext_client.py` | ERPNext integration |
| `ai_bom_agent/validators.py` | Business rule validation |
| `ai_bom_agent/data_contracts.py` | Data structures (ParsedSpec, etc.) |
| `ai_bom_agent/templates.py` | Template loading |
| `raven/bom_tracking_agent.py` | Existing Raven integration |

---

## 9. Test Commands

```bash
# Dry-run test
bench --site <site> execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
  --kwargs '{"request_text": "0227 organic 10:1", "dry_run": True}'

# Production run
bench --site <site> execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
  --kwargs '{"request_text": "0227 organic 10:1", "dry_run": False}'
```

---

## 10. Conclusion

The AI BOM Agent provides a solid foundation for natural language BOM generation. The recommended Raven integrations would significantly improve user experience and reduce manual data entry for the AMB Wellness production team.

**Priority Order for Raven Integration:**
1. Natural Language BOM Creation (HIGH)
2. Quotation-to-BOM Bridge (HIGH)
3. Batch Tracking Integration (MEDIUM)
4. Cost Estimation (MEDIUM)
5. Template Suggestions (LOW)
6. Certification Documents (LOW)

---

*Report prepared for Orchestrator Team*  
*AMB Wellness ERP Integration Project*
