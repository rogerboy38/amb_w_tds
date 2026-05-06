import frappe
from frappe import _
from frappe.model.document import Document


class SampleRequestAMB(Document):
    
    def validate_batch_consistency(self):
        """Validate that batch data is consistent with fetched values"""
        if self.batch_reference:
            batch = frappe.get_doc("Batch AMB", self.batch_reference)
            
            # Check COA consistency (warning only, not blocking)
            if batch.coa_amb and self.coa_amb and batch.coa_amb != self.coa_amb:
                frappe.msgprint(
                    _("Warning: COA AMB ({0}) differs from Batch ({1})").format(
                        self.coa_amb, batch.coa_amb
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # Check item consistency (warning only, not blocking)
            if batch.item_to_manufacture and self.item and batch.item_to_manufacture != self.item:
                frappe.msgprint(
                    _("Warning: Item ({0}) differs from Batch item ({1})").format(
                        self.item, batch.item_to_manufacture
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # NEW: Check Sales Order consistency
            if batch.sales_order_related and self.sales_order_related and batch.sales_order_related != self.sales_order_related:
                frappe.msgprint(
                    _("Warning: Sales Order ({0}) differs from Batch Sales Order ({1})").format(
                        self.sales_order_related, batch.sales_order_related
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # NEW: Auto-set Sales Order if empty
            if batch.sales_order_related and not self.sales_order_related:
                self.sales_order_related = batch.sales_order_related
                frappe.msgprint(
                    _("Sales Order auto-set to: {0}").format(batch.sales_order_related),
                    alert=True,
                    indicator="green"
                )
    def set_customer_name(self):
        if self.customer and not self.customer_name:
            self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

    def update_totals(self):
        for row in self.get("samples") or []:
            if row.samples_count and row.qty_per_sample:
                row.total_qty = row.samples_count * row.qty_per_sample
            else:
                row.total_qty = 0
    
    def validate_batch_consistency(self):
        """Validate that batch data is consistent with fetched values"""
        if self.batch_reference:
            batch = frappe.get_doc("Batch AMB", self.batch_reference)
            
            # Check COA consistency (warning only, not blocking)
            if batch.coa_amb and self.coa_amb and batch.coa_amb != self.coa_amb:
                frappe.msgprint(
                    _("Warning: COA AMB ({0}) differs from Batch ({1})").format(
                        self.coa_amb, batch.coa_amb
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # Check item consistency (warning only, not blocking)
            if batch.item_to_manufacture and self.item and batch.item_to_manufacture != self.item:
                frappe.msgprint(
                    _("Warning: Item ({0}) differs from Batch item ({1})").format(
                        self.item, batch.item_to_manufacture
                    ),
                    alert=True,
                    indicator="orange"
                )
    
    def validate_coa_from_batch(self):
        """Ensure COA AMB matches the batch reference (blocking validation)"""
        if self.batch_reference and self.coa_amb:
            batch_coa = frappe.db.get_value("Batch AMB", self.batch_reference, "coa_amb")
            if batch_coa and batch_coa != self.coa_amb:
                frappe.throw(
                    _("COA AMB ({0}) does not match Batch Reference COA ({1})").format(
                        self.coa_amb, batch_coa
                    )
                )
