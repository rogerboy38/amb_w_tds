import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate

class BOMVersion(Document):
    def validate(self):
        self.validate_dates()
        self.validate_version_uniqueness()
        self.set_version_status()
        self.calculate_version_metrics()
    
    def validate_dates(self):
        """Validate effective and expiration dates"""
        if self.effective_date:
            if getdate(self.effective_date) < getdate(nowdate()):
                frappe.throw(_("Effective date cannot be in the past"))
        
        if self.effective_date and self.expiration_date:
            if getdate(self.effective_date) > getdate(self.expiration_date):
                frappe.throw(_("Effective date cannot be after expiration date"))
    
    def validate_version_uniqueness(self):
        """Ensure version name is unique for this BOM"""
        if self.bom_name and self.version:
            existing = frappe.db.exists("BOM Version", {
                "bom_name": self.bom_name,
                "version": self.version,
                "name": ["!=", self.name]
            })
            if existing:
                frappe.throw(_("Version {0} already exists for BOM {1}").format(
                    self.version, self.bom_name
                ))
    
    def set_version_status(self):
        """Automatically set status based on dates and conditions"""
        if not self.status:
            self.status = "Draft"
        
        if self.effective_date and getdate(self.effective_date) <= getdate(nowdate()):
            if self.status == "Approved":
                self.status = "Active"
        
        if self.expiration_date and getdate(self.expiration_date) < getdate(nowdate()):
            self.status = "Expired"
    
    def calculate_version_metrics(self):
        """Calculate metrics for this BOM version"""
        if self.bom_name:
            bom = frappe.get_doc("BOM", self.bom_name)
            
            # Calculate total cost
            total_cost = 0
            total_items = len(bom.items)
            
            for item in bom.items:
                total_cost += (item.rate or 0) * (item.qty or 0)
            
            self.total_cost = total_cost
            self.total_items = total_items
            
            # Calculate operations data if available
            if bom.with_operations:
                total_operations = len(bom.operations)
                total_operation_time = sum((op.time_in_mins or 0) for op in bom.operations)
                self.total_operations = total_operations
                self.total_operation_time = total_operation_time
    
    def on_submit(self):
        """Actions when BOM Version is submitted"""
        self.deactivate_other_versions()
        self.update_bom_reference()
        self.create_version_history()
    
    def deactivate_other_versions(self):
        """Deactivate other active versions of the same BOM"""
        if self.bom_name and self.status == "Active":
            frappe.db.sql("""
                UPDATE `tabBOM Version` 
                SET status = 'Inactive'
                WHERE bom_name = %s 
                AND name != %s 
                AND status = 'Active'
                AND docstatus < 2
            """, (self.bom_name, self.name))
    
    def update_bom_reference(self):
        """Update the main BOM with version information"""
        if self.bom_name:
            frappe.db.set_value("BOM", self.bom_name, {
                "current_version": self.version,
                "current_version_reference": self.name,
                "last_version_update": nowdate()
            })
    
    def create_version_history(self):
        """Create version history record"""
        history_doc = frappe.new_doc("Version History")
        history_doc.update({
            "ref_doctype": "BOM Version",
            "docname": self.name,
            "data": frappe.as_json({
                "bom_name": self.bom_name,
                "version": self.version,
                "status": self.status,
                "effective_date": self.effective_date,
                "changed_by": frappe.session.user
            })
        })
        history_doc.insert(ignore_permissions=True)
    
    def on_update_after_submit(self):
        """Handle updates after submission"""
        if self.has_value_changed('status'):
            if self.status == "Active":
                self.deactivate_other_versions()
    
    @frappe.whitelist()
    def compare_with_previous_version(self):
        """Compare this version with the previous active version"""
        if not self.bom_name:
            return {}
        
        # Get previous active version
        previous_version = frappe.get_all("BOM Version",
            filters={
                "bom_name": self.bom_name,
                "status": ["in", ["Active", "Inactive"]],
                "name": ["!=", self.name],
                "docstatus": 1
            },
            fields=["name", "version", "total_cost", "total_items"],
            order_by="creation desc",
            limit=1
        )
        
        if not previous_version:
            return {"has_previous": False}
        
        previous = previous_version[0]
        current_bom = frappe.get_doc("BOM", self.bom_name)
        
        comparison = {
            "has_previous": True,
            "previous_version": previous.version,
            "previous_cost": previous.total_cost or 0,
            "current_cost": self.total_cost or 0,
            "cost_difference": (self.total_cost or 0) - (previous.total_cost or 0),
            "item_count_difference": (self.total_items or 0) - (previous.total_items or 0)
        }
        
        return comparison
    
    @frappe.whitelist()
    def create_new_bom_from_version(self):
        """Create a new BOM based on this version"""
        if not self.bom_name:
            frappe.throw(_("Please select a BOM first"))
        
        original_bom = frappe.get_doc("BOM", self.bom_name)
        
        # Create new BOM
        new_bom = frappe.new_doc("BOM")
        new_bom.update({
            "item": original_bom.item,
            "item_name": original_bom.item_name,
            "quantity": original_bom.quantity,
            "uom": original_bom.uom,
            "is_active": 1,
            "is_default": 0,
            "with_operations": original_bom.with_operations,
            "source_bom": self.bom_name,
            "version_source": self.name
        })
        
        # Copy items
        for item in original_bom.items:
            new_bom.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "uom": item.uom,
                "rate": item.rate,
                "amount": item.amount
            })
        
        # Copy operations if exists
        if original_bom.with_operations:
            for op in original_bom.operations:
                new_bom.append("operations", {
                    "operation": op.operation,
                    "workstation": op.workstation,
                    "time_in_mins": op.time_in_mins,
                    "hour_rate": op.hour_rate,
                    "operating_cost": op.operating_cost
                })
        
        new_bom.insert()
        
        return {
            "bom_created": True,
            "new_bom_name": new_bom.name,
            "message": _("New BOM {0} created from version {1}").format(new_bom.name, self.version)
        }

# Server-side methods
@frappe.whitelist()
def get_bom_versions(bom_name):
    """Get all versions for a BOM"""
    versions = frappe.get_all("BOM Version",
        filters={"bom_name": bom_name},
        fields=["name", "version", "status", "effective_date", "expiration_date", "total_cost"],
        order_by="effective_date desc, creation desc"
    )
    return versions

@frappe.whitelist()
def get_version_comparison(version1, version2):
    """Compare two BOM versions"""
    v1 = frappe.get_doc("BOM Version", version1)
    v2 = frappe.get_doc("BOM Version", version2)
    
    comparison = {
        "version1": {
            "name": v1.name,
            "version": v1.version,
            "total_cost": v1.total_cost,
            "total_items": v1.total_items,
            "status": v1.status
        },
        "version2": {
            "name": v2.name,
            "version": v2.version,
            "total_cost": v2.total_cost,
            "total_items": v2.total_items,
            "status": v2.status
        },
        "differences": {
            "cost_difference": (v2.total_cost or 0) - (v1.total_cost or 0),
            "item_difference": (v2.total_items or 0) - (v1.total_items or 0)
        }
    }
    
    return comparison

@frappe.whitelist()
def set_version_active(version_name):
    """Set a version as active"""
    version = frappe.get_doc("BOM Version", version_name)
    
    if version.docstatus != 1:
        frappe.throw(_("Version must be submitted before activating"))
    
    version.status = "Active"
    version.save()
    
    return {"success": True, "message": _("Version activated successfully")}
