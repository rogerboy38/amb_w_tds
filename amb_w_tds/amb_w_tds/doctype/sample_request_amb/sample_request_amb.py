import frappe
from frappe.model.document import Document


class SampleRequestAMB(Document):
    def validate(self):
        self.set_customer_name()
        self.update_totals()

    def set_customer_name(self):
        if self.customer and not self.customer_name:
            self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

    def update_totals(self):
        for row in self.get("samples") or []:
            if row.samples_count and row.qty_per_sample:
                row.total_qty = row.samples_count * row.qty_per_sample
            else:
                row.total_qty = 0
