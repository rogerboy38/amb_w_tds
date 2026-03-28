# -*- coding: utf-8 -*-
"""
BUG 87C: Dashboard Override for Prospect Connections
Adds Sample Request AMB to the Connections section of Prospect
"""

import frappe
from frappe import _


def get_data(data=None):
    """
    Add Sample Request AMB to Prospect's connections
    
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
            {"label": _("Opportunities"), "items": ["Opportunity"]},
            {"label": _("Quotations"), "items": ["Quotation"]},
            {"label": _("Sales Orders"), "items": ["Sales Order"]},
            {"label": _("Sample Request"), "items": ["Sample Request AMB"]},
        ],
    }