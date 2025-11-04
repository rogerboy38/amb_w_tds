# Copyright (c) 2025, SPC Team and contributors
# Barrel Management Dashboard

import frappe
from frappe import _

@frappe.whitelist()
def get_dashboard_data():
    """Get comprehensive dashboard data for barrel management"""
    
    data = {
        'summary': get_summary_stats(),
        'status_distribution': get_status_distribution(),
        'location_distribution': get_location_distribution(),
        'fill_level_analysis': get_fill_level_analysis(),
        'recent_activities': get_recent_activities(),
        'barrel_types': get_barrel_type_distribution(),
        'alerts': get_alerts()
    }
    
    return data

def get_summary_stats():
    """Get summary statistics"""
    
    total_barrels = frappe.db.count('Barrel')
    active_barrels = frappe.db.count('Barrel', {'current_status': 'Active'})
    available_barrels = frappe.db.count('Barrel', {'current_status': 'Available'})
    in_use_barrels = frappe.db.count('Barrel', {'current_status': 'In Use'})
    maintenance_barrels = frappe.db.count('Barrel', {'current_status': 'Maintenance'})
    
    total_capacity = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(barrel_volume_gallons), 0) as total_volume,
            COALESCE(SUM(current_fill_level_gallons), 0) as filled_volume,
            COALESCE(SUM(available_volume_gallons), 0) as available_volume
        FROM `tabBarrel`
        WHERE current_status != 'Retired'
    """, as_dict=True)[0]
    
    total_vol = total_capacity.get('total_volume', 0)
    filled_vol = total_capacity.get('filled_volume', 0)
    
    return {
        'total_barrels': total_barrels,
        'active_barrels': active_barrels,
        'available_barrels': available_barrels,
        'in_use_barrels': in_use_barrels,
        'maintenance_barrels': maintenance_barrels,
        'total_capacity': total_vol,
        'filled_volume': filled_vol,
        'available_volume': total_capacity.get('available_volume', 0),
        'capacity_utilization': round((filled_vol / total_vol * 100), 2) if total_vol > 0 else 0
    }

def get_status_distribution():
    """Get barrel count by status"""
    
    results = frappe.db.sql("""
        SELECT 
            current_status,
            COUNT(*) as count
        FROM `tabBarrel`
        GROUP BY current_status
        ORDER BY count DESC
    """, as_dict=True)
    
    return results

def get_location_distribution():
    """Get barrel count by location"""
    
    results = frappe.db.sql("""
        SELECT 
            current_location,
            COUNT(*) as count,
            SUM(barrel_volume_gallons) as total_capacity
        FROM `tabBarrel`
        WHERE current_location IS NOT NULL
        GROUP BY current_location
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)
    
    return results

def get_fill_level_analysis():
    """Analyze fill levels"""
    
    results = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN fill_percentage >= 80 THEN '80-100%'
                WHEN fill_percentage >= 60 THEN '60-80%'
                WHEN fill_percentage >= 40 THEN '40-60%'
                WHEN fill_percentage >= 20 THEN '20-40%'
                ELSE '0-20%'
            END as fill_range,
            COUNT(*) as count
        FROM `tabBarrel`
        WHERE current_status != 'Retired'
        GROUP BY fill_range
        ORDER BY fill_range DESC
    """, as_dict=True)
    
    return results

def get_recent_activities():
    """Get recent barrel activities"""
    
    activities = frappe.db.sql("""
        SELECT 
            name,
            barrel_code,
            current_status,
            current_location,
            modified,
            modified_by
        FROM `tabBarrel`
        ORDER BY modified DESC
        LIMIT 10
    """, as_dict=True)
    
    return activities

def get_barrel_type_distribution():
    """Get distribution by barrel type"""
    
    results = frappe.db.sql("""
        SELECT 
            barrel_type,
            COUNT(*) as count,
            SUM(barrel_volume_gallons) as total_capacity
        FROM `tabBarrel`
        WHERE barrel_type IS NOT NULL
        GROUP BY barrel_type
        ORDER BY count DESC
    """, as_dict=True)
    
    return results

def get_alerts():
    """Get system alerts"""
    
    alerts = []
    
    maintenance_due = frappe.db.count('Barrel', {'current_status': 'Maintenance'})
    
    if maintenance_due > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{maintenance_due} barrel(s) need maintenance',
            'action': 'View Maintenance Queue'
        })
    
    overfilled = frappe.db.count('Barrel', {'fill_percentage': ['>', 95]})
    
    if overfilled > 0:
        alerts.append({
            'type': 'danger',
            'message': f'{overfilled} barrel(s) are over 95% full',
            'action': 'View Over-filled Barrels'
        })
    
    empty_available = frappe.db.count('Barrel', {
        'current_status': 'Available',
        'current_fill_level_gallons': 0
    })
    
    if empty_available > 5:
        alerts.append({
            'type': 'info',
            'message': f'{empty_available} empty barrels available for use',
            'action': 'View Available Barrels'
        })
    
    return alerts
