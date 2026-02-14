# Copyright (c) 2025, SPC Team and contributors
# Container Barrels Dashboard - Simplified for existing fields

import frappe
from frappe import _

@frappe.whitelist()
def get_dashboard_data():
    """Get dashboard data for container barrels"""
    
    data = {
        'summary': get_summary_stats(),
        'status_distribution': get_status_distribution(),
        'packaging_types': get_packaging_type_distribution(),
        'recent_activities': get_recent_activities(),
        'batch_distribution': get_batch_distribution(),
        'alerts': get_alerts()
    }
    
    return data

def get_summary_stats():
    """Get summary statistics"""
    
    total_barrels = frappe.db.count('Container Barrels')
    new_barrels = frappe.db.count('Container Barrels', {'status': 'New'})
    
    # Get all status counts
    status_counts = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabContainer Barrels`
        GROUP BY status
    """, as_dict=True)
    
    status_map = {s['status']: s['count'] for s in status_counts}
    
    # Weight statistics
    weight_stats = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(gross_weight), 0) as total_gross,
            COALESCE(SUM(net_weight), 0) as total_net,
            COALESCE(AVG(net_weight), 0) as avg_net,
            COUNT(*) as weighted_count
        FROM `tabContainer Barrels`
        WHERE net_weight > 0
    """, as_dict=True)[0]
    
    # Count validated barrels
    validated_count = frappe.db.count('Container Barrels', {'weight_validated': 1})
    unvalidated_count = total_barrels - validated_count
    
    return {
        'total_barrels': total_barrels,
        'new_barrels': new_barrels,
        'status_counts': status_map,
        'total_gross_weight': round(weight_stats.get('total_gross', 0), 2),
        'total_net_weight': round(weight_stats.get('total_net', 0), 2),
        'avg_net_weight': round(weight_stats.get('avg_net', 0), 2),
        'validated_count': validated_count,
        'unvalidated_count': unvalidated_count
    }

def get_status_distribution():
    """Get barrel count by status"""
    
    results = frappe.db.sql("""
        SELECT 
            COALESCE(status, 'No Status') as status,
            COUNT(*) as count
        FROM `tabContainer Barrels`
        GROUP BY status
        ORDER BY count DESC
    """, as_dict=True)
    
    return results

def get_packaging_type_distribution():
    """Get distribution by packaging type"""
    
    results = frappe.db.sql("""
        SELECT 
            COALESCE(packaging_type, 'Not Set') as packaging_type,
            COUNT(*) as count,
            ROUND(AVG(net_weight), 2) as avg_weight
        FROM `tabContainer Barrels`
        GROUP BY packaging_type
        ORDER BY count DESC
    """, as_dict=True)
    
    return results

def get_recent_activities():
    """Get recently modified barrels"""
    
    activities = frappe.db.sql("""
        SELECT 
            name,
            barrel_serial_number,
            status,
            packaging_type,
            net_weight,
            weight_validated,
            modified,
            modified_by,
            parent
        FROM `tabContainer Barrels`
        ORDER BY modified DESC
        LIMIT 10
    """, as_dict=True)
    
    return activities

def get_batch_distribution():
    """Get barrels per batch"""
    
    results = frappe.db.sql("""
        SELECT 
            parent as batch,
            COUNT(*) as barrel_count,
            SUM(net_weight) as total_weight,
            COUNT(CASE WHEN weight_validated = 1 THEN 1 END) as validated_count
        FROM `tabContainer Barrels`
        GROUP BY parent
        ORDER BY barrel_count DESC
        LIMIT 10
    """, as_dict=True)
    
    return results

def get_alerts():
    """Get system alerts"""
    
    alerts = []
    
    # Check for unvalidated weights
    unvalidated = frappe.db.count('Container Barrels', {'weight_validated': 0})
    
    if unvalidated > 5:
        alerts.append({
            'type': 'warning',
            'message': f'{unvalidated} barrel(s) need weight validation'
        })
    
    # Check for missing weights
    missing_weight = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabContainer Barrels`
        WHERE net_weight IS NULL OR net_weight = 0
    """)[0][0]
    
    if missing_weight > 0:
        alerts.append({
            'type': 'info',
            'message': f'{missing_weight} barrel(s) missing weight data'
        })
    
    # Check for missing serial numbers
    missing_serial = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabContainer Barrels`
        WHERE barrel_serial_number IS NULL OR barrel_serial_number = ''
    """)[0][0]
    
    if missing_serial > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{missing_serial} barrel(s) missing serial numbers'
        })
    
    return alerts
