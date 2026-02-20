# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BOMTemplateItem(Document):
    def validate(self):
        """Validate BOM Template Item"""
        self.calculate_amount()
    
    def calculate_amount(self):
        """Calculate amount based on quantity and rate"""
        if self.qty and self.rate:
            self.amount = self.qty * self.rate
