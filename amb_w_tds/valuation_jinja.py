"""BUG208 — the Jinja surface the six armed print formats call.

Exposed via hooks.jinja so every format shares ONE arithmetic:

    {% set v = amb_valuation(doc) %}
    {% for ln in v.lines %} ... {{ ln.quantity }} {{ ln.unit_text }} {{ ln.subtotal_text }}
    {{ v.total_text }}

⭐ Why a hook and not six template edits: the ruled property is "the same
shipment renders ONE total across every enabled format". Six copies of an
expression satisfy that only until one of them is edited. One callable makes it
structural.

⚠ Currency is read from the DOCUMENT, never asserted here -- `currency='MXN'`
exists on 4 of 16 live documents while every template hardcoded "USD".
"""

from __future__ import annotations

import frappe

from amb_w_tds.valuation import (
    MODE_FLAT,
    lines_for,
    money,
    normalize_mode,
    total_for,
)


def _fmt(amount, currency) -> str:
    """Format a money figure in the document's currency.

    Falls back to a plain 2dp string if the site cannot resolve the currency --
    a print must degrade to a readable number, never to a traceback.
    """
    if amount is None:
        return ""
    code = currency or "USD"
    # ⭐ The ISO code is printed alongside the symbol on purpose. These are
    # customs documents and 4 of 16 live shipments carry MXN against templates
    # that hardcoded "USD" -- "$" alone is ambiguous between the two.
    try:
        return f"{frappe.utils.fmt_money(float(amount), currency=code)} {code}"
    except Exception:
        return f"{amount:.2f} {code}"


def amb_valuation(doc) -> dict:
    """Everything a format needs to print the value block, computed once."""
    rows = doc.get("samples") or []
    currency = doc.get("currency") or "USD"
    mode = normalize_mode(doc.get("custom_valuation_mode"), doc.get("shipment_nature"))
    value = doc.get("commercial_value_usd")

    lines = []
    for row, computed in zip(rows, lines_for(mode, value, rows)):
        lines.append({
            "row": row,
            "mode": mode,
            "quantity": computed["quantity"],
            "unit": computed["unit"],
            # A prints no per-line money at all; B/C print theirs.
            "unit_text": "" if computed["unit"] is None else _fmt(computed["unit"], currency),
            "subtotal": computed["subtotal"],
            "subtotal_text": "" if computed["subtotal"] is None else _fmt(money(computed["subtotal"]), currency),
        })

    total = total_for(mode, value, rows)
    return {
        "mode": mode,
        "is_flat": mode == MODE_FLAT,
        "currency": currency,
        "lines": lines,
        "total": total,
        "total_text": _fmt(total, currency),
    }


def amb_customs_value(doc) -> str:
    """The single declared customs figure the ES/ENG memos print.

    ⭐ Identical to the Proforma's total by construction -- the memos and the
    Proforma can no longer disagree, which was the original ticket.
    """
    return amb_valuation(doc)["total_text"]


def amb_row_uom(row) -> str:
    """D-UOM: the row's real unit, never a literal fallback.

    The templates carried `{{ it.uom or "g" }}` with `uom` NULL on 6 of 11 live
    child rows whose Item is stocked in Kg -- printing "1.000 g" for a 1 Kg line
    is a 1000x MASS UNDER-DECLARATION on a customs document. The controller now
    backfills `uom` from the Item, and this is the render-side belt: it asks the
    Item rather than inventing grams.
    """
    uom = (row.get("uom") or "").strip() if hasattr(row, "get") else ""
    if uom:
        return uom
    item = row.get("item") if hasattr(row, "get") else None
    if item:
        stock_uom = frappe.db.get_value("Item", item, "stock_uom")
        if stock_uom:
            return stock_uom
    # ⛔ No silent unit. An absent unit is shown as absent so it is caught by a
    # human, rather than defaulted to the one that under-declares by 1000x.
    return ""
