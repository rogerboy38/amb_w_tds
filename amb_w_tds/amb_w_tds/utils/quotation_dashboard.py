# -*- coding: utf-8 -*-
"""
BUG 74: Quotation Dashboard Override
Adds Sample Request AMB to the Connections section of Quotation
"""

import frappe


def get_dashboard_data(data):
    """
    Extend Quotation dashboard to show Sample Request AMB links
    
    This function adds a link to the Quotation's Connections section
    showing related Sample Request AMB documents
    """
    # Add Sample Request AMB to the links section
    data.setdefault("links", [])
    
    # Check if Sample Request AMB link already exists
    link_exists = any(
        link.get("link_doctype") == "Sample Request AMB" 
        for link in data.get("links", [])
    )
    
    if not link_exists:
        data["links"].append({
            "link_doctype": "Sample Request AMB",
            "link_fieldname": "party",
            "table_fieldname": "samples",
            "get_filters": get_sample_request_filters
        })
    
    return data


def get_sample_request_filters(doctype, docname):
    """
    Get filters to find Sample Request AMB documents linked to this Quotation
    """
    # Try to find Sample Request AMB where party links to this Quotation
    # The connection could be via different fields depending on implementation
    return [
        ["Sample Request AMB", "party", "=", docname],
        ["Sample Request AMB", "party_type", "=", "Quotation"]
    ]
