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
    
    The transactions format should be:
    {
        "label": "Display Label",
        "items": ["DocType1", "DocType2"]
    }
    """
    return {
        "fieldname": "name",
        "non_standard_fieldnames": {
            "Sample Request AMB": "party",
        },
        "transactions": [
            {"label": _("Quotations"), "items": ["Quotation"]},
            {"label": _("Sales Orders"), "items": ["Sales Order"]},
            {"label": _("Sample Request"), "items": ["Sample Request AMB"]},
        ],
    }