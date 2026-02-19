# Raven AI Agent - Command Reference

## AMB W TDS v9.2.0

This document provides a quick reference for all Raven AI agent commands available in AMB W TDS.

---

## Serial Tracking Agent

Commands for barrel/container serial number management.

| Command | Description | Example |
|---------|-------------|---------|
| `serial health` | Check overall serial system health | `serial health` |
| `serial status <SERIAL>` | Get status of specific serial number | `serial status AMB-2024-B001-0001` |
| `serial batch <BATCH>` | List all serials in a batch | `serial batch BATCH-001` |

### Usage Examples

```
@Raven serial health
@Raven serial status AMB-2024-B001-0001
@Raven serial batch BATCH-001
```

---

## BOM Tracking Agent

Commands for Bill of Materials health monitoring and inspection.

| Command | Description | Example |
|---------|-------------|---------|
| `bom health` | Run comprehensive BOM health check | `bom health` |
| `bom inspect <BOM>` | Inspect specific BOM structure | `bom inspect BOM-0307-004` |
| `bom status <ITEM>` | Get BOM status for an item | `bom status 0307` |
| `bom issues` | List all known BOM issues | `bom issues` |

### Usage Examples

```
@Raven bom health
@Raven bom inspect BOM-0307-004
@Raven bom status 0307
@Raven bom issues
```

### Health Check Output

The `bom health` command checks for:
- **Multiple Default BOMs** - Items with more than one default BOM
- **Inactive Default BOMs** - Default BOMs that are not active
- **Cost Anomalies** - BOMs with costs significantly different from average
- **Missing Components** - BOMs with empty or missing components

Severity levels: 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low

---

## BOM Creator Agent (Phase 7)

Commands for creating multi-level BOMs from natural language specifications.

| Command | Description | Example |
|---------|-------------|---------|
| `bom create <spec>` | Create BOM from specification | `bom create 0227 EU organic 30:1 in IBC` |
| `bom plan <spec>` | Plan/preview BOM (dry run) | `bom plan HIGHPOL 20/25 100 mesh` |
| `bom help` | Show BOM creator help | `bom help` |

### Supported Specifications

**Product Families:**
- `0227` - Aloe Vera Gel Concentrate (liquid)
- `0307` - Aloe Vera Spray Dried Powder
- `HIGHPOL` - Highpol Powder (polysaccharide variants)
- `ACETYPOL` - Acetypol Powder (acemannan variants)

**Certifications:**
- `EU organic`, `NOP USA`, `Korean organic` → Organic variants
- `fair trade`, `kosher`, `halal`, `conventional`

**Mesh Sizes (Powder only):**
- `60 mesh`, `80 mesh`, `100 mesh`, `120 mesh`, `200 mesh`

**Packaging:**
- `1000L IBC`, `200L drum`, `25kg bags`

**Customer Naming:**
- `for customer XYZ` - Use customer-specific naming pattern

### Usage Examples

```
@Raven bom create 0227 EU organic 30:1 in 1000L IBC
@Raven bom plan HIGHPOL 20/25 100 mesh fair trade 25kg bags
@Raven bom create 0307 200:1 powder for customer XYZ
@Raven bom help
```

### Response Format

The agent returns:
- Specification summary (family, variant, certification, mesh, packaging)
- Items created/reused list with ERPNext links
- BOMs created/reused list with ERPNext links
- Batch tracking status
- Execution time

---

## Quick Reference Card

| Agent | Prefix | Commands |
|-------|--------|----------|
| Serial | `serial` | `health`, `status`, `batch` |
| BOM Tracking | `bom` | `health`, `inspect`, `status`, `issues` |
| BOM Creator | `bom` | `create`, `plan`, `help` |

---

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| BOM Health Check | Weekly | Automated health scan with email report |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v9.2.0 | 2026-02-19 | Added BOM Creator Agent (Phase 7) |
| v9.1.0 | 2026-02-17 | Added BOM Tracking Agent |
| v9.0.0 | 2026-01 | Added Serial Tracking Agent |

---

*For more information, see the main README.md or contact the development team.*
