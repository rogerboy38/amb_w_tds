# -*- coding: utf-8 -*-
"""
BUG 74 & 79: Dashboard Override for Sample Request AMB Connections
Adds Sample Request AMB to the Connections section of various doctypes
"""

import frappe


def get_dashboard_data(data):
    """
    Extend various doctype dashboards to show Sample Request AMB links
    
    This function adds a link to the Connections section
    showing related Sample Request AMB documents
    """
    # Get the current doctype from data
    doctype = data.get("name") or frappe.form_dict.doctype or ""
    
    # Add Sample Request AMB to the links section
    data.setdefault("links", [])
    
    # Check if Sample Request AMB link already exists
    link_exists = any(
        link.get("link_doctype") == "Sample Request AMB" 
        for link in data.get("links", [])
    )
    
    if not link_exists:
        # Determine the correct filter based on doctype
        if doctype == "Quotation":
            # Quotation has direct 'quotation' field
            data["links"].append({
                "label": "Sample Requests",
                "type": "DocType",
                "doctype": "Sample Request AMB",
                "link_filters": [
                    ["Sample Request AMB", "quotation", "=", "${ doctype.name }"]
                ]
            })
        else:
            # Lead, Prospect, Opportunity, Sales Order use Dynamic Link (party_type/party)
            # We need to use the custom script approach instead
            pass
    
    return data


def get_sample_request_filters(doctype, docname):
    """
    Get filters to find Sample Request AMB documents linked to this document
    """
    filters = []
    
    if doctype == "Quotation":
        # Direct quotation field
        filters = [
            ["Sample Request AMB", "quotation", "=", docname]
        ]
    elif doctype in ["Lead", "Prospect", "Opportunity", "Sales Order"]:
        # Dynamic Link via party_type + party
        party_type_map = {
            "Lead": "Lead",
            "Prospect": "Prospect", 
            "Opportunity": "Opportunity",
            "Sales Order": "Sales Order"
        }
        filters = [
            ["Sample Request AMB", "party", "=", docname],
            ["Sample Request AMB", "party_type", "=", party_type_map.get(doctype, doctype)]
        ]
    
    return filters
