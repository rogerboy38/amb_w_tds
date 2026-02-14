# Copyright (c) 2025, SPC Team and contributors
# Barrel Bulk Operations API

import frappe
from frappe import _
from frappe.utils import now_datetime, today
import json

@frappe.whitelist()
def bulk_transfer_barrels(barrel_names, to_location, transfer_date=None, reason=None):
    """Transfer multiple barrels to a new location"""
    
    if isinstance(barrel_names, str):
        barrel_names = json.loads(barrel_names)
    
    if not barrel_names:
        frappe.throw(_("No barrels selected"))
    
    if not to_location:
        frappe.throw(_("Target location is required"))
    
    transfer_date = transfer_date or today()
    
    results = {
        'success': [],
        'failed': []
    }
    
    for barrel_name in barrel_names:
        try:
            barrel = frappe.get_doc('Barrel', barrel_name)
            from_location = barrel.current_location
            
            barrel.current_location = to_location
            barrel.add_comment('Comment', f'Bulk transferred from {from_location} to {to_location}. Reason: {reason or "N/A"}')
            barrel.save(ignore_permissions=True)
            
            create_activity_log(
                barrel=barrel_name,
                activity_type='Transfer',
                description=f'Bulk transferred from {from_location} to {to_location}',
                from_location=from_location,
                to_location=to_location,
                activity_date=transfer_date,
                notes=reason
            )
            
            results['success'].append(barrel_name)
            
        except Exception as e:
            results['failed'].append({
                'barrel': barrel_name,
                'error': str(e)
            })
            frappe.log_error(f"Bulk transfer failed for {barrel_name}: {str(e)}")
    
    frappe.db.commit()
    
    message = _("Successfully transferred {0} barrel(s). {1} failed.").format(
        len(results['success']), 
        len(results['failed'])
    )
    
    return {
        'success': True,
        'message': message,
        'results': results
    }


@frappe.whitelist()
def bulk_update_status(barrel_names, new_status, reason=None):
    """Update status for multiple barrels"""
    
    if isinstance(barrel_names, str):
        barrel_names = json.loads(barrel_names)
    
    if not barrel_names:
        frappe.throw(_("No barrels selected"))
    
    if not new_status:
        frappe.throw(_("New status is required"))
    
    valid_statuses = ['Active', 'Available', 'In Use', 'Maintenance', 'Reserved', 'In Transit', 'Retired']
    if new_status not in valid_statuses:
        frappe.throw(_("Invalid status: {0}").format(new_status))
    
    results = {
        'success': [],
        'failed': []
    }
    
    for barrel_name in barrel_names:
        try:
            barrel = frappe.get_doc('Barrel', barrel_name)
            old_status = barrel.current_status
            
            barrel.current_status = new_status
            barrel.add_comment('Comment', f'Bulk status change from {old_status} to {new_status}. Reason: {reason or "N/A"}')
            barrel.save(ignore_permissions=True)
            
            create_activity_log(
                barrel=barrel_name,
                activity_type='Status Change',
                description=f'Status changed from {old_status} to {new_status}',
                activity_date=today(),
                notes=reason
            )
            
            results['success'].append(barrel_name)
            
        except Exception as e:
            results['failed'].append({
                'barrel': barrel_name,
                'error': str(e)
            })
            frappe.log_error(f"Bulk status update failed for {barrel_name}: {str(e)}")
    
    frappe.db.commit()
    
    message = _("Successfully updated {0} barrel(s). {1} failed.").format(
        len(results['success']), 
        len(results['failed'])
    )
    
    return {
        'success': True,
        'message': message,
        'results': results
    }


@frappe.whitelist()
def export_barrels(barrel_names, format='csv'):
    """Export barrel data in various formats"""
    
    if isinstance(barrel_names, str):
        barrel_names = json.loads(barrel_names)
    
    if not barrel_names:
        frappe.throw(_("No barrels selected"))
    
    barrels = frappe.get_all(
        'Barrel',
        filters={'name': ['in', barrel_names]},
        fields=[
            'name', 'barrel_code', 'barrel_type', 'barrel_volume_gallons',
            'current_status', 'current_location', 'current_fill_level_gallons',
            'available_volume_gallons', 'fill_percentage', 'owner',
            'creation', 'modified'
        ]
    )
    
    if format == 'csv':
        return export_to_csv(barrels)
    elif format == 'json':
        return json.dumps(barrels, indent=2, default=str)
    else:
        frappe.throw(_("Unsupported format: {0}").format(format))


def export_to_csv(barrels):
    """Convert barrel data to CSV format"""
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    headers = [
        'Barrel Code', 'Type', 'Volume (gal)', 'Status', 'Location',
        'Fill Level (gal)', 'Available (gal)', 'Fill %', 'Owner',
        'Created', 'Modified'
    ]
    writer.writerow(headers)
    
    for barrel in barrels:
        writer.writerow([
            barrel.get('barrel_code'),
            barrel.get('barrel_type'),
            barrel.get('barrel_volume_gallons'),
            barrel.get('current_status'),
            barrel.get('current_location'),
            barrel.get('current_fill_level_gallons'),
            barrel.get('available_volume_gallons'),
            barrel.get('fill_percentage'),
            barrel.get('owner'),
            barrel.get('creation'),
            barrel.get('modified')
        ])
    
    return output.getvalue()


def create_activity_log(barrel, activity_type, description, **kwargs):
    """Helper function to create activity log"""
    
    try:
        activity = frappe.get_doc({
            'doctype': 'Barrel Activity Log',
            'barrel': barrel,
            'activity_type': activity_type,
            'activity_date': kwargs.get('activity_date', today()),
            'description': description,
            'from_location': kwargs.get('from_location'),
            'to_location': kwargs.get('to_location'),
            'product': kwargs.get('product'),
            'quantity': kwargs.get('quantity'),
            'notes': kwargs.get('notes')
        })
        activity.insert(ignore_permissions=True)
        
    except Exception as e:
        frappe.log_error(f"Failed to create activity log: {str(e)}")
