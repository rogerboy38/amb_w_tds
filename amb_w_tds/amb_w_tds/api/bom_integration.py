"""
BOM Integration API - Bill of Materials integration for container validation
Validates expected containers from production data and BOM specifications
"""

import frappe
from frappe import _
from frappe.utils import flt
import json

# BOM Container Validation APIs
@frappe.whitelist()
def get_bom_containers(bom_name, qty=1):
    """Get expected containers from BOM"""
    try:
        # Get BOM document
        bom = frappe.get_doc('BOM', bom_name)
        
        containers = []
        
        # Scan BOM items for containers
        for item in bom.items:
            # Check if item is a container type
            item_doc = frappe.get_doc('Item', item.item_code)
            
            # Check item groups that might indicate containers
            container_groups = ['Containers', 'Packaging', 'Barrels', 'Bottles', 'Bags', 'Pails']
            is_container = False
            
            if item_doc.item_group in container_groups:
                is_container = True
            elif any(keyword in item_doc.item_name.lower() for keyword in ['barrel', 'container', 'bottle', 'bag', 'pail', 'ibc']):
                is_container = True
            
            if is_container:
                required_qty = item.qty * qty
                
                containers.append({
                    'item_code': item.item_code,
                    'item_name': item_doc.item_name,
                    'item_group': item_doc.item_group,
                    'required_qty': required_qty,
                    'unit': item.uom,
                    'rate': item.rate,
                    'amount': item.amount * qty,
                    'description': item_doc.description
                })
        
        return {
            'success': True,
            'bom_name': bom_name,
            'production_qty': qty,
            'containers': containers,
            'total_container_cost': sum(c['amount'] for c in containers)
        }
        
    except frappe.DoesNotExistError:
        return {'success': False, 'error': f'BOM {bom_name} not found'}
    except Exception as e:
        frappe.log_error(f"BOM container fetch error: {str(e)}", "BOM Integration API")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def validate_batch_containers(batch_amb_name, bom_name=None):
    """Validate containers assigned to batch against BOM requirements"""
    try:
        # Get batch document
        batch = frappe.get_doc('Batch AMB', batch_amb_name)
        
        # Get BOM if not provided
        if not bom_name:
            # Try to find BOM from batch item or work order
            if hasattr(batch, 'bom'):
                bom_name = batch.bom
            elif hasattr(batch, 'item'):
                # Find default BOM for item
                bom_list = frappe.get_all('BOM', 
                    filters={'item': batch.item, 'is_default': 1, 'is_active': 1},
                    fields=['name'])
                if bom_list:
                    bom_name = bom_list[0].name
        
        if not bom_name:
            return {
                'success': False,
                'error': 'No BOM found for batch validation'
            }
        
        # Get BOM container requirements
        production_qty = getattr(batch, 'qty', 1) or 1
        bom_result = get_bom_containers(bom_name, production_qty)
        
        if not bom_result['success']:
            return bom_result
        
        expected_containers = bom_result['containers']
        
        # Get assigned containers from batch
        assigned_containers = []
        if hasattr(batch, 'container_barrels'):
            for barrel in batch.container_barrels:
                assigned_containers.append({
                    'container_type': barrel.container_type,
                    'serial_number': barrel.serial_number,
                    'status': barrel.status,
                    'net_weight': barrel.net_weight
                })
        
        # Validate container assignments
        validation_result = {
            'bom_name': bom_name,
            'batch_name': batch_amb_name,
            'production_qty': production_qty,
            'expected_containers': expected_containers,
            'assigned_containers': assigned_containers,
            'validation_summary': {},
            'missing_containers': [],
            'excess_containers': [],
            'status': 'valid'
        }
        
        # Group expected containers by type
        expected_by_type = {}
        for container in expected_containers:
            container_type = container['item_code']
            if container_type not in expected_by_type:
                expected_by_type[container_type] = 0
            expected_by_type[container_type] += container['required_qty']
        
        # Group assigned containers by type
        assigned_by_type = {}
        for container in assigned_containers:
            container_type = container['container_type']
            if container_type not in assigned_by_type:
                assigned_by_type[container_type] = 0
            assigned_by_type[container_type] += 1
        
        # Compare expected vs assigned
        all_types = set(list(expected_by_type.keys()) + list(assigned_by_type.keys()))
        
        for container_type in all_types:
            expected = expected_by_type.get(container_type, 0)
            assigned = assigned_by_type.get(container_type, 0)
            
            validation_result['validation_summary'][container_type] = {
                'expected': expected,
                'assigned': assigned,
                'difference': assigned - expected,
                'status': 'ok' if assigned == expected else ('missing' if assigned < expected else 'excess')
            }
            
            if assigned < expected:
                validation_result['missing_containers'].append({
                    'container_type': container_type,
                    'missing_qty': expected - assigned
                })
                validation_result['status'] = 'missing_containers'
            elif assigned > expected:
                validation_result['excess_containers'].append({
                    'container_type': container_type,
                    'excess_qty': assigned - expected
                })
                if validation_result['status'] == 'valid':
                    validation_result['status'] = 'excess_containers'
        
        return {'success': True, 'validation': validation_result}
        
    except Exception as e:
        frappe.log_error(f"Batch container validation error: {str(e)}", "BOM Integration API")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def suggest_containers_for_batch(batch_amb_name, bom_name=None, plant=None):
    """Suggest available containers for batch based on BOM requirements"""
    try:
        # Get BOM container requirements
        batch = frappe.get_doc('Batch AMB', batch_amb_name)
        production_qty = getattr(batch, 'qty', 1) or 1
        
        if not bom_name and hasattr(batch, 'bom'):
            bom_name = batch.bom
        
        if not bom_name:
            return {'success': False, 'error': 'BOM name required for container suggestions'}
        
        bom_result = get_bom_containers(bom_name, production_qty)
        if not bom_result['success']:
            return bom_result
        
        suggestions = []
        
        # For each required container type, find available containers
        for container_req in bom_result['containers']:
            container_type = container_req['item_code']
            required_qty = int(container_req['required_qty'])
            
            # Find available containers of this type
            filters = {
                'lifecycle_status': 'Available',
                'container_type': container_type
            }
            
            if plant:
                filters['plant'] = plant
            
            available_containers = frappe.get_all(
                'Container Selection',
                filters=filters,
                fields=['name', 'container_id', 'serial_number', 'net_weight', 'quality_check_status'],
                order_by='creation desc',
                limit=required_qty + 5  # Get a few extra options
            )
            
            suggestions.append({
                'container_type': container_type,
                'required_qty': required_qty,
                'available_containers': available_containers[:required_qty],
                'total_available': len(available_containers),
                'suggestion_status': 'sufficient' if len(available_containers) >= required_qty else 'insufficient'
            })
        
        return {
            'success': True,
            'batch_name': batch_amb_name,
            'bom_name': bom_name,
            'production_qty': production_qty,
            'suggestions': suggestions
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Production Integration APIs
@frappe.whitelist()
def create_containers_from_work_order(work_order_name):
    """Create container selection records from work order requirements"""
    try:
        # Get work order
        work_order = frappe.get_doc('Work Order', work_order_name)
        
        if not work_order.bom_no:
            return {'success': False, 'error': 'Work order has no BOM specified'}
        
        # Get container requirements from BOM
        bom_result = get_bom_containers(work_order.bom_no, work_order.qty)
        if not bom_result['success']:
            return bom_result
        
        created_containers = []
        
        # Create container selection records
        for container_req in bom_result['containers']:
            required_qty = int(container_req['required_qty'])
            
            for i in range(required_qty):
                container = frappe.new_doc('Container Selection')
                container.container_type = container_req['item_code']
                container.lifecycle_status = 'Planned'
                container.plant = work_order.production_item_plant if hasattr(work_order, 'production_item_plant') else 'Juice'
                container.created_by_user = frappe.session.user
                
                # Generate container ID and serial number
                container.container_id = f"WO-{work_order.name}-{container_req['item_code']}-{i+1:03d}"
                container.serial_number = container.container_id
                
                # Set expected weight from BOM if available
                if hasattr(container_req, 'weight'):
                    container.expected_weight = container_req['weight']
                
                container.save()
                created_containers.append(container.name)
        
        # Link containers to work order (if custom field exists)
        if hasattr(work_order, 'container_selections'):
            for container_name in created_containers:
                work_order.append('container_selections', {
                    'container_selection': container_name
                })
            work_order.save()
        
        return {
            'success': True,
            'work_order': work_order_name,
            'created_containers': created_containers,
            'total_created': len(created_containers)
        }
        
    except Exception as e:
        frappe.log_error(f"Create containers from WO error: {str(e)}", "BOM Integration API")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def update_production_yield(batch_amb_name, actual_yield, yield_variance_reason=None):
    """Update production yield and adjust container calculations"""
    try:
        batch = frappe.get_doc('Batch AMB', batch_amb_name)
        
        # Calculate yield variance
        planned_yield = getattr(batch, 'qty', 1) or 1
        yield_variance = ((actual_yield - planned_yield) / planned_yield) * 100
        
        # Update batch with actual yield
        batch.actual_yield = actual_yield
        batch.yield_variance_percentage = yield_variance
        if yield_variance_reason:
            batch.yield_variance_reason = yield_variance_reason
        
        # If significant variance, suggest container adjustments
        container_adjustments = []
        if abs(yield_variance) > 5:  # More than 5% variance
            
            # Get current container assignments
            current_containers = {}
            if hasattr(batch, 'container_barrels'):
                for barrel in batch.container_barrels:
                    container_type = barrel.container_type
                    if container_type not in current_containers:
                        current_containers[container_type] = 0
                    current_containers[container_type] += 1
            
            # Calculate adjusted requirements
            if batch.bom_no:
                adjusted_bom = get_bom_containers(batch.bom_no, actual_yield)
                if adjusted_bom['success']:
                    for container_req in adjusted_bom['containers']:
                        container_type = container_req['item_code']
                        required_qty = int(container_req['required_qty'])
                        current_qty = current_containers.get(container_type, 0)
                        
                        if required_qty != current_qty:
                            container_adjustments.append({
                                'container_type': container_type,
                                'current_qty': current_qty,
                                'required_qty': required_qty,
                                'adjustment': required_qty - current_qty,
                                'action': 'add' if required_qty > current_qty else 'remove'
                            })
        
        batch.save()
        
        return {
            'success': True,
            'batch_name': batch_amb_name,
            'planned_yield': planned_yield,
            'actual_yield': actual_yield,
            'yield_variance_percentage': yield_variance,
            'container_adjustments': container_adjustments
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Container Cost Analysis
@frappe.whitelist()
def analyze_container_costs(bom_name, production_qty=1, include_reuse_savings=True):
    """Analyze container costs including reuse savings"""
    try:
        bom_result = get_bom_containers(bom_name, production_qty)
        if not bom_result['success']:
            return bom_result
        
        cost_analysis = {
            'bom_name': bom_name,
            'production_qty': production_qty,
            'container_costs': [],
            'total_new_cost': 0,
            'total_reuse_cost': 0,
            'potential_savings': 0
        }
        
        for container in bom_result['containers']:
            container_type = container['item_code']
            required_qty = container['required_qty']
            unit_cost = container['rate']
            
            # Calculate new container cost
            new_cost = required_qty * unit_cost
            
            # Calculate reuse cost (assume 70% cost reduction for reused containers)
            reuse_cost = new_cost * 0.3 if include_reuse_savings else new_cost
            
            # Get reuse availability
            available_reuse = frappe.db.count('Container Selection', {
                'container_type': container_type,
                'lifecycle_status': 'Available'
            })
            
            actual_reuse_qty = min(required_qty, available_reuse)
            actual_new_qty = required_qty - actual_reuse_qty
            
            actual_cost = (actual_new_qty * unit_cost) + (actual_reuse_qty * unit_cost * 0.3)
            savings = new_cost - actual_cost
            
            cost_analysis['container_costs'].append({
                'container_type': container_type,
                'required_qty': required_qty,
                'unit_cost': unit_cost,
                'new_container_cost': new_cost,
                'reuse_container_cost': reuse_cost,
                'available_for_reuse': available_reuse,
                'actual_new_qty': actual_new_qty,
                'actual_reuse_qty': actual_reuse_qty,
                'actual_cost': actual_cost,
                'savings': savings
            })
            
            cost_analysis['total_new_cost'] += new_cost
            cost_analysis['total_reuse_cost'] += reuse_cost
            cost_analysis['potential_savings'] += savings
        
        # Calculate percentage savings
        if cost_analysis['total_new_cost'] > 0:
            cost_analysis['savings_percentage'] = (cost_analysis['potential_savings'] / cost_analysis['total_new_cost']) * 100
        
        return {'success': True, 'cost_analysis': cost_analysis}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Integration Utilities
@frappe.whitelist()
def sync_bom_container_items():
    """Sync container items between BOM and Container Selection"""
    try:
        # Get all container-related items from BOMs
        container_items = frappe.db.sql("""
            SELECT DISTINCT bi.item_code, i.item_name, i.item_group
            FROM `tabBOM Item` bi
            INNER JOIN `tabItem` i ON bi.item_code = i.item_code
            WHERE i.item_group IN ('Containers', 'Packaging', 'Barrels', 'Bottles', 'Bags', 'Pails')
               OR i.item_name LIKE '%barrel%'
               OR i.item_name LIKE '%container%'
               OR i.item_name LIKE '%bottle%'
               OR i.item_name LIKE '%bag%'
               OR i.item_name LIKE '%pail%'
               OR i.item_name LIKE '%ibc%'
        """, as_dict=True)
        
        # Update item configurations for containers
        updated_items = []
        for item in container_items:
            try:
                item_doc = frappe.get_doc('Item', item.item_code)
                
                # Ensure proper item group
                if item_doc.item_group not in ['Containers', 'Packaging']:
                    item_doc.item_group = 'Containers'
                
                # Set default UOM if not set
                if not item_doc.stock_uom:
                    item_doc.stock_uom = 'Nos'
                
                # Enable stock tracking
                item_doc.maintain_stock = 1
                item_doc.is_stock_item = 1
                
                item_doc.save()
                updated_items.append(item.item_code)
                
            except Exception as e:
                frappe.log_error(f"Error updating item {item.item_code}: {str(e)}")
        
        return {
            'success': True,
            'container_items_found': len(container_items),
            'items_updated': updated_items,
            'total_updated': len(updated_items)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_production_container_forecast(date_range, plant=None):
    """Get container requirements forecast based on planned production"""
    try:
        date_filter = json.loads(date_range) if isinstance(date_range, str) else date_range
        
        # Get planned work orders
        wo_filters = {
            'planned_start_date': ['between', [date_filter['from_date'], date_filter['to_date']]],
            'status': ['not in', ['Completed', 'Cancelled']]
        }
        
        if plant:
            wo_filters['production_item_plant'] = plant
        
        work_orders = frappe.get_all(
            'Work Order',
            filters=wo_filters,
            fields=['name', 'production_item', 'bom_no', 'qty', 'planned_start_date']
        )
        
        # Calculate container requirements
        forecast = {
            'period': date_filter,
            'plant': plant,
            'work_orders': len(work_orders),
            'container_forecast': {},
            'total_containers': 0
        }
        
        for wo in work_orders:
            if wo.bom_no:
                bom_result = get_bom_containers(wo.bom_no, wo.qty)
                if bom_result['success']:
                    for container in bom_result['containers']:
                        container_type = container['item_code']
                        required_qty = container['required_qty']
                        
                        if container_type not in forecast['container_forecast']:
                            forecast['container_forecast'][container_type] = {
                                'total_required': 0,
                                'work_orders': []
                            }
                        
                        forecast['container_forecast'][container_type]['total_required'] += required_qty
                        forecast['container_forecast'][container_type]['work_orders'].append({
                            'work_order': wo.name,
                            'planned_date': wo.planned_start_date,
                            'qty_required': required_qty
                        })
                        
                        forecast['total_containers'] += required_qty
        
        return {'success': True, 'forecast': forecast}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}