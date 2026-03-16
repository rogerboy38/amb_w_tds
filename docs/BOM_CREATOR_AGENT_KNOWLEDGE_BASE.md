# BOM Creator Agent - Complete Knowledge Base

**Version:** 9.2.0  
**Last Updated:** 2026-02-19  
**System:** AMB Wellness ERPNext - AI BOM Agent Module  
**Vector Store ID:** vs_6996ab4fce808191b9889701ef1521a6

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Product Families](#3-product-families)
4. [Specification Syntax](#4-specification-syntax)
5. [API Reference](#5-api-reference)
6. [Raven Chat Commands](#6-raven-chat-commands)
7. [Mesh Size Guidelines](#7-mesh-size-guidelines)
8. [Customer-Specific Items](#8-customer-specific-items)
9. [Certifications](#9-certifications)
10. [Packaging Options](#10-packaging-options)
11. [Batch Tracking](#11-batch-tracking)
12. [Multi-Level BOM Structure](#12-multi-level-bom-structure)
13. [ERPNext v16 MRP Integration](#13-erpnext-v16-mrp-integration)
14. [Example Specifications](#14-example-specifications)
15. [Error Handling](#15-error-handling)
16. [Best Practices](#16-best-practices)
17. [Troubleshooting Guide](#17-troubleshooting-guide)
18. [Architecture](#18-architecture)
19. [Configuration Files](#19-configuration-files)
20. [Glossary](#20-glossary)

---

## 1. Executive Summary

The BOM Creator Agent is an AI-powered conversational interface for automating the creation and management of multi-level Bills of Materials (BOMs) within the ERPNext v16 system for AMB Wellness. The agent parses natural language product specifications and generates complete hierarchical BOM structures, including Semi-Finished Goods (SFGs), finished goods items, and their relationships.

### Key Capabilities

- **Natural Language Processing**: Understands product specifications in plain English/Spanish
- **Multi-Level BOM Generation**: Creates up to 6-level hierarchical BOMs automatically
- **Intelligent Item Reuse**: Checks for existing items before creating duplicates
- **Raven Chat Integration**: Create BOMs directly from the Raven messaging system
- **Batch Tracking**: Automatic lot traceability for regulated products
- **Customer-Specific Naming**: Configurable item naming patterns per customer
- **MRP Integration**: Output feeds directly into ERPNext v16 MRP engine

### Success Metrics

| Metric | Target |
|--------|--------|
| Time Reduction | 90% reduction in multi-level BOM creation time |
| Accuracy | 100% BOMs pass validation rules |
| MRP Efficiency | 100% correct MRP plans with no manual intervention |
| Adoption | All new products use agent-generated BOMs |

---

## 2. System Overview

### Core Business Objective

Automate instantiation of complex, up-to-6-level BOMs from master templates or product specifications, ensuring all intermediate SFGs are correctly created and linked before final assembly. Output feeds directly into ERPNext v16 MRP engine for automated purchase requests and work orders.

### System Access

**Prerequisites:**
- Valid ERPNext user account
- BOM Manager or System Manager role
- Access to the Raven chat system (for chat-based creation)

**Access Methods:**
1. **API Access**: Via Frappe desk scripts, bench console, or custom integrations
2. **Raven Chat**: Via the internal messaging system with `bom` commands
3. **Bench Execute**: Direct command-line execution

---

## 3. Product Families

The BOM Creator Agent supports the following AMB Wellness product families:

### 3.1 Family 0227 - Aloe Vera Gel Concentrate (Liquid)

| Variant | Description | Typical Use |
|---------|-------------|-------------|
| 1X | Standard concentration | General applications |
| 10X | 10:1 concentration | Cosmetics |
| 30X | 30:1 concentration | Standard dietary supplements |
| 40X | 40:1 concentration | Dietary supplements |
| 100X | 100:1 concentration | Nutraceuticals |
| 200X | 200:1 concentration | High-potency formulations |

**Characteristics:**
- Type: Semi-Finished Good (SFG)
- Default Variant: 30X
- Mesh Size Support: No (liquid product)
- Default UOM: Liters (L)

### 3.2 Family 0307 - Aloe Vera Spray Dried Powder

| Variant | Description | Mesh Options |
|---------|-------------|--------------|
| 1X | Standard powder | 40M, 60M, 80M, 100M, 120M, 200M |
| 100X | 100:1 concentration | 40M, 60M, 80M, 100M, 120M, 200M |
| 200X | 200:1 concentration | 40M, 60M, 80M, 100M, 120M, 200M |

**Characteristics:**
- Type: Finished Good (FG)
- Default Variant: 200X
- Mesh Size Support: Yes
- Default UOM: Kilograms (Kg)

### 3.3 Family HIGHPOL - Highpol Powder (High Polysaccharide)

| Variant | Description | Mesh Options |
|---------|-------------|--------------|
| 10/15 | 10-15% polysaccharide content | 60M, 80M, 100M, 120M |
| 15/20 | 15-20% polysaccharide content | 60M, 80M, 100M, 120M |
| 20/25 | 20-25% polysaccharide content | 60M, 80M, 100M, 120M |

**Characteristics:**
- Type: Finished Good (FG)
- Default Variant: 20/25
- Mesh Size Support: Yes
- Default UOM: Kilograms (Kg)
- Uses slash notation for variants

### 3.4 Family ACETYPOL - Acetypol Powder (Acemannan)

| Variant | Description | Mesh Options |
|---------|-------------|--------------|
| 5/10 | 5-10% acemannan content | 60M, 80M, 100M, 120M |
| 10/15 | 10-15% acemannan content | 60M, 80M, 100M, 120M |
| 15/20 | 15-20% acemannan content | 60M, 80M, 100M, 120M |

**Characteristics:**
- Type: Finished Good (FG)
- Default Variant: 15/20
- Mesh Size Support: Yes
- Default UOM: Kilograms (Kg)
- Uses slash notation for variants

### 3.5 Family 0303 - Aloe Vera Normal Powder (SFG)

**Characteristics:**
- Type: Semi-Finished Good (SFG)
- Default Variant: 200X
- Mesh Size Support: No
- Used as intermediate in powder production

### 3.6 Family 0301 - Aloe Vera Powder Base (SFG)

**Characteristics:**
- Type: Semi-Finished Good (SFG)
- Default Variant: 200X
- Mesh Size Support: No
- Used as base material in powder production

---

## 4. Specification Syntax

### 4.1 Basic Syntax Structure

```
[FAMILY] [VARIANT] [CERTIFICATION] [MESH_SIZE] [PACKAGING] [for CUSTOMER]
```

**Component Order:** The components can appear in any order. The parser is flexible and will extract each component regardless of position.

### 4.2 Variant Formats

| Input Format | Interpreted As | Product Family |
|--------------|----------------|----------------|
| `30:1` | 30X | 0227, 0307 |
| `200:1` | 200X | 0227, 0307 |
| `30X` | 30X | 0227, 0307 |
| `10X` | 10X | 0227, 0307 |
| `20/25` | 20/25 | HIGHPOL, ACETYPOL |
| `15/20` | 15/20 | HIGHPOL, ACETYPOL |

### 4.3 Natural Language Keywords

The parser recognizes various natural language expressions:

| Keyword | Maps To |
|---------|---------|
| `concentrate`, `gel`, `juice` | Family 0227 |
| `powder`, `spray dried` | Family 0307 |
| `highpol`, `high polysaccharide` | Family HIGHPOL |
| `acetypol`, `acemannan` | Family ACETYPOL |
| `organic`, `EU organic` | ORG-EU certification |
| `conventional`, `non-organic` | CONV certification |
| `fair trade` | FT certification |

---

## 5. API Reference

### 5.1 Main API Endpoint

```python
amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec
```

### 5.2 Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| request_text | string | Yes | - | Natural language specification |
| dry_run | boolean | No | False | If True, plan only without creating records |
| customer | string | No | None | Override customer name |

### 5.3 Response Format

```json
{
  "success": true,
  "spec": {
    "family": "0307",
    "attribute": "ORG",
    "variant": "200X",
    "mesh_size": "80M",
    "packaging": "25KG-BAG",
    "target_uom": "Kg",
    "target_qty": 1.0,
    "customer": null,
    "customer_code": null,
    "raw_request": "0307 200:1 organic EU 80 mesh",
    "parsed_at": "2026-02-19T10:30:00"
  },
  "items_created": ["0307-ORG-200X-80M-25KG-BAG"],
  "items_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
  "boms_created": ["0307-ORG-200X-80M-25KG-BAG"],
  "boms_reused": ["SFG-0307-STEP1-SPRAY-DRYING"],
  "errors": [],
  "warnings": [],
  "dry_run": true,
  "execution_time_seconds": 0.042,
  "batch_tracking": {"enabled": true}
}
```

### 5.4 API Usage Examples

#### Via Bench Console
```python
from amb_w_tds.ai_bom_agent.api import create_multi_level_bom_from_spec

# Dry run (recommended first step)
result = create_multi_level_bom_from_spec(
    request_text="0307 200:1 organic EU 80 mesh",
    dry_run=True
)
print(result)

# Production run
result = create_multi_level_bom_from_spec(
    request_text="0307 200:1 organic EU 80 mesh",
    dry_run=False
)
```

#### Via Bench Execute
```bash
# Dry Run
bench --site [your-site] execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 200:1 organic EU 80 mesh", "dry_run": True}'

# Production Run
bench --site [your-site] execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 200:1 organic EU 80 mesh", "dry_run": False}'
```

---

## 6. Raven Chat Commands

### 6.1 BOM Creator Commands

| Command | Description | Example |
|---------|-------------|---------|
| `bom help` | Display help and available commands | `bom help` |
| `bom create [spec]` | Create BOM from specification | `bom create 0227 EU organic 30:1 in 1000L IBC` |
| `bom plan [spec]` | Dry run - show what would be created | `bom plan HIGHPOL 20/25 100 mesh` |

### 6.2 Natural Language Alternatives

The following phrases are also recognized:
- `create bom for 0307 powder 80 mesh`
- `make bom for HIGHPOL 20/25`
- `new bom 0227 10X conventional`
- `@ai bom create 0227 EU organic 30:1`

### 6.3 Trigger Keywords

The BOM Creator Agent responds to:
- `bom create`, `bom plan`, `bom help`
- `create bom`, `make bom`, `new bom`
- Family codes: `0227`, `0307`, `HIGHPOL`, `ACETYPOL`

### 6.4 BOM Tracking Commands (Phase 6)

| Command | Description |
|---------|-------------|
| `bom health` | Run full BOM health check |
| `bom inspect <BOM>` | Detailed BOM inspection |
| `bom status <ITEM>` | Check BOM status for item |
| `bom issues` | List known issues |

### 6.5 Chat Response Format

**Successful Creation:**
```
✅ BOM Created

### Specification
- **Family:** 0227
- **Certification:** ORG-EU
- **Variant:** 30X
- **Packaging:** 1000L-IBC

### Items
**Created:** 2
- 0227-ORG-30X-1000L-IBC
- SFG-0227-STEP1-CONCENTRATION
**Reused:** 3

### BOMs
**Created:** 1
- BOM-0227-ORG-30X-1000L-IBC
**Reused:** 2

_Execution time: 1.23s_
```

---

## 7. Mesh Size Guidelines

### 7.1 Supported Mesh Sizes

| Mesh | Particle Size | Common Applications |
|------|---------------|---------------------|
| 40M | Coarse | Industrial, non-cosmetic |
| 60M | Medium-Coarse | General supplements |
| 80M | Medium | Standard supplements |
| 100M | Medium-Fine | Premium supplements |
| 120M | Fine | Cosmetics |
| 200M | Ultra-Fine | High-end cosmetics, pharmaceuticals |

### 7.2 Mesh Size Input Formats

The AI agent recognizes various input formats:

| Input | Interpreted As |
|-------|----------------|
| `80 mesh` | 80M |
| `80M` | 80M |
| `80-mesh` | 80M |
| `mesh 80` | 80M |
| `80 malla` | 80M |
| `malla 80` | 80M |

### 7.3 Valid Mesh Sizes by Family

| Product Family | Valid Mesh Sizes |
|----------------|------------------|
| 0307 | 60M, 80M, 100M, 120M, 200M |
| HIGHPOL | 60M, 80M, 100M, 120M |
| ACETYPOL | 60M, 80M, 100M, 120M |
| 0227 (Liquid) | Not applicable |

### 7.4 Mesh Size in Item Codes

When mesh size is specified, it appears in the item code:
```
Without mesh: 0307-ORG-200X-25KG-BAG
With mesh:    0307-ORG-200X-80M-25KG-BAG
```

---

## 8. Customer-Specific Items

### 8.1 Customer Naming Convention

When a customer is specified, item codes are prefixed with the customer name:

```
Standard:  0307-ORG-200X-80M-25KG-BAG
Customer:  ACME-0307-ORG-200X-80M-25KG-BAG
```

### 8.2 Specifying Customers

#### Via API Parameter:
```python
result = create_multi_level_bom_from_spec(
    request_text="0307 200:1 organic",
    customer="ACME"
)
```

#### Via Natural Language:
- `bom create 0307 200:1 organic for ACME customer`
- `bom create 0307 200:1 organic for customer ACME`
- `bom create 0307 200:1 organic (customer: ACME)`
- `bom plan HIGHPOL 20/25 for ABC Industries`

### 8.3 Customer Code Extraction Patterns

The AI agent extracts customer names from phrases like:
- `for ACME customer`
- `for customer ACME`
- `customer: ACME`
- `client ACME`
- `for ACME`

### 8.4 Customer Naming Rules Configuration

Customer-specific naming patterns are configured in `customer_naming_rules.json`:

```json
{
  "XYZ": {
    "customer_code": "XYZ",
    "pattern": "{FAMILY}-{CUSTOMER_CODE}-{VARIANT}-{PACKAGING}",
    "default_cert": "ORG-EU",
    "default_packaging": "1000L-IBC"
  },
  "ACME": {
    "customer_code": "ACME",
    "pattern": "{CUSTOMER_CODE}-{FAMILY}-{VARIANT}",
    "default_cert": "CONV"
  }
}
```

### 8.5 Customer Item Behavior

- Customer-specific items are created as new items
- They reference the same base BOM structure
- Customer items inherit all specifications
- Batch tracking is enabled by default for customer items

---

## 9. Certifications

### 9.1 Supported Certification Codes

| Code | Full Name | Description |
|------|-----------|-------------|
| ORG-EU | Organic EU | European Union organic certification |
| ORG-NOP | Organic NOP | USDA National Organic Program |
| ORG-KR | Organic Korea | Korean organic certification |
| KOS-ORG | Kosher Organic | Kosher and organic dual certification |
| FT | Fair Trade | Fair trade certified |
| CONV | Conventional | No organic certification |
| KOS | Kosher | Kosher certification only |
| HALAL | Halal | Islamic dietary certification |
| COSMOS | COSMOS | Cosmetic organic standard (Ecocert) |

### 9.2 Natural Language Certification Mapping

| Input Phrase | Maps To |
|--------------|---------|
| `EU organic`, `organic EU` | ORG-EU |
| `NOP organic`, `USA organic`, `USDA organic` | ORG-NOP |
| `Korean organic`, `KR organic` | ORG-KR |
| `kosher organic` | KOS-ORG |
| `fair trade`, `fairtrade` | FT |
| `conventional`, `non-organic`, `regular` | CONV |
| `kosher` | KOS |
| `halal` | HALAL |
| `cosmos`, `ecocert` | COSMOS |

### 9.3 Certification in Item Codes

Certifications appear in item codes using their short code:
```
0307-ORG-200X-80M-25KG-BAG  (Organic EU)
0307-CONV-200X-80M-25KG-BAG (Conventional)
0307-FT-200X-80M-25KG-BAG   (Fair Trade)
```

---

## 10. Packaging Options

### 10.1 Supported Packaging Types

| Code | Description | Typical Product |
|------|-------------|-----------------|
| 25KG-BAG | 25 kilogram bags | Powder products |
| 20KG-DRUM | 20 kilogram drums | Powder products |
| 200L-DRUM | 200 liter drums | Liquid concentrates |
| 1000L-IBC | 1000 liter IBC containers | Liquid concentrates |

### 10.2 Natural Language Packaging Mapping

| Input Phrase | Maps To |
|--------------|---------|
| `25kg bags`, `25 kg bag`, `bags` | 25KG-BAG |
| `20kg drums`, `drums` | 20KG-DRUM |
| `200L drums`, `200 liter drum` | 200L-DRUM |
| `IBC`, `1000L IBC`, `IBC container` | 1000L-IBC |

### 10.3 Default Packaging by Family

| Family | Default Packaging |
|--------|-------------------|
| 0227 | 1000L-IBC |
| 0307 | 25KG-BAG |
| HIGHPOL | 25KG-BAG |
| ACETYPOL | 25KG-BAG |

---

## 11. Batch Tracking

### 11.1 Overview

Batch tracking enables lot traceability for manufactured items. When enabled, each production batch receives a unique identifier that can be tracked through the supply chain.

### 11.2 Automatic Batch Tracking

The AI BOM Agent automatically enables batch tracking (`has_batch_no = 1`) for:
- All finished goods items
- Customer-specific items
- Items from regulated product families

### 11.3 Batch Tracking Families

```python
BATCH_TRACKING_FAMILIES = ["0227", "0307", "HIGHPOL", "ACETYPOL"]
```

### 11.4 Batch Number Format

Recommended batch number format:
```
[FAMILY]-[YYYYMMDD]-[SEQUENCE]

Example: 0307-20260219-001
         0227-20260219-042
```

### 11.5 Verifying Batch Tracking

After creating an item, verify batch tracking in ERPNext:
1. Navigate to Stock > Item
2. Open the created item
3. Check "Inventory" section
4. Confirm "Has Batch No" is checked

---

## 12. Multi-Level BOM Structure

### 12.1 BOM Decomposition

The agent creates hierarchical BOMs with up to 6 levels:

```
Level 1 (FG): 0227-ORG-30X-1000L-IBC
    └── Level 2 (SFG): SFG-0227-STEP2-STANDARDIZE
        └── Level 3 (SFG): SFG-0227-STEP1-CONCENTRATE
            └── Level 4 (Raw): Raw Aloe Vera Gel
                └── Level 5: Processing Agents
                    └── Level 6: Packaging Materials
```

### 12.2 Semi-Finished Goods (SFG) Naming

SFG items follow a standard naming convention:
```
SFG-[FAMILY]-STEP[N]-[OPERATION]

Examples:
- SFG-0227-STEP1-CONCENTRATE
- SFG-0227-STEP2-STANDARDIZE
- SFG-0307-STEP1-SPRAY-DRYING
```

### 12.3 BOM Creation Process

1. **Parse Specification**: Extract family, variant, certification, mesh, packaging, customer
2. **Retrieve Template**: Load master BOM template for the product family
3. **Check/Create SFGs**: Recursively create intermediate SFG items and BOMs
4. **Build Final BOM**: Create FG item and BOM with SFG references
5. **Add Operations**: Attach operations to each BOM level
6. **Validate & Activate**: Run validation rules, set BOMs as active

### 12.4 Item Reuse Logic

Before creating any item, the agent:
1. Checks if item with same code exists
2. If exists, reuses the item (adds to `items_reused` list)
3. If not exists, creates new item (adds to `items_created` list)

---

## 13. ERPNext v16 MRP Integration

### 13.1 MRP Feature Integration

| ERPNext v16 MRP Feature | How AI Agent Enables It | Business Impact |
|-------------------------|-------------------------|-----------------|
| Multi-level BOM Explosion | Creates complete nested BOM structure (FG → SFG → Raw) | Accurate planning for all production levels |
| Stock Reservation for Production | Defines precise BOM structure for material reservation | Prevents accidental stock consumption |
| Track SFG via Job Cards | Defines SFG items and BOMs enabling Work Orders with Job Card tracking | Real-time WIP visibility at each stage |
| Transfer Extra Raw Materials to WIP | Defines yield percentages/loss rates | Reduces stoppages from normal waste |
| Subcontracting Integration | Flags SFG items for subcontracting | Seamless outsourced operation integration |
| Landed Cost for Manufacturing | Associates overhead costs with operations | Accurate product costing per stage |

### 13.2 MRP Workflow

1. **Sales Order Created**: Customer order triggers demand
2. **MRP Multi-level Explosion**: ERPNext explodes BOMs to raw material level
3. **Material Requests Generated**: Automatic purchase requests for materials
4. **Work Orders Created**: Production orders for each BOM level
5. **Job Cards for Tracking**: WIP monitoring via Job Cards

---

## 14. Example Specifications

### 14.1 Liquid Products (0227)

```
0227 EU organic 10:1 in 200L drums
0227 30X NOP organic 1000L IBC
0227 conventional 100X
0227 fair trade 30:1 in IBC
0227 kosher organic 40X drums
```

### 14.2 Powder Products (0307)

```
0307 200:1 organic EU 80 mesh
0307 conventional 100X 200 mesh 25kg bags
0307 powder 40 mesh fair trade
0307 200X NOP organic 100 mesh
0307 halal 200:1 80 mesh bags
```

### 14.3 Specialty Powders (HIGHPOL)

```
HIGHPOL 20/25 organic EU 100 mesh
HIGHPOL 15/20 conventional 80 mesh
HIGHPOL 20/25 fair trade 80 mesh 25kg bags
```

### 14.4 Specialty Powders (ACETYPOL)

```
ACETYPOL 10/15 conventional
ACETYPOL 15/20 organic EU 100 mesh
ACETYPOL 5/10 cosmos 80 mesh bags
```

### 14.5 Customer-Specific Examples

```
0307 200:1 organic for ACME customer
0227 30X conventional for customer XYZ Corp
HIGHPOL 20/25 for ABC Industries
0307 100 mesh organic for customer MedPharm
```

---

## 15. Error Handling

### 15.1 Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown product family` | Invalid family code | Use 0227, 0307, HIGHPOL, or ACETYPOL |
| `Invalid mesh size` | Unsupported mesh value | Use 40, 60, 80, 100, 120, or 200 |
| `Mesh size not applicable` | Mesh specified for liquid | Remove mesh for 0227 family |
| `Customer not found` | Customer doesn't exist | Create customer first or check spelling |
| `Duplicate item exists` | Item already in system | System will reuse existing item |
| `Missing certification` | No cert specified | Specify ORG-EU, CONV, etc. |
| `Invalid variant format` | Unrecognized concentration | Use format like 30:1, 200X, or 20/25 |

### 15.2 Validation Warnings

Warnings are informational and don't prevent creation:
- `Mesh size not applicable for liquid products` - Mesh ignored for 0227
- `Customer item will be created` - New customer-specific item
- `Reusing existing BOM` - BOM already exists
- `Default packaging applied` - No packaging specified, using default

### 15.3 Error Recovery Steps

1. Note the exact error message
2. Check the specification syntax
3. Verify all referenced items exist
4. Run dry run to validate before production
5. Check user permissions for BOM creation
6. Contact system administrator if issue persists

---

## 16. Best Practices

### 16.1 Specification Writing

**DO:**
- Use standard family codes (0227, 0307, HIGHPOL, ACETYPOL)
- Specify certification clearly (EU organic, conventional, etc.)
- Include mesh size for powder products
- Spell customer names consistently
- Always run dry run first

**DON'T:**
- Mix multiple specifications in one request
- Use abbreviations not recognized by the system
- Skip dry run for new specification formats
- Include special characters in customer names

### 16.2 Workflow Recommendations

1. **Standard Workflow:**
   - Run dry run first
   - Review output carefully
   - Execute production run
   - Verify in ERPNext

2. **Batch Creation:**
   - Process one specification at a time
   - Verify each creation before proceeding
   - Document any issues

3. **Customer Orders:**
   - Confirm customer name spelling
   - Use dry run to verify customer prefix
   - Check for existing customer items

### 16.3 Quality Assurance Checklist

- [ ] Review created items in ERPNext within 24 hours
- [ ] Verify BOM structure matches expected hierarchy
- [ ] Confirm batch tracking settings
- [ ] Check item descriptions and UoM
- [ ] Validate BOM costs are calculated
- [ ] Test MRP explosion produces correct results

---

## 17. Troubleshooting Guide

### 17.1 Specification Not Recognized

**Symptom:** System returns "Unknown product family" or similar error.

**Solutions:**
1. Check family code spelling (case-sensitive for some keywords)
2. Verify family is supported (0227, 0307, HIGHPOL, ACETYPOL)
3. Try simplified specification first
4. Use explicit family code instead of keywords

### 17.2 Wrong Mesh Size Extracted

**Symptom:** Mesh size in output doesn't match input.

**Solutions:**
1. Use explicit format: `80 mesh` or `80M`
2. Place mesh size after concentration
3. Avoid other numbers near mesh value
4. Check mesh is valid for the family

### 17.3 Customer Not Extracted

**Symptom:** Customer field is empty or incorrect.

**Solutions:**
1. Use explicit format: `for CUSTOMER_NAME customer`
2. Avoid special characters in customer name
3. Check customer exists in ERPNext
4. Use `customer` parameter in API call as override

### 17.4 BOM Not Created

**Symptom:** Items created but BOM missing.

**Solutions:**
1. Check for validation errors in response
2. Verify all base items exist
3. Confirm BOM doesn't already exist
4. Check user permissions for BOM creation
5. Review `boms_reused` list - may have been reused

### 17.5 Wrong Certification Detected

**Symptom:** Certification code doesn't match input.

**Solutions:**
1. Use explicit certification code (ORG-EU, CONV, FT)
2. Place certification near the beginning
3. Avoid ambiguous terms like "organic" alone (specify EU/NOP/KR)

### 17.6 System Timeout

**Symptom:** Request times out without response.

**Solutions:**
1. Simplify specification
2. Try again during off-peak hours
3. Check server logs for errors
4. Contact system administrator

---

## 18. Architecture

### 18.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Raven Chat Interface                      │
├─────────────────────────────────────────────────────────────┤
│  bom_creator_agent.py  │  bom_tracking_agent.py             │
├─────────────────────────────────────────────────────────────┤
│                    API Layer (api.py)                        │
├─────────────────────────────────────────────────────────────┤
│ Parser │ Engine │ Validators │ Templates │ ERPNext Client   │
├─────────────────────────────────────────────────────────────┤
│                    ERPNext/Frappe v16                        │
└─────────────────────────────────────────────────────────────┘
```

### 18.2 Component Overview

| Component | File | Purpose |
|-----------|------|---------|
| Parser | `parser.py` | Parse natural language specifications |
| Data Contracts | `data_contracts.py` | Define data structures |
| Engine | `engine.py` | BOM generation logic |
| Validators | `validators.py` | Validation rules |
| Templates | `templates/*.json` | BOM templates per family |
| ERPNext Client | `erpnext_client.py` | ERPNext API integration |
| API | `api.py` | External API endpoints |
| Raven Agent | `raven/bom_creator_agent.py` | Chat interface |

### 18.3 Module Path

```
amb_w_tds/
├── ai_bom_agent/
│   ├── __init__.py
│   ├── api.py
│   ├── parser.py
│   ├── engine.py
│   ├── data_contracts.py
│   ├── erpnext_client.py
│   ├── validators.py
│   ├── customer_naming_rules.json
│   └── templates/
│       ├── 0227_template.json
│       ├── 0307_template.json
│       └── ...
└── raven/
    ├── __init__.py
    ├── bom_creator_agent.py
    └── bom_tracking_agent.py
```

---

## 19. Configuration Files

### 19.1 Customer Naming Rules

**File:** `customer_naming_rules.json`

```json
{
  "XYZ": {
    "customer_code": "XYZ",
    "pattern": "{FAMILY}-{CUSTOMER_CODE}-{VARIANT}-{PACKAGING}",
    "default_cert": "ORG-EU",
    "default_packaging": "1000L-IBC"
  }
}
```

### 19.2 BOM Known Issues Registry

**File:** `bom_known_issues.json`

Registry of accepted BOM issues that should not trigger alerts.

### 19.3 BOM Templates

**Location:** `templates/`

JSON templates defining BOM structure for each product family.

### 19.4 Business Rules

**File:** `business_rules.json`

Validation rules configuration for BOM creation.

---

## 20. Glossary

| Term | Definition |
|------|------------|
| **BOM** | Bill of Materials - comprehensive list of raw materials, components, and instructions required to manufacture a product |
| **Item** | A product, raw material, or component in the ERPNext inventory system |
| **FG** | Finished Good - a completed product ready for sale |
| **SFG** | Semi-Finished Good - an intermediate product used in further manufacturing |
| **Dry Run** | A test execution that shows what would be created without actually creating records |
| **Product Family** | A group of related products sharing common characteristics (e.g., 0227, 0307) |
| **Variant** | A specific concentration or formulation within a product family (e.g., 10X, 200X, 20/25) |
| **Mesh Size** | Particle size specification for powder products (e.g., 40M, 80M, 200M) |
| **Certification** | Quality or regulatory certification (e.g., ORG-EU, CONV, HALAL) |
| **MRP** | Material Requirements Planning - system for production planning and inventory control |
| **Raven** | The internal chat/messaging system integrated with ERPNext |
| **Job Card** | Document used to track work-in-progress at each production stage |
| **IBC** | Intermediate Bulk Container - 1000L container for liquid products |
| **UOM** | Unit of Measure (e.g., Kg, L) |

---

## Version History

| Version | Date | Features |
|---------|------|----------|
| 9.2.0 | 2026-02-19 | Phase 7: Mesh sizes, Customer naming, Batch flags, Raven skill |
| 9.1.0 | 2026-02-17 | Phase 6: BOM Tracking Agent, Health checks |
| 9.0.0 | 2026-02-15 | Phase 5: Hooks, Scheduler, Known issues |
| 8.0.0 | 2026-02-10 | Phase 4: HIGHPOL/ACETYPOL, Organic sub-certs |

---

**Document Owner:** AMB Wellness Operations Department  
**Review Cycle:** Quarterly  
**Next Review:** 2026-05-19  
**Vector Store:** bom_creator_agent (vs_6996ab4fce808191b9889701ef1521a6)

---

*End of Knowledge Base Document*
