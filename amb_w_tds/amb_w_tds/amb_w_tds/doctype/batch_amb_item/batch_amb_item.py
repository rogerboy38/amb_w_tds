import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt

class BatchAMBItem(Document):
    def validate(self):
        """Validate the batch item before saving"""
        self.validate_quantity()
        self.validate_item()
        self.calculate_amount()
    
    def validate_quantity(self):
        """Validate quantity is positive"""
        if flt(self.quantity) <= 0:
            frappe.throw(_("Quantity must be greater than 0"))
    
    def validate_item(self):
        """Validate item exists and is stock item"""
        if self.item_code and not frappe.db.exists("Item", self.item_code):
            frappe.throw(_("Item {0} does not exist").format(self.item_code))
    
    def calculate_amount(self):
        """Calculate amount based on quantity and rate"""
        if self.quantity and self.rate:
            self.amount = flt(self.quantity) * flt(self.rate)
        else:
            self.amount = 0.0
    
    def before_save(self):
        """Set default UOM if not provided"""
        if self.item_code and not self.uom:
            self.uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
    
    def on_update(self):
        """Update parent batch totals"""
        self.update_parent_totals()
    
    def update_parent_totals(self):
        """Update parent Batch AMB totals"""
        if self.get("parent"):
            from frappe.model.workflow import apply_workflow
            parent = frappe.get_doc("Batch AMB", self.parent)
            parent.calculate_totals()
            parent.save(ignore_permissions=True)
