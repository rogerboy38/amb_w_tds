# AMB W TDS - Technical Data Sheet Management System

[![Version](https://img.shields.io/badge/version-v9.1.0-blue.svg)](https://github.com/rogerboy38/amb_w_tds/releases/tag/v9.1.0)
[![Frappe](https://img.shields.io/badge/frappe-v15-orange.svg)](https://github.com/frappe/frappe)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Golden Rule](https://img.shields.io/badge/naming-100%25%20compliant-success.svg)](GOLDEN_RULE.md)

> **Technical Data Sheet (TDS) and Certificate of Analysis (COA) management system for AMB-Wellness**

## 🎯 Version 9.1.0 - BOM Hierarchy & AI Agent Release

### What's New in v9.1.0

✨ **Major Updates:**
- ✅ **BOM Hierarchy Management**: Multi-level BOM structure with real-time health monitoring
- ✅ **AI-Powered BOM Tracking Agent**: Raven AI commands for BOM health, inspection, and issue tracking
- ✅ **Scheduled Health Checks**: Weekly automated BOM status reports
- ✅ **Known Issues Tracking**: Centralized BOM issue management via `bom_known_issues.json`
- ✅ **Serial Number Validation**: Complete barrel lifecycle management with auto-retirement

### 🤖 Raven AI Agent Commands

#### Serial Tracking Commands
| Command | Description |
|---------|-------------|
| `serial health` | Overall serial system health check |
| `serial status <SERIAL>` | Get status of specific serial number |
| `serial batch <BATCH>` | List all serials in a batch |

#### BOM Tracking Commands
| Command | Description |
|---------|-------------|
| `bom health` | Run BOM hierarchy health check |
| `bom inspect <BOM>` | Inspect specific BOM structure |
| `bom status <ITEM>` | Get BOM status for an item |
| `bom issues` | List all known BOM issues |

### 🎉 Key Features

#### 📦 BOM Hierarchy Management
- **Multi-level Structure**: Support for complex BOM hierarchies
- **Health Monitoring**: Automated checks for inactive items, missing data
- **Issue Tracking**: JSON-based known issues with status management
- **Scheduled Reports**: Weekly health check emails to stakeholders

#### 📋 Batch Management (Batch AMB)
- **Smart Validation**: Production dates, quantities, container tracking
- **Work Order Integration**: Auto-fill item details from Work Orders
- **Cost Calculation**: Automatic BOM, labor, and overhead cost tracking
- **Stock Entry Creation**: Automated stock entries on batch completion

#### 📊 Certificate of Analysis (COA AMB)
- **TDS Synchronization**: Auto-populate specifications from approved TDS
- **Quality Validation**: Real-time result validation against specifications
- **Batch Linking**: Automatic quality status updates to production batches
- **PDF Generation**: Professional COA certificates

#### 📖 Technical Data Sheets (TDS Product Specification)
- **Version Control**: Automatic version numbering and history tracking
- **Specification Management**: Detailed parameter definitions
- **Auto-COA Creation**: Generate COA templates from approved TDS

#### 🛢️ Barrel Lifecycle Management
- **Serial Validation**: Real-time format validation (AMB-YYYY-BATCH-NUMBER)
- **Warehouse Integration**: Auto-update status on Stock Entry
- **Usage Tracking**: Fill & empty cycle monitoring
- **Auto-Retirement**: Automatic at configurable max usage

### 📦 Installation

#### Prerequisites
- Frappe Framework v15.x or higher
- ERPNext v15.x (optional but recommended)
- Python 3.10+
- Node.js 18+

#### Quick Install

```bash
# Get the app
bench get-app https://github.com/rogerboy38/amb_w_tds.git --branch v9.1.0

# Install on site
bench --site your-site.com install-app amb_w_tds

# Migrate database
bench --site your-site.com migrate

# Build assets
bench build --app amb_w_tds

# Clear cache
bench --site your-site.com clear-cache

# Restart
bench restart
```

### 📁 Project Structure

```
amb_w_tds/
├── amb_w_tds/
│   ├── doctype/           # DocType definitions
│   ├── raven/             # AI Agent modules
│   │   ├── bom_tracking_agent.py      # BOM AI commands
│   │   ├── serial_minimal_working.py  # Serial AI commands
│   │   └── config.py                  # Agent registration
│   └── scripts/           # Utility scripts
│       ├── bom_status_manager.py      # BOM health logic
│       ├── bom_known_issues.json      # Known issues database
│       └── scheduled_bom_health.py    # Scheduler integration
├── version.txt
└── README.md
```

### 🏗️ Architecture

- **24 DocTypes** with 100% Golden Rule compliant naming
- **Controller-based logic** - No database scripts
- **RESTful APIs** for validation and lifecycle operations
- **Raven AI Integration** for natural language commands

### 📝 Release History

| Version | Date | Highlights |
|---------|------|------------|
| v9.1.0 | 2026-02 | BOM Hierarchy & AI Agent |
| v9.0.0 | 2026-01 | BOM Status Manager |
| v8.x | 2025-12 | Serial Lifecycle Management |
| v7.0.0 | 2025-11 | Controller Migration |

### 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Maintained by:** AMB-Wellness Team
