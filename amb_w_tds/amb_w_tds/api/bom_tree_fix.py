# Copyright (c) 2024, AMB and contributors
# Fix for BOM Creator tree view get_all_nodes parameter mismatch in Frappe v16

import frappe
from frappe import _


@frappe.whitelist()
def get_all_nodes_fixed(doctype, parent=None, tree_method=None, parent_id=None, label=None, is_root=False, **filters):
	"""
	Wrapper for frappe.desk.treeview.get_all_nodes that handles both old and new parameter formats.
	This fixes the BOM Creator tree view error in Frappe v16 where get_all_nodes() is missing
	the required 'label' and 'parent' positional arguments.
	
	Args:
		doctype (str): The doctype for the tree (e.g., 'BOM Configurator')
		parent (str): The parent node value
		tree_method (str): The method to call to get tree children
		parent_id (str): Legacy parameter name for parent
		label (str): The label for the node
		is_root (bool): Whether this is the root node
		**filters: Additional filters to pass to tree_method
	
	Returns:
		list: Tree node data
	"""
	# Handle legacy parameter names - BOM Creator passes 'parent_id' instead of 'parent'
	if parent_id and not parent:
		parent = parent_id
	
	# If label is not provided, use parent as label (common in tree views)
	if not label:
		label = parent or doctype or "Root"
	
	# Ensure we have a tree_method
	if not tree_method:
		frappe.throw(_("tree_method is required"))
	
	# Clean filters - remove parameters that shouldn't be passed to get_all_nodes
	for key in ['cmd', 'parent_id', 'data']:
		filters.pop(key, None)
	
	frappe.logger().debug(f"BOM Tree Fix: doctype={doctype}, label={label}, parent={parent}, tree_method={tree_method}, is_root={is_root}")
	
	try:
		# Call the original get_all_nodes with correct parameters
		from frappe.desk import treeview
		return treeview.get_all_nodes(doctype, label, parent, tree_method, **filters)
	except Exception as e:
		frappe.log_error(f"BOM Tree Fix Error: {str(e)}", "BOM Tree Fix")
		raise
