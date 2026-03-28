# -*- coding: utf-8 -*-
"""
BUG 87D: Dashboard Override for Opportunity Connections
Adds Sample Request AMB to the Connections section of Opportunity
"""

import frappe
from frappe import _


def get_data(data=None):
    """
    Add Sample Request AMB to Opportunity's connections
    Extends the original ERPNext Opportunity dashboard
    """
    # Get original ERPNext Opportunity dashboard data
    try:
        original_data = frappe.call("erpnext.crm.doctype.opportunity.opportunity_dashboard.get_data")
    except:
        original_data = {"transactions": []}
    
    # Add Sample Request to transactions if not already present
    if original_data:
        transactions = original_data.get("transactions", [])
        # Check if Sample Request already exists
        sr_exists = any(
            "Sample Request AMB" in t.get("items", [])
            for t in transactions
        )
        if not sr_exists:
            transactions.append(
                {"label": _("Sample Request"), "items": ["Sample Request AMB"]}
            )
        original_data["transactions"] = transactions
        
        # Add non_standard_fieldnames if not present
        if "non_standard_fieldnames" not in original_data:
            original_data["non_standard_fieldnames"] = {}
        original_data["non_standard_fieldnames"]["Sample Request AMB"] = "party"
    
    return original_data