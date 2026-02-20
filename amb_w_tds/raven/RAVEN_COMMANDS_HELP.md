# Raven AI Agent - Command Reference

## AMB W TDS v9.1.0

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

## Quick Reference Card

| Agent | Prefix | Commands |
|-------|--------|----------|
| Serial | `serial` | `health`, `status`, `batch` |
| BOM | `bom` | `health`, `inspect`, `status`, `issues` |

---

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| BOM Health Check | Weekly | Automated health scan with email report |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v9.1.0 | 2026-02 | Added BOM Tracking Agent |
| v9.0.0 | 2026-01 | Added Serial Tracking Agent |

---

*For more information, see the main README.md or contact the development team.*
