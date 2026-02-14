"""
BOM Creator Tree View Fix for Frappe v16

Monkey-patches frappe.desk.treeview.get_all_nodes to handle parameter mismatches
in Frappe v16. The BOM Creator was calling the treeview function with 'parent_id'
instead of 'parent' and missing the 'label' parameter, causing TypeError in the
BOM Tree tab.

This fix translates between the old API (parent_id) and new API (parent + label).
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_all_nodes_fixed(doctype, parent=None, parent_id=None, label=None, **kwargs):
    """
    Fixed version of frappe.desk.treeview.get_all_nodes that handles both old and new API
    
    Args:
        doctype: DocType name
        parent: Parent node (Frappe v16 parameter name)
        parent_id: Parent node (BOM Creator parameter name - legacy)
        label: Label field (Frappe v16 parameter)
        **kwargs: Additional parameters
    
    Returns:
        List of child nodes
    """
    # Handle legacy 'parent_id' parameter from BOM Creator
    if parent_id and not parent:
        parent = parent_id
    
    # Default label if not provided
    if not label:
        # Get the default title field for this doctype
        meta = frappe.get_meta(doctype)
        label = meta.get_title_field() or "name"
    
    # Call the original Frappe function with corrected parameters
    from frappe.desk.treeview import get_all_nodes as original_get_all_nodes
    
    return original_get_all_nodes(
        doctype=doctype,
        parent=parent,
        label=label,
        **kwargs
    )
