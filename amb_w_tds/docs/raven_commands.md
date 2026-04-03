# Raven Commands - Batch AMB

## Overview
This document lists the available Raven commands for interacting with the Batch AMB system. Raven is the internal communication platform used for system notifications and commands.

## Available Commands

### Batch Management

| Command | Description | Example |
|---------|-------------|---------|
| `!batch create` | Create new batch | `!batch create L1 JAR020 100` |
| `!batch status` | Get batch status | `!batch status LOTE-26-14-0013` |
| `!batch list` | List all batches | `!batch list` |
| `!batch serials` | Generate serials | `!batch serials LOTE-26-14-0013 10` |

### Hierarchy Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!batch create sublot` | Create Level 2 batch | `!batch create sublot LOTE-26-14-0011` |
| `!batch create container` | Create Level 3 batch | `!batch create container LOTE-26-14-0012` |
| `!batch hierarchy` | Show batch hierarchy | `!batch hierarchy LOTE-26-14-0013` |

### Pipeline Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!batch transition` | Change pipeline status | `!batch transition LOTE-26-14-0013 "In Progress"` |
| `!batch approve` | Approve batch (QA) | `!batch approve LOTE-26-14-0013` |
| `!batch reject` | Reject batch (QA) | `!batch reject LOTE-26-14-0013 "Weight mismatch"` |

### Serial Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!serial validate` | Validate serial format | `!serial validate JAR0001261-1-C1-001` |
| `!serial lookup` | Find batch by serial | `!serial lookup JAR0001261-1-C1-001` |
| `!serial list` | List serials for batch | `!serial list LOTE-26-14-0013` |

### Report Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!report batches` | Generate batch report | `!report batches --status "In Progress"` |
| `!report serials` | Generate serial report | `!report serials --date 2026-04-01` |
| `!report production` | Production metrics | `!report production --range 30d` |

### Help Commands

| Command | Description |
|---------|-------------|
| `!help batch` | Show batch commands |
| `!help serial` | Show serial commands |
| `!help report` | Show report commands |

## Command Syntax

### Basic Syntax
```
!batch <action> [parameters]
```

### Parameters
- Batch names: `LOTE-XX-XX-XXXX`
- Item codes: `JAR020`, `JAR021`, etc.
- Quantities: Numeric values
- Dates: `YYYY-MM-DD` format

### Examples

**Create Level 1 Batch:**
```
!batch create L1 JAR020 100
```

**Check Status:**
```
!batch status LOTE-26-14-0013
```

**Generate Serials:**
```
!batch serials LOTE-26-14-0013 50
```

**Transition Pipeline:**
```
!batch transition LOTE-26-14-0013 "Quality Check"
```

## Permissions

| Role | Allowed Commands |
|------|-----------------|
| Operator | create, status, list, serials |
| Inspector | approve, reject, validate |
| Manager | all commands |

## Notifications

Raven sends notifications for:
- Batch created
- Serials generated
- Status changed
- QC approval/rejection
- Error conditions

## Troubleshooting

### Common Issues

**"Batch not found"**
- Verify batch name spelling
- Check if batch exists in system

**"Permission denied"**
- User lacks required role
- Contact administrator

**"Invalid serial format"**
- Serial must follow: `TITLE-NNN`
- Check for invalid characters

## Support

For issues with Raven commands, contact: it-support@sysmayal.cloud
