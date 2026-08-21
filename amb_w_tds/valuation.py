"""BUG208 D-VALUE — the ONE money contract every Sample Request document shares.

⭐ THE MODEL (Hugh, rulings V-1/V-2/V-3, 2026-08-21). One contract, no modes.

  TOTAL      = the stored `commercial_value_usd` scalar, exactly as a human
               entered it. It does NOT scale with bags, rows, or anything else.
  PER-BAG    = DERIVED: total / Σ(samples_count), displayed at 4 decimals.
  SUBTOTAL   = the derived unit x that row's bag count.
  ⭐ THE TOTAL WINS THE RESIDUAL. Footing is TOTAL-ANCHORED, never unit-summed:
     3 bags of a $1.00 total print $0.3333 each and the total stays $1.00.

⛔ THIS REPLACES THE A/B/C MODE MODEL (V-3). There is no `custom_valuation_mode`,
no nature-derived default and no per-mode multiplier. The earlier design made
the declared total a FUNCTION of the bag count, so adding a sample row silently
changed what a shipment declared to customs. Pinning the total to the scalar
removes that entirely -- and with it the "zero-row sale declares $0.00" gap,
which is now impossible rather than guarded.

⚠ PRECISION IS A RENDER PROPERTY, NOT AN ARITHMETIC ONE -- the trap that caught
two seats in sequence here. Quantizing a Decimal to 0.3333 is NOT the same as
printing it: `fmt_money(0.3333, currency="USD")` returns **"$ 0.33"**, so a
reader multiplies 3 x 0.33 = 0.99 against a declared $1.00 and sees a FULL CENT
missing. The residue that matters is the one on the page. The 4-decimal unit is
enforced at the format layer (`valuation_jinja._fmt`), and the test that guards
it asserts the RENDERED STRING, not the Decimal.

⚠ Money is `Decimal` throughout, built via `str()`: in binary floats
0.1 + 0.2 == 0.30000000000000004, so "full precision" has to be a property of
the instrument, not an intention.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_MONEY = Decimal("0.01")
_UNIT = Decimal("0.0001")


def to_decimal(value) -> Decimal:
    """The single entry point into the money path. `str()` first, always.

    Decimal(0.1) carries a float's binary tail; Decimal(str(0.1)) does not.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value) -> Decimal:
    """2dp, half-up (not banker's rounding -- customs figures round up at .005)."""
    return to_decimal(value).quantize(_MONEY, rounding=ROUND_HALF_UP)


def unit_display(value) -> Decimal:
    """4dp for the DERIVED per-bag unit (V-2)."""
    return to_decimal(value).quantize(_UNIT, rounding=ROUND_HALF_UP)


def bag_count(row) -> int:
    """A row's declared bag count, floored at zero.

    ⚠ Zero is preserved rather than coerced to 1: inventing a bag would move
    every other row's derived unit, and the total is pinned regardless.
    """
    raw = row.get("samples_count") if hasattr(row, "get") else getattr(row, "samples_count", None)
    try:
        return max(int(raw or 0), 0)
    except (TypeError, ValueError):
        return 0


def total_bags(rows) -> int:
    return sum(bag_count(r) for r in (rows or []))


def total_for(value, rows=None) -> Decimal:
    """V-1: the declared total IS the stored scalar. `rows` is accepted and
    ignored, so no caller can accidentally reintroduce a bag multiplier."""
    return money(value)


def unit_for(value, rows) -> Decimal | None:
    """The derived per-bag unit: total / Σbags, at 4dp.

    Returns None when there are no bags -- a shipment can declare a total with
    no per-bag breakdown, and dividing by zero to print something would be
    inventing a figure on a customs document.
    """
    bags = total_bags(rows)
    if bags <= 0:
        return None
    return unit_display(to_decimal(value) / bags)


def lines_for(value, rows):
    """One entry per row: bag count, the shared derived unit, and the row's
    subtotal (unit x bags). The TOTAL is authoritative over the sum of these."""
    unit = unit_for(value, rows)
    out = []
    for row in (rows or []):
        bags = bag_count(row)
        out.append({
            "row": row,
            "quantity": bags,
            "unit": unit,
            "subtotal": None if unit is None else unit * bags,
        })
    return out


def residual(value, rows) -> Decimal:
    """total − Σ(rounded subtotals): what the total absorbs (V-2).

    Exposed so the property can be TESTED rather than asserted in prose. It is
    normally 0 and is at most a rounding crumb; if it is ever large, the derived
    unit is wrong and this is the number that says so.
    """
    lines = lines_for(value, rows)
    summed = sum((money(ln["subtotal"]) for ln in lines if ln["subtotal"] is not None), Decimal("0"))
    return money(total_for(value)) - summed
