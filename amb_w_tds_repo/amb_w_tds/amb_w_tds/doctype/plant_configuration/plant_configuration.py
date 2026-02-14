"""
Plant Configuration DocType Controller
Manages plant-specific container rules and settings
"""

import frappe
from frappe.model.document import Document
import json

class PlantConfiguration(Document):
    """Plant Configuration controller"""
    
    def validate(self):
        """Validate plant configuration"""
        self.validate_plant_code()
        self.validate_thresholds()
        self.validate_tara_weights()
    
    def validate_plant_code(self):
        """Ensure plant code is unique and follows format"""
        if self.plant_code:
            self.plant_code = self.plant_code.upper()
            
            # Check for duplicates
            existing = frappe.db.get_value(
                'Plant Configuration', 
                {'plant_code': self.plant_code, 'name': ['!=', self.name]}, 
                'name'
            )
            if existing:
                frappe.throw(f"Plant code {self.plant_code} already exists")
    
    def validate_thresholds(self):
        """Validate fill thresholds"""
        if self.min_fill_threshold >= self.max_fill_threshold:
            frappe.throw("Minimum fill threshold must be less than maximum fill threshold")
        
        if self.min_fill_threshold < 0 or self.max_fill_threshold > 100:
            frappe.throw("Fill thresholds must be between 0 and 100")
    
    def validate_tara_weights(self):
        """Validate tara weights JSON format"""
        if self.default_tara_weights:
            try:
                weights = json.loads(self.default_tara_weights)
                if not isinstance(weights, dict):
                    frappe.throw("Default tara weights must be a JSON object")
                
                # Validate weight values are numeric
                for container_type, weight in weights.items():
                    if not isinstance(weight, (int, float)) or weight < 0:
                        frappe.throw(f"Invalid weight for {container_type}: {weight}")
                        
            except json.JSONDecodeError:
                frappe.throw("Invalid JSON format for default tara weights")
    
    def get_container_rules_for_type(self, container_type):
        """Get container rules for specific type"""
        for rule in self.container_rules:
            if rule.container_type == container_type:
                return rule
        return None
    
    def get_tara_weight(self, container_type):
        """Get tara weight for container type"""
        # First check container rules
        rule = self.get_container_rules_for_type(container_type)
        if rule and rule.tara_weight:
            return rule.tara_weight
        
        # Fallback to default tara weights
        if self.default_tara_weights:
            try:
                weights = json.loads(self.default_tara_weights)
                return weights.get(container_type, 0.0)
            except:
                pass
        
        return 0.0
    
    def get_juice_conversion_factor(self, brix_level, target_concentration):
        """Get conversion factor for 1X/30X juice conversion"""
        for rule in self.juice_conversion_rules:
            if (rule.min_brix <= brix_level <= rule.max_brix and 
                rule.target_concentration == target_concentration):
                return rule.conversion_factor
        
        # Default conversion factors
        if target_concentration == '30X':
            return 30.0
        elif target_concentration == '1X':
            return 1.0
        
        return 1.0

# API Methods
@frappe.whitelist()
def get_plant_config(plant_name):
    """Get plant configuration"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        return {
            'success': True,
            'config': {
                'plant_name': config.plant_name,
                'plant_code': config.plant_code,
                'is_active': config.is_active,
                'min_fill_threshold': config.min_fill_threshold,
                'max_fill_threshold': config.max_fill_threshold,
                'weight_tolerance_percentage': config.weight_tolerance_percentage,
                'auto_sync_enabled': config.auto_sync_enabled,
                'sync_interval_minutes': config.sync_interval_minutes,
                'container_rules': [dict(rule) for rule in config.container_rules],
                'juice_conversion_rules': [dict(rule) for rule in config.juice_conversion_rules]
            }
        }
    except frappe.DoesNotExistError:
        return {'success': False, 'error': f'Plant configuration not found: {plant_name}'}

@frappe.whitelist()
def get_container_capacity(plant_name, container_type):
    """Get container capacity for plant and type"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        rule = config.get_container_rules_for_type(container_type)
        
        if rule:
            return {'success': True, 'capacity': rule.capacity, 'tara_weight': rule.tara_weight}
        else:
            return {'success': False, 'error': 'Container rule not found'}
            
    except frappe.DoesNotExistError:
        return {'success': False, 'error': 'Plant configuration not found'}

@frappe.whitelist()
def calculate_juice_containers(plant_name, batch_size, brix_level, target_concentration='30X'):
    """Calculate required containers for juice production"""
    try:
        config = frappe.get_doc('Plant Configuration', plant_name)
        conversion_factor = config.get_juice_conversion_factor(float(brix_level), target_concentration)
        
        # Calculate final volume after concentration
        final_volume = batch_size * conversion_factor
        
        # Get barrel capacity (typically 220L for juice)
        barrel_rule = config.get_container_rules_for_type('220L Barrel')
        barrel_capacity = barrel_rule.capacity if barrel_rule else 220.0
        
        # Calculate number of barrels needed
        barrels_needed = final_volume / barrel_capacity
        truck_loads = barrels_needed / 180  # 165-180 barrels per truck
        
        return {
            'success': True,
            'batch_size': batch_size,
            'final_volume': final_volume,
            'conversion_factor': conversion_factor,
            'barrels_needed': barrels_needed,
            'truck_loads': truck_loads,
            'barrel_capacity': barrel_capacity
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}