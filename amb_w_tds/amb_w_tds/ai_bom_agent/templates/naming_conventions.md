# BOM Naming Conventions - AMB W TDS v9.2.0

## Overview

This document defines the standardized naming conventions for all BOM-related items in the AMB W TDS system. Consistent naming enables automated BOM creation and maintenance.

---

## 1. Semi-Finished Goods (SFGs)

### Pattern
```
SFG-{FAMILY}-STEP{N}-{PROCESS}-{ATTRIBUTE}[-{VARIANT}]
```

### Components
| Component | Description | Examples |
|-----------|-------------|----------|
| `SFG` | Fixed prefix for Semi-Finished Goods | - |
| `FAMILY` | 4-digit product family code | 0227, 0307 |
| `STEP{N}` | Process step number (1-9) | STEP1, STEP2, STEP3 |
| `PROCESS` | 4-letter process abbreviation | CONC, STD, FILT, PWD |
| `ATTRIBUTE` | Product attribute | ORGANIC, KOSHER, CONVENTIONAL |
| `VARIANT` | Optional variant (flavor, mesh size) | MANGO, 200-MESH |

### Process Abbreviations
| Code | Full Name | Family |
|------|-----------|--------|
| CONC | Concentration | 0227, 0307 |
| STD | Standardization | 0227 |
| FILT | Filtration | 0307 |
| PWD | Powder | 0307 |
| PACK | Packing | All |

### Examples
```
SFG-0227-STEP1-CONC-ORGANIC        # Organic concentrated aloe juice
SFG-0227-STEP2-STD-ORGANIC-MANGO   # Organic mango standardized juice
SFG-0307-STEP3-PWD-KOSHER-200MESH  # Kosher 200-mesh powder
```

---

## 2. Finished Goods (FGs)

### Pattern
```
{FAMILY}-{ATTRIBUTE}-{FLAVOR/MESH}-{PACKAGING}
```

### Components
| Component | Description | Examples |
|-----------|-------------|----------|
| `FAMILY` | 4-digit product family code | 0227, 0307 |
| `ATTRIBUTE` | Product attribute | ORG, CONV, KOS, KOS-ORG |
| `FLAVOR/MESH` | Product variant | MANGO, PLAIN, 100MESH |
| `PACKAGING` | Package type code | IBC, DRUM, 25KG |

### Attribute Codes
| Code | Full Name |
|------|-----------|
| ORG | Organic |
| CONV | Conventional |
| KOS | Kosher |
| KOS-ORG | Kosher Organic |

### Packaging Codes
| Code | Description | Size |
|------|-------------|------|
| IBC | IBC Container | 1000L |
| DRUM | Drum | 200L |
| PAIL | Pail | 20L |
| 5GAL | 5 Gallon | 18.93L |
| 25KG | 25Kg Bag | 25Kg |
| 10KG | 10Kg Bag | 10Kg |

### Examples
```
0227-ORG-MANGO-IBC      # Organic mango juice in IBC
0227-CONV-PLAIN-DRUM    # Conventional plain juice in drum
0307-KOS-200MESH-25KG   # Kosher 200-mesh powder in 25kg bag
```

---

## 3. Raw Materials (RMs)

### Pattern
```
RM-{CATEGORY}-{NAME}[-{VARIANT}]
```

### Categories
| Category | Description |
|----------|-------------|
| ALOE | Aloe vera base materials |
| WATER | Water types |
| ACID | Acids and preservatives |
| FLAVOR | Flavoring agents |
| CARRIER | Carrier materials (maltodextrin) |

### Examples
```
RM-ALOE-ORGANIC         # Organic raw aloe
RM-ALOE-CONVENTIONAL    # Conventional raw aloe
RM-WATER-PURIFIED       # Purified water
RM-CITRIC-ACID          # Citric acid
RM-ADDITIVE-ACEMANNAN   # Acemannan concentrate
RM-MALTODEXTRIN         # Maltodextrin carrier
```

---

## 4. Packaging Materials (PKG)

### Pattern
```
PKG-{TYPE}[-{SIZE}]
```

### Examples
```
PKG-IBC-1000L           # 1000L IBC container
PKG-DRUM-200L           # 200L drum
PKG-BAG-25KG            # 25Kg bag
PKG-LABEL-0227          # Label for 0227 products
PKG-DESICCANT           # Desiccant packet
```

---

## 5. BOM Naming

### Pattern
```
BOM-{ITEM_CODE}-{SEQUENCE}
```

### Examples
```
BOM-0227-ORG-MANGO-IBC-001      # First BOM for organic mango IBC
BOM-SFG-0227-STEP1-CONC-ORG-001 # First BOM for SFG concentrate
```

---

## 6. Validation Rules

1. **No spaces** - Use hyphens (`-`) as separators
2. **Uppercase only** - All codes must be uppercase
3. **Fixed lengths**:
   - Family codes: 4 digits
   - Process codes: 3-4 letters
   - Attribute codes: 2-7 letters
4. **Sequential numbering** - 3-digit sequence (001-999)
5. **No special characters** - Only alphanumeric and hyphens

---

## 7. Quick Reference Card

| Item Type | Pattern | Example |
|-----------|---------|---------|
| SFG | `SFG-{FAM}-STEP{N}-{PROC}-{ATTR}` | `SFG-0227-STEP1-CONC-ORGANIC` |
| FG | `{FAM}-{ATTR}-{VAR}-{PKG}` | `0227-ORG-MANGO-IBC` |
| RM | `RM-{CAT}-{NAME}` | `RM-ALOE-ORGANIC` |
| PKG | `PKG-{TYPE}-{SIZE}` | `PKG-DRUM-200L` |
| BOM | `BOM-{ITEM}-{SEQ}` | `BOM-0227-ORG-MANGO-IBC-001` |

---

*Document Version: 1.0*
*Last Updated: 2026-02-17*
*Author: BOM_Creator_Agent v9.2.0*
