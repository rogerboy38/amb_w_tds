import frappe

@frappe.whitelist()
def get_dashboard_data():
    """Get data for container barrels dashboard"""
    try:
        # Get data from Container Selection doctype
        total_containers = frappe.db.count('Container Selection')
        
        # Get container counts by sync_status (not status)
        new_containers = frappe.db.count('Container Selection', filters={'sync_status': 'New'})
        in_use_containers = frappe.db.count('Container Selection', filters={'sync_status': 'In Use'})
        empty_containers = frappe.db.count('Container Selection', filters={'sync_status': 'Empty'})
        cleaning_containers = frappe.db.count('Container Selection', filters={'sync_status': 'Cleaning'})
        ready_containers = frappe.db.count('Container Selection', filters={'sync_status': 'Ready for Reuse'})
        retired_containers = frappe.db.count('Container Selection', filters={'sync_status': 'Retired'})
        
        # Calculate active containers (all except retired)
        active_containers = total_containers - retired_containers
        
        # First, let's check what fields actually exist in Container Barrels
        container_barrels_fields = [f.fieldname for f in frappe.get_meta('Container Barrels').fields]
        print("Container Barrels fields:", container_barrels_fields)  # For debugging
        
        # Build fields list dynamically based on what exists
        fields_to_select = ['name', 'creation']
        
        # Add fields only if they exist
        possible_fields = [
            'barrel_serial_number', 'packaging_type', 'barcode_scan_input', 
            'scan_timestamp', 'status', 'gross_weight', 'tara_weight', 
            'net_weight', 'weight_validated', 'label', 'type'
        ]
        
        for field in possible_fields:
            if field in container_barrels_fields:
                fields_to_select.append(field)
        
        # Get Container Barrels data with only existing fields
        container_barrels_data = frappe.get_all('Container Barrels',
                                              fields=fields_to_select,
                                              order_by='creation desc',
                                              limit=20)
        
        # Calculate totals from Container Barrels
        total_barrels = len(container_barrels_data)
        total_gross_weight = 0
        total_net_weight = 0
        
        for barrel in container_barrels_data:
            if 'gross_weight' in container_barrels_fields:
                total_gross_weight += (barrel.get('gross_weight', 0) or 0)
            if 'net_weight' in container_barrels_fields:
                total_net_weight += (barrel.get('net_weight', 0) or 0)
        
        # Get status counts for Container Barrels
        barrels_by_status = {}
        for barrel in container_barrels_data:
            status = barrel.get('status', 'Unknown') if 'status' in container_barrels_fields else 'No Status'
            barrels_by_status[status] = barrels_by_status.get(status, 0) + 1
        
        # Get container status summary using sync_status
        container_status = frappe.db.sql("""
            SELECT sync_status as status, COUNT(*) as count
            FROM `tabContainer Selection`
            GROUP BY sync_status
        """, as_dict=True) or []
        
        # Get recent container selections
        recent_containers = frappe.get_all('Container Selection',
                                         fields=['name', 'creation', 'sync_status'],
                                         order_by='creation desc',
                                         limit=5)
        
        # Build HTML content
        html_content = '<div class="container-summary">'
        
        # Container Selection Status
        html_content += '<div class="status-section"><h4>Container Selection Status</h4><div class="status-list">'
        if container_status:
            for status in container_status:
                status_name = status.get('status', 'Unknown')
                count = status.get('count', 0)
                html_content += f'<div class="status-item"><strong>{status_name}:</strong> {count} containers</div>'
        else:
            html_content += '<p>No status data available</p>'
        html_content += '</div></div>'
        
        # Container Barrels Overview
        html_content += f'''
        <div class="barrels-overview-section">
            <h4>Container Barrels Overview</h4>
            <div class="overview-stats">
                <div class="overview-stat">
                    <strong>Total Barrels:</strong> {total_barrels}
                </div>
        '''
        
        if 'gross_weight' in container_barrels_fields:
            html_content += f'''
                <div class="overview-stat">
                    <strong>Total Gross Weight:</strong> {total_gross_weight:.2f} kg
                </div>
            '''
        
        if 'net_weight' in container_barrels_fields:
            html_content += f'''
                <div class="overview-stat">
                    <strong>Total Net Weight:</strong> {total_net_weight:.2f} kg
                </div>
            '''
        
        html_content += '</div>'
        
        # Container Barrels Status Breakdown
        if barrels_by_status:
            html_content += '<div class="barrels-status"><h5>Barrels by Status:</h5>'
            for status, count in barrels_by_status.items():
                html_content += f'<div class="status-item"><strong>{status}:</strong> {count} barrels</div>'
            html_content += '</div>'
        
        html_content += '</div>'
        
        # Container Barrels Detailed Table
        html_content += '''
        <div class="barrels-detail-section">
            <h4>Recent Container Barrels</h4>
            <div class="barrels-table-container">
                <table class="barrels-table">
                    <thead>
                        <tr>
        '''
        
        # Build table headers dynamically based on available fields
        headers = []
        if 'barrel_serial_number' in container_barrels_fields:
            headers.append('<th>Serial Number</th>')
        if 'packaging_type' in container_barrels_fields:
            headers.append('<th>Packaging Type</th>')
        if 'status' in container_barrels_fields:
            headers.append('<th>Status</th>')
        if 'gross_weight' in container_barrels_fields:
            headers.append('<th>Gross Weight</th>')
        if 'net_weight' in container_barrels_fields:
            headers.append('<th>Net Weight</th>')
        if 'weight_validated' in container_barrels_fields:
            headers.append('<th>Weight Validated</th>')
        if 'label' in container_barrels_fields:
            headers.append('<th>Label</th>')
        if 'type' in container_barrels_fields:
            headers.append('<th>Type</th>')
        headers.append('<th>Created</th>')
        
        html_content += ''.join(headers) + '</tr></thead><tbody>'
        
        if container_barrels_data:
            for barrel in container_barrels_data:
                html_content += '<tr>'
                
                if 'barrel_serial_number' in container_barrels_fields:
                    serial = barrel.get('barrel_serial_number', 'N/A')
                    html_content += f'<td>{serial}</td>'
                
                if 'packaging_type' in container_barrels_fields:
                    packaging = barrel.get('packaging_type', 'N/A')
                    html_content += f'<td>{packaging}</td>'
                
                if 'status' in container_barrels_fields:
                    status = barrel.get('status', 'N/A')
                    html_content += f'<td>{status}</td>'
                
                if 'gross_weight' in container_barrels_fields:
                    gross = barrel.get('gross_weight', 0) or 0
                    html_content += f'<td>{gross:.2f} kg</td>'
                
                if 'net_weight' in container_barrels_fields:
                    net = barrel.get('net_weight', 0) or 0
                    html_content += f'<td>{net:.2f} kg</td>'
                
                if 'weight_validated' in container_barrels_fields:
                    validated = 'Yes' if barrel.get('weight_validated') else 'No'
                    html_content += f'<td>{validated}</td>'
                
                if 'label' in container_barrels_fields:
                    label = barrel.get('label', 'N/A')
                    html_content += f'<td>{label}</td>'
                
                if 'type' in container_barrels_fields:
                    barrel_type = barrel.get('type', 'N/A')
                    html_content += f'<td>{barrel_type}</td>'
                
                created = barrel.get('creation', 'N/A')
                html_content += f'<td>{created}</td>'
                
                html_content += '</tr>'
        else:
            colspan = len(headers)
            html_content += f'<tr><td colspan="{colspan}" style="text-align: center;">No container barrels data found</td></tr>'
        
        html_content += '''
                    </tbody>
                </table>
            </div>
        </div>
        '''
        
        # Recent Container Selections
        html_content += '<div class="recent-containers-section"><h4>Recent Container Selections</h4><div class="recent-list">'
        if recent_containers:
            for container in recent_containers:
                container_name = container.get('name', 'Unknown')
                status = container.get('sync_status', 'No Status')
                timestamp = container.get('creation', '')
                html_content += f'<div class="recent-item"><strong>{container_name}</strong> - {status} <small>{timestamp}</small></div>'
        else:
            html_content += '<p>No container selections found</p>'
        
        html_content += '</div></div></div>'
        
        return {
            'total_containers': total_containers,
            'active_containers': active_containers,
            'new_containers': new_containers,
            'in_use_containers': in_use_containers,
            'empty_containers': empty_containers,
            'cleaning_containers': cleaning_containers,
            'ready_containers': ready_containers,
            'retired_containers': retired_containers,
            'total_barrels': total_barrels,
            'total_gross_weight': total_gross_weight,
            'total_net_weight': total_net_weight,
            'container_status': container_status,
            'container_barrels_data': container_barrels_data,
            'barrels_by_status': barrels_by_status,
            'html': html_content
        }
    except Exception as e:
        frappe.log_error(f"Error in container barrels dashboard: {str(e)}")
        return {
            'total_containers': 0,
            'active_containers': 0,
            'total_barrels': 0,
            'html': f'<p>Error loading container data: {str(e)}</p>'
        }
