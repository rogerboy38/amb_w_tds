# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BOMTemplate(Document):
    """
    BOM Template for different product types
    Stores component structure without hardcoding
    """
    
    def validate(self):
        """Validation"""
        if not self.product_code:
            frappe.throw("Product Code is required")
        
        if not self.template_name:
            self.template_name = f"BOM Template - {self.product_code}"
    
    def get_component_items(self, component_type):
        """Get items for a specific component type (Utility, Supplies, etc.)"""
        items = []
        for item in self.template_items:
            if item.component_type == component_type:
                items.append({
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.default_qty,
                    "uom": item.uom,
                    "rate": item.default_rate,
                    "item_group": item.item_group
                })
        return items
