# AI BOM Agent - Standard Operating Procedure (SOP)

**Document Version:** 9.2.0  
**Effective Date:** 2026-02-19  
**Department:** Operations / Production Planning  
**Application:** AMB Wellness ERP - AI BOM Agent Module  

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Definitions](#3-definitions)
4. [System Access](#4-system-access)
5. [Product Families](#5-product-families)
6. [Specification Syntax](#6-specification-syntax)
7. [Creating BOMs via API](#7-creating-boms-via-api)
8. [Creating BOMs via Raven Chat](#8-creating-boms-via-raven-chat)
9. [Mesh Size Guidelines](#9-mesh-size-guidelines)
10. [Customer-Specific Items](#10-customer-specific-items)
11. [Batch Tracking](#11-batch-tracking)
12. [Dry Run vs Production](#12-dry-run-vs-production)
13. [Error Handling](#13-error-handling)
14. [Best Practices](#14-best-practices)
15. [Troubleshooting](#15-troubleshooting)
16. [Revision History](#16-revision-history)

---

## 1. Purpose

This Standard Operating Procedure (SOP) provides step-by-step instructions for using the AI BOM Agent to create multi-level Bills of Materials (BOMs) from natural language specifications. The AI BOM Agent automates the creation of Items and BOMs in ERPNext, reducing manual data entry and ensuring consistency in product naming conventions.

---

## 2. Scope

This SOP applies to:
- Production Planning personnel
- Operations team members
- Quality Assurance staff
- Sales representatives creating customer quotes
- Any authorized user with BOM creation privileges

This SOP covers:
- API-based BOM creation
- Raven chat-based BOM creation
- All supported product families (0227, 0307, HIGHPOL, ACETYPOL)
- Customer-specific item generation
- Batch tracking configuration

---

## 3. Definitions

| Term | Definition |
|------|------------|
| **BOM** | Bill of Materials - a comprehensive list of raw materials, components, and instructions required to manufacture a product |
| **Item** | A product, raw material, or component in the ERPNext inventory system |
| **Dry Run** | A test execution that shows what would be created without actually creating records |
| **Product Family** | A group of related products sharing common characteristics (e.g., 0227, 0307) |
| **Variant** | A specific concentration or formulation within a product family (e.g., 10X, 200X) |
| **Mesh Size** | Particle size specification for powder products (e.g., 40M, 80M, 200M) |
| **Certification** | Quality or regulatory certification (e.g., ORG-EU, CONV, HALAL) |
| **Raven** | The internal chat/messaging system integrated with ERPNext |

---

## 4. System Access

### 4.1 Prerequisites

Before using the AI BOM Agent, ensure you have:
- Valid ERPNext user account
- BOM Manager or System Manager role
- Access to the Raven chat system (for chat-based creation)

### 4.2 API Access

The AI BOM Agent API is accessible via:
- Frappe desk scripts
- Bench console commands
- Custom integrations

### 4.3 Raven Access

To use the chat interface:
1. Open Raven from the ERPNext sidebar
2. Navigate to the appropriate channel
3. Use the `@ai` mention or BOM-specific commands

---

## 5. Product Families

The AI BOM Agent supports the following product families:

### 5.1 Family 0227 - Aloe Vera Gel Concentrate (Liquid)

| Variant | Description | Typical Use |
|---------|-------------|-------------|
| 1X | Standard concentration | General applications |
| 10X | 10:1 concentration | Cosmetics |
| 40X | 40:1 concentration | Dietary supplements |
| 100X | 100:1 concentration | Nutraceuticals |
| 200X | 200:1 concentration | High-potency formulations |

### 5.2 Family 0307 - Aloe Vera Spray Dried Powder

| Variant | Description | Mesh Options |
|---------|-------------|--------------|
| 1X | Standard powder | 40M, 60M, 80M, 100M, 200M |
| 100X | 100:1 concentration | 40M, 60M, 80M, 100M, 200M |
| 200X | 200:1 concentration | 40M, 60M, 80M, 100M, 200M |

### 5.3 Family HIGHPOL - Highpol Powder (High Polysaccharide)

| Variant | Description |
|---------|-------------|
| 10/15 | 10-15% polysaccharide content |
| 15/20 | 15-20% polysaccharide content |
| 20/25 | 20-25% polysaccharide content |

### 5.4 Family ACETYPOL - Acetypol Powder (Acemannan)

| Variant | Description |
|---------|-------------|
| 5/10 | 5-10% acemannan content |
| 10/15 | 10-15% acemannan content |
| 15/20 | 15-20% acemannan content |

---

## 6. Specification Syntax

### 6.1 Basic Syntax Structure

```
[FAMILY] [VARIANT] [CERTIFICATION] [MESH_SIZE] [PACKAGING] [for CUSTOMER]
```

### 6.2 Supported Certifications

| Code | Full Name | Description |
|------|-----------|-------------|
| ORG-EU | Organic EU | European Union organic certification |
| ORG-NOP | Organic NOP | USDA National Organic Program |
| ORG-KR | Organic Korea | Korean organic certification |
| KOS-ORG | Kosher Organic | Kosher and organic dual certification |
| FT | Fair Trade | Fair trade certified |
| CONV | Conventional | No organic certification |
| HALAL | Halal | Islamic dietary certification |
| COSMOS | COSMOS | Cosmetic organic standard |

### 6.3 Packaging Options

| Code | Description |
|------|-------------|
| 25KG-BAG | 25 kilogram bags |
| 20KG-DRUM | 20 kilogram drums |
| 200L-DRUM | 200 liter drums |
| 1000L-IBC | 1000 liter IBC containers |

### 6.4 Example Specifications

| Input | Interpretation |
|-------|----------------|
| `0227 EU organic 30:1 in 1000L IBC` | Family 0227, 30X variant, ORG-EU cert, 1000L IBC |
| `0307 200:1 powder 80 mesh` | Family 0307, 200X variant, 80M mesh |
| `HIGHPOL 20/25 fair trade` | Family HIGHPOL, 20/25 variant, FT certification |
| `0307 conventional for ACME customer` | Family 0307, CONV cert, customer ACME |

---

## 7. Creating BOMs via API

### 7.1 API Endpoint

```python
amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec
```

### 7.2 Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| request_text | string | Yes | Natural language specification |
| dry_run | boolean | No | If True, plan only (default: False) |
| customer | string | No | Override customer name |

### 7.3 API Usage via Bench Console

#### Step 1: Open Bench Console
```bash
cd ~/frappe-bench
bench --site [your-site] console
```

#### Step 2: Execute Dry Run (Recommended First Step)
```python
from amb_w_tds.ai_bom_agent.api import create_multi_level_bom_from_spec

result = create_multi_level_bom_from_spec(
    request_text="0307 200:1 organic EU 80 mesh",
    dry_run=True
)
print(result)
```

#### Step 3: Review Output
```json
{
  "success": true,
  "spec": {
    "family": "0307",
    "attribute": "ORG",
    "variant": "200X",
    "mesh_size": "80M",
    "packaging": "25KG-BAG"
  },
  "items_created": ["0307-ORG-200X-80M-25KG-BAG"],
  "boms_created": ["0307-ORG-200X-80M-25KG-BAG"],
  "dry_run": true
}
```

#### Step 4: Execute Production Run
```python
result = create_multi_level_bom_from_spec(
    request_text="0307 200:1 organic EU 80 mesh",
    dry_run=False
)
```

### 7.4 API Usage via Bench Execute

```bash
# Dry Run
bench --site [your-site] execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 200:1 organic EU 80 mesh", "dry_run": True}'

# Production Run
bench --site [your-site] execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307 200:1 organic EU 80 mesh", "dry_run": False}'
```

---

## 8. Creating BOMs via Raven Chat

### 8.1 Available Commands

| Command | Description |
|---------|-------------|
| `bom help` | Display help and available commands |
| `bom create [spec]` | Create BOM from specification |
| `bom plan [spec]` | Dry run - show what would be created |

### 8.2 Step-by-Step Chat Workflow

#### Step 1: Open Raven Chat
Navigate to Raven from the ERPNext sidebar menu.

#### Step 2: Request Help (Optional)
```
bom help
```

#### Step 3: Plan the BOM (Recommended)
```
bom plan 0227 EU organic 30:1 in 1000L IBC
```

#### Step 4: Review the Plan
The system will respond with:
- Parsed specification details
- Items that would be created
- Items that would be reused
- BOMs that would be created
- Any warnings or errors

#### Step 5: Create the BOM
```
bom create 0227 EU organic 30:1 in 1000L IBC
```

### 8.3 Natural Language Alternatives

The following phrases are also recognized:
- `create bom for 0307 powder 80 mesh`
- `make bom for HIGHPOL 20/25`
- `new bom 0227 10X conventional`

### 8.4 Chat Response Format

Successful creation returns:
```
BOM Created

Specification
- Family: 0227
- Certification: ORG-EU
- Variant: 30X
- Packaging: 1000L-IBC

Items
Created: 2
- 0227-ORG-30X-1000L-IBC
- SFG-0227-STEP1-CONCENTRATION
Reused: 3

BOMs
Created: 1
- BOM-0227-ORG-30X-1000L-IBC
Reused: 2

Execution time: 1.23s
```

---

## 9. Mesh Size Guidelines

### 9.1 Supported Mesh Sizes

| Mesh | Particle Size | Common Applications |
|------|---------------|---------------------|
| 40M | Coarse | Industrial, non-cosmetic |
| 60M | Medium-Coarse | General supplements |
| 80M | Medium | Standard supplements |
| 100M | Medium-Fine | Premium supplements |
| 120M | Fine | Cosmetics |
| 200M | Ultra-Fine | High-end cosmetics, pharmaceuticals |

### 9.2 Mesh Size Input Formats

The AI agent recognizes various input formats:

| Input | Interpreted As |
|-------|----------------|
| `80 mesh` | 80M |
| `80M` | 80M |
| `80-mesh` | 80M |
| `mesh 80` | 80M |
| `80 malla` | 80M |

### 9.3 Mesh Size Applicability

| Product Family | Mesh Size Applicable |
|----------------|----------------------|
| 0227 (Liquid) | No |
| 0307 (Powder) | Yes |
| HIGHPOL (Powder) | Yes |
| ACETYPOL (Powder) | Yes |

---

## 10. Customer-Specific Items

### 10.1 Customer Naming Convention

When a customer is specified, item codes are prefixed with the customer name:

```
Standard:  0307-ORG-200X-80M-25KG-BAG
Customer:  ACME-0307-ORG-200X-80M-25KG-BAG
```

### 10.2 Specifying Customers

#### Via API:
```python
result = create_multi_level_bom_from_spec(
    request_text="0307 200:1 organic",
    customer="ACME"
)
```

#### Via Natural Language:
```
bom create 0307 200:1 organic for ACME customer
bom create 0307 200:1 organic for customer ACME
bom create 0307 200:1 organic (customer: ACME)
```

### 10.3 Customer Code Extraction

The AI agent extracts customer names from phrases like:
- `for ACME customer`
- `for customer ACME`
- `customer: ACME`
- `client ACME`
- `for ACME`

### 10.4 Customer Item Behavior

- Customer-specific items are created as new items
- They reference the same base BOM structure
- Customer items inherit all specifications
- Batch tracking is enabled by default

---

## 11. Batch Tracking

### 11.1 Overview

Batch tracking enables lot traceability for manufactured items. When enabled, each production batch receives a unique identifier.

### 11.2 Automatic Batch Tracking

The AI BOM Agent automatically enables batch tracking (`has_batch_no = 1`) for:
- Finished goods items
- Customer-specific items
- Items marked for regulated markets

### 11.3 Batch Number Format

Recommended batch number format:
```
[FAMILY]-[YYYYMMDD]-[SEQUENCE]

Example: 0307-20260219-001
```

### 11.4 Verifying Batch Tracking

After creating an item, verify batch tracking in ERPNext:
1. Navigate to Stock > Item
2. Open the created item
3. Check "Inventory" section
4. Confirm "Has Batch No" is checked

---

## 12. Dry Run vs Production

### 12.1 When to Use Dry Run

ALWAYS use dry run (`dry_run=True`) when:
- Testing a new specification format
- Verifying customer name extraction
- Checking mesh size interpretation
- Training new users
- Troubleshooting specification issues

### 12.2 Dry Run Output

Dry run returns complete information without creating records:
- Parsed specification
- Items that would be created
- Items that would be reused (already exist)
- BOMs that would be created
- BOMs that would be reused
- Validation warnings

### 12.3 Production Run Checklist

Before executing a production run:
- [ ] Completed dry run successfully
- [ ] Verified specification interpretation
- [ ] Confirmed customer name (if applicable)
- [ ] Checked mesh size (for powders)
- [ ] Reviewed items to be created
- [ ] Verified no duplicate items exist

---

## 13. Error Handling

### 13.1 Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown product family` | Invalid family code | Use 0227, 0307, HIGHPOL, or ACETYPOL |
| `Invalid mesh size` | Unsupported mesh | Use 40, 60, 80, 100, 120, or 200 |
| `Customer not found` | Customer doesn't exist in system | Create customer first or check spelling |
| `Duplicate item exists` | Item already in system | Review existing items, system will reuse |
| `Missing certification` | No cert specified | Specify ORG-EU, CONV, etc. |

### 13.2 Validation Warnings

Warnings are informational and don't prevent creation:
- `Mesh size not applicable for liquid products` - Mesh ignored for 0227
- `Customer item will be created` - New customer-specific item
- `Reusing existing BOM` - BOM already exists

### 13.3 Error Recovery

If an error occurs during production run:
1. Note the error message
2. Check the specification syntax
3. Verify all referenced items exist
4. Run dry run to validate
5. Contact system administrator if issue persists

---

## 14. Best Practices

### 14.1 Specification Writing

DO:
- Use standard family codes (0227, 0307, HIGHPOL, ACETYPOL)
- Specify certification clearly (EU organic, conventional, etc.)
- Include mesh size for powder products
- Spell customer names consistently

DON'T:
- Mix multiple specifications in one request
- Use abbreviations not recognized by the system
- Skip dry run for new specification formats

### 14.2 Workflow Recommendations

1. **Standard Workflow:**
   - Dry run first
   - Review output
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

### 14.3 Quality Assurance

- Review created items in ERPNext within 24 hours
- Verify BOM structure matches expected hierarchy
- Confirm batch tracking settings
- Check item descriptions and UoM

---

## 15. Troubleshooting

### 15.1 Specification Not Recognized

**Symptom:** System returns "Unknown product family" or similar error.

**Solution:**
1. Check family code spelling (case-sensitive)
2. Verify family is supported (0227, 0307, HIGHPOL, ACETYPOL)
3. Try simplified specification
4. Contact support with exact input text

### 15.2 Wrong Mesh Size Extracted

**Symptom:** Mesh size in output doesn't match input.

**Solution:**
1. Use explicit format: `80 mesh` or `80M`
2. Place mesh size after concentration
3. Avoid ambiguous numbers near mesh value

### 15.3 Customer Not Extracted

**Symptom:** Customer field is empty or incorrect.

**Solution:**
1. Use explicit format: `for CUSTOMER_NAME customer`
2. Avoid special characters in customer name
3. Check customer exists in ERPNext
4. Use `customer` parameter in API call

### 15.4 BOM Not Created

**Symptom:** Items created but BOM missing.

**Solution:**
1. Check for validation errors in response
2. Verify base items exist
3. Confirm BOM doesn't already exist
4. Check user permissions for BOM creation

### 15.5 System Timeout

**Symptom:** Request times out without response.

**Solution:**
1. Simplify specification
2. Try again during off-peak hours
3. Contact system administrator
4. Check server logs for errors

---

## 16. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 9.0.0 | 2026-01-15 | AMB Team | Initial release with base functionality |
| 9.1.0 | 2026-02-01 | AMB Team | Added HIGHPOL and ACETYPOL families |
| 9.2.0 | 2026-02-19 | AMB Team | Phase 7: Mesh sizes, Customer naming, Raven integration, Batch tracking |

---

## Appendix A: Quick Reference Card

### API Endpoint
```
amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec
```

### Chat Commands
```
bom help          - Show help
bom plan [spec]   - Dry run
bom create [spec] - Create BOM
```

### Product Families
```
0227     - Aloe Gel Concentrate (Liquid)
0307     - Aloe Spray Dried Powder
HIGHPOL  - High Polysaccharide Powder
ACETYPOL - Acemannan Powder
```

### Certifications
```
ORG-EU, ORG-NOP, ORG-KR, KOS-ORG, FT, CONV, HALAL, COSMOS
```

### Mesh Sizes (Powders Only)
```
40M, 60M, 80M, 100M, 120M, 200M
```

---

## Appendix B: Example Specifications

### Liquid Products (0227)
```
0227 EU organic 10:1 in 200L drums
0227 30X NOP organic 1000L IBC
0227 conventional 100X
```

### Powder Products (0307)
```
0307 200:1 organic EU 80 mesh
0307 conventional 100X 200 mesh 25kg bags
0307 powder 40 mesh fair trade
```

### Specialty Powders (HIGHPOL/ACETYPOL)
```
HIGHPOL 20/25 organic EU 100 mesh
ACETYPOL 10/15 conventional
HIGHPOL 15/20 fair trade 80 mesh
```

### Customer-Specific
```
0307 200:1 organic for ACME customer
0227 30X conventional for customer XYZ Corp
HIGHPOL 20/25 for ABC Industries
```

---

*End of Document*

**Document Owner:** Operations Department  
**Review Cycle:** Quarterly  
**Next Review:** 2026-05-19  
