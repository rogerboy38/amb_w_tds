# Raven AI Agent Integration Project

## AMB W TDS v9.1.0 - Raven AI Environment Integration

---

## Project Overview

This document outlines the Raven AI agent integration for AMB W TDS ERP system, including the Batch Widget, Serial Tracking Agent, and BOM Tracking Agent.

---

## 1. Production Monitor Widget (Batch Widget)

### Purpose
Real-time monitoring of production batches with drag-and-drop positioning.

### Key Features
| Feature | Description |
|---------|-------------|
| **Position** | Bottom-left corner (default), draggable anywhere |
| **Status Display** | Shows High priority, WC count, Container count |
| **Auto-refresh** | Updates every 5 minutes |
| **Close Options** | 1hr, 8hr, 24hr, or until refresh |

### Widget Buttons
| Button | Color | Action |
|--------|-------|--------|
| Minimize | Yellow `-` | Collapse to header only |
| Maximize | Green `□` | Expand to full size |
| Close | Red `×` | Close with duration selection |
| Starting → Running | Yellow badge | Click to change batch status and restart |

### Technical Files
- **Source**: `amb_w_tds/public/js/batch_widget.js`
- **Hooks**: `amb_w_tds/hooks.py` (app_include_js)
- **Storage**: localStorage keys: `amb_batch_widget_hidden_until`, `amb_batch_widget_position`

### Deployment Commands
```bash
# Build assets
cd ~/frappe-bench && bench build --app amb_w_tds --force

# Clear cache and restart
bench clear-cache
sudo supervisorctl restart all
```

---

## 2. Serial Tracking Agent

### Purpose
Manages ERPNext serial tracking with Batch AMB hierarchy.

### Commands
```
@Raven serial health         # Check system health
@Raven serial status <SERIAL>  # Get serial status
@Raven serial batch <BATCH>    # List serials in batch
```

### Agent Class
- **File**: `amb_w_tds/raven/serial_tracking_agent.py`
- **Class**: `SerialTrackingAgent`
- **Version**: 1.0.0

### Capabilities
- `configure_serial_tracking` - Enable serial tracking for items
- `generate_serial_numbers` - Generate serials for batches
- `validate_compliance` - Validate serial compliance
- `basic_health_checks` - System health monitoring

### API Methods
| Method | Description |
|--------|-------------|
| `process(message)` | Main message handler |
| `_handle_help()` | Return help text |
| `_handle_health()` | Return health status |
| `_enable_serial_tracking(item_code)` | Enable tracking for item |
| `_generate_serials(batch, qty)` | Generate serial numbers |

---

## 3. BOM Tracking Agent

### Purpose
BOM health monitoring and inspection via Raven chat interface.

### Commands
```
@Raven bom health              # Run health check
@Raven bom inspect <BOM-NAME>  # Inspect specific BOM
@Raven bom status <ITEM-CODE>  # BOM status for item
@Raven bom issues              # Show known issues
```

### Agent Class
- **File**: `amb_w_tds/raven/bom_tracking_agent.py`
- **Class**: `BOMTrackingAgent`
- **Version**: 1.0.0

### Health Check Categories
| Category | Description | Severity |
|----------|-------------|----------|
| Multiple Default BOMs | Items with >1 default BOM | 🔴 Critical |
| Inactive Default BOMs | Default BOMs not active | 🟠 High |
| Cost Anomalies | Costs differ from average | 🟡 Medium |
| Missing Components | Empty/missing components | 🔵 Low |

### Dependencies
- `amb_w_tds.scripts.bom_status_manager`
- `amb_w_tds.scripts.bom_known_issues.json`

---

## 4. Project Structure

```
amb_w_tds/
├── raven/
│   ├── __init__.py
│   ├── bom_tracking_agent.py      # BOM monitoring agent
│   ├── serial_tracking_agent.py   # Serial management agent
│   ├── config.py                  # Raven configuration
│   ├── utils.py                   # Shared utilities
│   ├── cli.py                     # CLI interface
│   ├── setup.py                   # Agent registration
│   └── RAVEN_COMMANDS_HELP.md     # Command reference
├── scripts/
│   ├── bom_status_manager.py      # BOM health check logic
│   ├── bom_audit_agent.py         # BOM audit functions
│   ├── bom_known_issues.json      # Tracked issues
│   └── scheduled_bom_health.py    # Scheduled task
├── public/js/
│   └── batch_widget.js            # Production monitor widget
└── hooks.py                       # Frappe hooks (includes js)
```

---

## 5. Raven Integration Setup

### Register Agents
```python
# In setup.py or hooks.py
from amb_w_tds.raven.bom_tracking_agent import BOMTrackingAgent
from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent

def register_raven_agents():
    return [
        BOMTrackingAgent(),
        SerialTrackingAgent()
    ]
```

### Message Routing
The agents respond to messages prefixed with `@Raven` followed by the agent command:

```
@Raven bom health       → BOMTrackingAgent.handle_message("bom health")
@Raven serial health    → SerialTrackingAgent.process("serial health")
```

---

## 6. API Endpoints

### BOM Agent API
```python
# API for external integrations
@frappe.whitelist()
def bom_agent_api(command, params=None):
    agent = BOMTrackingAgent()
    return agent.handle_message(command)
```

### Serial Agent API
```python
@frappe.whitelist()
async def serial_agent_api(command, params=None):
    agent = SerialTrackingAgent()
    return await agent.process(command)
```

---

## 7. Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| BOM Health Check | Weekly | Automated health scan with email report |
| Serial Audit | Daily | Check for orphaned serials |

### Scheduler Configuration
```python
# In hooks.py
scheduler_events = {
    "weekly": [
        "amb_w_tds.scripts.scheduled_bom_health.run"
    ]
}
```

---

## 8. Testing

### Test Commands
```bash
# Test BOM agent
bench execute amb_w_tds.raven.bom_tracking_agent.BOMTrackingAgent.handle_message --args "['bom health']"

# Test Serial agent
bench execute amb_w_tds.raven.serial_tracking_agent.test_agent
```

### Test via Raven Chat
1. Open Raven chat interface
2. Type: `@Raven bom health`
3. Verify response shows health summary

---

## 9. Deployment Checklist

- [ ] Pull latest code: `git pull origin feature/v9.1.0-development`
- [ ] Build assets: `bench build --app amb_w_tds --force`
- [ ] Clear cache: `bench clear-cache`
- [ ] Restart services: `sudo supervisorctl restart all`
- [ ] Verify widget position (bottom-left)
- [ ] Test `@Raven bom health` command
- [ ] Test `@Raven serial health` command

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| v9.1.0 | 2026-02 | Widget repositioned, BOM Tracking Agent added |
| v9.0.0 | 2026-01 | Serial Tracking Agent initial release |

---

## Contact

For issues or questions, contact the development team or create a ticket in the project repository.

**Repository**: `github.com/rogerboy38/amb_w_tds`
**Branch**: `feature/v9.1.0-development`
