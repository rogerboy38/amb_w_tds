"""BUG208 D-VALUE — the ONE money arithmetic every Sample Request document shares.

Six enabled print formats declare a customs value for the same shipment. Before
this module each one carried its own literals, so "the total" was whatever a
given template happened to print. Every format now calls in here, which is what
makes "one consistent total across every enabled format" a property of the code
rather than of six hand-edits staying in step.

⭐ THE ROUNDING DOCTRINE (amendment v5 §3, ruled 2026-08-20)
    Compute at full precision; round only for display.
    Money displays at 2dp; a DERIVED per-sample unit price displays at 4dp.
    The shipment TOTAL is the sum of FULL-PRECISION subtotals, rounded ONCE at
    the end -- never the sum of the rounded line displays, which is where penny
    drift comes from.

⚠ "Full precision" is a claim about the INSTRUMENT, not an intention: in binary
floats 0.1 + 0.2 == 0.30000000000000004, so every figure here is `Decimal`,
constructed via `str()` so a float's binary tail never enters the money path.

⭐ THE AUTHORITATIVE LINE FIGURE IS THE SUBTOTAL, never `round(unit) x qty`.
That is what keeps the total exact under Mode B, where a row's value is SHARED
across its samples and the per-sample unit can be a repeating fraction
(1.00 / 3 = 0.3333...).

⭐ MODE B FOOTS AT THE PRINTED PRECISION (Hugh, 2026-08-21 -- round to 2dp).
A Mode-B row shares its value across its samples, so the per-sample unit can be
a repeating fraction: 1.00 / 3 = 0.3333... The printed line reads
    quantity 3  x  unit $0.3333  =  $0.9999  -> ROUNDED TO 2dp -> $1.00
which is exactly the declared subtotal. So the reader's arithmetic reproduces
the declaration at the precision money is stated in, and the total stays exact
because it sums the SUBTOTALS, never the rounded units.

⚠ Read that claim precisely, because it is easy to over-state: the raw product
0.9999 is NOT equal to 1.00, and no display precision makes it so -- 1/3 does
not terminate, so adding digits moves the residue rather than removing it. What
is true, and what was ruled, is that the two agree ONCE ROUNDED TO THE 2dp the
money is declared in. The subtotal remains the authoritative figure.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

# ---- the modes (amendment v4 1) -------------------------------------------
MODE_FLAT = "A"        # one declared amount for the whole shipment
MODE_PER_ROW = "B"     # value is per ROW; the row's samples SHARE it
MODE_PER_SAMPLE = "C"  # value is per SAMPLE; the row's samples ADD

VALID_MODES = (MODE_FLAT, MODE_PER_ROW, MODE_PER_SAMPLE)

_MONEY = Decimal("0.01")
_UNIT = Decimal("0.0001")


def to_decimal(value) -> Decimal:
    """Every entry point into the money path. `str()` first, always.

    Decimal(0.1) is 0.1000000000000000055511151231257827, while
    Decimal(str(0.1)) is exactly 0.1 -- the difference between carrying a
    float's binary tail into a customs declaration and not.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value) -> Decimal:
    """Display rounding for a money figure: 2dp, half-up (not banker's)."""
    return to_decimal(value).quantize(_MONEY, rounding=ROUND_HALF_UP)


def unit_display(value) -> Decimal:
    """Display rounding for a DERIVED per-sample unit price: 4dp."""
    return to_decimal(value).quantize(_UNIT, rounding=ROUND_HALF_UP)


def default_mode_for(shipment_nature) -> str:
    """A2 (ruled): derive the default mode from the shipment's nature.

    Ruled explicitly:  "Venta" -> C (per sample) ·  "Muestra sin valor" -> A.
    ⚠ INFERRED, and flagged as such to the verifiers: the Select also offers
    "Regalo" and "Muestra mutilada", which the ruling does not name. Both are
    non-sale shipments, so they take A (flat nominal) alongside "Muestra sin
    valor". If that is wrong it is wrong for a stated reason, not silently.
    """
    return MODE_PER_SAMPLE if (shipment_nature or "").strip() == "Venta" else MODE_FLAT


def normalize_mode(mode, shipment_nature=None) -> str:
    """A stored mode wins; an absent or unrecognised one falls back to the
    derived default. Never raises -- a print must not die on a bad Select."""
    candidate = (mode or "").strip().upper()
    if candidate in VALID_MODES:
        return candidate
    return default_mode_for(shipment_nature)


def _count(row) -> int:
    """A row's sample count, floored at zero.

    ⚠ Zero is preserved rather than coerced to 1: under Mode C a zero-sample
    row genuinely contributes nothing, and inventing a sample would inflate a
    customs declaration. The zero-document case is handled by the caller.
    """
    raw = row.get("samples_count") if hasattr(row, "get") else getattr(row, "samples_count", None)
    try:
        n = int(raw or 0)
    except (TypeError, ValueError):
        n = 0
    return max(n, 0)


def line_for(mode, value, row) -> dict:
    """The three printed cells for ONE row, plus the exact subtotal.

    Returns `quantity`, `unit` (already display-rounded, or None when the mode
    prints no per-line value) and `subtotal` (FULL PRECISION -- the caller sums
    these before rounding, per the doctrine).
    """
    mode = mode if mode in VALID_MODES else MODE_FLAT
    val = to_decimal(value)
    n = _count(row)

    if mode == MODE_FLAT:
        # A declares one amount for the shipment; the lines carry no money.
        return {"quantity": n or 1, "unit": None, "subtotal": None, "mode": mode}

    if mode == MODE_PER_ROW:
        # The row's samples SHARE the row's value; the subtotal IS the value.
        if n > 1:
            return {"quantity": n, "unit": unit_display(val / n), "subtotal": val, "mode": mode}
        return {"quantity": 1, "unit": unit_display(val), "subtotal": val, "mode": mode}

    # MODE_PER_SAMPLE: the samples ADD.
    return {"quantity": n, "unit": unit_display(val), "subtotal": val * n, "mode": mode}


def lines_for(mode, value, rows) -> list:
    return [line_for(mode, value, r) for r in (rows or [])]


def total_for(mode, value, rows) -> Decimal:
    """The shipment total, computed once at full precision and rounded once.

    ⛔ Deliberately NOT `sum(money(l["subtotal"]) for l in lines)` -- summing
    rounded displays is the drift the doctrine forbids.
    """
    mode = mode if mode in VALID_MODES else MODE_FLAT
    val = to_decimal(value)

    if mode == MODE_FLAT:
        return money(val)

    subtotals = [ln["subtotal"] for ln in lines_for(mode, val, rows) if ln["subtotal"] is not None]
    return money(sum(subtotals, Decimal("0")))
