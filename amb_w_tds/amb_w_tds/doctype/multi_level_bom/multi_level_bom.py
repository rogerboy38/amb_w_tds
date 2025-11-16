import frappe
from frappe.model.document import Document

class MultiLevelBOM(Document):
    def validate(self):
        """Validate Multi-Level BOM"""
        self.calculate_total_cost()
        self.validate_bom_levels()
        self.update_item_names()
    
    def calculate_total_cost(self):
        """Calculate total cost across all BOM levels"""
        total_material_cost = 0
        total_operation_cost = 0
        
        for level in self.bom_levels:
            # Calculate material cost for each level
            material_cost = level.quantity * (level.material_rate or 0)
            total_material_cost += material_cost
            
            # Calculate operation cost for each level
            operation_cost = level.quantity * (level.operation_cost or 0)
            total_operation_cost += operation_cost
        
        self.total_material_cost = total_material_cost
        self.total_operation_cost = total_operation_cost
        self.total_cost = total_material_cost + total_operation_cost
    
    def validate_bom_levels(self):
        """Validate that BOM levels are properly structured"""
        if not self.bom_levels:
            frappe.throw("At least one BOM level is required")
        
        # Check for circular references
        level_items = [level.item_code for level in self.bom_levels if level.item_code]
        if len(level_items) != len(set(level_items)):
            frappe.throw("Duplicate items found in BOM levels")
    
    def update_item_names(self):
        """Update item names from item codes"""
        for level in self.bom_levels:
            if level.item_code and not level.item_name:
                item_name = frappe.db.get_value("Item", level.item_code, "item_name")
                if item_name:
                    level.item_name = item_name

@frappe.whitelist()
def generate_multi_level_bom_from_item(item_code, quantity=1):
    """Generate a multi-level BOM structure from an item"""
    # Get the main BOM for the item
    main_bom = frappe.get_all("BOM", 
        filters={"item": item_code, "is_active": 1, "is_default": 1},
        fields=["name", "item", "quantity", "uom"]
    )
    
    if not main_bom:
        frappe.throw(f"No active default BOM found for item {item_code}")
    
    main_bom = main_bom[0]
    
    # Create multi-level BOM document
    ml_bom = frappe.new_doc("Multi Level BOM")
    ml_bom.main_item = item_code
    ml_bom.quantity = quantity
    ml_bom.uom = main_bom.uom
    ml_bom.company = frappe.defaults.get_user_default("company")
    
    # Add main level
    ml_bom.append("bom_levels", {
        "level": 1,
        "item_code": item_code,
        "quantity": quantity,
        "bom_no": main_bom.name,
        "level_description": "Main Product"
    })
    
    # TODO: Recursively add sub-levels by exploding BOMs
    # This would require recursive BOM explosion logic
    
    return ml_bom

@frappe.whitelist()
def get_bom_cost_breakdown(multi_level_bom_name):
    """Get detailed cost breakdown for multi-level BOM"""
    ml_bom = frappe.get_doc("Multi Level BOM", multi_level_bom_name)
    
    cost_breakdown = {
        "total_material_cost": ml_bom.total_material_cost,
        "total_operation_cost": ml_bom.total_operation_cost,
        "total_cost": ml_bom.total_cost,
        "levels": []
    }
    
    for level in ml_bom.bom_levels:
        material_cost = level.quantity * (level.material_rate or 0)
        operation_cost = level.quantity * (level.operation_cost or 0)
        
        cost_breakdown["levels"].append({
            "level": level.level,
            "item_code": level.item_code,
            "item_name": level.item_name,
            "quantity": level.quantity,
            "material_rate": level.material_rate,
            "material_cost": material_cost,
            "operation_cost": operation_cost,
            "total_level_cost": material_cost + operation_cost
        })
    
    return cost_breakdown

@frappe.whitelist()
def create_bom_from_template(bom_template, target_item, quantity=1):
    """Create a BOM from a BOM Template"""
    template = frappe.get_doc("BOM Template", bom_template)
    
    bom = frappe.new_doc("BOM")
    bom.item = target_item
    bom.quantity = quantity * (template.default_quantity or 1)
    bom.uom = template.uom
    bom.with_operations = template.with_operations
    bom.company = frappe.defaults.get_user_default("company")
    bom.currency = frappe.defaults.get_user_default("currency")
    
    # Copy items from template
    for template_item in template.bom_template_items:
        bom.append("items", {
            "item_code": template_item.item_code,
            "qty": template_item.qty * quantity,
            "uom": template_item.uom,
            "rate": template_item.rate,
            "source_warehouse": template_item.source_warehouse,
            "do_not_explode": template_item.do_not_explode
        })
    
    # Copy operations from template
    if template.with_operations and hasattr(template, 'standard_operations'):
        for template_op in template.standard_operations:
            bom.append("operations", {
                "operation": template_op.operation,
                "workstation": template_op.workstation,
                "time_in_mins": template_op.time_in_mins
            })
    
    return bom
