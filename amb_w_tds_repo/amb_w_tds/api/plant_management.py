"""
Plant Management API - Plant-specific container rules and operations
Handles plant configurations, container type rules, and juice conversion calculations
"""

import frappe
from frappe import _
from frappe.utils import flt
import json

# Plant Configuration APIs
@frappe.whitelist()
def get_plant_config(plant_name):
    """Get complete plant configuration"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        
        # Convert to dict with all details
        plant_data = {
            'plant_name': config.plant_name,
            'plant_code': config.plant_code,
            'is_active': config.is_active,
            'plant_manager': config.plant_manager,
            'location': config.location,
            'operating_hours': config.operating_hours,
            'settings': {
                'min_fill_threshold': config.min_fill_threshold,
                'max_fill_threshold': config.max_fill_threshold,
                'weight_tolerance_percentage': config.weight_tolerance_percentage,
                'auto_sync_enabled': config.auto_sync_enabled,
                'sync_interval_minutes': config.sync_interval_minutes
            },
            'container_rules': [],
            'juice_conversion_rules': [],
            'default_tara_weights': {}
        }
        
        # Add container rules
        for rule in config.container_rules:
            plant_data['container_rules'].append({
                'container_type': rule.container_type,
                'capacity': rule.capacity,
                'tara_weight': rule.tara_weight,
                'is_reusable': rule.is_reusable,
                'max_reuse_count': rule.max_reuse_count,
                'cleaning_required': rule.cleaning_required
            })
        
        # Add juice conversion rules
        for rule in config.juice_conversion_rules:
            plant_data['juice_conversion_rules'].append({
                'target_concentration': rule.target_concentration,
                'min_brix': rule.min_brix,
                'max_brix': rule.max_brix,
                'conversion_factor': rule.conversion_factor,
                'yield_percentage': rule.yield_percentage,
                'notes': rule.notes
            })
        
        # Parse default tara weights
        if config.default_tara_weights:
            try:
                plant_data['default_tara_weights'] = json.loads(config.default_tara_weights)
            except:
                plant_data['default_tara_weights'] = {}
        
        return {'success': True, 'config': plant_data}
        
    except frappe.DoesNotExistError:
        return {'success': False, 'error': f'Plant configuration not found: {plant_name}'}
    except Exception as e:
        frappe.log_error(f"Get plant config error: {str(e)}", "Plant Management API")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_all_plants():
    """Get list of all plant configurations"""
    try:
        plants = frappe.get_all(
            'Plant Configuration',
            fields=['plant_name', 'plant_code', 'is_active', 'plant_manager', 'location'],
            order_by='plant_name'
        )
        
        return {'success': True, 'plants': plants}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Container Type and Rules APIs
@frappe.whitelist()
def get_container_types_for_plant(plant_name):
    """Get available container types for a plant"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        
        container_types = []
        for rule in config.container_rules:
            container_types.append({
                'container_type': rule.container_type,
                'capacity': rule.capacity,
                'tara_weight': rule.tara_weight,
                'is_reusable': rule.is_reusable,
                'max_reuse_count': rule.max_reuse_count
            })
        
        return {'success': True, 'container_types': container_types}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_container_capacity(plant_name, container_type):
    """Get capacity and tara weight for specific container type in plant"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        
        for rule in config.container_rules:
            if rule.container_type == container_type:
                return {
                    'success': True,
                    'capacity': rule.capacity,
                    'tara_weight': rule.tara_weight,
                    'is_reusable': rule.is_reusable,
                    'max_reuse_count': rule.max_reuse_count,
                    'cleaning_required': rule.cleaning_required
                }
        
        return {'success': False, 'error': f'Container type {container_type} not found for plant {plant_name}'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def validate_container_for_plant(plant_name, container_type, operation='general'):
    """Validate if container type is allowed for plant and operation"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        
        # Check if container type is configured for this plant
        container_rule = None
        for rule in config.container_rules:
            if rule.container_type == container_type:
                container_rule = rule
                break
        
        if not container_rule:
            return {
                'success': False,
                'valid': False,
                'error': f'Container type {container_type} not configured for plant {plant_name}'
            }
        
        # Plant-specific validations
        validations = {
            'Juice': ['220L Barrel', '1000L IBC'],
            'Dry': ['Industrial Bag', '20L Pail'],
            'Mix': ['Industrial Bag', '20L Pail'],
            'Lab': ['20L Pail', 'Laboratory Bottle']
        }
        
        expected_types = validations.get(plant_name, [])
        if expected_types and container_type not in expected_types:
            return {
                'success': True,
                'valid': False,
                'warning': f'Container type {container_type} unusual for {plant_name} plant. Expected: {", ".join(expected_types)}'
            }
        
        return {
            'success': True,
            'valid': True,
            'container_rule': {
                'capacity': container_rule.capacity,
                'tara_weight': container_rule.tara_weight,
                'is_reusable': container_rule.is_reusable,
                'max_reuse_count': container_rule.max_reuse_count
            }
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Juice Conversion APIs (1X/30X)
@frappe.whitelist()
def calculate_juice_containers(plant_name, batch_size, brix_level, target_concentration='30X'):
    """Calculate required containers for juice production with 1X/30X conversion"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        
        # Get conversion factor from configuration
        conversion_factor = config.get_juice_conversion_factor(
            float(brix_level), 
            target_concentration
        )
        
        # Calculate final volume after concentration
        batch_size = float(batch_size)
        final_volume = batch_size / conversion_factor  # Concentrated volume
        
        # Get barrel specifications for juice plant
        barrel_rule = None
        for rule in config.container_rules:
            if 'barrel' in rule.container_type.lower() or '220' in rule.container_type:
                barrel_rule = rule
                break
        
        if not barrel_rule:
            return {
                'success': False,
                'error': 'No barrel configuration found for juice plant'
            }
        
        barrel_capacity = barrel_rule.capacity
        
        # Calculate containers needed
        barrels_needed = final_volume / barrel_capacity
        barrels_required = int(barrels_needed) + (1 if barrels_needed % 1 > 0 else 0)
        
        # Calculate truck loads (165-180 barrels per truck for juice)
        barrels_per_truck = 175  # Average
        truck_loads = barrels_required / barrels_per_truck
        
        # Calculate yield percentage
        yield_factor = 1.0
        for rule in config.juice_conversion_rules:
            if (rule.min_brix <= float(brix_level) <= rule.max_brix and 
                rule.target_concentration == target_concentration):
                yield_factor = rule.yield_percentage / 100
                break
        
        actual_yield = final_volume * yield_factor
        actual_barrels = int(actual_yield / barrel_capacity) + 1
        
        return {
            'success': True,
            'calculation': {
                'batch_size': batch_size,
                'brix_level': float(brix_level),
                'target_concentration': target_concentration,
                'conversion_factor': conversion_factor,
                'theoretical_volume': final_volume,
                'expected_yield_percentage': yield_factor * 100,
                'actual_yield_volume': actual_yield,
                'barrel_capacity': barrel_capacity,
                'theoretical_barrels': barrels_required,
                'actual_barrels_needed': actual_barrels,
                'truck_loads': truck_loads,
                'barrels_per_truck': barrels_per_truck
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Juice calculation error: {str(e)}", "Plant Management API")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_juice_conversion_chart(plant_name):
    """Get juice conversion chart for all configured rules"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        
        conversion_chart = []
        for rule in config.juice_conversion_rules:
            conversion_chart.append({
                'target_concentration': rule.target_concentration,
                'brix_range': f"{rule.min_brix}-{rule.max_brix}",
                'conversion_factor': rule.conversion_factor,
                'yield_percentage': rule.yield_percentage,
                'notes': rule.notes
            })
        
        return {'success': True, 'conversion_chart': conversion_chart}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Plant Performance and Analytics
@frappe.whitelist()
def get_plant_performance(plant_name, date_range=None):
    """Get plant performance metrics"""
    try:
        # Base filters
        filters = {'plant': plant_name}
        
        # Add date range if provided
        if date_range:
            date_filter = json.loads(date_range) if isinstance(date_range, str) else date_range
            if 'from_date' in date_filter:
                filters['creation'] = ['>=', date_filter['from_date']]
            if 'to_date' in date_filter:
                filters['creation'] = ['<=', date_filter['to_date']]
        
        # Get container statistics
        total_containers = frappe.db.count('Container Selection', filters)
        
        # Status distribution
        status_counts = frappe.db.sql("""
            SELECT lifecycle_status, COUNT(*) as count
            FROM `tabContainer Selection`
            WHERE plant = %(plant)s
            GROUP BY lifecycle_status
        """, {'plant': plant_name}, as_dict=True)
        
        # Sync performance
        sync_performance = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_syncs,
                SUM(CASE WHEN sync_status = 'Success' THEN 1 ELSE 0 END) as successful_syncs,
                SUM(CASE WHEN sync_status = 'Error' THEN 1 ELSE 0 END) as failed_syncs
            FROM `tabContainer Sync Log` csl
            INNER JOIN `tabContainer Selection` cs ON csl.container_selection = cs.name
            WHERE cs.plant = %(plant)s
        """, {'plant': plant_name}, as_dict=True)
        
        # Weight variance analysis
        weight_analysis = frappe.db.sql("""
            SELECT 
                AVG(weight_variance_percentage) as avg_variance,
                COUNT(CASE WHEN is_within_tolerance = 1 THEN 1 END) as within_tolerance,
                COUNT(CASE WHEN is_within_tolerance = 0 THEN 1 END) as outside_tolerance,
                COUNT(CASE WHEN is_partial_fill = 1 THEN 1 END) as partial_fills
            FROM `tabContainer Selection`
            WHERE plant = %(plant)s AND net_weight IS NOT NULL
        """, {'plant': plant_name}, as_dict=True)
        
        return {
            'success': True,
            'performance': {
                'total_containers': total_containers,
                'status_distribution': status_counts,
                'sync_performance': sync_performance[0] if sync_performance else {},
                'weight_analysis': weight_analysis[0] if weight_analysis else {},
                'plant_name': plant_name
            }
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Configuration Management
@frappe.whitelist()
def export_plant_config(plant_name):
    """Export plant configuration as JSON"""
    try:
        result = get_plant_config(plant_name)
        if result['success']:
            return {
                'success': True,
                'config': result['config'],
                'export_timestamp': frappe.utils.now(),
                'exported_by': frappe.session.user
            }
        else:
            return result
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def import_plant_config(plant_name, config_data):
    """Import plant configuration from JSON"""
    try:
        config_dict = json.loads(config_data) if isinstance(config_data, str) else config_data
        
        # Validate required fields
        required_fields = ['plant_name', 'plant_code']
        for field in required_fields:
            if field not in config_dict:
                return {'success': False, 'error': f'Missing required field: {field}'}
        
        # Create or update plant configuration
        try:
            config = frappe.get_doc('Plant Configuration', plant_name)
        except frappe.DoesNotExistError:
            config = frappe.new_doc('Plant Configuration')
            config.plant_name = plant_name
        
        # Update configuration fields
        for field, value in config_dict.items():
            if field not in ['container_rules', 'juice_conversion_rules']:
                if hasattr(config, field):
                    setattr(config, field, value)
        
        # Clear existing rules
        config.container_rules = []
        config.juice_conversion_rules = []
        
        # Add container rules
        for rule_data in config_dict.get('container_rules', []):
            config.append('container_rules', rule_data)
        
        # Add juice conversion rules
        for rule_data in config_dict.get('juice_conversion_rules', []):
            config.append('juice_conversion_rules', rule_data)
        
        config.save()
        
        return {
            'success': True,
            'message': f'Plant configuration imported successfully for {plant_name}'
        }
        
    except Exception as e:
        frappe.log_error(f"Import plant config error: {str(e)}", "Plant Management API")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def create_default_plant_configs():
    """Create default plant configurations for all plants"""
    try:
        default_configs = {
            'Juice': {
                'plant_code': 'JCE',
                'container_rules': [
                    {
                        'container_type': '220L Barrel',
                        'capacity': 220.0,
                        'tara_weight': 15.0,
                        'is_reusable': 1,
                        'max_reuse_count': 50,
                        'cleaning_required': 1
                    },
                    {
                        'container_type': '1000L IBC',
                        'capacity': 1000.0,
                        'tara_weight': 45.0,
                        'is_reusable': 1,
                        'max_reuse_count': 100,
                        'cleaning_required': 1
                    }
                ],
                'juice_conversion_rules': [
                    {
                        'target_concentration': '30X',
                        'min_brix': 60.0,
                        'max_brix': 70.0,
                        'conversion_factor': 30.0,
                        'yield_percentage': 85.0
                    },
                    {
                        'target_concentration': '1X',
                        'min_brix': 10.0,
                        'max_brix': 15.0,
                        'conversion_factor': 1.0,
                        'yield_percentage': 95.0
                    }
                ]
            },
            'Dry': {
                'plant_code': 'DRY',
                'container_rules': [
                    {
                        'container_type': 'Industrial Bag',
                        'capacity': 25.0,
                        'tara_weight': 0.5,
                        'is_reusable': 0,
                        'max_reuse_count': 1,
                        'cleaning_required': 0
                    },
                    {
                        'container_type': '20L Pail',
                        'capacity': 20.0,
                        'tara_weight': 2.5,
                        'is_reusable': 1,
                        'max_reuse_count': 20,
                        'cleaning_required': 1
                    }
                ]
            },
            'Mix': {
                'plant_code': 'MIX',
                'container_rules': [
                    {
                        'container_type': 'Industrial Bag',
                        'capacity': 25.0,
                        'tara_weight': 0.5,
                        'is_reusable': 0,
                        'max_reuse_count': 1,
                        'cleaning_required': 0
                    },
                    {
                        'container_type': '20L Pail',
                        'capacity': 20.0,
                        'tara_weight': 2.5,
                        'is_reusable': 1,
                        'max_reuse_count': 20,
                        'cleaning_required': 1
                    }
                ]
            },
            'Lab': {
                'plant_code': 'LAB',
                'container_rules': [
                    {
                        'container_type': '20L Pail',
                        'capacity': 20.0,
                        'tara_weight': 2.5,
                        'is_reusable': 1,
                        'max_reuse_count': 10,
                        'cleaning_required': 1
                    },
                    {
                        'container_type': 'Laboratory Bottle',
                        'capacity': 1.0,
                        'tara_weight': 0.1,
                        'is_reusable': 1,
                        'max_reuse_count': 50,
                        'cleaning_required': 1
                    }
                ]
            }
        }
        
        created_configs = []
        for plant_name, config_data in default_configs.items():
            try:
                # Check if config already exists
                if frappe.db.exists('Plant Configuration', plant_name):
                    continue
                
                # Create new configuration
                config = frappe.new_doc('Plant Configuration')
                config.plant_name = plant_name
                config.plant_code = config_data['plant_code']
                config.is_active = 1
                
                # Add container rules
                for rule_data in config_data.get('container_rules', []):
                    config.append('container_rules', rule_data)
                
                # Add juice conversion rules
                for rule_data in config_data.get('juice_conversion_rules', []):
                    config.append('juice_conversion_rules', rule_data)
                
                config.save()
                created_configs.append(plant_name)
                
            except Exception as e:
                frappe.log_error(f"Error creating config for {plant_name}: {str(e)}")
        
        return {
            'success': True,
            'created_configs': created_configs,
            'message': f'Created default configurations for: {", ".join(created_configs)}'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}