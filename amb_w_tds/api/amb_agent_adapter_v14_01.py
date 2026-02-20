"""
AMB Agent Adapter v14.01
Safe wrapper around amb_w_tds/api/agent.py

Author: Migration v14
"""

from typing import Dict, Any, Optional
import frappe
import traceback


class AmbAgentAdapterV14:
    """
    Adapter for amb_w_tds API agent.
    All migration code must go through this adapter.
    """

    def __init__(self):
        self._load_agent()

    # ---------------------------------------------------------
    # Internal
    # ---------------------------------------------------------

    def _load_agent(self):
        try:
            from amb_w_tds.api import agent
            self.agent = agent
        except Exception as e:
            raise ImportError(
                "Failed to import amb_w_tds.api.agent"
            ) from e

    def _safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            frappe.log_error(
                title="AMB Agent Adapter Error",
                message=traceback.format_exc()
            )
            raise RuntimeError(str(e))

    # ---------------------------------------------------------
    # Quotation
    # ---------------------------------------------------------

    
    #
    def create_or_get_quotation(self, payload: Dict[str, Any]) -> str:
        try:
            fn = getattr(self.agent, "create_or_get_quotation")
        except AttributeError:
            raise NotImplementedError(
                "create_or_get_quotation not found in amb_w_tds.api.agent"
            )
    
        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Quotation")

    
    # ---------------------------------------------------------
    # Sales Order
    # ---------------------------------------------------------

    def create_or_get_sales_order(
        self,
        payload: Dict[str, Any]
    ) -> str:
        """
        Create or fetch a Sales Order via amb agent.
        Returns sales order name.
        """

        if not hasattr(self.agent, "create_sales_order"):
            raise NotImplementedError(
                "create_sales_order not found in amb_w_tds.api.agent"
            )

        result = self._safe_call(
            self.agent.create_sales_order,
            payload=payload
        )

        return self._extract_name(result, "Sales Order")

    # ---------------------------------------------------------
    # Sales Invoice
    # ---------------------------------------------------------

    def create_or_get_invoice(
        self,
        payload: Dict[str, Any]
    ) -> str:
        """
        Create or fetch a Sales Invoice via amb agent.
        Returns invoice name.
        """

        if hasattr(self.agent, "create_sales_invoice"):
            result = self._safe_call(
                self.agent.create_sales_invoice,
                payload
            )
        elif hasattr(self.agent, "create_invoice"):
            result = self._safe_call(
                self.agent.create_invoice,
                payload
            )
        else:
            raise NotImplementedError(
                "No invoice creation method found in amb_w_tds.api.agent"
            )

        return self._extract_name(result, "Sales Invoice")

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _extract_name(
        self,
        result: Any,
        doctype: str
    ) -> str:
        """
        Normalize agent return values.
        Supports dict, doc, string.
        """

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            if "name" in result:
                return result["name"]
            if "data" in result and isinstance(result["data"], dict):
                return result["data"].get("name")

        # Fallback: last created doc
        name = frappe.db.get_value(
            doctype,
            {},
            "name",
            order_by="creation desc"
        )

        if not name:
            raise RuntimeError(
                f"Failed to resolve {doctype} name from agent response"
            )

        return name
@frappe.whitelist()
def test_create_quotation(payload: dict):
    adapter = AmbAgentAdapterV14()
    return adapter.create_or_get_quotation(payload)
