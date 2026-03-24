# -*- coding: utf-8 -*-
"""
BUG 79: Dashboard Override for Sample Request AMB Connections
Adds Sample Request AMB to the Connections section of various doctypes
"""

import frappe


def get_dashboard_data(data):
    """
    Extend various doctype dashboards to show Sample Request AMB links
    
    This function calls the original get_data() for each doctype,
    then appends Sample Request AMB to the transactions/links section
    """
    # Get current doctype from the form
    doctype = frappe.form_dict.doctype if hasattr(frappe, 'form_dict') and frappe.form_dict.get('doctype') else None
    
    # If no doctype provided, return data as-is
    if not doctype:
        return data
    
    # Call original get_data based on doctype and append Sample Request link
    if doctype == "Lead":
        try:
            original_data = frappe.call({
                "method": "erpnext.crm.doctype.lead.lead_dashboard.get_data",
            })
            if original_data:
                data = original_data
        except Exception:
            pass
        
        # Add Sample Request AMB to transactions
        add_sample_request_to_transactions(data, doctype)
        
    elif doctype == "Prospect":
        try:
            original_data = frappe.call({
                "method": "erpnext.crm.doctype.prospect.prospect_dashboard.get_data",
            })
            if original_data:
                data = original_data
        except Exception:
            pass
        
        add_sample_request_to_transactions(data, doctype)
        
    elif doctype == "Opportunity":
        try:
            original_data = frappe.call({
                "method": "erpnext.crm.doctype.opportunity.opportunity_dashboard.get_data",
            })
            if original_data:
                data = original_data
        except Exception:
            pass
        
        add_sample_request_to_transactions(data, doctype)
        
    elif doctype == "Quotation":
        try:
            original_data = frappe.call({
                "method": "erpnext.selling.doctype.quotation.quotation_dashboard.get_data",
            })
            if original_data:
                data = original_data
        except Exception:
            pass
        
        add_sample_request_to_transactions(data, doctype)
        
    elif doctype == "Sales Order":
        try:
            original_data = frappe.call({
                "method": "erpnext.selling.doctype.sales_order.sales_order_dashboard.get_data",
            })
            if original_data:
                data = original_data
        except Exception:
            pass
        
        add_sample_request_to_transactions(data, doctype)
    
    return data


def add_sample_request_to_transactions(data, doctype):
    """
    Add Sample Request AMB to the transactions section of dashboard data
    """
    if not data:
        return data
    
    # Get or create transactions/transactions_children section
    transactions = data.get("transactions") or data.get("transaction_details") or []
    
    # Check if Sample Request AMB already exists
    sr_exists = any(
        (isinstance(t, dict) and t.get("label") == "Sample Request") or
        (isinstance(t, str) and t == "Sample Request AMB")
        for t in transactions
    )
    
    if not sr_exists:
        # Determine the correct filter based on doctype
        party_type_map = {
            "Lead": "Lead",
            "Prospect": "Prospect",
            "Opportunity": "Opportunity",
            "Quotation": "Quotation",
            "Sales Order": "Sales Order"
        }
        
        # Add Sample Request AMB to transactions (filter is handled by Frappe automatically)
        new_entry = {
            "label": "Sample Request",
            "doctype": "Sample Request AMB",
            "type": "Link",
        }
        
        if isinstance(transactions, list):
            transactions.append(new_entry)
            data["transactions"] = transactions
    
    return data
