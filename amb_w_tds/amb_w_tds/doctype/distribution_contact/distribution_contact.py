"""
Distribution Contact DocType Controller

This module contains the server-side logic for managing distribution contacts
including validation, integration with organization data, and communication tracking.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import validate_email_address, nowdate, now
from frappe import _

class DistributionContact(Document):
    """
    Distribution Contact DocType controller.
    
    Handles business logic for managing contacts within distribution organizations,
    communication preferences, and regulatory role tracking.
    """
    
    # Website attributes to fix the AttributeError
    website = frappe._dict(
        condition_field="disabled",  # Uses the 'disabled' field to determine if web view should be shown
        page_title_field="full_name"  # Uses 'full_name' as the page title in web view
    )
    
    def validate(self):
        """Validate the distribution contact before saving."""
        self.validate_email()
        self.validate_organization()
        self.set_full_name()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_organization_country()
        
    def after_insert(self):
        """Called after inserting a new distribution contact."""
        self.create_contact_link()
        self.send_welcome_notification()
        
    def on_update(self):
        """Called after updating the distribution contact."""
        self.update_linked_contact()
        
    def validate_email(self):
        """Validate email address format and uniqueness."""
        if self.email_id:
            if not validate_email_address(self.email_id):
                frappe.throw(_("Please enter a valid email address"))
                
            # Check for duplicate email within the same organization
            existing = frappe.db.get_value(
                "Distribution Contact",
                {
                    "email_id": self.email_id,
                    "organization": self.organization,
                    "name": ["!=", self.name or ""]
                },
                "name"
            )
            
            if existing:
                frappe.throw(_("A contact with this email already exists in the organization"))
                
    def validate_organization(self):
        """Validate organization relationship."""
        if self.organization:
            org_doc = frappe.get_doc("Distribution Organization", self.organization)
            
            # Check if organization is active
            if org_doc.status not in ["Active", "Pending"]:
                frappe.msgprint(
                    _("Warning: The organization {0} is not active").format(self.organization),
                    indicator="orange"
                )
                
    def set_full_name(self):
        """Set the full name based on first and last name."""
        if self.first_name:
            if self.last_name:
                self.full_name = f"{self.first_name} {self.last_name}"
            else:
                self.full_name = self.first_name
                
    def set_defaults(self):
        """Set default values based on business rules."""
        if not self.status:
            self.status = "Active"
            
        if not self.communication_preference:
            self.communication_preference = "Email"
            
        if not self.contact_frequency:
            self.contact_frequency = "Monthly"
            
        # Set default regulatory role based on designation
        if not self.regulatory_role and self.designation:
            role_mapping = {
                "Quality Manager": "Quality Manager",
                "QA Manager": "Quality Manager", 
                "Regulatory Affairs": "Regulatory Affairs Manager",
                "Product Manager": "Product Manager",
                "Sales Manager": "Sales Manager",
                "Business Development": "Business Development",
                "Compliance": "Compliance Officer",
                "Legal": "Legal Counsel"
            }
            
            for key, role in role_mapping.items():
                if key.lower() in self.designation.lower():
                    self.regulatory_role = role
                    break
                    
    def update_organization_country(self):
        """Update contact's country from organization if not set."""
        if self.organization and not self.country:
            org_country = frappe.db.get_value(
                "Distribution Organization", 
                self.organization, 
                "country"
            )
            if org_country:
                self.country = org_country
                
    def create_contact_link(self):
        """Create corresponding Contact record in ERPNext."""
        try:
            if not frappe.db.exists("Contact", {"email_id": self.email_id}):
                contact = frappe.new_doc("Contact")
                contact.first_name = self.first_name
                contact.last_name = self.last_name
                contact.email_id = self.email_id
                contact.phone = self.phone
                contact.mobile_no = self.mobile_no
                contact.designation = self.designation
                contact.department = self.department
                
                # Add organization link
                if self.organization:
                    # Check if organization has corresponding Customer/Supplier
                    org_doc = frappe.get_doc("Distribution Organization", self.organization)
                    
                    customer_name = frappe.db.get_value(
                        "Customer",
                        {"custom_distribution_organization": self.organization},
                        "name"
                    )
                    
                    supplier_name = frappe.db.get_value(
                        "Supplier", 
                        {"custom_distribution_organization": self.organization},
                        "name"
                    )
                    
                    if customer_name:
                        contact.append("links", {
                            "link_doctype": "Customer",
                            "link_name": customer_name
                        })
                        
                    if supplier_name:
                        contact.append("links", {
                            "link_doctype": "Supplier", 
                            "link_name": supplier_name
                        })
                
                contact.save(ignore_permissions=True)
                
                # Link back to distribution contact
                contact.db_set("custom_distribution_contact", self.name)
                
        except Exception as e:
            frappe.log_error(
                message=f"Error creating Contact link: {str(e)}",
                title="Distribution Contact Link Creation Error"
            )
            
    def send_welcome_notification(self):
        """Send welcome notification to the contact."""
        if self.email_id and self.status == "Active":
            try:
                frappe.sendmail(
                    recipients=[self.email_id],
                    subject=_("Welcome to Our Distribution Network"),
                    template="welcome_distribution_contact",
                    args={
                        "full_name": self.full_name,
                        "organization": self.organization,
                        "designation": self.designation,
                        "regulatory_role": self.regulatory_role
                    }
                )
                
                # Update last contacted
                self.db_set("last_contacted", now())
                
            except Exception as e:
                frappe.log_error(
                    message=f"Error sending welcome email: {str(e)}",
                    title="Welcome Email Error"
                )
                
    def update_linked_contact(self):
        """Update linked Contact record with current information."""
        try:
            contact_name = frappe.db.get_value(
                "Contact",
                {"custom_distribution_contact": self.name},
                "name"
            )
            
            if contact_name:
                contact = frappe.get_doc("Contact", contact_name)
                contact.first_name = self.first_name
                contact.last_name = self.last_name
                contact.phone = self.phone
                contact.mobile_no = self.mobile_no
                contact.designation = self.designation
                contact.department = self.department
                contact.save(ignore_permissions=True)
                
        except Exception as e:
            frappe.log_error(
                message=f"Error updating linked Contact: {str(e)}",
                title="Contact Update Error"
            )
            
    @frappe.whitelist()
    def get_organization_details(self):
        """Get details about the contact's organization."""
        if not self.organization:
            return {}
            
        org_doc = frappe.get_doc("Distribution Organization", self.organization)
        
        return {
            "organization_name": org_doc.organization_name,
            "organization_type": org_doc.organization_type,
            "country": org_doc.country,
            "territory": org_doc.territory,
            "status": org_doc.status,
            "regulatory_status": org_doc.regulatory_status,
            "website": org_doc.website,
            "primary_contact": org_doc.contact_person,
            "primary_email": org_doc.email_id
        }
        
    @frappe.whitelist()
    def get_communication_history(self):
        """Get communication history for this contact."""
        communications = frappe.get_all(
            "Communication",
            filters={"recipients": ["like", f"%{self.email_id}%"]},
            fields=[
                "name", "subject", "content", "sent_or_received",
                "communication_type", "creation", "sender", "status"
            ],
            order_by="creation desc",
            limit=20
        )
        
        return communications
        
    @frappe.whitelist()
    def update_last_contacted(self):
        """Update the last contacted timestamp."""
        self.db_set("last_contacted", now())
        return _("Last contacted timestamp updated")
        
    @frappe.whitelist()
    def get_regulatory_requirements(self):
        """Get regulatory requirements relevant to this contact's role and country."""
        requirements = []
        
        if self.country:
            country_regs = frappe.get_all(
                "Country Regulation",
                filters={"country_name": self.country},
                fields=["name", "regulatory_authority", "key_requirements"]
            )
            
            for reg in country_regs:
                requirements.append({
                    "source": "Country Regulation",
                    "authority": reg.regulatory_authority,
                    "requirements": reg.key_requirements or "Not specified"
                })
                
        # Add role-specific requirements
        if self.regulatory_role:
            role_requirements = {
                "Quality Manager": [
                    "Quality Management System certification",
                    "Good Manufacturing Practices compliance",
                    "Product testing and validation protocols"
                ],
                "Regulatory Affairs Manager": [
                    "Product registration and approval",
                    "Regulatory submission management", 
                    "Compliance monitoring and reporting"
                ],
                "Product Manager": [
                    "Product labeling compliance",
                    "Market authorization requirements",
                    "Product lifecycle management"
                ],
                "Compliance Officer": [
                    "Audit preparation and management",
                    "Documentation compliance",
                    "Training and awareness programs"
                ]
            }
            
            if self.regulatory_role in role_requirements:
                requirements.append({
                    "source": "Role-specific",
                    "authority": self.regulatory_role,
                    "requirements": role_requirements[self.regulatory_role]
                })
                
        return requirements
        
    def get_dashboard_data(self):
        """Get data for the contact dashboard."""
        return {
            "fieldname": "distribution_contact",
            "transactions": [
                {
                    "label": _("Organization"),
                    "items": ["Distribution Organization"]
                },
                {
                    "label": _("Communications"),
                    "items": ["Communication", "Email Campaign"]
                },
                {
                    "label": _("Compliance"),
                    "items": ["Product Compliance", "Certification Document"]
                }
            ]
        }

# Utility functions for the DocType

@frappe.whitelist()
def get_contacts_by_organization(organization):
    """Get all contacts for a specific organization."""
    
    contacts = frappe.get_all(
        "Distribution Contact",
        filters={"organization": organization},
        fields=[
            "name", "full_name", "designation", "email_id", 
            "phone", "regulatory_role", "status", "last_contacted"
        ],
        order_by="full_name"
    )
    
    return contacts

@frappe.whitelist()
def get_contacts_by_regulatory_role(regulatory_role, country=None):
    """Get contacts by regulatory role, optionally filtered by country."""
    
    filters = {"regulatory_role": regulatory_role}
    if country:
        filters["country"] = country
        
    contacts = frappe.get_all(
        "Distribution Contact",
        filters=filters,
        fields=[
            "name", "full_name", "organization", "email_id",
            "phone", "country", "status"
        ],
        order_by="full_name"
    )
    
    return contacts

@frappe.whitelist()
def bulk_update_contact_status(contact_names, new_status):
    """Bulk update status for multiple contacts."""
    
    if isinstance(contact_names, str):
        contact_names = frappe.parse_json(contact_names)
        
    updated_count = 0
    
    for contact_name in contact_names:
        try:
            frappe.db.set_value("Distribution Contact", contact_name, "status", new_status)
            updated_count += 1
        except Exception as e:
            frappe.log_error(
                message=f"Error updating contact {contact_name}: {str(e)}",
                title="Bulk Contact Update Error"
            )
            
    frappe.db.commit()
    
    return _("{0} contacts updated successfully").format(updated_count)

@frappe.whitelist()
def export_contacts_for_organization(organization):
    """Export contact data for a specific organization."""
    
    contacts = frappe.get_all(
        "Distribution Contact",
        filters={"organization": organization},
        fields="*"
    )
    
    # Format data for export
    export_data = []
    for contact in contacts:
        export_data.append({
            "Full Name": contact.get("full_name"),
            "Email": contact.get("email_id"),
            "Phone": contact.get("phone"),
            "Mobile": contact.get("mobile_no"),
            "Designation": contact.get("designation"),
            "Department": contact.get("department"),
            "Regulatory Role": contact.get("regulatory_role"),
            "Status": contact.get("status"),
            "Country": contact.get("country"),
            "Last Contacted": contact.get("last_contacted")
        })
        
    return export_data
