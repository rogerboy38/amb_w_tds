"""BUG208 — the Jinja surface the armed print formats call.

Exposed via hooks.jinja so every format shares ONE money contract:

    {% set v = amb_valuation(doc) %}
    {% for ln in v.lines %} {{ ln.quantity }} {{ ln.unit_text }} {{ ln.subtotal_text }}
    {{ v.total_text }}

⭐ A hook, not six template edits: the ruled property is "the same shipment
renders ONE total across every enabled format". Six copies of an expression hold
that only until one is edited; one callable makes it structural.

⛔⛔ THE PRECISION BUG THIS FILE EXISTS TO NOT REPEAT. `fmt_money` defaults to
the currency's precision (2), so a correctly-derived unit of 0.3333 PRINTS as
"$ 0.33" and a reader computes 3 x 0.33 = 0.99 against a declared $1.00 -- a
FULL CENT of visible residue. Two seats verified the Decimal layer, found
0.3333, and both concluded the document was fine. **The residue that matters is
the one on the page**, so the unit path passes precision=4 explicitly and the
guard test asserts the RENDERED STRING.
"""

from __future__ import annotations

import frappe

from amb_w_tds.valuation import (
    currency_name_es,
    lines_for,
    money,
    total_for,
    unit_for,
)

__all__ = ["amb_valuation", "amb_customs_value", "amb_row_uom", "currency_name_es"]

# V-2: the derived per-bag unit prints at 4 decimals; money prints at 2.
UNIT_PRECISION = 4


def _fmt(amount, currency, precision=None) -> str:
    """Format a money figure in the DOCUMENT's currency.

    `precision=4` self-trims: fmt_money(1.00, precision=4) -> "$ 1.00" while
    fmt_money(0.3333, precision=4) -> "$ 0.3333", so the unit path never pads a
    round number with noise.

    ⚠ The except-branch mirrors the SAME precision. It previously hardcoded
    `:.2f`, which meant a site that could not resolve the currency silently fell
    back to the exact rounding this fix removes -- a fallback that reintroduces
    the bug is worse than no fallback, because it only fires where nobody looks.
    """
    if amount is None:
        return ""
    code = currency or "USD"

    # ⛔ Coerce BEFORE the try. The earlier version called float(amount) inside
    # the try AND again in the except, so a non-numeric value raised twice and
    # the "graceful fallback" killed the print outright — measured: _fmt("abc")
    # raised ValueError. A fallback that can raise is not a fallback.
    try:
        numeric = float(amount)
    except (TypeError, ValueError):
        return ""

    digits = 2 if precision is None else precision
    try:
        if precision is None:
            rendered = frappe.utils.fmt_money(numeric, currency=code)
        else:
            rendered = frappe.utils.fmt_money(numeric, currency=code, precision=precision)
    except Exception:
        rendered = f"{numeric:.{digits}f}"

    # ⚠ For an unrecognised currency fmt_money prefixes the CODE rather than a
    # symbol, so appending it again yields "MXN 1.00 MXN". Only append when the
    # code is not already there.
    return rendered if code in rendered else f"{rendered} {code}"


def amb_valuation(doc) -> dict:
    """Everything a format needs to print the value block, computed once."""
    rows = doc.get("samples") or []
    currency = doc.get("currency") or "USD"
    value = doc.get("commercial_value_usd")

    unit = unit_for(value, rows)
    lines = []
    for computed in lines_for(value, rows):
        lines.append({
            "row": computed["row"],
            "quantity": computed["quantity"],
            "unit": computed["unit"],
            # ⭐ 4dp — the whole point of the render-layer fix.
            "unit_text": _fmt(computed["unit"], currency, precision=UNIT_PRECISION),
            "subtotal": computed["subtotal"],
            "subtotal_text": _fmt(None if computed["subtotal"] is None else money(computed["subtotal"]), currency),
        })

    total = total_for(value)
    return {
        "currency": currency,
        # the Spanish half of the bilingual caption names the currency in words
        "currency_es": currency_name_es(currency),
        "lines": lines,
        "unit": unit,
        "unit_text": _fmt(unit, currency, precision=UNIT_PRECISION),
        "total": total,
        "total_text": _fmt(total, currency),
    }


def amb_customs_value(doc) -> str:
    """The single declared customs figure the memos print.

    ⭐ Identical to the Proforma's total BY CONSTRUCTION -- memo and proforma can
    no longer disagree, which was the original ticket.
    """
    return amb_valuation(doc)["total_text"]


def amb_row_uom(row) -> str:
    """D-UOM: the row's real unit, never a literal fallback.

    The templates carried `{{ it.uom or "g" }}` with `uom` NULL on live rows
    whose Item is stocked in Kg -- printing "1.000 g" for a 1 Kg line is a 1000x
    MASS UNDER-DECLARATION on a customs document. The controller backfills from
    the Item; this is the render-side belt.
    """
    uom = (row.get("uom") or "").strip() if hasattr(row, "get") else ""
    if uom:
        return uom
    item = row.get("item") if hasattr(row, "get") else None
    if item:
        stock_uom = frappe.db.get_value("Item", item, "stock_uom")
        if stock_uom:
            return stock_uom
    # ⛔ No silent unit: an absent unit shows as absent, so a human catches it
    # rather than it defaulting to the one that under-declares by 1000x.
    return ""
