# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class COAAMB(Document):
    """
    COA AMB - Certificate of Analysis for Batch AMB
    """
    def validate(self):
        self.set_defaults()
        self.validate_batch_link()

    def set_defaults(self):
        if not self.issued_by:
            self.issued_by = frappe.session.user
        if not self.issued_date:
            self.issued_date = frappe.utils.nowdate()

    def validate_batch_link(self):
        if self.batch_amb:
            batch = frappe.get_doc("Batch AMB", self.batch_amb)
            self.item_code = batch.item_to_manufacture
            self.batch_number = batch.title or batch.name

    def on_submit(self):
        self.status = "Issued"
        # Link back to Batch AMB
        if self.batch_amb:
            try:
                batch = frappe.get_doc("Batch AMB", self.batch_amb)
                if hasattr(batch, "pipeline_status"):
                    batch.pipeline_status = "COA Ready"
                    batch.save(ignore_permissions=True)
            except Exception:
                pass

    def on_cancel(self):
        self.status = "Cancelled"
