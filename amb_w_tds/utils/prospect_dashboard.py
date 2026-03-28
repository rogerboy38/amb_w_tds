# -*- coding: utf-8 -*-
"""
BUG 87C: Dashboard Override for Prospect Connections
Adds Sample Request AMB to the Connections section of Prospect
"""

import frappe
from frappe import _


def get_data(data):
    """
    Add Sample Request AMB to Prospect's connections
    The 'data' parameter already contains the original ERPNext dashboard
    """
    # Modify data in place - append Sample Request
    data['transactions'].append(
        {"label": _("Sample Request"), "items": ["Sample Request AMB"]}
    )
    
    # Add non_standard_fieldnames if not present
    if "non_standard_fieldnames" not in data:
        data["non_standard_fieldnames"] = {}
    data["non_standard_fieldnames"]["Sample Request AMB"] = "party"
    
    return data