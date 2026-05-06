import frappe
from frappe.model.document import Document

class QuotationAMB(Document):

    def validate(self):
        self.validate_required_fields()
        self.validate_folio()

    def validate_folio(self):
        if not self.custom_folio:
            frappe.throw("custom_folio is required")

    def apply_agent_hooks_for_quotation(self, method=None):
        """Apply agent hooks"""
        # This is referenced in your doc_events
        pass

