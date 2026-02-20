"""
Product Compliance DocType Controller

This module manages product compliance tracking across different countries
and regulatory frameworks, ensuring aloe vera products meet all requirements.
"""

import frappe
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import nowdate, add_months, date_diff, cstr
from frappe import _

class ProductCompliance(WebsiteGenerator):
    # Website configuration to fix the AttributeError
    website = frappe._dict({
        'condition_field': 'published',
        'page_title_field': 'title',
        'route': 'product-compliance'
    })
    """
    Product Compliance DocType controller.
    
    Manages compliance status tracking for aloe vera products across
    different countries and regulatory jurisdictions.
    """
    
    def validate(self):
        """Validate product compliance before saving."""
        self.validate_dates()
        self.validate_compliance_status()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_compliance_percentage()
        self.check_expiry_dates()
        
    def on_update(self):
        """Called after updating the document."""
        self.send_compliance_alerts()
        
    def validate_dates(self):
        """Validate date fields."""
        if self.manufacturing_date and self.expiry_date:
            if self.manufacturing_date >= self.expiry_date:
                frappe.throw(_("Manufacturing date cannot be after expiry date"))
                
        if self.last_review_date and self.next_review_date:
            if self.last_review_date > self.next_review_date:
                frappe.throw(_("Last review date cannot be after next review date"))
                
    def validate_compliance_status(self):
        """Validate compliance status consistency."""
        if self.compliance_status == "Compliant" and self.compliance_percentage < 100:
            frappe.msgprint(_("Warning: Product marked as compliant but compliance percentage is less than 100%"), 
                          indicator="orange")
            
        if self.compliance_status == "Non-Compliant" and not self.outstanding_requirements:
            frappe.msgprint(_("Please specify outstanding requirements for non-compliant products"),
                          indicator="orange")
            
    def set_defaults(self):
        """Set default values."""
        if not self.compliance_status:
            self.compliance_status = "Pending Review"
            
        if not self.risk_level:
            self.risk_level = "Medium"
            
        if not self.testing_status:
            self.testing_status = "Not Started"
            
        if not self.approval_status:
            self.approval_status = "Not Submitted"
            
        if not self.next_review_date:
            self.next_review_date = add_months(nowdate(), 12)
            
    def update_compliance_percentage(self):
        """Calculate compliance percentage based on various factors."""
        if not self.compliance_percentage:
            percentage = 0
            
            # Basic information completeness (20%)
            if all([self.product_name, self.country, self.product_category]):
                percentage += 20
                
            # Regulatory information (30%)
            if self.approval_status == "Approved":
                percentage += 30
            elif self.approval_status in ["Pending Approval", "Conditional Approval"]:
                percentage += 15
                
            # Testing completion (25%)
            if self.testing_status == "Completed":
                percentage += 25
            elif self.testing_status == "In Progress":
                percentage += 10
                
            # Documentation (25%)
            if self.supporting_documents and self.regulatory_submissions:
                percentage += 25
            elif self.supporting_documents or self.regulatory_submissions:
                percentage += 12
                
            self.compliance_percentage = min(percentage, 100)
            
    def check_expiry_dates(self):
        """Check for approaching expiry dates."""
        if self.expiry_date:
            days_to_expiry = date_diff(self.expiry_date, nowdate())
            if days_to_expiry <= 30 and days_to_expiry > 0:
                self.add_comment("Comment", f"Product expires in {days_to_expiry} days")
            elif days_to_expiry <= 0:
                self.compliance_status = "Expired"
                
        if self.next_review_date:
            days_to_review = date_diff(self.next_review_date, nowdate())
            if days_to_review <= 7 and days_to_review > 0:
                self.add_comment("Comment", f"Compliance review due in {days_to_review} days")
                
    def send_compliance_alerts(self):
        """Send alerts for compliance issues."""
        alerts = []
        
        # Check for critical compliance issues
        if self.compliance_status == "Non-Compliant":
            alerts.append("Product is non-compliant and requires immediate attention")
            
        if self.risk_level == "Critical":
            alerts.append("Product has critical risk level")
            
        if self.expiry_date and date_diff(self.expiry_date, nowdate()) <= 30:
            alerts.append("Product expiry approaching")
            
        # Send notifications if there are alerts
        if alerts and self.responsible_person:
            try:
                frappe.sendmail(
                    recipients=[self.contact_email or frappe.db.get_value("User", self.responsible_person, "email")],
                    subject=f"Compliance Alert: {self.product_name}",
                    message=f"<ul>{''.join([f'<li>{alert}</li>' for alert in alerts])}</ul>"
                )
            except Exception as e:
                frappe.log_error(f"Failed to send compliance alert: {str(e)}")
                
    @frappe.whitelist()
    def get_compliance_summary(self):
        """Get comprehensive compliance summary."""
        summary = {
            "product_name": self.product_name,
            "country": self.country,
            "compliance_status": self.compliance_status,
            "compliance_percentage": self.compliance_percentage or 0,
            "risk_level": self.risk_level,
            "approval_status": self.approval_status,
            "testing_status": self.testing_status
        }
        
        # Calculate days to next review
        if self.next_review_date:
            summary["days_to_review"] = date_diff(self.next_review_date, nowdate())
            
        # Calculate days to expiry
        if self.expiry_date:
            summary["days_to_expiry"] = date_diff(self.expiry_date, nowdate())
            
        # Get country-specific requirements
        country_reqs = frappe.get_value("Country Regulation", self.country, 
                                      ["regulatory_authority", "key_requirements"], as_dict=True)
        if country_reqs:
            summary["regulatory_authority"] = country_reqs.regulatory_authority
            summary["key_requirements"] = country_reqs.key_requirements
            
        return summary
        
    @frappe.whitelist()
    def update_compliance_status(self, new_status, notes=None):
        """Update compliance status with audit trail."""
        old_status = self.compliance_status
        self.compliance_status = new_status
        
        # Update audit trail
        audit_entry = f"{nowdate()}: Status changed from {old_status} to {new_status} by {frappe.session.user}"
        if notes:
            audit_entry += f" - Notes: {notes}"
            
        if self.audit_trail:
            self.audit_trail += f"<br>{audit_entry}"
        else:
            self.audit_trail = audit_entry
            
        self.save()
        return _("Compliance status updated successfully")
    
    def before_save(self):
        """Set route before saving"""
        #super().before_save()
        if not getattr(self, 'route', None):
            product = getattr(self, 'product_name', '') or getattr(self, 'item_code', '')
            country = getattr(self, 'country', '') or getattr(self, 'region', '')
            
            if product and country:
                self.route = self.scrub(f"{product}-compliance-{country}")
            elif product:
                self.route = self.scrub(f"product-compliance-{product}")
            elif getattr(self, 'title', None):
                self.route = self.scrub(self.title)
    
    def get_context(self, context):
        """Website context for rendering"""
        context.no_cache = 1
        context.show_sidebar = True
        context.parents = [{"title": _("Product Compliance"), "route": "product-compliance"}]
        
        # Add related compliance records
        context.related_compliance = self.get_related_compliance()
        
        # Add compliance statistics
        context.compliance_stats = self.get_compliance_stats()
        
        return context
    
    def get_related_compliance(self):
        """Get related product compliance records"""
        filters = {
            "name": ["!=", self.name],
            "published": 1
        }
        
        # Add product filter if available
        if getattr(self, 'product_name', None):
            filters["product_name"] = self.product_name
        
        return frappe.get_all(
            "Product Compliance",
            filters=filters,
            fields=["name", "product_name", "country", "compliance_status", "route"],
            limit=5
        )
    
    def get_compliance_stats(self):
        """Get compliance statistics for context"""
        stats = {}
        
        if getattr(self, 'product_name', None):
            stats = {
                "total_records": frappe.db.count("Product Compliance", {"product_name": self.product_name}),
                "compliant_records": frappe.db.count("Product Compliance", {
                    "product_name": self.product_name,
                    "compliance_status": "Compliant"
                }),
                "non_compliant_records": frappe.db.count("Product Compliance", {
                    "product_name": self.product_name,
                    "compliance_status": "Non-Compliant"
                })
            }
        
        return stats
    
    def get_feed(self):
        """Feed for timeline"""
        product = getattr(self, 'product_name', '') or 'Unknown Product'
        status = getattr(self, 'compliance_status', '') or 'Unknown Status'
        return f"Product Compliance: {product} - {status}"
    
    def scrub(self, text):
        """Convert text to URL-friendly format"""
        import re
        return re.sub(r'[^a-zA-Z0-9]+', '-', cstr(text)).strip('-').lower()

# Utility functions

@frappe.whitelist()
def get_compliance_dashboard_data():
    """Get dashboard data for product compliance."""
    
    # Compliance status distribution
    status_data = frappe.db.sql("""
        SELECT compliance_status, COUNT(*) as count
        FROM `tabProduct Compliance`
        GROUP BY compliance_status
    """, as_dict=True)
    
    # Risk level distribution
    risk_data = frappe.db.sql("""
        SELECT risk_level, COUNT(*) as count
        FROM `tabProduct Compliance`
        GROUP BY risk_level
    """, as_dict=True)
    
    # Country-wise compliance
    country_data = frappe.db.sql("""
        SELECT country, compliance_status, COUNT(*) as count
        FROM `tabProduct Compliance`
        GROUP BY country, compliance_status
    """, as_dict=True)
    
    # Products expiring soon (within 90 days)
    expiring_soon = frappe.db.sql("""
        SELECT product_name, country, expiry_date,
               DATEDIFF(expiry_date, CURDATE()) as days_to_expiry
        FROM `tabProduct Compliance`
        WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 90 DAY)
        ORDER BY expiry_date
    """, as_dict=True)
    
    return {
        "status_distribution": status_data,
        "risk_distribution": risk_data,
        "country_compliance": country_data,
        "expiring_products": expiring_soon
    }

@frappe.whitelist()
def get_compliance_by_country(country):
    """Get compliance data for a specific country."""
    
    compliance_data = frappe.get_all(
        "Product Compliance",
        filters={"country": country},
        fields=[
            "name", "product_name", "compliance_status", "compliance_percentage",
            "risk_level", "approval_status", "next_review_date", "expiry_date"
        ],
        order_by="compliance_percentage desc"
    )
    
    return compliance_data

@frappe.whitelist()
def bulk_update_compliance_status(product_names, new_status, notes=None):
    """Bulk update compliance status for multiple products."""
    
    if isinstance(product_names, str):
        product_names = frappe.parse_json(product_names)
        
    updated_count = 0
    
    for product_name in product_names:
        try:
            doc = frappe.get_doc("Product Compliance", product_name)
            doc.update_compliance_status(new_status, notes)
            updated_count += 1
        except Exception as e:
            frappe.log_error(f"Error updating compliance for {product_name}: {str(e)}")
            
    return _("{0} products updated successfully").format(updated_count)

@frappe.whitelist()
def generate_compliance_report(country=None, status=None, risk_level=None):
    """Generate compliance report with filters."""
    
    filters = {}
    if country:
        filters["country"] = country
    if status:
        filters["compliance_status"] = status
    if risk_level:
        filters["risk_level"] = risk_level
        
    products = frappe.get_all(
        "Product Compliance",
        filters=filters,
        fields=[
            "name", "product_name", "product_code", "country", "compliance_status",
            "compliance_percentage", "risk_level", "approval_status", "testing_status",
            "next_review_date", "expiry_date", "responsible_person"
        ],
        order_by="country, product_name"
    )
    
    return products
