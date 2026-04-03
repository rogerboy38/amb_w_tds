# API Reference - bot_iot for Batch AMB

## Overview
This document describes the API integration for IoT devices to interact with the Batch AMB system.

## Base Configuration

| Parameter | Value |
|-----------|-------|
| Endpoint | `https://v2.sysmayal.cloud/api/method/amb_w_tds.doctype.batch_amb.batch_amb` |
| Authentication | API Key via Header |
| Format | JSON |

## Authentication

Include your API key in the request header:

```
Authorization: token <api_key>
```

## Available Methods

### 1. generate_serial_numbers

Generate serial numbers for a batch container.

**Endpoint:** `amb_w_tds.doctype.batch_amb.batch_amb.generate_serial_numbers`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| batch_name | String | Yes | Batch AMB document name |
| quantity | Integer | Yes | Number of serials to generate |
| prefix | String | No | Custom prefix for serials |

**Request Example:**
```json
{
    "batch_name": "LOTE-26-14-0013",
    "quantity": 10
}
```

**Response Example:**
```json
{
    "status": "success",
    "count": 10,
    "serial_numbers": [
        "JAR0001261-1-C1-001",
        "JAR0001261-1-C1-002",
        "...",
        "JAR0001261-1-C1-010"
    ]
}
```

**Error Responses:**
```json
{
    "status": "error",
    "message": "No permission to modify Batch AMB"
}
```

### 2. update_batch_status

Update the pipeline status of a batch.

**Endpoint:** `amb_w_tds.doctype.batch_amb.batch_amb.update_batch_status`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| batch_name | String | Yes | Batch AMB document name |
| status | String | Yes | New pipeline status |

**Valid Status Values:**
- `Draft`
- `WO Linked`
- `In Progress`
- `Quality Check`
- `Completed`
- `Cancelled`

**Request Example:**
```json
{
    "batch_name": "LOTE-26-14-0013",
    "status": "In Progress"
}
```

### 3. sync_with_lote_amb

Synchronize batch data with Lote AMB records.

**Endpoint:** `amb_w_tds.doctype.batch_amb.batch_amb.sync_with_lote_amb`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| batch_name | String | Yes | Batch AMB document name |

**Request Example:**
```json
{
    "batch_name": "LOTE-26-14-0013"
}
```

### 4. get_batch_details

Retrieve batch information including hierarchy and serials.

**Endpoint:** `amb_w_tds.doctype.batch_amb.batch_amb.get_batch_details`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| batch_name | String | Yes | Batch AMB document name |

**Response Example:**
```json
{
    "name": "LOTE-26-14-0013",
    "title": "JAR0001261-1-C1",
    "custom_batch_level": "3",
    "parent_batch_amb": "LOTE-26-14-0012",
    "item_to_manufacture": "JAR020",
    "pipeline_status": "Draft",
    "container_barrels": [
        {
            "barrel_serial_number": "JAR0001261-1-C1-001",
            "status": "New",
            "gross_weight": 25.5,
            "tara_weight": 2.5,
            "net_weight": 23.0
        }
    ]
}
```

## IoT Device Integration

### Connection Flow

1. **Register Device**: Obtain API key from administrator
2. **Configure Endpoint**: Set server URL in IoT device
3. **Test Connection**: Validate authentication
4. **Send Data**: Push serial/weight data

### Best Practices

- Use HTTPS for all connections
- Implement retry logic for failed requests
- Log all API transactions
- Validate data before sending

### Error Handling

| Error Code | Description | Action |
|------------|-------------|--------|
| 401 | Invalid API key | Verify credentials |
| 403 | Permission denied | Check API permissions |
| 404 | Batch not found | Verify batch name |
| 500 | Server error | Retry later |

## Webhook Support

For real-time updates, configure webhooks for:
- `batch_created`
- `batch_updated`
- `serials_generated`
- `status_changed`

## Rate Limits

- Standard: 100 requests/minute
- Burst: 200 requests/minute

## Support

For API issues, contact: support@sysmayal.cloud
