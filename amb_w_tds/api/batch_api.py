# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime
import json


@frappe.whitelist()
def receive_weight(barrel_serial: str, gross_weight: float, device_id: str = None, timestamp: str = None):
    """
    API endpoint for IoT weight capture.
    POST /api/method/amb_w_tds.api.receive_weight
    
    Payload: {
        "barrel_serial": "BRL-2026-001",
        "gross_weight": 25.5,
        "device_id": "raspi-001",  (optional)
        "timestamp": "2026-04-02 12:00:00"  (optional)
    }
    
    Returns: {
        "success": true,
        "barrel_serial": "BRL-2026-001",
        "gross_weight": 25.5,
        "net_weight": 22.3,
        "validated": true,
        "batch": "LOTE-26-14-0002",
        "message": "Weight captured successfully"
    }
    """
    # Authentication check - verify API key/token
    auth_header = frappe.get_request_header("Authorization")
    if not auth_header:
        return {"success": False, "error": "Authentication required"}
    
    # TODO: Add proper API key validation against AMB W TDS Settings
    # For now, accept any valid token format (Bearer token)
    if not auth_header.startswith("Bearer "):
        return {"success": False, "error": "Invalid authentication format"}
    
    # Device validation - check device_id against allowed list
    allowed_devices = ["raspi-001", "raspi-002", "iot-scale-01", "iot-scale-02"]
    if device_id and device_id not in allowed_devices:
        frappe.throw(_("Device not authorized"), frappe.AuthenticationError)
    
    try:
        # Parse inputs
        barrel_serial = barrel_serial.strip() if barrel_serial else None
        gross_weight = float(gross_weight) if gross_weight else 0
        
        if not barrel_serial:
            return {"success": False, "error": "barrel_serial is required"}
        
        if gross_weight <= 0:
            return {"success": False, "error": "gross_weight must be positive"}
        
        # Find the batch and barrel
        batch = None
        barrel_row = None
        
        # Search in all Batch AMB documents
        batches = frappe.get_all(
            "Batch AMB",
            filters={"custom_batch_level": "3"},
            fields=["name", "title", "custom_golden_number"],
            limit=50
        )
        
        for b in batches:
            try:
                doc = frappe.get_doc("Batch AMB", b.name)
                if doc.container_barrels:
                    for row in doc.container_barrels:
                        if row.get('serial_number') == barrel_serial:
                            batch = doc
                            barrel_row = row
                            break
                if batch:
                    break
            except Exception:
                continue
        
        if not batch:
            return {
                "success": False,
                "error": f"Barrel serial '{barrel_serial}' not found in any batch"
            }
        
        # Get tara weight if not set
        if not barrel_row.get('tara_weight'):
            packaging = barrel_row.get('packaging_type')
            tara = 0
            if packaging:
                try:
                    if frappe.db.exists("Item", packaging):
                        item = frappe.get_doc("Item", packaging)
                        tara = float(item.standard_weight or 0)
                except Exception:
                    pass
            barrel_row.tara_weight = tara
        
        # Update weights
        barrel_row.gross_weight = gross_weight
        
        # Calculate net weight
        if barrel_row.tara_weight:
            barrel_row.net_weight = gross_weight - barrel_row.tara_weight
        else:
            barrel_row.net_weight = gross_weight
        
        # Validate weight
        min_weight = 0.1
        max_weight = 1000
        packaging = barrel_row.get('packaging_type')
        
        if packaging:
            try:
                if frappe.db.exists("Item", packaging):
                    item = frappe.get_doc("Item", packaging)
                    if item.standard_weight:
                        min_weight = item.standard_weight * 0.8
                        max_weight = item.standard_weight * 1.5
            except Exception:
                pass
        
        is_valid = min_weight <= barrel_row.net_weight <= max_weight
        barrel_row.weight_validated = is_valid
        
        # Save the batch
        batch.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Log the IoT reading if device_id provided
        if device_id:
            try:
                reading = frappe.get_doc({
                    "doctype": "IoT Sensor Reading",
                    "sensor_id": device_id,
                    "reading_type": "weight",
                    "value": gross_weight,
                    "unit": "kg",
                    "timestamp": get_datetime(timestamp) if timestamp else now_datetime(),
                    "batch_amb": batch.name
                })
                reading.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to log IoT reading: {str(e)}")
        
        # Format timestamp for response
        ts_str = timestamp or str(now_datetime())
        
        return {
            "success": True,
            "barrel_serial": barrel_serial,
            "gross_weight": gross_weight,
            "tara_weight": barrel_row.tara_weight or 0,
            "net_weight": barrel_row.net_weight,
            "validated": is_valid,
            "batch": batch.name,
            "batch_title": batch.title,
            "device_id": device_id,
            "timestamp": ts_str,
            "message": f"Weight received for {barrel_serial}: {gross_weight} kg (net: {barrel_row.net_weight} kg)"
        }
        
    except frappe.DoesNotExistError:
        return {"success": False, "error": f"Barrel serial '{barrel_serial}' not found"}
    except Exception as e:
        frappe.log_error(f"Error in receive_weight: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_running_batch_announcements(include_companies=True, include_plants=True, include_quality=True):
    """
    Get running batch announcements for widget display
    """
    try:
        # Get running batches
        batches = frappe.get_all(
            'Batch AMB',
            filters={
                'docstatus': ['!=', 2],  # Not cancelled
                'batch_status': ['in', ['Draft', 'In Progress', 'Running']]
            },
            fields=[
                'name', 'batch_number', 'item_to_manufacture', 'item_name',
                'batch_status', 'company', 'production_start_date', 
                'produced_qty', 'uom', 'modified', 'creation'
            ],
            order_by='modified desc',
            limit=50
        )
        
        if not batches:
            return {
                'success': True,
                'message': 'No active batches found',
                'announcements': [],
                'grouped_announcements': {},
                'stats': {'total': 0}
            }
        
        # Format announcements
        announcements = []
        grouped = {}
        stats = {
            'total': len(batches),
            'high_priority': 0,
            'quality_check': 0,
            'container_level': 0
        }
        
        for batch in batches:
            # Create announcement object
            announcement = {
                'name': batch.name,
                'title': batch.batch_number or batch.name,
                'batch_code': batch.batch_number,
                'item_code': batch.item_to_manufacture,
                'status': batch.batch_status,
                'company': batch.company or 'Unknown',
                'level': 'Batch',
                'priority': 'medium',
                'quality_status': 'Pending',
                'content': f"Item: {batch.item_name}\nQty: {batch.produced_qty or 0} {batch.uom or ''}",
                'message': f"Batch in progress",
                'modified': batch.modified,
                'creation': batch.creation
            }
            
            announcements.append(announcement)
            
            # Group by company and plant
            if include_companies:
                company = batch.company or 'Unknown'
                plant = '1'  # Default plant
                
                if company not in grouped:
                    grouped[company] = {}
                
                if plant not in grouped[company]:
                    grouped[company][plant] = []
                
                grouped[company][plant].append(announcement)
        
        return {
            'success': True,
            'announcements': announcements,
            'grouped_announcements': grouped,
            'stats': stats
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_running_batch_announcements: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load batch data'
        }
