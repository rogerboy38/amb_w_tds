"""
Container API - Comprehensive container management endpoints
Handles barcode scanning, weight calculations, sync operations, and mobile interface
"""

import frappe
from frappe import _
from frappe.utils import now, flt
import json

# Barcode and Scanner APIs
@frappe.whitelist()
def scan_barcode(barcode, plant=None):
    """Enhanced barcode scanning with plant-specific validation"""
    try:
        # Find container by barcode/serial number
        containers = frappe.get_all(
            'Container Selection',
            filters={'serial_number': barcode},
            fields=['name', 'container_type', 'lifecycle_status', 'gross_weight', 'net_weight', 'plant', 'batch_amb_link']
        )
        
        if not containers:
            return {
                'success': False,
                'message': f'Container not found with barcode: {barcode}'
            }
        
        container = containers[0]
        
        # Validate plant if specified
        if plant and container.plant != plant:
            return {
                'success': False,
                'message': f'Container belongs to {container.plant} plant, not {plant}'
            }
        
        # Update scan timestamp and user
        frappe.db.set_value('Container Selection', container.name, {
            'barcode_scanned_at': now(),
            'scanned_by': frappe.session.user
        }, update_modified=False)
        
        # Get additional container details
        container_doc = frappe.get_doc('Container Selection', container.name)
        
        return {
            'success': True,
            'container': {
                'name': container.name,
                'container_type': container.container_type,
                'lifecycle_status': container.lifecycle_status,
                'gross_weight': container.gross_weight,
                'net_weight': container.net_weight,
                'tara_weight': container_doc.tara_weight,
                'expected_weight': container_doc.expected_weight,
                'plant': container.plant,
                'batch_amb_link': container.batch_amb_link,
                'sync_status': container_doc.sync_status,
                'is_partial_fill': container_doc.is_partial_fill,
                'fill_percentage': container_doc.fill_percentage
            },
            'message': 'Container found and scan recorded'
        }
        
    except Exception as e:
        frappe.log_error(f"Barcode scan error: {str(e)}", "Container API - Barcode Scan")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def batch_scan_barcodes(barcodes, plant=None):
    """Scan multiple barcodes in batch"""
    try:
        barcodes_list = json.loads(barcodes) if isinstance(barcodes, str) else barcodes
        results = []
        
        for barcode in barcodes_list:
            result = scan_barcode(barcode, plant)
            results.append({
                'barcode': barcode,
                'result': result
            })
        
        successful_scans = len([r for r in results if r['result']['success']])
        
        return {
            'success': True,
            'total_scanned': len(barcodes_list),
            'successful_scans': successful_scans,
            'failed_scans': len(barcodes_list) - successful_scans,
            'results': results
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Weight Calculation APIs
@frappe.whitelist()
def calculate_weights(container_name, gross_weight):
    """Calculate weights with enhanced validation"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        container.gross_weight = flt(gross_weight, 3)
        
        # Use WeightTracker class for advanced calculations
        from amb_w_tds.doctype.container_selection.container_selection import WeightTracker
        tracker = WeightTracker(container)
        result = tracker.calculate_net_weight()
        
        if result['success']:
            # Update container with calculated values
            container.net_weight = result['net_weight']
            container.weight_variance_percentage = result.get('variance_percent', 0)
            container.is_within_tolerance = 1 if result.get('is_valid', True) else 0
            container.save()
            
            return {
                'success': True,
                'net_weight': result['net_weight'],
                'tara_weight': result['tara_weight'],
                'gross_weight': result['gross_weight'],
                'expected_weight': result.get('expected_weight'),
                'variance_percentage': result.get('variance_percent', 0),
                'is_within_tolerance': result.get('is_valid', True),
                'tolerance_check': result.get('tolerance_check', 'N/A')
            }
        else:
            return result
            
    except Exception as e:
        frappe.log_error(f"Weight calculation error: {str(e)}", "Container API - Weight Calculation")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def auto_calculate_tara_weight(container_name):
    """Auto-calculate tara weight from Item master or plant configuration"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        
        # Try to get tara weight from plant configuration first
        if container.plant:
            try:
                plant_config = frappe.get_doc('Plant Configuration', container.plant)
                tara_weight = plant_config.get_tara_weight(container.container_type)
                if tara_weight > 0:
                    container.tara_weight = tara_weight
                    container.save()
                    return {
                        'success': True,
                        'tara_weight': tara_weight,
                        'source': 'Plant Configuration'
                    }
            except:
                pass
        
        # Fallback to Item master
        container.set_tara_weight_from_item()
        container.save()
        
        return {
            'success': True,
            'tara_weight': container.tara_weight,
            'source': 'Item Master'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Container Assignment and Status APIs
@frappe.whitelist()
def assign_to_batch(container_name, batch_amb_name):
    """Assign container to Batch AMB with validation"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        
        # Validate container is available for assignment
        if container.lifecycle_status not in ['Available', 'Planned']:
            return {
                'success': False,
                'error': f'Container status is {container.lifecycle_status}, cannot assign'
            }
        
        # Validate batch exists and is active
        try:
            batch = frappe.get_doc('Batch AMB', batch_amb_name)
            if batch.status == 'Completed':
                return {
                    'success': False,
                    'error': 'Cannot assign to completed batch'
                }
        except frappe.DoesNotExistError:
            return {
                'success': False,
                'error': f'Batch {batch_amb_name} not found'
            }
        
        # Assign container
        container.batch_amb_link = batch_amb_name
        container.lifecycle_status = 'Reserved'
        container.reserved_date = now()
        container.sync_status = 'Pending'
        container.save()
        
        # Trigger sync
        container.trigger_sync()
        
        return {
            'success': True,
            'message': f'Container assigned to batch {batch_amb_name}',
            'new_status': 'Reserved'
        }
        
    except Exception as e:
        frappe.log_error(f"Container assignment error: {str(e)}", "Container API - Assignment")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def update_status(container_name, new_status, notes=None):
    """Update container lifecycle status with validation"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        old_status = container.lifecycle_status
        
        # Validate status transition
        container.lifecycle_status = new_status
        container.validate_lifecycle_transition()
        
        # Set appropriate date fields
        if new_status == 'Reserved' and not container.reserved_date:
            container.reserved_date = now()
        elif new_status == 'Completed' and not container.completed_date:
            container.completed_date = now()
        
        # Add notes if provided
        if notes:
            container.notes = (container.notes or '') + f"\n{now()}: {notes}"
        
        # Update sync status if linked to batch
        if container.batch_amb_link:
            container.sync_status = 'Pending'
        
        container.save()
        
        # Trigger sync if needed
        if container.batch_amb_link:
            container.trigger_sync()
        
        return {
            'success': True,
            'message': f'Status updated from {old_status} to {new_status}',
            'old_status': old_status,
            'new_status': new_status
        }
        
    except Exception as e:
        frappe.log_error(f"Status update error: {str(e)}", "Container API - Status Update")
        return {'success': False, 'error': str(e)}

# Container Search and Availability APIs
@frappe.whitelist()
def get_available_containers(plant=None, container_type=None, limit=50):
    """Get available containers with filtering"""
    try:
        filters = {'lifecycle_status': 'Available'}
        
        if plant:
            filters['plant'] = plant
        if container_type:
            filters['container_type'] = container_type
        
        containers = frappe.get_all(
            'Container Selection',
            filters=filters,
            fields=[
                'name', 'container_id', 'serial_number', 'container_type', 
                'net_weight', 'last_synced', 'sync_status', 'plant',
                'quality_check_status', 'is_partial_fill'
            ],
            order_by='creation desc',
            limit=limit
        )
        
        return {'success': True, 'containers': containers, 'count': len(containers)}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def search_containers(search_term, filters=None):
    """Search containers by various criteria"""
    try:
        # Build search filters
        search_filters = []
        
        if search_term:
            search_filters.extend([
                ['container_id', 'like', f'%{search_term}%'],
                ['serial_number', 'like', f'%{search_term}%'],
                ['batch_amb_link', 'like', f'%{search_term}%']
            ])
        
        # Add additional filters
        additional_filters = {}
        if filters:
            additional_filters = json.loads(filters) if isinstance(filters, str) else filters
        
        # Combine filters with OR logic for search terms
        if search_filters:
            base_query = frappe.qb.from_('Container Selection')
            for key, value in additional_filters.items():
                base_query = base_query.where(frappe.qb.Field(key) == value)
            
            # Apply search term with OR logic
            or_conditions = None
            for field, operator, value in search_filters:
                condition = frappe.qb.Field(field).like(value)
                or_conditions = condition if or_conditions is None else or_conditions | condition
            
            if or_conditions is not None:
                base_query = base_query.where(or_conditions)
            
            containers = base_query.select('*').limit(100).run(as_dict=True)
        else:
            containers = frappe.get_all(
                'Container Selection',
                filters=additional_filters,
                fields=['*'],
                limit=100
            )
        
        return {'success': True, 'containers': containers, 'count': len(containers)}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Sync Operations
@frappe.whitelist()
def manual_sync(container_name):
    """Manually trigger container sync"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        
        if not container.batch_amb_link:
            return {
                'success': False,
                'error': 'No batch AMB linked to this container'
            }
        
        # Use ContainerSyncEngine for sync
        from amb_w_tds.doctype.container_selection.container_selection import ContainerSyncEngine
        sync_engine = ContainerSyncEngine(container)
        result = sync_engine.execute_sync()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Manual sync error: {str(e)}", "Container API - Manual Sync")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def retry_failed_sync(sync_log_name, container_name):
    """Retry a failed sync operation"""
    try:
        # Update sync log status
        frappe.db.set_value('Container Sync Log', sync_log_name, 'sync_status', 'Retrying')
        
        # Trigger manual sync
        result = manual_sync(container_name)
        
        if result['success']:
            # Update sync log with success
            frappe.db.set_value('Container Sync Log', sync_log_name, {
                'sync_status': 'Success',
                'error_message': None
            })
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Reporting and Analytics
@frappe.whitelist()
def get_container_summary(plant=None, date_range=None):
    """Get container usage summary"""
    try:
        filters = {}
        if plant:
            filters['plant'] = plant
        
        # Get status distribution
        status_summary = frappe.db.sql("""
            SELECT lifecycle_status, COUNT(*) as count
            FROM `tabContainer Selection`
            WHERE {where_clause}
            GROUP BY lifecycle_status
        """.format(
            where_clause="plant = %(plant)s" if plant else "1=1"
        ), filters, as_dict=True)
        
        # Get sync status distribution
        sync_summary = frappe.db.sql("""
            SELECT sync_status, COUNT(*) as count
            FROM `tabContainer Selection`
            WHERE {where_clause}
            GROUP BY sync_status
        """.format(
            where_clause="plant = %(plant)s" if plant else "1=1"
        ), filters, as_dict=True)
        
        # Get total counts
        total_containers = frappe.db.count('Container Selection', filters)
        available_containers = frappe.db.count('Container Selection', 
                                              dict(filters, lifecycle_status='Available'))
        
        return {
            'success': True,
            'total_containers': total_containers,
            'available_containers': available_containers,
            'status_distribution': status_summary,
            'sync_distribution': sync_summary
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_sync_log(container_name, limit=20):
    """Get sync log for container"""
    try:
        from amb_w_tds.doctype.container_sync_log.container_sync_log import get_sync_history
        return get_sync_history(container_name, limit)
        
    except Exception as e:
        return {'success': False, 'error': str(e)}