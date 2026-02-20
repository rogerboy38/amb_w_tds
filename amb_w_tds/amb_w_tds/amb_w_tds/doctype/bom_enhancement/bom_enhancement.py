# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BOMEnhancement(Document):
    def validate(self):
        """Validate BOM Enhancement"""
        self.validate_bom_template()
    
    def validate_bom_template(self):
        """Validate that BOM Template exists"""
        if self.bom_template and not frappe.db.exists("BOM Template", self.bom_template):
            frappe.throw(f"BOM Template {self.bom_template} does not exist")
