# -*- coding: utf-8 -*-
"""
Protection script for Sample Request AMB DocTypes
================================================

This module prevents custom DocTypes from being deleted during bench migrate.

GitHub Issue #37799: remove_orphan_doctypes() incorrectly deletes custom DocTypes
because it uses get_controller() as the sole orphan test, which fails during migration
due to cache issues.

Solution: By adding these DocTypes to override_doctype_class in hooks.py, Frappe
will skip the orphan check for them entirely.

This file exists solely to make the import path valid - the actual protection
is configured in hooks.py via override_doctype_class.
"""

from frappe.model.document import Document


class SampleRequestAMB(Document):
    """Marker class to protect Sample Request AMB DocType from deletion during migrate."""
    pass


class SampleRequestAMBItem(Document):
    """Marker class to protect Sample Request AMB Item DocType from deletion during migrate."""
    pass
