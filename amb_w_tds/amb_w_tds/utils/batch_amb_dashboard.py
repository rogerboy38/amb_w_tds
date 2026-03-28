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
    
    The transactions format should be:
    {
        "label": "Display Label",
        "items": ["DocType1", "DocType2"]
    }
    """
    return {
        "fieldname": "name",
        "non_standard_fieldnames": {
            "Sample Request AMB": "batch_reference",
        },
        "transactions": [
            {"label": _("Sample Request"), "items": ["Sample Request AMB"]},
        ],
    }