# Sprint 1: Batch AMB AI Widget Implementation

## Overview
Reposition and enhance the Batch AMB widget with drag capability and Lot ID auto-suggestion.

## Files to Deploy

### 1. Widget JS (Replace existing)
**Path:** `/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/public/js/formulated_agent_widget.js`

### 2. Batch AMB Client Script (Update)
**Path:** `/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.js`

### 3. Batch AMB Server Script (Update)  
**Path:** `/home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py`

---

## Deployment Commands

```bash
# SSH to server
ssh frappe@v2.sysmayal.cloud

# Navigate to app
cd /home/frappe/frappe-bench/apps/amb_w_tds

# Backup existing files
cp amb_w_tds/public/js/formulated_agent_widget.js amb_w_tds/public/js/formulated_agent_widget.js.backup

# Edit widget file (paste new code)
nano amb_w_tds/public/js/formulated_agent_widget.js

# Clear cache and rebuild
cd /home/frappe/frappe-bench
bench --site v2.sysmayal.cloud clear-cache
bench build --app amb_w_tds

# Optional: Watch for live changes during development
bench watch
```

---

## Implementation Details

### Widget Features (Sprint 1)
1. **Bottom-left positioning** - Fixed at bottom: 20px, left: 20px
2. **Drag functionality** - Save position to localStorage
3. **Context awareness** - Detect if on Work Order or Batch AMB form
4. **Lot ID suggestion** - Auto-generate LOTE-YY-WW-NNNN format

### Lot ID Generation Logic
```
LOTE-{YY}-{WW}-{NNNN}
  YY = Current year (last 2 digits)
  WW = Current week number
  NNNN = Sequence number (auto-increment within same YY-WW)
```

### Title Generation Logic
```
{SalesOrder}-{Seq}-{Component}
  SalesOrder = From linked Work Order's sales_order field
  Seq = Batch sequence (1, 2, 3...)
  Component = C1, C2, C3... (component identifier)
```

---

## Success Criteria
- [ ] Widget appears in bottom-left corner
- [ ] Widget is draggable (position persists via localStorage)
- [ ] Agent assists with batch creation form
- [ ] Auto-suggests Lot ID based on current date
- [ ] Validates naming conventions
- [ ] Integrates with existing @ai command

---

## Next Steps (Sprint 2)
- Work Order linkage validation
- Sequence number auto-increment  
- Duplicate batch functionality
- Form validation rules
