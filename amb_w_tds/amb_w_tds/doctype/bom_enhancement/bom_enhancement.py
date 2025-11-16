import frappe
from frappe.model.document import Document
from frappe import _

class BOMEnhancement(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_total_cost()
        self.set_status()
    
    def validate_dates(self):
        if self.valid_from and self.valid_to:
            if self.valid_from > self.valid_to:
                frappe.throw(_("Valid From date cannot be after Valid To date"))
    
    def calculate_total_cost(self):
        """Calculate total cost based on BOM items"""
        total_cost = 0
        if self.bom_reference:
            bom_items = frappe.get_all("BOM Item", 
                filters={"parent": self.bom_reference},
                fields=["amount", "qty"]
            )
            for item in bom_items:
                total_cost += item.amount * item.qty
        
        self.total_estimated_cost = total_cost
    
    def set_status(self):
        """Automatically set status based on conditions"""
        if not self.status:
            if self.is_active:
                self.status = "Active"
            else:
                self.status = "Inactive"
    
    def on_submit(self):
        """Actions when BOM Enhancement is submitted"""
        self.create_bom_version()
        self.update_related_bom()
    
    def create_bom_version(self):
        """Create a BOM Version record when enhanced BOM is submitted"""
        if self.bom_reference and self.create_version_on_submit:
            version_doc = frappe.new_doc("BOM Version")
            version_doc.update({
                "bom_name": self.bom_reference,
                "version": self.version or "1.0",
                "bom_enhancement": self.name,
                "effective_date": self.valid_from,
                "status": "Approved"
            })
            version_doc.insert()
    
    def update_related_bom(self):
        """Update related BOM with enhancement references"""
        if self.bom_reference:
            frappe.db.set_value("BOM", self.bom_reference, {
                "has_enhancements": 1,
                "last_enhancement_date": frappe.utils.nowdate()
            })
    
    @frappe.whitelist()
    def get_bom_details(self):
        """Fetch BOM details for the reference"""
        if self.bom_reference:
            bom = frappe.get_doc("BOM", self.bom_reference)
            return {
                "item": bom.item,
                "item_name": bom.item_name,
                "quantity": bom.quantity,
                "uom": bom.uom
            }
        return {}

    @frappe.whitelist()
    def create_enhanced_bom(self):
        """Create a new BOM based on enhancement template"""
        if not self.bom_reference:
            frappe.throw(_("Please select a BOM Reference first"))
        
        # Create new BOM with enhancements
        original_bom = frappe.get_doc("BOM", self.bom_reference)
        new_bom = frappe.new_doc("BOM")
        
        # Copy basic fields
        new_bom.update({
            "item": original_bom.item,
            "item_name": original_bom.item_name,
            "quantity": original_bom.quantity,
            "uom": original_bom.uom,
            "is_active": 1,
            "is_default": 0,
            "with_operations": original_bom.with_operations,
            "transfer_material_against": original_bom.transfer_material_against,
            "rm_cost_as_per": original_bom.rm_cost_as_per,
            "source_bom": self.bom_reference,
            "bom_enhancement_reference": self.name
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
            "message": _("Enhanced BOM {0} created successfully").format(new_bom.name)
        }

# Server-side methods
@frappe.whitelist()
def get_available_boms():
    """Get list of BOMs that can be enhanced"""
    boms = frappe.get_all("BOM",
        filters={"is_active": 1},
        fields=["name", "item", "item_name", "quantity", "uom"]
    )
    return boms

@frappe.whitelist()
def create_bom_from_template(template_name, bom_reference):
    """Create BOM enhancement from template"""
    template = frappe.get_doc("BOM Template", template_name)
    enhancement = frappe.new_doc("BOM Enhancement")
    
    enhancement.update({
        "bom_reference": bom_reference,
        "enhancement_type": template.enhancement_type,
        "priority": template.priority,
        "description": template.description,
        "notes": template.notes
    })
    
    enhancement.insert()
    
    return enhancement.name
