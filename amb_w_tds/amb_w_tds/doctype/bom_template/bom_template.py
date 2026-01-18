import frappe
from frappe.model.document import Document
from frappe import _

class BOMTemplate(Document):
    def validate(self):
        """Validate BOM Template"""
        self.calculate_total_cost()
        self.validate_operations()
        self.update_item_names()
    
    def calculate_total_cost(self):
        """Calculate total cost from items and operations"""
        total_material_cost = 0
        total_operation_cost = 0
        
        # Calculate material costs
        for item in self.bom_template_items:
            item.amount = item.qty * (item.rate or 0)
            total_material_cost += item.amount
        
        # Calculate operation costs (if operations exist)
        if hasattr(self, 'standard_operations') and self.standard_operations:
            for operation in self.standard_operations:
                operation_cost = (operation.time_in_mins / 60) * (self.labor_cost_per_hour or 0)
                total_operation_cost += operation_cost
        
        # Apply overhead
        overhead_cost = (total_material_cost + total_operation_cost) * (self.overhead_percentage / 100)
        
        self.total_material_cost = total_material_cost
        self.total_operation_cost = total_operation_cost
        self.total_overhead_cost = overhead_cost
        self.total_cost = total_material_cost + total_operation_cost + overhead_cost
    
    def validate_operations(self):
        """Validate that operations have workstations"""
        if self.with_operations and hasattr(self, 'standard_operations') and self.standard_operations:
            for operation in self.standard_operations:
                if not operation.workstation:
                    frappe.throw(_("Workstation is required for operation: {0}").format(operation.operation))
    
    def update_item_names(self):
        """Update item names from item codes"""
        for item in self.bom_template_items:
            if item.item_code and not item.item_name:
                item_name = frappe.db.get_value("Item", item.item_code, "item_name")
                if item_name:
                    item.item_name = item_name

@frappe.whitelist()
def generate_bom_from_template(bom_template, item_code, quantity=1, company=None):
    """Generate a BOM from a template"""
    template = frappe.get_doc("BOM Template", bom_template)
    
    if not company:
        company = frappe.defaults.get_user_default("company")
    
    # Create new BOM
    bom = frappe.new_doc("BOM")
    bom.update({
        "item": item_code,
        "quantity": quantity * (template.default_quantity or 1),
        "uom": template.uom,
        "with_operations": template.with_operations,
        "company": company,
        "currency": frappe.defaults.get_user_default("currency") or "USD"
    })
    
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
    if template.with_operations and hasattr(template, 'standard_operations') and template.standard_operations:
        for template_op in template.standard_operations:
            bom.append("operations", {
                "operation": template_op.operation,
                "workstation": template_op.workstation,
                "time_in_mins": template_op.time_in_mins,
                "description": template_op.description
            })
    
    return bom

@frappe.whitelist()
def get_bom_template_cost_breakdown(bom_template):
    """Get cost breakdown for BOM template"""
    template = frappe.get_doc("BOM Template", bom_template)
    template.calculate_total_cost()
    
    cost_breakdown = {
        "total_material_cost": template.total_material_cost,
        "total_operation_cost": template.total_operation_cost,
        "total_overhead_cost": template.total_overhead_cost,
        "total_cost": template.total_cost,
        "materials": [],
        "operations": []
    }
    
    # Material breakdown
    for item in template.bom_template_items:
        cost_breakdown["materials"].append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "quantity": item.qty,
            "rate": item.rate,
            "amount": item.amount
        })
    
    # Operations breakdown
    if hasattr(template, 'standard_operations') and template.standard_operations:
        for operation in template.standard_operations:
            operation_cost = (operation.time_in_mins / 60) * (template.labor_cost_per_hour or 0)
            cost_breakdown["operations"].append({
                "operation": operation.operation,
                "workstation": operation.workstation,
                "time_in_mins": operation.time_in_mins,
                "cost": operation_cost
            })
    
    return cost_breakdown

@frappe.whitelist()
def create_bom_template_from_existing_bom(bom_name, template_name):
    """Create a BOM Template from an existing BOM"""
    bom = frappe.get_doc("BOM", bom_name)
    
    # Create new template
    template = frappe.new_doc("BOM Template")
    template.bom_template_name = template_name
    template.item_group = frappe.db.get_value("Item", bom.item, "item_group")
    template.default_quantity = bom.quantity
    template.uom = bom.uom
    template.with_operations = bom.with_operations
    template.company = bom.company
    
    # Copy items
    for bom_item in bom.items:
        template.append("bom_template_items", {
            "item_code": bom_item.item_code,
            "qty": bom_item.qty,
            "uom": bom_item.uom,
            "rate": bom_item.rate,
            "source_warehouse": bom_item.source_warehouse
        })
    
    # Copy operations
    if bom.with_operations and bom.operations:
        for bom_op in bom.operations:
            template.append("standard_operations", {
                "operation": bom_op.operation,
                "workstation": bom_op.workstation,
                "time_in_mins": bom_op.time_in_mins
            })
    
    return template
