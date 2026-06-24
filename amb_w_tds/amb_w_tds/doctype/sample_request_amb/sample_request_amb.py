import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SampleRequestAMB(Document):
    
    def before_save(self):
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
    
    def validate(self):
        self.validate_batch_consistency()
        self.validate_shipment_values()
        self.validate_shipment_weights()
        self._fill_sample_item_names()
    
    def _fill_sample_item_names(self):
        """Backfill each sample row's description from the linked Item.
        Prefers item_name (always populated) over description (empty on some
        prod items). Only fills blanks -- never overwrites. Covers interactive
        and programmatic rows."""
        for row in (self.samples or []):
            if row.item and not (row.description or "").strip():
                name = (frappe.db.get_value("Item", row.item, "item_name")
                        or frappe.db.get_value("Item", row.item, "description"))
                if name:
                    row.description = name

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
            
            # Check Sales Order consistency
            if batch.sales_order_related and self.sales_order_related and batch.sales_order_related != self.sales_order_related:
                frappe.msgprint(
                    _("Warning: Sales Order ({0}) differs from Batch Sales Order ({1})").format(
                        self.sales_order_related, batch.sales_order_related
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # Auto-set Sales Order if empty
            if batch.sales_order_related and not self.sales_order_related:
                self.sales_order_related = batch.sales_order_related
                frappe.msgprint(
                    _("Sales Order auto-set to: {0}").format(batch.sales_order_related),
                    alert=True,
                    indicator="green"
                )
    
    def validate_shipment_values(self):
        """Validate shipment values for Proforma"""
        # Ensure commercial value has a default if needed
        if not self.commercial_value_usd:
            self.commercial_value_usd = 1.00
        
        # Ensure number of packages has a default
        if not self.number_of_packages:
            self.number_of_packages = 1
        
        # Ensure weight has a default
        if not self.gross_weight_kg:
            self.gross_weight_kg = 0.5

    def validate_shipment_weights(self):
        """Reject customs weights that print a negative tara (net must not exceed gross)."""
        net = flt(self.shipment_net_weight)
        gross = flt(self.gross_weight_kg)
        if net > 0 and gross > 0 and (net - gross) > 1e-6:
            frappe.throw(_(
                "Shipment Net Weight ({0} Kg) cannot exceed Gross Weight ({1} Kg) - "
                "this prints a negative Tara on the Proforma. Raise Gross Weight to at "
                "least the rolled-up net, or correct the box/bag weights on the rows."
            ).format(net, gross))
    
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
    
    def get_shipment_purpose(self):
        """Get the shipment purpose text for proforma"""
        if self.shipment_nature:
            return self.shipment_nature
        elif self.internal_export_type:
            return self.internal_export_type
        elif self.special_export_type:
            return self.special_export_type
        return "Muestra sin valor comercial"
    
    def get_waybill_display(self):
        """Get waybill number or placeholder"""
        return self.waybill_number or "12 629 A50 04 9499 3785"
