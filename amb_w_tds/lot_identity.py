"""LOOP-1 · `amb_lot_identity(doc, surface)` — which lot identity a surface shows.

⭐ THE PROBLEM THIS EXISTS TO END. A lot has SEVERAL identities and they are not
interchangeable:

    golden number      0227022211            the minted lot identity
    historic lot_real  the FoxPro lote_real  what the legacy system called it
    sales lot          lote_de_venta         what a CUSTOMER was told it was
    system name        LOTE-YY-WW-####       the ERPNext document name

Every format currently decides for itself, so the same lot can appear under
different identities on two documents for the same shipment — the exact class
BUG208 was opened for, one layer up. One resolver, one matrix, one answer.

⛔ THE MATRIX IS DATA-IN-CODE (I-5). It is a module-level dict, read by nothing
but this file. There is deliberately NO config DocType, NO Single, and NO
Property Setter behind it: a matrix living in a DocType would be editable
without review, unversioned, and invisible to a code read — and the identity a
customs document prints is not a preference.

⛔ FAIL VISIBLE, NEVER SUBSTITUTE (I-6). Where a surface is ruled to print the
CUSTOMER's lot and the document has none, this returns nothing at all. It does
NOT fall back to the golden. A silent fallback is how a customs page ends up
declaring an internal number as though it were the customer's — wrong, and
wrong in a way nobody can see on the page.

⚠ ROWS THAT ARE NOT YET RULED ARE ABSENT, NOT GUESSED. The customs row awaits
Alicia/Comet returning what the issued pages actually show, and R-1's amendment
(the formats print a THIRD, SYSTEM identity) is provisional. `DEFERRED_SURFACES`
names them so a caller gets an explicit refusal instead of an invented answer,
and so a reader can see the gap rather than infer its absence.

⚠ NO FORMAT CALLS THIS YET. Migration is per-format and lands later, by ruling.
Registering it in `hooks.jinja` makes it REACHABLE from a render (I-4); it does
not change any existing page.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# The identity kinds. Strings, not DocType links — see the module docstring.
# ─────────────────────────────────────────────────────────────────────────────
GOLDEN = "golden"
HISTORIC_REAL = "historic_lot_real"
SALES_LOT = "sales_lot"
SYSTEM_NAME = "system_name"

#: Where each identity is read from. Field names only — no queries live here.
_SOURCE = {
    GOLDEN: "custom_golden_number",
    HISTORIC_REAL: "custom_historic_lot_real",
    SYSTEM_NAME: "name",
    # SALES_LOT is a CHILD TABLE, not a scalar — resolved in _sales_lot().
}

# ─────────────────────────────────────────────────────────────────────────────
# ⭐ THE MATRIX — matrix v1, ruled rows only.
#
#   order        which identities to try, in order
#   fallback     ⛔ False = fail VISIBLE. True would permit substitution and is
#                deliberately unused by every ruled row.
# ─────────────────────────────────────────────────────────────────────────────
MATRIX = {
    # An internal/operational surface may name the lot however it is held: the
    # golden is the minted identity and is correct here. This is the only row
    # where falling through to the golden is the RULED answer rather than a
    # substitution, because the reader is internal.
    "internal": {"order": (GOLDEN, HISTORIC_REAL, SYSTEM_NAME), "fallback": False},

    # The system name is what the ERPNext document is called. R-1's amendment
    # observed the formats already print it; that observation is provisional,
    # so this row resolves ONLY the system name and claims nothing more.
    "system": {"order": (SYSTEM_NAME,), "fallback": False},
}

#: ⛔ Ruled-but-unanswered, or observed-but-provisional. A caller asking for one
#: of these gets `None` and a reason — never a guess. Remove a row from here
#: only when its ruling lands, and add it to MATRIX in the same commit.
DEFERRED_SURFACES = {
    "customs": (
        "R-1 amended and provisional: Alicia/Comet must return what the ISSUED "
        "customs pages actually show before this row can be ruled. Until then a "
        "customs surface has no resolved identity — deliberately, so nothing "
        "prints the golden in a customer's place."
    ),
    "label": "matrix v1 does not rule the label surface.",
    "coa": "matrix v1 does not rule the COA surface.",
}


def _get(doc, fieldname):
    """Read one field off a doc or a plain dict. No DB access, ever."""
    if doc is None:
        return None
    if hasattr(doc, "get"):
        value = doc.get(fieldname)
    else:
        value = getattr(doc, fieldname, None)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _sales_lot(doc):
    """The first historic sales lot, read off the already-loaded child rows.

    ⚠ Reads `doc.custom_historic_sales_lots` as given. It does NOT query — the
    rows are on the document the caller already loaded, and issuing a query here
    would put a DB read on a render path.
    """
    rows = _get_rows(doc)
    for row in rows:
        lot = _get(row, "sales_lot")
        if lot:
            return lot
    return None


def _get_rows(doc):
    if doc is None:
        return []
    rows = doc.get("custom_historic_sales_lots") if hasattr(doc, "get") else getattr(
        doc, "custom_historic_sales_lots", None
    )
    return rows or []


def resolve(doc, surface):
    """Return `(identity_kind, value)` for `surface`, or `(None, None)`.

    ⛔ Returning `(None, None)` is a RESULT, not an error: it means this surface
    has no identity it may honestly show for this document. Callers must render
    nothing — not a placeholder, and never another identity.
    """
    key = (surface or "").strip().lower()

    if key in DEFERRED_SURFACES:
        return (None, None)

    row = MATRIX.get(key)
    if row is None:
        return (None, None)

    for kind in row["order"]:
        value = _sales_lot(doc) if kind == SALES_LOT else _get(doc, _SOURCE[kind])
        if value:
            return (kind, value)

    return (None, None)


def amb_lot_identity(doc, surface="internal"):
    """Jinja entry point: the identity string a surface may show, or `""`.

    ⭐ Empty string, not a placeholder — a template that prints this renders
    nothing where there is nothing to say. That is the fail-visible contract:
    the absence is on the page, where a human can see it.
    """
    _, value = resolve(doc, surface)
    return value or ""


def amb_lot_identity_kind(doc, surface="internal"):
    """Which identity was chosen — for tests and for a template that must label
    what it printed ("Lote" vs "Customer lot" are not the same caption)."""
    kind, _ = resolve(doc, surface)
    return kind or ""


def surface_status(surface):
    """Why a surface resolves to nothing: `ruled`, `deferred`, or `unknown`.

    Exposed so a verifier can tell a DEFERRED row from an UNKNOWN one. Without
    it both look like an empty string, and "not yet ruled" would be
    indistinguishable from "you typed the surface name wrong".
    """
    key = (surface or "").strip().lower()
    if key in MATRIX:
        return "ruled"
    if key in DEFERRED_SURFACES:
        return "deferred"
    return "unknown"
