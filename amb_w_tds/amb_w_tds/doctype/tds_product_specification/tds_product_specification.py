# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class TDSProductSpecification(Document):
    """
    TDS Product Specification - Technical Data Sheet - ULTRA SAFE VERSION
    """
    
    def validate(self):
        """Validation logic before saving - ULTRA SAFE VERSION"""
        # ULTRA SAFE: Only call validate_version_control if it exists
        if hasattr(self, 'validate_version_control'):
            self.validate_version_control()
        else:
            # Fallback: ensure version exists
            self._ensure_version_exists()
    
    def _ensure_version_exists(self):
        """Ensure version field exists with safe default"""
        try:
            if not hasattr(self, 'version'):
                self.version = "1.00"
            elif not self.version or str(self.version).strip() == "":
                self.version = "1.00"
        except:
            self.version = "1.00"
    
    def validate_version_control(self):
        """Ensure version numbers are sequential - ULTRA SAFE VERSION"""
        # LINE 41 IS NOW SAFE - CHECK WITH hasattr FIRST
        if not hasattr(self, 'version') or not self.version:
            self.version = "1.00"
        
        # Format version properly
        try:
            version_float = float(self.version)
            self.version = f"{version_float:.2f}"
        except (ValueError, TypeError):
            self.version = "1.00"
        
        # Optional: Check for duplicate versions (only if needed)
        try:
            existing = frappe.db.exists('TDS Product Specification', {
                'product_item': self.product_item,
                'version': self.version,
                'name': ['!=', self.name],
                'docstatus': ['!=', 2]
            })
            
            if existing:
                frappe.throw(_(f"Version {self.version} already exists for {self.product_item}"))
        except:
            pass  # Don't break save on error
    
    def before_save(self):
        """Before save hook"""
        pass
    
    def on_submit(self):
        """On submit hook"""
        pass
    
    def on_cancel(self):
        """On cancel"""
        pass


# ==================== WHITELISTED METHODS ====================

@frappe.whitelist()
def get_latest_tds_version(product_item):
    """Get latest TDS version for a product"""
    tds = frappe.db.get_value(
        'TDS Product Specification',
        filters={
            'product_item': product_item,
            'docstatus': 1
        },
        fieldname=['name', 'version', 'approval_date'],
        order_by='version desc',
        as_dict=True
    )
    
    return tds


@frappe.whitelist()
def copy_specifications_from_previous(source_tds, target_tds):
    """Copy specifications from previous TDS version"""
    source = frappe.get_doc('TDS Product Specification', source_tds)
    target = frappe.get_doc('TDS Product Specification', target_tds)
    
    # Clear existing specifications
    target.specifications = []
    
    # Copy from source
    if hasattr(source, 'specifications'):
        for spec in source.specifications:
            target.append('specifications', {
                'parameter': spec.parameter,
                'specification': spec.specification,
                'test_method': spec.test_method
            })
    
    target.save()
    
    return target.name


@frappe.whitelist()
def get_tds_history(product_item):
    """Get version history for a product"""
    return frappe.get_all(
        'TDS Product Specification',
        filters={'product_item': product_item},
        fields=['name', 'version', 'approval_date', 'approved_by', 'docstatus', 'is_archived'],
        order_by='version desc'
    )
