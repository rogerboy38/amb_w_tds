"""
Market Research DocType

This module handles market intelligence tracking for global distribution
including competitive analysis, market trends, and customer insights.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days
from frappe import _

class MarketResearch(Document):
    """Market Research document class for managing market intelligence data."""
    
    def validate(self):
        """Validate market research data before saving."""
        self.validate_research_dates()
        self.validate_completion_percentage()
        self.set_default_values()
        
    def validate_research_dates(self):
        """Validate research date is not in the future."""
        if self.research_date and self.research_date > nowdate():
            frappe.throw(_("Research date cannot be in the future"))
            
    def validate_completion_percentage(self):
        """Validate completion percentage based on status."""
        if self.research_status == "Completed" and self.completion_percentage != 100:
            self.completion_percentage = 100
        elif self.research_status == "Planning" and self.completion_percentage > 10:
            frappe.msgprint(_("Completion percentage seems high for Planning status"))
            
    def set_default_values(self):
        """Set default values for new research records."""
        if not self.research_date:
            self.research_date = nowdate()
            
        if not self.research_lead:
            self.research_lead = frappe.session.user
            
        if not self.priority:
            self.priority = "Medium"
            
    def on_update(self):
        """Actions to perform when document is updated."""
        self.update_related_projects()
        
    def update_related_projects(self):
        """Update related R&D projects with market research insights."""
        if self.research_status == "Completed" and self.strategic_recommendations:
            # Find related projects by country and product category
            related_projects = frappe.get_all(
                "Product Development Project",
                filters={
                    "target_countries": ["like", f"%{self.country}%"],
                    "product_category": self.product_category,
                    "status": ["in", ["Planning", "In Progress"]]
                },
                fields=["name", "project_name"]
            )
            
            # Add a comment to related projects about the research findings
            for project in related_projects:
                frappe.get_doc("Product Development Project", project.name).add_comment(
                    "Comment",
                    f"Market Research insights available: {self.research_title}. "
                    f"Key findings: {self.key_findings[:200]}..."
                )

    @frappe.whitelist()
    def get_competitive_analysis_summary(self):
        """Generate a summary of competitive analysis data."""
        summary = {
            "main_competitors": self.main_competitors,
            "competitive_threats": self.competitive_threats,
            "competitive_advantages": self.competitive_advantages,
            "market_share_data": self.market_share_analysis
        }
        return summary
        
    @frappe.whitelist()
    def generate_market_report(self):
        """Generate a comprehensive market research report."""
        report_data = {
            "research_title": self.research_title,
            "research_type": self.research_type,
            "country": self.country,
            "product_category": self.product_category,
            "market_overview": {
                "market_size": self.market_size,
                "market_value": self.market_value,
                "growth_rate": self.market_growth_rate,
                "key_drivers": self.key_drivers,
                "barriers": self.market_barriers
            },
            "competitive_landscape": {
                "main_competitors": self.main_competitors,
                "market_share": self.market_share_analysis,
                "competitive_threats": self.competitive_threats,
                "our_advantages": self.competitive_advantages
            },
            "customer_insights": {
                "demographics": self.target_demographics,
                "behavior": self.customer_behavior,
                "preferences": self.customer_preferences,
                "price_sensitivity": self.price_sensitivity
            },
            "swot_analysis": {
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "opportunities": self.opportunities,
                "threats": self.threats
            },
            "trends_and_projections": {
                "market_trends": self.market_trends,
                "future_projections": self.future_projections,
                "growth_opportunities": self.growth_opportunities,
                "risk_factors": self.risk_factors
            },
            "conclusions": {
                "key_findings": self.key_findings,
                "recommendations": self.strategic_recommendations,
                "next_steps": self.next_steps,
                "action_items": self.action_items
            }
        }
        return report_data

def get_research_dashboard_data():
    """Get dashboard data for market research overview."""
    
    # Research by status
    status_data = frappe.db.sql("""
        SELECT research_status, COUNT(*) as count
        FROM `tabMarket Research`
        WHERE docstatus < 2
        GROUP BY research_status
        ORDER BY count DESC
    """, as_dict=True)
    
    # Research by country
    country_data = frappe.db.sql("""
        SELECT country, COUNT(*) as count, 
               AVG(completion_percentage) as avg_completion
        FROM `tabMarket Research`
        WHERE docstatus < 2 AND country IS NOT NULL
        GROUP BY country
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)
    
    # Research by product category
    category_data = frappe.db.sql("""
        SELECT product_category, COUNT(*) as count
        FROM `tabMarket Research`
        WHERE docstatus < 2 AND product_category IS NOT NULL
        GROUP BY product_category
        ORDER BY count DESC
    """, as_dict=True)
    
    # Recent completed research
    recent_research = frappe.get_all(
        "Market Research",
        filters={"research_status": "Completed"},
        fields=["name", "research_title", "country", "research_date", "research_type"],
        order_by="research_date desc",
        limit=5
    )
    
    return {
        "status_distribution": status_data,
        "country_distribution": country_data,
        "category_distribution": category_data,
        "recent_completed": recent_research
    }

@frappe.whitelist()
def get_market_intelligence_by_country(country):
    """Get market intelligence summary for a specific country."""
    
    research_data = frappe.get_all(
        "Market Research",
        filters={"country": country, "research_status": "Completed"},
        fields=["*"]
    )
    
    if not research_data:
        return {"message": f"No market research data available for {country}"}
    
    # Aggregate insights
    insights = {
        "country": country,
        "total_research_studies": len(research_data),
        "market_segments": set(),
        "key_competitors": set(),
        "growth_opportunities": [],
        "regulatory_challenges": [],
        "market_trends": []
    }
    
    for research in research_data:
        if research.product_category:
            insights["market_segments"].add(research.product_category)
        if research.main_competitors:
            competitors = research.main_competitors.split(",")
            insights["key_competitors"].update([c.strip() for c in competitors])
        if research.growth_opportunities:
            insights["growth_opportunities"].append(research.growth_opportunities)
        if research.regulatory_challenges:
            insights["regulatory_challenges"].append(research.regulatory_challenges)
        if research.market_trends:
            insights["market_trends"].append(research.market_trends)
    
    # Convert sets to lists for JSON serialization
    insights["market_segments"] = list(insights["market_segments"])
    insights["key_competitors"] = list(insights["key_competitors"])
    
    return insights

@frappe.whitelist()
def generate_competitive_landscape_report(product_category=None, region=None):
    """Generate competitive landscape report across multiple research studies."""
    
    filters = {"research_status": "Completed"}
    if product_category:
        filters["product_category"] = product_category
    if region:
        filters["region"] = region
    
    research_studies = frappe.get_all(
        "Market Research",
        filters=filters,
        fields=["*"]
    )
    
    if not research_studies:
        return {"message": "No completed research studies found for the specified criteria"}
    
    # Aggregate competitive data
    competitive_data = {
        "total_studies": len(research_studies),
        "markets_analyzed": set(),
        "all_competitors": {},
        "competitive_threats": [],
        "market_opportunities": [],
        "swot_summary": {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": []
        }
    }
    
    for study in research_studies:
        if study.country:
            competitive_data["markets_analyzed"].add(study.country)
            
        # Aggregate competitor mentions
        if study.main_competitors:
            competitors = [c.strip() for c in study.main_competitors.split(",")]
            for competitor in competitors:
                if competitor:
                    competitive_data["all_competitors"][competitor] = competitive_data["all_competitors"].get(competitor, 0) + 1
        
        # Collect threats and opportunities
        if study.competitive_threats:
            competitive_data["competitive_threats"].append({
                "market": study.country,
                "threat": study.competitive_threats
            })
            
        if study.growth_opportunities:
            competitive_data["market_opportunities"].append({
                "market": study.country,
                "opportunity": study.growth_opportunities
            })
            
        # Aggregate SWOT data
        if study.strengths:
            competitive_data["swot_summary"]["strengths"].append(study.strengths)
        if study.weaknesses:
            competitive_data["swot_summary"]["weaknesses"].append(study.weaknesses)
        if study.opportunities:
            competitive_data["swot_summary"]["opportunities"].append(study.opportunities)
        if study.threats:
            competitive_data["swot_summary"]["threats"].append(study.threats)
    
    # Convert sets to lists and sort competitors by frequency
    competitive_data["markets_analyzed"] = list(competitive_data["markets_analyzed"])
    competitive_data["top_competitors"] = sorted(
        competitive_data["all_competitors"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return competitive_data
