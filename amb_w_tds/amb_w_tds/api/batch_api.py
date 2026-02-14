# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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
