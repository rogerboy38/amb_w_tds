# Sample Request AMB - Standard Operating Procedure

**Document Code:** SOP-SAMPLE-001  
**Version:** 1.0  
**Effective Date:** 2026-03-19  
**Department:** Quality Control / Sales / R&D  
**Author:** AMB Wellness

---

## 1. Purpose

This document establishes the standardized procedure for requesting, preparing, and managing samples throughout the AMB Wellness production workflow. The Sample Request AMB system tracks samples from initial request through delivery and retention.

## 2. Scope

This SOP applies to:

- Sales department sample requests for clients and prospects
- R&D sample requests for product homologation
- Quality Control sampling during production (Juice, Dry, Mix, Laboratory, Formulated)
- Retention samples for customer complaints and COA verification
- External laboratory analysis samples

## 3. Related Documents

| Document Code | Description |
|---------------|-------------|
| CPEM-020 | Sample Preparation Format |
| CPMF-028 | Physicochemical Sampling and Analysis Format |
| CPMR-032 | Retention Sample Reception and Handling Format |
| TDS-BASE | Technical Data Sheet - Base Product Specifications |

---

## 4. Sample Request Workflow

### 4.1 Sample Request Triggers

Sample requests occur at multiple stages:

| Stage | Trigger | Description |
|-------|---------|-------------|
| **Pre-Sales / Prospect** | New prospect evaluation | Initial product samples for potential clients |
| **TDS Approval** | Pre-approval sample | Samples required for TDS workflow approval |
| **Quotation** | Explicit customer request | Samples included in quotation (e.g., 500g powder + 50 bags of 20g) |
| **Sales Order** | Production sample | Samples tied to production workflow |
| **R&D / Homologation** | Product development | Liquid or powder samples for customer homologation |
| **Production (All Plants)** | Quality control | Juice, Dry, Mix, Laboratory, Formulated plant samples |
| **Inspection** | Compliance | Samples for batch inspection and COA construction |

### 4.2 Sample Request Creation

1. Navigate to the Lead, Prospect, Opportunity, Quotation, or Sales Order
2. Click the **"Sample Request"** button
3. The system creates a new Sample Request AMB document with:
   - Automatic link to the source document (Party Type + Party)
   - Current date as Request Date
   - Auto-generated naming series (SR-.YYYY.-.#####)

---

## 5. Sample Preparation - CPEM-020

### 5.1 Powder Samples for Clients

**Requirements:**
- Clean repackaging area
- Clean scale and utensils
- Appropriate bag size based on quantity:

| Sample Size | Bag Type |
|-------------|----------|
| < 30 grams | 7 oz sterile bag |
| 30-70 grams | 11 oz sterile bag |
| 100-300 grams | Sterile bags |
| > 300 grams | Natural polyethylene bag 30x60 cm |

**Procedure:**
1. Weigh components according to required proportions
2. Empty into sterile bag and mix thoroughly
3. Apply label with product type, code, manufacturing date, and content

### 5.2 Juice and Concentrate Samples

**Dilution Formula:**
```
C1 × V1 = C2 × V2
```
Where:
- C1 = Desired concentration
- V1 = Volume to prepare
- C2 = Sample concentration (°Bx)
- V2 = Concentrate volume to use

**Procedure:**
1. Measure °Bx of concentrate
2. Calculate concentrate volume based on desired specification
3. Measure concentrate with graduated cylinder
4. Complete with distilled water (e.g., 900ml total = 34ml concentrate + 866ml water)
5. Heat to 85°C with agitation
6. If preservatives required, heat to 90°C
7. Pour into sterile wide-mouth containers and Whypal bags
8. Label with product type, code, manufacturing date, and content

---

## 6. Physicochemical Sampling - CPMF-028

### 6.1 Aloe Vera Penca (Leaf)

- Take 9 samples per leaf/filet distributed at start, middle, and end of truck
- Sample before washing
- Record in Aloe Vera Reception Format

### 6.2 Raw Juice (Pressed)

- Take 1L sample in clean dry beaker for isotherms (Tank 1)
- Take 2 x 150ml samples for each batch (Tanks 2 and 3)
- Evaluate: °Bx, pH, total solids
- Record in Pressing Format

### 6.3 Filtered Juice

- Use 9 clean 125ml plastic containers, identified
- Take 3 samples at start, middle, and end of each filter batch
- Take 50-100ml from filter purge valve (purge 5 seconds, rinse 2-3 times)
- Measure turbidity every 20 minutes (range: filtered 0-20, re-filtered 0-5)
- Evaluate: °Bx, pH, color, turbidity, total solids, acidity, polysaccharides
- Record in Filtered Format

### 6.4 Concentrate

- Use clean 125ml plastic container
- Take 4 samples per concentrate batch
- Start sampling 1 hour after concentration start, then hourly
- Evaluate: °Bx, pH, color, turbidity, total solids, acidity
- Record in Concentration Format

### 6.5 Finished Product: Concentrated (Bottled)

- Take samples in pre-sterilized National containers (1L, 500ml, 125ml)
- Take 1 sterile Whypal bag per barrel for microbiology
- For client-specific juices/concentrates: sample 50% of total product
- Evaluate: °Bx, pH, color, turbidity, total solids, acidity, polysaccharides
- Record in Bottling Format

### 6.6 Finished Product: Powder

- For external drying: take 2 samples per 2 dried drums (75g each)
- Proper identification required:

```
Aloe Vera Powder Organic NOP, LPO, EC, KOC / FAIR TRADE, COSMOS, HALAL, KOSHER, IASC
Produced by:
LOT:
Manufacturing Date:
Drum Number:
Net Content
```

---

## 7. Retention Sample Handling - CPMR-032

### 7.1 Powder Samples

**Procedure:**
1. Take samples from dried product (sterile sealed bags)
2. Reserve set for physicochemical, microbiological, and external lab analysis
3. Keep at least one set unmanipulated for reference
4. For mixed products: take double samples (one for analysis, one for reference)
5. Label if missing: lot number, manufacture date, drum number, supplier name
6. Store at room temperature, free of humidity
7. Retain for 1.5x shelf life (powder: 24 months)

### 7.2 Liquid Samples

**Preparation:**
- Sterilize 3 wide-mouth National containers: 1L, 500ml, 125ml
- For client orders: sterilize 1L (client + retention), 500ml (retention), 125ml (analysis)
- Take 4L independently for shelf life tracking

**Procedure:**
1. Provide containers to quality inspector
2. Collect samples at midpoint of bottling process
3. Label and store in refrigeration (≤ 7°C)
4. Retain for 1.5x shelf life:
   - Food preservatives: 12 months
   - Cosmetics: 24 months
   - Antimicrobial: 18 months
   - No preservatives: 6-12 months

**Usage:**
- Customer complaint investigation
- Physicochemical and microbiological verification
- Batch investigation

---

## 8. Sample Request AMB DocType Fields

### 8.1 Header Information

| Field | Type | Description |
|-------|------|-------------|
| Series | Select | Auto-generated (SR-.YYYY.-.#####) |
| Request Date | Date | Date of sample request |
| Request Type | Select | Marketing, Prospect, Pre-sample Approved, External Analysis, New Product Development, Inspector/Sublot Report, New Process Trial, External Laboratory, Other |
| Party Type | Link | Lead, Prospect, Customer, etc. |
| Party | Dynamic Link | Reference to the source document |
| Customer | Link | Customer record |
| Customer Name | Data | Auto-populated customer name |
| Customer PO | Data | Customer Purchase Order |

### 8.2 Product Information

| Field | Type | Description |
|-------|------|-------------|
| Item | Link | Product item |
| Batch Reference | Link | Batch AMB reference |
| Batch Quantity | Float | Quantity from batch |

### 8.3 Contact & Address

| Field | Type | Description |
|-------|------|-------------|
| Contact Person | Link | Contact record |
| Phone | Data | Phone number |
| Email | Data | Email address |
| Address | Link | Address record |
| City | Data | City |
| State | Data | State |
| Country | Link | Country |
| Postal Code | Data | Postal code |

### 8.4 Logistics

| Field | Type | Description |
|-------|------|-------------|
| Received By | Data | Who received the sample |
| Received Date | Date | Date received |
| Sent By | Data | Who sent the sample |
| Sent Date | Date | Date sent |
| AWB Number | Data | Airway Bill / Tracking number |
| Project | Link | Associated project |
| Label Type | Data | Type of label required |
| Application | Data | Desired application |
| Promotion or Event | Data | Related promotion/event |

### 8.5 Sample Items (Child Table)

| Field | Type | Description |
|-------|------|-------------|
| Item | Link | Product item |
| Description | Data | Item description |
| Batch | Link | Batch reference |
| SPC Specification | Link | SPC Specification |
| Number of Samples | Int | Count of samples |
| Qty per Sample | Float | Quantity per sample |
| UOM | Link | Unit of Measure |
| Total Qty | Float | Total quantity (calculated) |
| Container Type | Data | Type of container |
| Container Size | Data | Container capacity |
| Label Text | Small Text | Label content |
| For Retention | Check | Retention sample flag |
| For Microbiology | Check | Microbiology sample flag |
| For Customer | Check | Customer sample flag |
| For Distributor | Check | Distributor sample flag |
| For External Lab | Check | External lab sample flag |
| Target Warehouse | Link | Destination warehouse |
| Sample Role | Select | Routine Control, Validation, Investigation, Stability Study, Customer Complaint, Marketing |
| Criticality | Select | Critical, Major, Minor |
| Lab Notes | Small Text | Laboratory notes |

---

## 9. Status Workflow

| Status | Description |
|--------|-------------|
| Draft | Initial state, being edited |
| Requested | Sample request submitted |
| In Process | Sample being prepared |
| Completed | Sample delivered/completed |
| Cancelled | Request cancelled |

---

## 10. Integration Points

### 10.1 Batch AMB Integration

Sample Requests are linked to Batch AMB records because:
- Many samples are requested with labels related to lot, sublot, container, and serial numbers
- Enables traceability between samples and production batches

### 10.2 Print Module Integration (print_amb)

- Labels are generated and printed directly to printer or PDF
- Labels include lot information, manufacturing date, and content

### 10.3 Sales Workflow Integration

```
Prospect → Lead → Opportunity → Quotation → Sales Order → Production
                        ↓
              Sample Request (at any stage)
```

---

## 11. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-19 | AMB Wellness | Initial release |

---

## 12. Appendix: Product Codes Reference

### Sales Product Codes
- Range: 0334 - 1090

### Plant-Specific Codes

| Plant | Code Range | Description |
|-------|------------|-------------|
| Mix Plant | 0612 | Mix processing |
| Dry Plant | 0301 | Permeate, 0302 Retained, 0303 Normal, 0304 Scraps |
| Juice | 0227 | 1X Juice (converts to 0227-030X for drying) |
| Powder | A301-A304 | Dried powder (before analysis) → SFG after analysis |

### Homogenizations
- Combination of multiple powders to create new blends
- Results in new COA (Certificate of Analysis)
