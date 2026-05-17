import frappe
from frappe.model.document import Document

class TDSDefaultParameter(Document):
    def validate(self):
        # Basic validation for limits
        if self.upper_limit and self.lower_limit and self.upper_limit <= self.lower_limit:
            frappe.throw("Upper Limit must be greater than Lower Limit")
            
        if self.target_value:
            if self.upper_limit and self.target_value > self.upper_limit:
                frappe.throw("Target Value cannot be greater than Upper Limit")
            if self.lower_limit and self.target_value < self.lower_limit:
                frappe.throw("Target Value cannot be less than Lower Limit")
