# -*- coding: utf-8 -*-
"""
BUG 87E: Dashboard Override for Sales Order Connections
Adds Sample Request AMB to the Connections section of Sales Order
"""

import frappe
from frappe import _


def get_data(data=None):
    """
    Add Sample Request AMB to Sales Order's connections
    
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
            {"label": _("Invoices"), "items": ["Sales Invoice"]},
            {"label": _("Delivery Notes"), "items": ["Delivery Note"]},
            {"label": _("Purchase Orders"), "items": ["Purchase Order"]},
            {"label": _("Sample Request"), "items": ["Sample Request AMB"]},
        ],
    }