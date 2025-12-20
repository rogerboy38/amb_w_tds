"""
AMB Agent Adapter v14.02
Safe, Frappe-cloud compatible adapter around amb_w_tds.api.agent

Author: Migration v14
"""


from amb_w_tds.api.agent import AmbAgent
from amb_w_tds.api.utils import resolve_agent_fn
import frappe
import traceback
from typing import Dict, Any


class AmbAgentAdapterV14:
    def __init__(self):
        self._load_agent()

    def _load_agent(self):
        try:
            # load class instead of module-level free functions
            self.agent = AmbAgent()
        except Exception as e:
            frappe.log_error(
                title="AMB Agent Import Error",
                message=traceback.format_exc()
            )
            raise ImportError("Failed to import AmbAgent") from e

    def _safe_call(self, fn, payload: dict | None = None):
        try:
            # bench / internal calls: pass payload kwarg
            if payload is not None:
                return fn(payload=payload)
            return fn()
        except Exception:
            frappe.log_error(
                title="AMB Agent Adapter Error",
                message=traceback.format_exc()
            )
            raise

    # QUOTATION
    def create_or_get_quotation(self, payload: Dict[str, Any]) -> str:
        # resolve_agent_fn can just be: getattr(self.agent, "create_or_get_quotation")
        fn = resolve_agent_fn(self.agent, "create_or_get_quotation")
        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Quotation")


    # ------------------------------------------------------------------
    # SALES ORDER
    # ------------------------------------------------------------------

    def create_or_get_sales_order(self, payload: Dict[str, Any]) -> str:
        """
        Create or fetch Sales Order from Quotation
        """
        fn = resolve_agent_fn(self.agent, "create_or_get_sales_order")

        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Sales Order")

    # ------------------------------------------------------------------
    # WORK ORDER
    # ------------------------------------------------------------------

    def create_or_get_work_order(self, payload: Dict[str, Any]) -> str:
        """
        Create or fetch Work Order from Sales Order / BOM
        """
        fn = resolve_agent_fn(self.agent, "create_or_get_work_order")

        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Work Order")

    # ------------------------------------------------------------------
    # STOCK ENTRY
    # ------------------------------------------------------------------

    def create_stock_entry(self, payload: Dict[str, Any]) -> str:
        """
        Create Stock Entry (SAP 561 / 261 supported)
        """
        fn = resolve_agent_fn(self.agent, "create_stock_entry")

        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Stock Entry")

    # ------------------------------------------------------------------
    # DELIVERY NOTE
    # ------------------------------------------------------------------

    def create_delivery_note(self, payload: Dict[str, Any]) -> str:
        """
        Create Delivery Note from Sales Order
        """
        fn = resolve_agent_fn(self.agent, "create_delivery_note")

        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Delivery Note")

    # ------------------------------------------------------------------
    # SHIPMENT
    # ------------------------------------------------------------------

    def create_shipment(self, payload: Dict[str, Any]) -> str:
        """
        Create Shipment (eShipz / ERPNext Shipping compatible)
        """
        fn = resolve_agent_fn(self.agent, "create_shipment")

        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Shipment")

    # ------------------------------------------------------------------
    # SALES INVOICE
    # ------------------------------------------------------------------

    def create_or_get_invoice(self, payload: Dict[str, Any]) -> str:
        """
        Create or fetch Sales Invoice
        """
        fn = resolve_agent_fn(self.agent, "create_or_get_invoice")

        result = self._safe_call(fn, payload=payload)
        return self._extract_name(result, "Sales Invoice")

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _extract_name(self, result: Any, doctype: str) -> str:
        """
        Normalize agent return values.
        Supports:
        - string
        - dict {name}
        - dict {data: {name}}
        - fallback: latest doc
        """

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            if "name" in result:
                return result["name"]
            if "data" in result and isinstance(result["data"], dict):
                if "name" in result["data"]:
                    return result["data"]["name"]

        # Fallback (safe only in migration context)
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


# ----------------------------------------------------------------------
# WHITELISTED TEST ENDPOINTS (for curl / bench console)
# ----------------------------------------------------------------------

@frappe.whitelist()
def test_create_quotation(payload: dict):
    adapter = AmbAgentAdapterV14()
    return adapter.create_or_get_quotation(payload)


@frappe.whitelist()
def test_create_sales_order(payload: dict):
    adapter = AmbAgentAdapterV14()
    return adapter.create_or_get_sales_order(payload)


@frappe.whitelist()
def test_create_invoice(payload: dict):
    adapter = AmbAgentAdapterV14()
    return adapter.create_or_get_invoice(payload)
