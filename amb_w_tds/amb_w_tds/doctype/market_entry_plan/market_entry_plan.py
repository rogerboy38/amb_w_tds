"""
Market Entry Plan DocType Controller

This module manages strategic market entry planning for new geographic
markets, including analysis, regulatory strategy, and implementation tracking.
"""

import frappe
from frappe.model.document import Document
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import nowdate, add_months, date_diff, cstr
from frappe import _

class MarketEntryPlan(WebsiteGenerator):
    # Website configuration to fix the AttributeError
    website = frappe._dict({
        'condition_field': 'published',
        'page_title_field': 'title',
        'route': 'market-entry-plans'
    })
    """
    Market Entry Plan DocType controller.
    
    Manages strategic planning for entering new markets including
    regulatory strategy, financial projections, and implementation tracking.
    """
    
    def validate(self):
        """Validate market entry plan before saving."""
        self.validate_dates()
        self.validate_financial_data()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_progress_tracking()
        
    def validate_dates(self):
        """Validate date fields."""
        if self.plan_date and self.target_launch_date:
            if self.plan_date > self.target_launch_date:
                frappe.throw(_("Plan date cannot be after target launch date"))
                
        if self.next_milestone_date and self.target_launch_date:
            if self.next_milestone_date > self.target_launch_date:
                frappe.msgprint(_("Warning: Next milestone is after target launch date"), 
                              indicator="orange")
                
    def validate_financial_data(self):
        """Validate financial projections."""
        # Check for reasonable ROI projections
        if (self.year_1_revenue and self.initial_investment and 
            self.year_1_revenue > self.initial_investment * 10):
            frappe.msgprint(_("Warning: Year 1 revenue seems unusually high compared to investment"), 
                          indicator="orange")
            
        # Validate revenue progression
        if (self.year_1_revenue and self.year_2_revenue and 
            self.year_2_revenue < self.year_1_revenue * 0.5):
            frappe.msgprint(_("Warning: Year 2 revenue projection shows significant decline"), 
                          indicator="orange")
            
    def set_defaults(self):
        """Set default values."""
        if not self.status:
            self.status = "Planning"
            
        if not self.priority:
            self.priority = "Medium"
            
        if not self.plan_date:
            self.plan_date = nowdate()
            
        if not self.market_potential:
            self.market_potential = "Medium"
            
        if not self.entry_strategy:
            self.entry_strategy = "Distributor Partnership"
            
    def update_progress_tracking(self):
        """Update progress tracking based on status and milestones."""
        # Auto-calculate completion percentage based on status
        status_percentages = {
            "Planning": 10,
            "In Progress": 25,
            "Approval Required": 50,
            "Approved": 60,
            "Implementing": 80,
            "Completed": 100,
            "On Hold": 0,
            "Cancelled": 0
        }
        
        if not self.completion_percentage and self.status in status_percentages:
            self.completion_percentage = status_percentages[self.status]
            
    @frappe.whitelist()
    def get_market_analysis_summary(self):
        """Get comprehensive market analysis summary."""
        
        # Get country regulation information
        country_info = frappe.get_value("Country Regulation", self.target_country, 
                                      ["regulatory_authority", "key_requirements", 
                                       "typical_timeline", "aloe_classification"], as_dict=True)
        
        # Calculate financial ratios
        financial_summary = self._calculate_financial_metrics()
        
        # Get competitive intelligence
        competitive_analysis = self._get_competitive_analysis()
        
        return {
            "country_regulations": country_info,
            "financial_metrics": financial_summary,
            "competitive_landscape": competitive_analysis,
            "risk_assessment": self._assess_market_risks(),
            "timeline_analysis": self._analyze_timeline()
        }
        
    def _calculate_financial_metrics(self):
        """Calculate key financial metrics."""
        metrics = {}
        
        if self.initial_investment and self.year_1_revenue:
            metrics["year_1_roi"] = ((self.year_1_revenue - self.initial_investment) / 
                                   self.initial_investment * 100)
            
        if self.year_1_revenue and self.year_3_revenue:
            metrics["revenue_cagr"] = (((self.year_3_revenue / self.year_1_revenue) ** (1/2)) - 1) * 100
            
        if self.initial_investment and self.ongoing_costs:
            metrics["payback_period"] = self.initial_investment / (self.year_1_revenue - self.ongoing_costs)
            
        if all([self.year_1_revenue, self.year_2_revenue, self.year_3_revenue]):
            total_revenue = self.year_1_revenue + self.year_2_revenue + self.year_3_revenue
            total_costs = self.initial_investment + (self.ongoing_costs * 3) + (self.regulatory_costs or 0)
            metrics["three_year_roi"] = ((total_revenue - total_costs) / total_costs * 100)
            
        return metrics
        
    def _get_competitive_analysis(self):
        """Analyze competitive landscape."""
        # This could be enhanced to pull data from external sources
        # or link to competitor analysis documents
        
        analysis = {
            "market_maturity": self._assess_market_maturity(),
            "entry_barriers": self._identify_entry_barriers(),
            "competitive_intensity": self._assess_competitive_intensity()
        }
        
        return analysis
        
    def _assess_market_maturity(self):
        """Assess market maturity based on available data."""
        if self.market_size:
            if self.market_size > 100000000:  # $100M+
                return "Mature"
            elif self.market_size > 10000000:  # $10M+
                return "Growing"
            else:
                return "Emerging"
        return "Unknown"
        
    def _identify_entry_barriers(self):
        """Identify potential market entry barriers."""
        barriers = []
        
        if self.regulatory_costs and self.regulatory_costs > 100000:
            barriers.append("High regulatory costs")
            
        if self.initial_investment and self.initial_investment > 1000000:
            barriers.append("High capital requirements")
            
        if "pharmaceutical" in (self.target_products or "").lower():
            barriers.append("Pharmaceutical regulations")
            
        return barriers
        
    def _assess_competitive_intensity(self):
        """Assess competitive intensity."""
        # Simple heuristic based on market size and investment
        if (self.market_size and self.initial_investment and 
            self.initial_investment / self.market_size > 0.01):
            return "High"
        elif (self.market_size and self.initial_investment and 
              self.initial_investment / self.market_size > 0.001):
            return "Medium"
        else:
            return "Low"
            
    def _assess_market_risks(self):
        """Assess various market entry risks."""
        risks = []
        
        # Regulatory risks
        if not self.regulatory_pathway:
            risks.append({"type": "Regulatory", "level": "High", 
                         "description": "Regulatory pathway not defined"})
            
        # Financial risks
        if self.initial_investment and self.year_1_revenue:
            if self.initial_investment > self.year_1_revenue * 2:
                risks.append({"type": "Financial", "level": "High",
                             "description": "High investment relative to projected revenue"})
                
        # Timeline risks
        if self.target_launch_date and date_diff(self.target_launch_date, nowdate()) < 180:
            risks.append({"type": "Timeline", "level": "Medium",
                         "description": "Aggressive launch timeline"})
                         
        return risks
        
    def _analyze_timeline(self):
        """Analyze project timeline and critical path."""
        timeline = {
            "days_to_launch": date_diff(self.target_launch_date, nowdate()) if self.target_launch_date else None,
            "current_phase": self.current_phase,
            "completion_rate": self.completion_percentage or 0
        }
        
        if timeline["days_to_launch"]:
            if timeline["days_to_launch"] < 0:
                timeline["status"] = "Overdue"
            elif timeline["days_to_launch"] < 30:
                timeline["status"] = "Critical"
            elif timeline["days_to_launch"] < 90:
                timeline["status"] = "Urgent"
            else:
                timeline["status"] = "On Track"
                
        return timeline
        
    @frappe.whitelist()
    def update_milestone(self, milestone_description, completion_date=None):
        """Update project milestone."""
        if not completion_date:
            completion_date = nowdate()
            
        # Add to key milestones
        milestone_entry = f"{completion_date}: {milestone_description}"
        
        if self.key_milestones:
            self.key_milestones += f"<br>{milestone_entry}"
        else:
            self.key_milestones = milestone_entry
            
        # Update progress
        if self.completion_percentage < 90:
            self.completion_percentage += 10
            
        self.save()
        return _("Milestone updated successfully")
        
    @frappe.whitelist()
    def generate_executive_summary(self):
        """Generate executive summary for stakeholders."""
        summary = {
            "plan_overview": {
                "title": self.plan_title,
                "target_country": self.target_country,
                "target_launch": self.target_launch_date,
                "status": self.status,
                "completion": f"{self.completion_percentage or 0}%"
            },
            "market_opportunity": {
                "market_size": self.market_size,
                "potential": self.market_potential,
                "segments": self.target_segments
            },
            "financial_outlook": {
                "investment_required": self.initial_investment,
                "year_1_revenue": self.year_1_revenue,
                "year_3_revenue": self.year_3_revenue,
                "roi_3_year": self._calculate_financial_metrics().get("three_year_roi")
            },
            "key_risks": [risk["description"] for risk in self._assess_market_risks()],
            "next_actions": self.key_milestones,
            "team": {
                "project_manager": self.project_manager,
                "market_lead": self.market_lead,
                "regulatory_lead": self.regulatory_lead
            }
        }
        
        return summary
    
    def before_save(self):
        """Set route before saving"""
        #super().before_save()
        if not getattr(self, 'route', None) and getattr(self, 'plan_title', None):
            self.route = self.scrub(self.plan_title)
    
    def get_context(self, context):
        """Website context for rendering"""
        context.no_cache = 1
        context.show_sidebar = True
        context.parents = [{"title": _("Market Entry Plans"), "route": "market-entry-plans"}]
        
        # Add related plans
        context.related_plans = self.get_related_plans()
        
        return context
    
    def get_related_plans(self):
        """Get related market entry plans"""
        return frappe.get_all(
            "Market Entry Plan",
            filters={
                "name": ["!=", self.name],
                "published": 1
            },
            fields=["name", "plan_title", "target_country", "status", "route"],
            limit=5
        )
    
    def get_feed(self):
        """Feed for timeline"""
        return f"Market Entry Plan for {getattr(self, 'target_country', 'Unknown')}"
    
    def scrub(self, text):
        """Convert text to URL-friendly format"""
        import re
        return re.sub(r'[^a-zA-Z0-9]+', '-', cstr(text)).strip('-').lower()

# Utility functions

@frappe.whitelist()
def get_market_entry_dashboard():
    """Get dashboard data for market entry plans."""
    
    # Status distribution
    status_data = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabMarket Entry Plan`
        GROUP BY status
    """, as_dict=True)
    
    # Country analysis
    country_data = frappe.db.sql("""
        SELECT target_country, COUNT(*) as plans,
               AVG(completion_percentage) as avg_completion,
               SUM(initial_investment) as total_investment
        FROM `tabMarket Entry Plan`
        GROUP BY target_country
        ORDER BY plans DESC
    """, as_dict=True)
    
    # Financial summary
    financial_data = frappe.db.sql("""
        SELECT 
            SUM(initial_investment) as total_investment,
            SUM(year_1_revenue) as projected_y1_revenue,
            SUM(year_3_revenue) as projected_y3_revenue,
            AVG(completion_percentage) as avg_completion
        FROM `tabMarket Entry Plan`
        WHERE status NOT IN ('Cancelled', 'On Hold')
    """, as_dict=True)
    
    # Timeline analysis
    timeline_data = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN target_launch_date < CURDATE() THEN 'Overdue'
                WHEN target_launch_date < DATE_ADD(CURDATE(), INTERVAL 90 DAY) THEN 'Due Soon'
                ELSE 'Future'
            END as timeline_status,
            COUNT(*) as count
        FROM `tabMarket Entry Plan`
        WHERE status NOT IN ('Completed', 'Cancelled')
        GROUP BY timeline_status
    """, as_dict=True)
    
    return {
        "status_distribution": status_data,
        "country_analysis": country_data,
        "financial_summary": financial_data[0] if financial_data else {},
        "timeline_analysis": timeline_data
    }

@frappe.whitelist()
def get_market_opportunities():
    """Identify potential market opportunities."""
    
    # Countries with regulations but no active plans
    opportunities = frappe.db.sql("""
        SELECT cr.country_name, cr.regulatory_authority, cr.aloe_classification
        FROM `tabCountry Regulation` cr
        LEFT JOIN `tabMarket Entry Plan` mep ON cr.country_name = mep.target_country
        WHERE mep.name IS NULL OR mep.status IN ('Cancelled', 'Completed')
        ORDER BY cr.country_name
    """, as_dict=True)
    
    return opportunities

@frappe.whitelist()
def generate_market_entry_report(filters=None):
    """Generate comprehensive market entry report."""
    
    conditions = []
    values = []
    
    if filters:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)
            
        if filters.get("status"):
            conditions.append("status = %s")
            values.append(filters["status"])
            
        if filters.get("target_country"):
            conditions.append("target_country = %s")
            values.append(filters["target_country"])
            
        if filters.get("priority"):
            conditions.append("priority = %s")
            values.append(filters["priority"])
            
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT 
            name, plan_title, target_country, status, priority,
            target_launch_date, completion_percentage, current_phase,
            market_size, initial_investment, year_1_revenue, year_3_revenue,
            project_manager, market_lead, regulatory_lead,
            entry_strategy, market_potential
        FROM `tabMarket Entry Plan`
        WHERE {where_clause}
        ORDER BY target_launch_date, priority DESC
    """
    
    plans = frappe.db.sql(query, values, as_dict=True)
    
    return plans
