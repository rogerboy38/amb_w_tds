# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class TDSProductSpecification(Document):
    """
    TDS Product Specification - Technical Data Sheet
    """
    
    def validate(self):
        """Validation logic before saving"""
        self.validate_version_control()
        self.validate_product_item()
        self.set_approval_status()
    
    def before_save(self):
        """Before save hook"""
        self.update_version_counter()
        self.set_naming_series()
    
    def on_submit(self):
        """On submit hook"""
        if self.auto_create_coa:
            self.create_coa_if_needed()
        self.notify_stakeholders()
        self.archive_previous_versions()
    
    def on_cancel(self):
        """On cancel"""
        self.revert_version_status()
    
    # ==================== VALIDATION METHODS ====================
    
    def validate_version_control(self):
        """Ensure version numbers are sequential"""
        if not self.version:
            # Get latest version for this product
            latest = frappe.db.get_value(
                'TDS Product Specification',
                filters={
                    'product_item': self.product_item,
                    'name': ['!=', self.name]
                },
                fieldname='version',
                order_by='version desc'
            )
            self.version = (latest or 0) + 1
        
        # Check if version already exists
        existing = frappe.db.exists('TDS Product Specification', {
            'product_item': self.product_item,
            'version': self.version,
            'name': ['!=', self.name],
            'docstatus': ['!=', 2]
        })
        
        if existing:
            frappe.throw(_(f"Version {self.version} already exists for {self.product_item}"))
    
    def validate_product_item(self):
        """Validate product item exists"""
        if self.product_item:
            if not frappe.db.exists('Item', self.product_item):
                frappe.throw(_("Item {0} does not exist").format(self.product_item))
            
            # Get item details
            item = frappe.get_doc('Item', self.product_item)
            self.item_name = item.item_name
            self.item_code = item.item_code
    
    def set_approval_status(self):
        """Set approval status based on workflow"""
        if self.docstatus == 1:  # Submitted
            self.approval_status = 'Approved'
            if not self.approval_date:
                self.approval_date = nowdate()
            if not self.approved_by:
                self.approved_by = frappe.session.user
        elif self.docstatus == 0:
            self.approval_status = 'Draft'
        elif self.docstatus == 2:
            self.approval_status = 'Cancelled'
    
    # ==================== VERSION CONTROL ====================
    
    def update_version_counter(self):
        """Update version counter from TDS Settings"""
        if not self.tds_version:
            settings = frappe.get_single('TDS Settings')
            if settings:
                self.tds_version = getattr(settings, 'current_version', '1.0')
    
    def set_naming_series(self):
        """Set naming series based on product"""
        if not self.naming_series and self.product_item:
            # Use first 4 chars of item code
            item_prefix = self.product_item[:4].upper()
            self.naming_series = f"TDS-{item_prefix}-.####"
    
    def archive_previous_versions(self):
        """Mark previous versions as archived when new version is approved"""
        if self.docstatus == 1:
            previous_versions = frappe.get_all(
                'TDS Product Specification',
                filters={
                    'product_item': self.product_item,
                    'version': ['<', self.version],
                    'docstatus': 1,
                    'is_archived': 0
                },
                pluck='name'
            )
            
            for prev_tds in previous_versions:
                frappe.db.set_value('TDS Product Specification', prev_tds, 'is_archived', 1)
                frappe.db.set_value('TDS Product Specification', prev_tds, 'archived_date', nowdate())
    
    def revert_version_status(self):
        """Revert archived status of previous version if this is cancelled"""
        if self.version > 1:
            previous_version = frappe.db.get_value(
                'TDS Product Specification',
                filters={
                    'product_item': self.product_item,
                    'version': self.version - 1,
                    'docstatus': 1
                },
                fieldname='name'
            )
            
            if previous_version:
                frappe.db.set_value('TDS Product Specification', previous_version, 'is_archived', 0)
    
    # ==================== DOCUMENT CREATION ====================
    
    def create_coa_if_needed(self):
        """Create COA when TDS is approved"""
        if not self.auto_create_coa:
            return
        
        coa = frappe.new_doc('COA AMB')
        coa.linked_tds = self.name
        coa.product_item = self.product_item
        coa.insert()
        
        frappe.msgprint(_("COA {0} created automatically").format(coa.name))
    
    # ==================== NOTIFICATIONS ====================
    
    def notify_stakeholders(self):
        """Send notifications to relevant parties"""
        recipients = []
        
        # Get R&D team
        rnd_users = frappe.get_all('User', 
            filters={'role': ['like', '%R&D%']},
            pluck='email'
        )
        recipients.extend(rnd_users)
        
        # Get Quality team
        quality_users = frappe.get_all('User', 
            filters={'role': ['like', '%Quality%']},
            pluck='email'
        )
        recipients.extend(quality_users)
        
        if recipients:
            frappe.sendmail(
                recipients=list(set(recipients)),
                subject=f'TDS {self.name} Approved - Version {self.version}',
                message=f"""
                    <p>Technical Data Sheet <strong>{self.name}</strong> has been approved.</p>
                    <ul>
                        <li>Product: {self.item_name}</li>
                        <li>Version: {self.version}</li>
                        <li>Approval Date: {self.approval_date}</li>
                        <li>Approved By: {self.approved_by}</li>
                    </ul>
                    <p><a href="{frappe.utils.get_url()}/app/tds-product-specification/{self.name}">View TDS</a></p>
                """,
                now=True
            )


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
