"""
Country Regulation DocType Controller

This module contains the server-side logic for managing country-specific
regulatory information for aloe vera products.
"""

import frappe
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import nowdate, add_months, cstr
from frappe import _

class CountryRegulation(WebsiteGenerator):
    # Website configuration to fix the AttributeError
    website = frappe._dict({
        'condition_field': 'published',
        'page_title_field': 'title',
        'route': 'country-regulations'
    })
    """
    Country Regulation DocType controller.
    
    Handles business logic for managing country-specific regulatory requirements,
    compliance tracking, and regulatory updates.
    """
    
    def validate(self):
        """Validate the country regulation before saving."""
        self.validate_country_uniqueness()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_review_date()
        
    def validate_country_uniqueness(self):
        """Ensure only one regulation record per country."""
        if self.country_name:
            existing = frappe.db.get_value(
                "Country Regulation",
                {"country_name": self.country_name, "name": ["!=", self.name or ""]},
                "name"
            )
            
            if existing:
                frappe.throw(_("Regulation record for {0} already exists").format(self.country_name))
                
    def set_defaults(self):
        """Set default values based on business rules."""
        if not self.last_updated:
            self.last_updated = nowdate()
            
        if not self.verification_status:
            self.verification_status = "Pending Verification"
            
        if not self.next_review_date:
            self.next_review_date = add_months(nowdate(), 12)
            
    def update_review_date(self):
        """Update next review date if verification status changes."""
        if self.verification_status == "Verified":
            if not self.next_review_date or self.next_review_date < nowdate():
                self.next_review_date = add_months(nowdate(), 12)
        elif self.verification_status == "Expired":
            self.next_review_date = nowdate()
            
    @frappe.whitelist()
    def get_compliance_summary(self):
        """Get compliance summary for this country."""
        
        # Count organizations in this country
        org_count = frappe.db.count("Distribution Organization", {"country": self.country_name})
        
        # Count products with compliance status for this country  
        compliant_products = frappe.db.count(
            "Product Compliance", 
            {"country": self.country_name, "compliance_status": "Compliant"}
        )
        
        total_products = frappe.db.count("Product Compliance", {"country": self.country_name})
        
        return {
            "country": self.country_name,
            "organizations": org_count,
            "total_products": total_products,
            "compliant_products": compliant_products,
            "compliance_rate": round((compliant_products / total_products * 100) if total_products > 0 else 0, 1),
            "regulatory_authority": self.regulatory_authority,
            "last_updated": self.last_updated,
            "verification_status": self.verification_status
        }
    
    def before_save(self):
        """Set route before saving"""
        #super().before_save()
        if not getattr(self, 'route', None):
            if getattr(self, 'country_name', None):
                self.route = self.scrub(f"regulations-{self.country_name}")
            elif getattr(self, 'title', None):
                self.route = self.scrub(self.title)
    
    def get_context(self, context):
        """Website context for rendering"""
        context.no_cache = 1
        context.show_sidebar = True
        context.parents = [{"title": _("Country Regulations"), "route": "country-regulations"}]
        
        # Add related regulations
        context.related_regulations = self.get_related_regulations()
        
        return context
    
    def get_related_regulations(self):
        """Get related country regulations"""
        return frappe.get_all(
            "Country Regulation",
            filters={
                "name": ["!=", self.name],
                "published": 1
            },
            fields=["name", "country_name", "title", "route"],
            limit=5
        )
    
    def get_feed(self):
        """Feed for timeline"""
        return f"Country Regulations for {getattr(self, 'country_name', 'Unknown')}"
    
    def scrub(self, text):
        """Convert text to URL-friendly format"""
        import re
        return re.sub(r'[^a-zA-Z0-9]+', '-', cstr(text)).strip('-').lower()

# Utility functions

@frappe.whitelist()
def get_regulations_by_region(region):
    """Get all country regulations for a specific region."""
    
    regulations = frappe.get_all(
        "Country Regulation",
        filters={"region": region},
        fields=[
            "name", "country_name", "regulatory_authority", 
            "aloe_classification", "verification_status", "last_updated"
        ],
        order_by="country_name"
    )
    
    return regulations

@frappe.whitelist()
def import_regulation_data(regulation_data):
    """Import regulation data from external sources."""
    
    if isinstance(regulation_data, str):
        regulation_data = frappe.parse_json(regulation_data)
        
    created_count = 0
    updated_count = 0
    
    for country_code, data in regulation_data.get("countries", {}).items():
        country_name = data.get("country_name", country_code.replace("_", " ").title())
        
        existing = frappe.db.get_value("Country Regulation", {"country_name": country_name}, "name")
        
        if existing:
            # Update existing record
            reg_doc = frappe.get_doc("Country Regulation", existing)
            updated_count += 1
        else:
            # Create new record
            reg_doc = frappe.new_doc("Country Regulation")
            reg_doc.country_name = country_name
            created_count += 1
            
        # Update fields from data
        reg_doc.regulatory_authority = data.get("regulatory_authority", "")
        reg_doc.authority_website = data.get("website", "")
        reg_doc.last_updated = nowdate()
        reg_doc.data_source = "Import"
        reg_doc.verification_status = "Pending Verification"
        
        # Process product classifications
        if "product_classifications" in data:
            classifications = []
            for product_type, classification in data["product_classifications"].items():
                if "category" in classification:
                    classifications.append(classification["category"])
            
            if classifications:
                reg_doc.aloe_classification = classifications[0]  # Use first classification
                
        # Process requirements
        if "product_classifications" in data:
            requirements = []
            for product_type, classification in data["product_classifications"].items():
                if "requirements" in classification:
                    requirements.extend(classification["requirements"])
            
            if requirements:
                reg_doc.key_requirements = "<br>".join(requirements)
                
        reg_doc.save(ignore_permissions=True)
        
    return {
        "created": created_count,
        "updated": updated_count,
        "total": created_count + updated_count
    }
