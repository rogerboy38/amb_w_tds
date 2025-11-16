# Copyright (c) 2025, SPC Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Barrel(Document):
    def validate(self):
        """Validate barrel data before save"""
        self.calculate_available_volume()
        self.calculate_fill_percentage()
        self.validate_fill_level()
    
    def calculate_available_volume(self):
        """Calculate available volume"""
        if self.barrel_volume_gallons and self.current_fill_level_gallons:
            self.available_volume_gallons = self.barrel_volume_gallons - self.current_fill_level_gallons
        else:
            self.available_volume_gallons = self.barrel_volume_gallons or 0
    
    def calculate_fill_percentage(self):
        """Calculate fill percentage"""
        if self.barrel_volume_gallons and self.current_fill_level_gallons:
            self.fill_percentage = (self.current_fill_level_gallons / self.barrel_volume_gallons) * 100
        else:
            self.fill_percentage = 0
    
    def validate_fill_level(self):
        """Validate that fill level doesn't exceed capacity"""
        if self.current_fill_level_gallons and self.barrel_volume_gallons:
            if self.current_fill_level_gallons > self.barrel_volume_gallons:
                frappe.throw(f"Fill level ({self.current_fill_level_gallons} gal) cannot exceed barrel capacity ({self.barrel_volume_gallons} gal)")
    
    def on_update(self):
        """After save actions"""
        self.create_activity_log_on_status_change()
    
    def create_activity_log_on_status_change(self):
        """Create activity log when status changes"""
        if self.has_value_changed('current_status'):
            try:
                activity = frappe.get_doc({
                    'doctype': 'Barrel Activity Log',
                    'barrel': self.name,
                    'activity_type': 'Status Change',
                    'activity_date': frappe.utils.today(),
                    'description': f'Status changed from {self.get_doc_before_save().current_status if self.get_doc_before_save() else "New"} to {self.current_status}',
                    'notes': f'Automatic log entry on status change'
                })
                activity.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to create activity log: {str(e)}")
