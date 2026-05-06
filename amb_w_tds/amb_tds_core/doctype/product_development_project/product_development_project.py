"""
Product Development Project DocType Controller

This module contains the server-side logic for managing R&D projects
for aloe vera product development and regulatory compliance.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff
from frappe import _

class ProductDevelopmentProject(Document):
    """
    Product Development Project DocType controller.
    
    Handles business logic for R&D project management, milestone tracking,
    and regulatory compliance coordination.
    """
    
    # Website attribute to fix the AttributeError
    website = frappe._dict(
        condition_field="disabled",
        page_title_field="project_name"
    )
    
    def validate(self):
        """Validate the project before saving."""
        self.validate_dates()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_last_update_date()
        
    def validate_dates(self):
        """Validate project dates."""
        if self.start_date and self.expected_completion:
            if self.start_date > self.expected_completion:
                frappe.throw(_("Start date cannot be after expected completion date"))
                
    def set_defaults(self):
        """Set default values."""
        if not self.status:
            self.status = "Planning"
            
        if not self.priority:
            self.priority = "Medium"
            
        if not self.compliance_status:
            self.compliance_status = "Not Started"
            
    def update_last_update_date(self):
        """Update the last update date."""
        self.last_update_date = nowdate()
        
    @frappe.whitelist()
    def get_project_summary(self):
        """Get project summary information."""
        
        # Calculate project duration
        duration = None
        if self.start_date and self.expected_completion:
            duration = date_diff(self.expected_completion, self.start_date)
            
        # Get team size
        team_size = 0
        if self.project_manager:
            team_size += 1
        if self.r_and_d_lead:
            team_size += 1
        if self.regulatory_lead:
            team_size += 1
        if self.team_members:
            team_size += len(self.team_members.split(','))
            
        return {
            "project_name": self.project_name,
            "status": self.status,
            "priority": self.priority,
            "completion_percentage": self.completion_percentage or 0,
            "duration_days": duration,
            "team_size": team_size,
            "estimated_investment": self.estimated_investment,
            "current_phase": self.current_phase,
            "compliance_status": self.compliance_status,
            "target_countries_count": len(self.target_countries.split(',')) if self.target_countries else 0
        }


# Utility functions

@frappe.whitelist()
def get_project_dashboard_data():
    """Get dashboard data for R&D projects."""
    
    # Project status summary
    status_summary = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabProduct Development Project`
        GROUP BY status
    """, as_dict=True)
    
    # Priority distribution
    priority_summary = frappe.db.sql("""
        SELECT priority, COUNT(*) as count
        FROM `tabProduct Development Project`
        GROUP BY priority
    """, as_dict=True)
    
    # Projects by completion percentage
    completion_summary = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN completion_percentage < 25 THEN 'Starting'
                WHEN completion_percentage < 50 THEN 'In Progress'
                WHEN completion_percentage < 75 THEN 'Advanced'
                WHEN completion_percentage < 100 THEN 'Nearly Complete'
                ELSE 'Completed'
            END as phase,
            COUNT(*) as count
        FROM `tabProduct Development Project`
        GROUP BY phase
    """, as_dict=True)
    
    return {
        "status_summary": status_summary,
        "priority_summary": priority_summary,
        "completion_summary": completion_summary
    }
