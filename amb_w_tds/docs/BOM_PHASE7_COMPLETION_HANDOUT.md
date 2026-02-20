# Phase 7 Completion Handout

## BOM Creator Agent v9.2.0 - Mesh Sizes, Customer Naming, Batch Flags, Raven Skill

**Status:** ✅ COMPLETE  
**Branch:** `feature/v9.2.0-development`  
**Date:** 2026-02-19  

---

## 1. Scope Summary

Phase 7 implements usability and traceability enhancements for the BOM Creator Agent:

1. **Mesh Size Parsing** - Support for powder mesh specifications (e.g., "100 mesh")
2. **Customer-Specific Naming** - FG item codes can follow customer-specific patterns
3. **Batch/Lot Tracking Flags** - Items created for batch-tracked families auto-enable `has_batch_no`
4. **Raven BOM Creator Skill** - Create BOMs via Raven chat interface

---

## 2. Code Changes

### 2.1 Parser Enhancements (`parser.py`)

**New Constants:**
```python
MESH_PATTERNS = [
    re.compile(r"(\d+)\s*mesh", re.IGNORECASE),
    re.compile(r"mesh\s*(\d+)", re.IGNORECASE),
]

VALID_MESH_SIZES = {
    "0307": [60, 80, 100, 120, 200],
    "HIGHPOL": [60, 80, 100, 120],
    "ACETYPOL": [60, 80, 100, 120],
}

POWDER_FAMILIES = ["0307", "HIGHPOL", "ACETYPOL"]

CUSTOMER_PATTERNS = [
    re.compile(r"for\s+customer\s+(\w+)", re.IGNORECASE),
    re.compile(r"for\s+(\w+)\s+customer", re.IGNORECASE),
    re.compile(r"customer[:\s]+(\w+)", re.IGNORECASE),
]
```

**New Methods:**
- `_extract_mesh_size(text, family)` - Extracts and normalizes mesh size (e.g., "100M")
- `_extract_customer(text)` - Extracts customer identifier from request
- `_load_customer_rules()` - Loads customer naming rules from JSON config

### 2.2 Data Contracts (`data_contracts.py`)

**ParsedSpec Updates:**
```python
customer: Optional[str] = None       # Customer name
customer_code: Optional[str] = None  # Customer code for naming
```

**PlannedItem Updates:**
```python
has_batch_no: int = 0  # Batch tracking flag
```

**GenerationReport Updates:**
```python
batch_tracking: Dict[str, Any] = field(default_factory=dict)
```

### 2.3 Engine Updates (`engine.py`)

**New Methods:**
- `_get_customer_naming_rule(customer_code)` - Load customer-specific naming pattern
- `_apply_customer_pattern(spec, rule)` - Generate FG code using customer pattern

**FG Item Naming:**
- Default: `{FAMILY}-{ATTRIBUTE}-{VARIANT}-{MESH_SIZE}-{PACKAGING}`
- Customer: Uses pattern from `customer_naming_rules.json`

### 2.4 ERPNext Client (`erpnext_client.py`)

**Batch Tracking:**
```python
BATCH_TRACKING_FAMILIES = ["0227", "0307", "HIGHPOL", "ACETYPOL"]

def _should_enable_batch_tracking(self, item_code: str) -> bool:
    """Auto-enable batch tracking for specified families"""
```

### 2.5 Customer Naming Rules (`customer_naming_rules.json`)

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

### 2.6 Raven BOM Creator Agent (`raven/bom_creator_agent.py`)

**Commands:**
- `bom create <spec>` - Create BOM from specification
- `bom plan <spec>` - Dry run / plan BOM
- `bom help` - Show available commands

**API Endpoint:**
```python
@frappe.whitelist()
def bom_skill_api(request_text, dry_run=True, customer=None)
```

**Triggers:**
- "bom create", "bom plan", "bom help"
- "create bom", "make bom", "new bom"
- Family codes: "0227", "0307", "HIGHPOL", "ACETYPOL"

---

## 3. Test Commands

### T7.1 - Mesh Size Parsing (HIGHPOL)
```bash
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
  --kwargs '{"request_text": "Create HIGHPOL 20/25 100 mesh fair trade 25kg bags", "dry_run": True}'
```
**Expected:** `mesh_size = "100M"`

### T7.2 - Mesh Size Parsing (0307)
```bash
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
  --kwargs '{"request_text": "0307 200:1 powder 100 mesh", "dry_run": True}'
```
**Expected:** `mesh_size = "100M"`, `variant = "200X"`

### T7.3 - Customer Naming Rule
```bash
bench --site v2.sysmayal.cloud execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
  --kwargs '{"request_text": "0227 EU organic 30:1 for customer XYZ in 1000L IBC", "dry_run": True}'
```
**Expected:** `customer = "XYZ"`, FG code matches `{FAMILY}-{CUSTOMER_CODE}-{VARIANT}-{PACKAGING}`

### T7.4 - Raven Skill Import
```python
from amb_w_tds.raven.bom_creator_agent import get_agent_info, handle_raven_message
info = get_agent_info()
print(info["name"])  # "BOM Creator Agent"
```

### T7.5 - Raven Skill Command
```python
from amb_w_tds.raven.bom_creator_agent import process_bom_command
result = process_bom_command("bom plan 0227 fair trade 30:1 in IBC")
print(result["success"])  # True
```

---

## 4. Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `ai_bom_agent/parser.py` | Modified | Added mesh & customer extraction |
| `ai_bom_agent/data_contracts.py` | Modified | Added customer & batch fields |
| `ai_bom_agent/engine.py` | Modified | Added customer naming logic |
| `ai_bom_agent/erpnext_client.py` | Modified | Added batch tracking auto-enable |
| `ai_bom_agent/customer_naming_rules.json` | Created | Customer naming patterns config |
| `raven/bom_creator_agent.py` | Created | Raven chat skill for BOM creation |
| `raven/config.py` | Modified | Registered bom_creator agent |
| `raven/__init__.py` | Modified | Updated version to 9.2.0 |
| `scripts/test_v9.2.0_phase7.sh` | Created | Phase 7 test script |

---

## 5. Deployment Steps

1. **Pull latest code:**
   ```bash
   cd frappe-bench/apps/amb_w_tds
   git pull origin feature/v9.2.0-development
   ```

2. **Clear cache:**
   ```bash
   bench --site v2.sysmayal.cloud clear-cache
   ```

3. **Verify imports:**
   ```bash
   bench --site v2.sysmayal.cloud console
   >>> import amb_w_tds.raven.bom_creator_agent
   >>> print("OK")
   ```

4. **Run tests:**
   ```bash
   bash apps/amb_w_tds/scripts/test_v9.2.0_phase7.sh
   ```

---

## 6. Usage Examples

### Raven Chat
```
@ai bom create 0227 EU organic 30:1 in 1000L IBC
@ai bom plan HIGHPOL 20/25 100 mesh for customer XYZ in 25kg bags
@ai bom help
```

### API Call
```python
from amb_w_tds.ai_bom_agent.api import create_multi_level_bom_from_spec
result = create_multi_level_bom_from_spec(
    request_text="HIGHPOL 20/25 100 mesh fair trade 25kg bags",
    dry_run=True
)
```

---

## 7. Known Limitations

1. Customer rules file must be manually populated per customer
2. Mesh sizes are validated against predefined lists per family
3. Batch tracking requires `has_batch_no` custom field in ERPNext Item doctype
4. Raven integration requires raven_ai_agent app to be installed

---

**Report Generated:** 2026-02-19
