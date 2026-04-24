# -*- coding: utf-8 -*-
# ============================================================
# amb_w_tds.doctype_events.sales_invoice
# ============================================================
# V13.6.0 P3 Server Script -> Python migration (batch TDS-M2)
#
# Source Server Scripts (DocType Event, Sales Invoice):
#   1. "Force Customer Specific Account"             (Before Insert)
#   2. "Set Customer Invoice Currency from Sales Order" (Before Save)
#
# Both source scripts are/were Enabled in Frappe and now live
# in-code. After verification, the Server Script documents
# should be disabled and archived under docs/legacy/.
# ============================================================
import frappe


def force_customer_specific_account(doc, method=None):
    """Before Insert on Sales Invoice (migrated from Server Script
    'Force Customer Specific Account').
    """
    # Force Customer Specific Account
    # Forzar la cuenta especifica del cliente en la factura
    # Ejecutado ANTES de insertar la factura

    # Solo proceder si hay cliente y compania
    if doc.customer and doc.company:
        # Buscar la cuenta especifica del cliente en Party Account
        customer_account = frappe.db.get_value(
            "Party Account",
            {
                "parent": doc.customer,
                "parenttype": "Customer",
                "company": doc.company
            },
            "account"
        )

        if customer_account:
            # Si encontramos una cuenta especifica, forzarla
            doc.debit_to = customer_account

            # Opcional: Agregar un comentario visible
            doc.add_comment("Info", f"Usando cuenta especifica: {customer_account}")

            # Log para debugging
            frappe.log_error(
                title="Customer Account Applied",
                message=f"Customer: {doc.customer}\nAccount: {customer_account}"
            )
        else:
            # Si no hay cuenta especifica, usar la logica normal
            frappe.log_error(
                title="No Specific Account Found",
                message=f"Customer: {doc.customer} - usando cuenta por defecto"
            )


def set_customer_invoice_currency_from_sales_order(doc, method=None):
    """Before Save on Sales Invoice (migrated from Server Script
    'Set Customer Invoice Currency from Sales Order').
    """
    # Set Customer Invoice Currency fields to grand_total
    if doc.customer:
        doc.custom_customer_invoice_currency = doc.grand_total or 0
        doc.custom_customer_invoice_currency2 = doc.grand_total or 0
