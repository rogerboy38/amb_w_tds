# AMB W TDS - Technical Data Sheet Management System

[![Version](https://img.shields.io/badge/version-v7.0.0-blue.svg)](https://github.com/rogerboy38/amb_w_tds/releases/tag/v7.0.0)
[![Frappe](https://img.shields.io/badge/frappe-v15-orange.svg)](https://github.com/frappe/frappe)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Golden Rule](https://img.shields.io/badge/naming-100%25%20compliant-success.svg)](GOLDEN_RULE.md)

> **Technical Data Sheet (TDS) and Certificate of Analysis (COA) management system for AMB-Wellness**

## 🎯 Version 2.5.0 - Controller Migration Release

### What's New in v7.0.0

✨ **Major Updates:**
- ✅ **Complete Controller Migration**: All client/server scripts migrated to Python controllers
- ✅ **Golden Rule Compliance**: 24 DocTypes, 635 fields - 100% compliant naming conventions
- ✅ **Production Monitoring Widget**: Real-time batch tracking with intelligent caching
- ✅ **Enhanced Business Logic**: Comprehensive validation, automation, and notifications
- ✅ **Zero Database Scripts**: All logic in version-controlled Python/JavaScript files

### 🎉 Key Features

#### 📋 Batch Management (Batch AMB)
- **Smart Validation**: Production dates, quantities, container tracking
- **Work Order Integration**: Auto-fill item details from Work Orders
- **Cost Calculation**: Automatic BOM, labor, and overhead cost tracking
- **Stock Entry Creation**: Automated stock entries on batch completion
- **Lote AMB Sync**: Inventory tracking with automatic updates
- **Quality Status Tracking**: Integration with quality inspection workflow

#### 📊 Certificate of Analysis (COA AMB)
- **TDS Synchronization**: Auto-populate specifications from approved TDS
- **Quality Validation**: Real-time result validation against specifications
- **Batch Linking**: Automatic quality status updates to production batches
- **PDF Generation**: Professional COA certificates
- **Multi-level Support**: COA AMB and COA AMB2 variants

#### 📖 Technical Data Sheets (TDS Product Specification)
- **Version Control**: Automatic version numbering and history tracking
- **Specification Management**: Detailed parameter definitions
- **Auto-COA Creation**: Generate COA templates from approved TDS
- **Archive Management**: Automatic archiving of superseded versions
- **Change Notifications**: Stakeholder alerts on approvals

#### 🏭 Production Widget
- **Real-time Monitoring**: Live batch status dashboard
- **Smart Caching**: Optimized API calls with 2-minute cache
- **Company/Plant Grouping**: Organized view by location
- **Priority Indicators**: Visual alerts for quality issues
- **Auto-refresh**: 5-minute intervals with manual refresh option

### 📦 Installation

#### Prerequisites
- Frappe Framework v15.x or higher
- ERPNext v15.x (optional but recommended)
- Python 3.10+
- Node.js 18+

#### Quick Install

```bash
# Get the app
bench get-app https://github.com/rogerboy38/amb_w_tds.git --branch v7.0.0

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
Frappe Cloud Installation

Go to your Frappe Cloud dashboard
Navigate to your site
Click on "Apps" → "Add App"
Select amb_w_tds from available apps
Choose version: v7.0.0
Click "Install"

🏗️ Architecture
