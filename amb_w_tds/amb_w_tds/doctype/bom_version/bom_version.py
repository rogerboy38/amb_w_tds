# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class BOMVersion(Document):
    def validate(self):
        """Validate BOM Version"""
        self.validate_version_uniqueness()
        self.validate_effective_dates()
        self.manage_active_version()
    
    def validate_version_uniqueness(self):
        """Ensure version number is unique for this BOM Template"""
        existing = frappe.db.exists("BOM Version", {
            "bom_template": self.bom_template,
            "version_number": self.version_number,
            "name": ["!=", self.name]
        })
        if existing:
            frappe.throw(_("Version {0} already exists for BOM Template {1}").format(
                self.version_number, self.bom_template
            ))
    
    def validate_effective_dates(self):
        """Validate effective date range"""
        if self.effective_from and self.effective_to:
            if self.effective_from > self.effective_to:
                frappe.throw(_("Effective From date cannot be after Effective To date"))
    
    def manage_active_version(self):
        """Ensure only one active version per BOM Template"""
        if self.is_active:
            # Deactivate other active versions for this BOM Template
            frappe.db.sql("""
                UPDATE `tabBOM Version` 
                SET is_active = 0 
                WHERE bom_template = %s 
                AND name != %s 
                AND is_active = 1
            """, (self.bom_template, self.name))
