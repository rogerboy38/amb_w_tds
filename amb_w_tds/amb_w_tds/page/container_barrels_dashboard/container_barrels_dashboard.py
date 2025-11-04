# Copyright (c) 2025, SPC Team and contributors
# Container Barrels Dashboard

import frappe
from frappe import _

@frappe.whitelist()
def get_dashboard_data():
    """Get comprehensive dashboard data for container barrels"""
    
    data = {
        'summary': get_summary_stats(),
        'status_distribution': get_status_distribution(),
        'location_distribution': get_location_distribution(),
        'usage_analysis': get_usage_analysis(),
        'recent_activities': get_recent_activities(),
        'packaging_types': get_packaging_type_distribution(),
        'alerts': get_alerts(),
        'batch_distribution': get_batch_distribution()
    }
    
    return data

def get_summary_stats():
    """Get summary statistics"""
    
    total_barrels = frappe.db.count('Container Barrels')
    new_barrels = frappe.db.count('Container Barrels', {'status': 'New'})
    in_use_barrels = frappe.db.count('Container Barrels', {'status': 'In Use'})
    available_barrels = frappe.db.count('Container Barrels', {'status': 'Available'})
    maintenance_barrels = frappe.db.count('Container Barrels', {'status': 'Maintenance'})
    retired_barrels = frappe.db.count('Container Barrels', {'status': 'Retired'})
    
    # Usage statistics
    usage_stats = frappe.db.sql("""
        SELECT 
            COALESCE(AVG(usage_count), 0) as avg_usage,
            COALESCE(MAX(usage_count), 0) as max_usage,
            COALESCE(SUM(total_fill_cycles), 0) as total_fills,
            COALESCE(SUM(total_empty_cycles), 0) as total_empties
        FROM `tabContainer Barrels`
    """, as_dict=True)[0]
    
    # Weight statistics
    weight_stats = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(net_weight), 0) as total_net_weight,
            COALESCE(AVG(net_weight), 0) as avg_net_weight
        FROM `tabContainer Barrels`
        WHERE net_weight > 0
    """, as_dict=True)[0]
    
    return {
        'total_barrels': total_barrels,
        'new_barrels': new_barrels,
        'in_use_barrels': in_use_barrels,
        'available_barrels': available_barrels,
        'maintenance_barrels': maintenance_barrels,
        'retired_barrels': retired_barrels,
        'avg_usage': round(usage_stats.get('avg_usage', 0), 2),
        'max_usage': usage_stats.get('max_usage', 0),
        'total_fill_cycles': usage_stats.get('total_fills', 0),
        'total_empty_cycles': usage_stats.get('total_empties', 0),
        'total_net_weight': round(weight_stats.get('total_net_weight', 0), 2),
        'avg_net_weight': round(weight_stats.get('avg_net_weight', 0), 2)
    }

def get_status_distribution():
    """Get barrel count by status"""
    
    results = frappe.db.sql("""
        SELECT 
            status,
            COUNT(*) as count
        FROM `tabContainer Barrels`
        GROUP BY status
        ORDER BY count DESC
    """, as_dict=True)
    
    return results

def get_location_distribution():
    """Get barrel count by location"""
    
    results = frappe.db.sql("""
        SELECT 
            COALESCE(current_warehouse, 'Not Set') as location,
            COUNT(*) as count
        FROM `tabContainer Barrels`
        GROUP BY current_warehouse
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)
    
    return results

def get_usage_analysis():
    """Analyze usage patterns"""
    
    results = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN usage_count >= 8 THEN '80-100%'
                WHEN usage_count >= 6 THEN '60-80%'
                WHEN usage_count >= 4 THEN '40-60%'
                WHEN usage_count >= 2 THEN '20-40%'
                ELSE '0-20%'
            END as usage_range,
            COUNT(*) as count
        FROM `tabContainer Barrels`
        WHERE max_reuse_count > 0
        GROUP BY usage_range
        ORDER BY usage_range DESC
    """, as_dict=True)
    
    return results

def get_recent_activities():
    """Get recently modified barrels"""
    
    activities = frappe.db.sql("""
        SELECT 
            name,
            barrel_serial_number,
            status,
            current_warehouse,
            modified,
            modified_by,
            parent
        FROM `tabContainer Barrels`
        ORDER BY modified DESC
        LIMIT 10
    """, as_dict=True)
    
    return activities

def get_packaging_type_distribution():
    """Get distribution by packaging type"""
    
    results = frappe.db.sql("""
        SELECT 
            COALESCE(packaging_type, 'Not Set') as packaging_type,
            COUNT(*) as count
        FROM `tabContainer Barrels`
        GROUP BY packaging_type
        ORDER BY count DESC
    """, as_dict=True)
    
    return results

def get_batch_distribution():
    """Get barrels per batch"""
    
    results = frappe.db.sql("""
        SELECT 
            parent as batch,
            COUNT(*) as barrel_count
        FROM `tabContainer Barrels`
        GROUP BY parent
        ORDER BY barrel_count DESC
        LIMIT 10
    """, as_dict=True)
    
    return results

def get_alerts():
    """Get system alerts"""
    
    alerts = []
    
    # Check for high usage barrels
    high_usage = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabContainer Barrels`
        WHERE usage_count >= max_reuse_count * 0.9
        AND max_reuse_count > 0
    """)[0][0]
    
    if high_usage > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{high_usage} barrel(s) approaching max reuse limit',
            'action': 'Review High Usage Barrels'
        })
    
    # Check for maintenance needed
    maintenance_due = frappe.db.count('Container Barrels', {'status': 'Maintenance'})
    
    if maintenance_due > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{maintenance_due} barrel(s) need maintenance',
            'action': 'View Maintenance Queue'
        })
    
    # Check for unweighted barrels
    unweighted = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabContainer Barrels`
        WHERE weight_validated = 0
        OR net_weight IS NULL
        OR net_weight = 0
    """)[0][0]
    
    if unweighted > 5:
        alerts.append({
            'type': 'info',
            'message': f'{unweighted} barrel(s) need weight validation',
            'action': 'Validate Weights'
        })
    
    return alerts
