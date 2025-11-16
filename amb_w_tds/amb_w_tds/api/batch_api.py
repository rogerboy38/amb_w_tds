"""
Batch API Methods for AMB W TDS
API endpoints for batch-related operations
"""

import frappe
from frappe import _

@frappe.whitelist()
def get_running_batch_announcements(include_companies=True):
    """
    Get running batch announcements for navbar widget
    """
    try:
        # Get announcements from Batch Announcement doctype
        announcements = frappe.get_all(
            'Batch Announcement',
            filters={
                'status': 'Running',
                'start_date': ['<=', frappe.utils.nowdate()],
                'end_date': ['>=', frappe.utils.nowdate()]
            },
            fields=['title', 'message', 'batch_reference', 'priority', 'company'],
            order_by='priority desc, creation desc'
        )
        
        # If include_companies is False, remove company field
        if not include_companies:
            for announcement in announcements:
                if 'company' in announcement:
                    del announcement['company']
        
        return announcements
        
    except Exception as e:
        frappe.log_error(f"Error in get_running_batch_announcements: {str(e)}")
        return []

@frappe.whitelist()
def get_batch_dashboard_data():
    """
    Get comprehensive batch data for dashboard
    """
    try:
        return {
            'total_batches': frappe.db.count('Batch AMB', {'docstatus': ['<', 2]}),
            'active_announcements': frappe.db.count('Batch Announcement', {'status': 'Running'}),
            'recent_batches': frappe.get_all('Batch AMB', 
                fields=['name', 'title', 'custom_batch_level', 'quality_status', 'creation'],
                order_by='creation desc',
                limit=5
            )
        }
    except Exception as e:
        frappe.log_error(f"Error in get_batch_dashboard_data: {str(e)}")
        return {}
