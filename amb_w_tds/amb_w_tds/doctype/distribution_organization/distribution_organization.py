"""
Distribution Organization DocType Controller

This module contains the server-side logic for managing distribution organizations
including validation, business rules, and integration with other modules.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import validate_email_address, nowdate, add_days
from frappe import _

class DistributionOrganization(Document):
    """
    Distribution Organization DocType controller.
    
    Handles business logic for managing global distribution partners,
    regulatory compliance tracking, and integration with ERPNext modules.
    """
    website = frappe._dict(
        condition_field="disabled",
        page_title_field="organization_name"
    )
    def validate(self):
        """Validate the distribution organization before saving."""
        self.validate_email()
        self.validate_parent_organization()
        self.validate_agreement_dates()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_compliance_status()
        
    def after_insert(self):
        """Called after inserting a new distribution organization."""
        self.create_customer_supplier_links()
        self.send_welcome_notification()
        
    def on_update(self):
        """Called after updating the distribution organization."""
        self.update_linked_records()
        
    def validate_email(self):
        """Validate email address format."""
        if self.email_id:
            if not validate_email_address(self.email_id):
                frappe.throw(_("Please enter a valid email address"))
                
    def validate_parent_organization(self):
        """Validate parent organization relationship."""
        if self.parent_organization:
            if self.parent_organization == self.name:
                frappe.throw(_("Organization cannot be its own parent"))
                
            # Check for circular reference
            parent_doc = frappe.get_doc("Distribution Organization", self.parent_organization)
            if parent_doc.parent_organization == self.name:
                frappe.throw(_("Circular parent-child relationship not allowed"))
                
    def validate_agreement_dates(self):
        """Validate distribution agreement dates."""
        if self.agreement_expiry:
            if self.agreement_expiry < nowdate():
                frappe.msgprint(_("Distribution agreement has expired"), indicator="orange")
                
    def set_defaults(self):
        """Set default values based on business rules."""
        if not self.status:
            self.status = "Active"
            
        if not self.regulatory_status:
            self.regulatory_status = "Pending Review"
            
        if self.country and not self.currency:
            # Try to get default currency for the country
            country_doc = frappe.get_doc("Country", self.country)
            if hasattr(country_doc, 'default_currency') and country_doc.default_currency:
                self.currency = country_doc.default_currency
                
    def update_compliance_status(self):
        """Update compliance status based on certifications and audit dates."""
        if self.last_audit_date and self.next_audit_due:
            if nowdate() > self.next_audit_due:
                if self.regulatory_status in ["Compliant", "Pending Review"]:
                    self.regulatory_status = "Expired"
                    
    def create_customer_supplier_links(self):
        """Create corresponding Customer and/or Supplier records."""
        try:
            # Create Customer record for distributors and retailers
            if self.organization_type in ["Distributor", "Retailer", "Wholesaler"]:
                if not frappe.db.exists("Customer", self.organization_name):
                    customer = frappe.new_doc("Customer")
                    customer.customer_name = self.organization_name
                    customer.customer_type = "Company"
                    customer.customer_group = "Commercial"  # Default group
                    customer.territory = self.territory or "All Territories"
                    customer.save(ignore_permissions=True)
                    
                    # Link back to distribution organization
                    customer.db_set("custom_distribution_organization", self.name)
                    
            # Create Supplier record for suppliers and manufacturers
            if self.organization_type in ["Supplier", "Manufacturer"]:
                if not frappe.db.exists("Supplier", self.organization_name):
                    supplier = frappe.new_doc("Supplier")
                    supplier.supplier_name = self.organization_name
                    supplier.supplier_type = "Company"
                    supplier.supplier_group = "Raw Material"  # Default group
                    supplier.save(ignore_permissions=True)
                    
                    # Link back to distribution organization
                    supplier.db_set("custom_distribution_organization", self.name)
                    
        except Exception as e:
            frappe.log_error(
                message=f"Error creating Customer/Supplier links: {str(e)}",
                title="Distribution Organization Link Creation Error"
            )
            
    def send_welcome_notification(self):
        """Send welcome notification to the organization contact."""
        if self.email_id and self.contact_person:
            try:
                frappe.sendmail(
                    recipients=[self.email_id],
                    subject=_("Welcome to Our Distribution Network"),
                    template="welcome_distribution_partner",
                    args={
                        "organization_name": self.organization_name,
                        "contact_person": self.contact_person,
                        "territory": self.territory,
                        "organization_type": self.organization_type
                    }
                )
            except Exception as e:
                frappe.log_error(
                    message=f"Error sending welcome email: {str(e)}",
                    title="Welcome Email Error"
                )
                
    def update_linked_records(self):
        """Update linked Customer and Supplier records with current information."""
        try:
            # Update Customer record
            customer_name = frappe.db.get_value(
                "Customer", 
                {"custom_distribution_organization": self.name}, 
                "name"
            )
            if customer_name:
                customer = frappe.get_doc("Customer", customer_name)
                customer.territory = self.territory or "All Territories"
                customer.save(ignore_permissions=True)
                
            # Update Supplier record
            supplier_name = frappe.db.get_value(
                "Supplier",
                {"custom_distribution_organization": self.name},
                "name"
            )
            if supplier_name:
                supplier = frappe.get_doc("Supplier", supplier_name)
                # Update supplier information as needed
                supplier.save(ignore_permissions=True)
                
        except Exception as e:
            frappe.log_error(
                message=f"Error updating linked records: {str(e)}",
                title="Linked Records Update Error"
            )
            
    @frappe.whitelist()
    def get_country_regulations(self):
        """Get regulatory requirements for the organization's country."""
        if not self.country:
            return []
            
        regulations = frappe.get_all(
            "Country Regulation",
            filters={"country_name": self.country},
            fields=["name", "regulatory_authority", "authority_website", "key_requirements"]
        )
        
        return regulations
        
    @frappe.whitelist() 
    def get_compliance_checklist(self):
        """Get compliance checklist for the organization."""
        checklist = []
        
        # Basic information compliance
        checklist.append({
            "item": "Organization Information Complete",
            "status": "Complete" if all([self.organization_name, self.country, self.contact_person]) else "Incomplete",
            "details": "Basic organization details and contact information"
        })
        
        # Regulatory compliance
        checklist.append({
            "item": "Regulatory Status",
            "status": self.regulatory_status or "Not Set",
            "details": f"Current status: {self.regulatory_status or 'Not specified'}"
        })
        
        # Agreement status
        if self.agreement_expiry:
            days_to_expiry = frappe.utils.date_diff(self.agreement_expiry, nowdate())
            if days_to_expiry < 0:
                agreement_status = "Expired"
            elif days_to_expiry < 30:
                agreement_status = "Expiring Soon"
            else:
                agreement_status = "Valid"
        else:
            agreement_status = "Not Set"
            
        checklist.append({
            "item": "Distribution Agreement",
            "status": agreement_status,
            "details": f"Expiry: {self.agreement_expiry or 'Not specified'}"
        })
        
        return checklist
        
    def get_dashboard_data(self):
        """Get data for the organization dashboard."""
        return {
            "fieldname": "distribution_organization",
            "transactions": [
                {
                    "label": _("Contacts"),
                    "items": ["Distribution Contact"]
                },
                {
                    "label": _("Compliance"),
                    "items": ["Product Compliance", "Certification Document"]
                },
                {
                    "label": _("Business"),
                    "items": ["Customer", "Supplier", "Sales Order", "Purchase Order"]
                }
            ]
        }

# Utility functions for the DocType

@frappe.whitelist()
def get_organization_hierarchy(organization_name):
    """Get the organizational hierarchy for a given organization."""
    
    def get_children(parent):
        children = frappe.get_all(
            "Distribution Organization",
            filters={"parent_organization": parent},
            fields=["name", "organization_name", "organization_type", "status"]
        )
        
        for child in children:
            child["children"] = get_children(child["name"])
            
        return children
    
    # Get the root organization and its hierarchy
    organization = frappe.get_doc("Distribution Organization", organization_name)
    hierarchy = {
        "name": organization.name,
        "organization_name": organization.organization_name,
        "organization_type": organization.organization_type,
        "status": organization.status,
        "children": get_children(organization.name)
    }
    
    return hierarchy

@frappe.whitelist()
def get_organizations_by_country(country):
    """Get all distribution organizations in a specific country."""
    
    organizations = frappe.get_all(
        "Distribution Organization",
        filters={"country": country},
        fields=[
            "name", "organization_name", "organization_type", 
            "status", "regulatory_status", "contact_person", "email_id"
        ],
        order_by="organization_name"
    )
    
    return organizations

@frappe.whitelist()
def check_duplicate_organization(organization_name, country):
    """Check if an organization with the same name exists in the same country."""
    
    existing = frappe.db.get_value(
        "Distribution Organization",
        {"organization_name": organization_name, "country": country},
        "name"
    )
    
    return {"exists": bool(existing), "name": existing}
