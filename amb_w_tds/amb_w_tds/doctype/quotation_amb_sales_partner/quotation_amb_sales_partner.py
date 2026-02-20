# Copyright (c) 2025
# For license information, please see LICENSE

import frappe
from frappe.model.document import Document

class QuotationAMBSalesPartner(Document):

    def validate(self):
        self._compute_commission_amount()
        self._validate_sales_partner()

    def _compute_commission_amount(self):
        """Recalculate commission amount based on rate and parent total"""
        if self.commission_rate and self.parent:
            total = frappe.db.get_value(
                "Quotation AMB",
                self.parent,
                "base_total"
            )

            if total:
                self.commission_amount = (total * self.commission_rate) / 100

    def _validate_sales_partner(self):
        """Ensure Sales Partner exists (it always should, but safe to validate)"""
        if not self.sales_partner:
            frappe.throw("Sales Partner is required in commission rows")

