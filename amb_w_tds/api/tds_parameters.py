# -*- coding: utf-8 -*-
# amb_w_tds.api.tds_parameters
# V13.6.0 P3 / TDS-M3 migration of Server Script "load_tds_parameters"
# Whitelisted API, api_method: load_tds_parameters
import frappe
from frappe import _


@frappe.whitelist()
def load_tds_parameters(*args, **kwargs):
    # Migrated body (verbatim) from Server Script "load_tds_parameters"
    # BEST PRACTICE Server Script for TDS Parameter Loading
    # Use this only when client-side processing is not feasible
    # For most cases, prefer client-side processing with frappe.client.get()

    import frappe
    from frappe import _
    import json

    def load_tds_parameters(coa_name, tds_name):
        """
        Load parameters from TDS to COA - Best Practice Version
        Returns minimal data for client-side processing
        """
        try:
            # =====================
            # 1. INPUT VALIDATION
            # =====================
            if not coa_name or not tds_name:
                return {
                    "success": False,
                    "message": _("COA name and TDS name are required"),
                    "error_code": "MISSING_INPUT"
                }

            # =====================
            # 2. PERMISSION CHECK
            # =====================
            # Verify user has access to both documents
            if not frappe.has_permission('COA AMB', 'read', coa_name):
                return {
                    "success": False,
                    "message": _("You don't have permission to access this COA"),
                    "error_code": "PERMISSION_DENIED_COA"
                }

            if not frappe.has_permission('TDS Product Specification', 'read', tds_name):
                return {
                    "success": False,
                    "message": _("You don't have permission to access this TDS"),
                    "error_code": "PERMISSION_DENIED_TDS"
                }

            # =====================
            # 3. DATA RETRIEVAL
            # =====================
            # Get minimal required data - avoid full document fetching
            tds_params = frappe.db.get_value(
                'TDS Product Specification',
                tds_name,
                'item_quality_inspection_parameter'
            )

            if not tds_params:
                return {
                    "success": False,
                    "message": _("No parameters found in TDS document"),
                    "error_code": "NO_PARAMETERS"
                }

            # Parse the parameters (they're stored as JSON in DB)
            try:
                parameters = json.loads(tds_params) if isinstance(tds_params, str) else tds_params
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": _("Invalid parameter data in TDS"),
                    "error_code": "INVALID_PARAMETER_DATA"
                }

            # =====================
            # 4. DATA PROCESSING
            # =====================
            # Return processed data for client-side handling
            # Client will handle the actual document updates
            processed_parameters = []

            for param in parameters:
                processed_parameters.append({
                    "parameter": param.get("parameter", "Unnamed Parameter"),
                    "specification": param.get("specification", ""),
                    "min_value": param.get("min_value"),
                    "max_value": param.get("max_value"),
                    "is_numeric": 1 if param.get("min_value") or param.get("max_value") else 0,
                    "suggested_status": "Pending"
                })

            # =====================
            # 5. SUCCESS RESPONSE
            # =====================
            return {
                "success": True,
                "message": _("Successfully retrieved {0} parameters").format(len(processed_parameters)),
                "parameter_count": len(processed_parameters),
                "parameters": processed_parameters,
                "metadata": {
                    "coa_name": coa_name,
                    "tds_name": tds_name,
                    "processed_at": frappe.utils.now(),
                    "version": "1.0"
                }
            }

        except frappe.DoesNotExistError:
            return {
                "success": False,
                "message": _("Document not found"),
                "error_code": "DOCUMENT_NOT_FOUND"
            }

        except Exception as e:
            # =====================
            # 6. ERROR HANDLING
            # =====================
            error_id = frappe.generate_hash(length=8)
            error_message = f"Error loading TDS parameters (ID: {error_id}): {str(e)}"

            # Log detailed error for debugging
            frappe.log_error(
                title="TDS Parameter Loading Error",
                message=error_message,
                reference_doctype="COA AMB",
                reference_name=coa_name
            )

            return {
                "success": False,
                "message": _("System error occurred. Please contact support. Error ID: {0}").format(error_id),
                "error_code": "SYSTEM_ERROR",
                "error_id": error_id
            }


    # =====================
    # ALTERNATIVE: Client-focused helper
    # =====================
    def get_tds_parameters_only(tds_name):
        """
        Client-focused version: Returns only parameter data
        Client handles COA document updates
        """
        try:
            if not tds_name:
                return {"success": False, "message": _("TDS name is required")}

            # Get parameter data only
            tds_params = frappe.db.get_value(
                'TDS Product Specification',
                tds_name,
                'item_quality_inspection_parameter'
            )

            if not tds_params:
                return {"success": False, "message": _("No parameters found")}

            # Parse and return raw parameter data
            parameters = json.loads(tds_params) if isinstance(tds_params, str) else tds_params

            return {
                "success": True,
                "parameters": parameters,
                "parameter_count": len(parameters),
                "tds_name": tds_name
            }

        except Exception as e:
            error_id = frappe.generate_hash(length=8)
            frappe.log_error(f"TDS parameter fetch error {error_id}: {str(e)}")
            return {
                "success": False,
                "message": _("Failed to fetch parameters"),
                "error_id": error_id
            }


    # =====================
    # HEALTH CHECK ENDPOINT
    # =====================
    def health_check():
        """
        Simple health check for monitoring
        """
        return {
            "status": "healthy",
            "timestamp": frappe.utils.now(),
            "version": "1.0",
            "service": "tds_parameter_loader"
        }
