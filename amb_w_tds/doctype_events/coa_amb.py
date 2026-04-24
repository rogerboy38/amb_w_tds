# -*- coding: utf-8 -*-
# ==========================================================
# amb_w_tds.doctype_events.coa_amb
# ==========================================================
# V13.6.0 P3 / TDS-M1 migration of 3 COA AMB Server Scripts:
#   1. "coa_amb_1"                        (DE, COA AMB, Before Save, disabled=1)
#   2. "coa_amb_tds_loader_1"             (DE, COA AMB, Before Save, disabled=1)
#      -> byte-identical duplicate of coa_amb_1 (md5 match confirmed)
#   3. "coa_amb_load_tds_parameters_1"    (DE, COA AMB, Before Save, disabled=1)
#      -> body is a library function, not a hook-shaped handler;
#         preserved here for audit parity, not registered in hooks.py
#
# Unblocked by BUG-117A/B (UI-only) + forward-port 1910130.
# Registered hook: coa_amb_before_save (covers DB rows 1 and 2).
# ==========================================================
import frappe
from frappe import _


# ---- Migrated from Server Scripts "coa_amb_1" / "coa_amb_tds_loader_1" ----
# (both DB rows had identical bodies; registered ONCE in hooks.py to avoid double-run)
# DocType Event Server Script
def coa_amb_before_save(doc, method):
    """Automatically load TDS parameters when linked_tds is set"""
    if doc.linked_tds and doc.docstatus == 0:
        _load_tds_parameters_event(doc, doc.linked_tds)

def _load_tds_parameters_event(coa_doc, tds_name):
    """Load parameters for DocType event"""
    try:
        # Get TDS document
        tds_doc = frappe.get_doc('TDS Product Specification', tds_name)
        
        # Check if TDS has parameters
        if not hasattr(tds_doc, 'item_quality_inspection_parameter') or not tds_doc.item_quality_inspection_parameter:
            frappe.msgprint("No parameters found in selected TDS", alert=True)
            return
        
        # Clear existing parameters
        coa_doc.coa_quality_test_parameter = []
        
        # Copy parameters
        param_count = 0
        for tds_param in tds_doc.item_quality_inspection_parameter:
            new_param = {
                'parameter': tds_param.parameter or 'Parameter',
                'specification': tds_param.specification or '',
                'min_value': tds_param.min_value,
                'max_value': tds_param.max_value,
                'is_numeric': 1,
                'result_status': 'Pending'
            }
            coa_doc.append('coa_quality_test_parameter', new_param)
            param_count += 1
        
        frappe.msgprint(f"Loaded {param_count} parameters from TDS", alert=True)
        
    except Exception as e:
        frappe.log_error(f"Error loading TDS parameters: {str(e)}")


# ---- Migrated from Server Script "coa_amb_load_tds_parameters_1" ----
# Preserved verbatim for audit parity. NOT registered in hooks.py
# (source row was disabled=1 and the body is a library function, not a
#  before_save handler). Kill-patch will remove the DB row.
#import frappe
#from frappe import _

#@frappe.whitelist()
def _coa_amb_load_tds_parameters_legacy(coa_name, tds_name):
    try:
        # Get the COA document
        coa_doc = frappe.get_doc('COA AMB', coa_name)
        
        # Clear existing child table
        coa_doc.set('coa_quality_test_parameter', [])
        
        # Get the TDS document
        tds_doc = frappe.get_doc('TDS Product Specification', tds_name)
        
        # Check if TDS has parameters
        if not tds_doc.get('item_quality_inspection_parameter'):
            return {"success": False, "message": "No parameters found in TDS"}
        
        # Copy each parameter from TDS to COA
        param_count = 0
        for tds_param in tds_doc.get('item_quality_inspection_parameter'):
            coa_param = coa_doc.append('coa_quality_test_parameter', {})
            
            # Map the fields
            coa_param.parameter = tds_param.parameter or "Parameter"
            coa_param.specification = tds_param.specification or ""
            coa_param.min_value = tds_param.min_value
            coa_param.max_value = tds_param.max_value
            coa_param.is_numeric = 1
            coa_param.result_status = "N/A"
            
            param_count += 1
        
        # Save the document
        coa_doc.save()
        
        return {
            "success": True, 
            "message": "Loaded " + str(param_count) + " parameters from TDS",
            "parameter_count": param_count
        }
        
    except Exception as e:
        frappe.log_error(f"Error loading TDS parameters: {str(e)}")
        return {"success": False, "message": str(e)}
