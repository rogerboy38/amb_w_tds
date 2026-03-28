# -*- coding: utf-8 -*-
"""
BUG 87: Dashboard Override for Sample Request AMB Connections
Adds Sample Request AMB to the Connections section of Quotation
"""

import frappe
from frappe import _


def get_data(data=None):
    """
    Add Sample Request AMB to Quotation's connections
    
    The transactions format should be:
    {
        "label": "Display Label",
        "items": ["DocType1", "DocType2"]
    }
    """
    return {
        "fieldname": "name",
        "non_standard_fieldnames": {
            "Sample Request AMB": "quotation",
        },
        "transactions": [
            {"label": _("Sales Orders"), "items": ["Sales Order"]},
            {"label": _("Sample Request"), "items": ["Sample Request AMB"]},
        ],
    }