# -*- coding: utf-8 -*-
"""
BUG 87F: Dashboard Override for Batch AMB Connections
Adds Sample Request AMB to the Connections section of Batch AMB
"""

import frappe
from frappe import _


def get_data(data=None):
    """
    Add Sample Request AMB to Batch AMB's connections
    This is a custom DocType, so we create the full dashboard
    """
    # Batch AMB is a custom DocType - no original dashboard to extend
    # We'll check if there's any existing setup via Custom DocType
    try:
        # Try to get any existing dashboard config
        original_data = {"transactions": []}
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
        
        # Add non_standard_fieldnames
        if "non_standard_fieldnames" not in original_data:
            original_data["non_standard_fieldnames"] = {}
        original_data["non_standard_fieldnames"]["Sample Request AMB"] = "batch_reference"
    
    return original_data