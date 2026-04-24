"""
Archived Server Script: coa_amb_load_tds_parameters

V13.6.0 P3 Server Script Migration
Decision: DEL / archived
Script Type: DocType Event
Reference DocType: COA AMB
Doctype Event: Before Save
Disabled: 1
Module: RND

Runtime status:
  DO NOT IMPORT. Archive only.
"""

ORIGINAL_SCRIPT = """
#import frappe
#from frappe import _

#@frappe.whitelist()
def load_tds_parameters(coa_name, tds_name):
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
"""
