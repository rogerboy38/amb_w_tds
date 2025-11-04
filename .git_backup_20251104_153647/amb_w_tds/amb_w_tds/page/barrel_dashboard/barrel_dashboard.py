import frappe

@frappe.whitelist()
def get_dashboard_data():
    """Get data for barrel dashboard"""
    try:
        # Barrel doctype exists - let's use it
        total_barrels = frappe.db.count('Barrel')
        
        # Get status-based counts using current_status field
        active_barrels = frappe.db.count('Barrel', filters={'current_status': 'Active'})
        available_barrels = frappe.db.count('Barrel', filters={'current_status': 'Available'})
        in_use_barrels = frappe.db.count('Barrel', filters={'current_status': 'In Use'})
        maintenance_barrels = frappe.db.count('Barrel', filters={'current_status': 'Maintenance'})
        reserved_barrels = frappe.db.count('Barrel', filters={'current_status': 'Reserved'})
        in_transit_barrels = frappe.db.count('Barrel', filters={'current_status': 'In Transit'})
        retired_barrels = frappe.db.count('Barrel', filters={'current_status': 'Retired'})
        
        # Get recent barrel records
        recent_barrels = frappe.get_all('Barrel',
                                      fields=['name', 'creation', 'current_status'],
                                      order_by='creation desc',
                                      limit=5)
        
        html_content = '<div class="recent-activities"><h4>Recent Barrels</h4><div class="activity-list">'
        
        if recent_barrels:
            for barrel in recent_barrels:
                barrel_name = barrel.get('name', 'Unknown')
                status = barrel.get('current_status', 'No Status')
                timestamp = barrel.get('creation', '')
                html_content += f'<div class="activity-item"><strong>{barrel_name}</strong> - {status} <small>{timestamp}</small></div>'
        else:
            html_content += '<p>No barrels found</p>'
        
        html_content += '</div></div>'
        
        return {
            'total_barrels': total_barrels,
            'active_barrels': active_barrels,
            'available_barrels': available_barrels,
            'in_use_barrels': in_use_barrels,
            'maintenance_barrels': maintenance_barrels,
            'reserved_barrels': reserved_barrels,
            'in_transit_barrels': in_transit_barrels,
            'retired_barrels': retired_barrels,
            'recent_activities': recent_barrels,
            'html': html_content
        }
    except Exception as e:
        frappe.log_error(f"Error in barrel dashboard: {str(e)}")
        return {
            'total_barrels': 0,
            'active_barrels': 0,
            'available_barrels': 0,
            'html': f'<p>Error loading barrel data: {str(e)}</p>'
        }
