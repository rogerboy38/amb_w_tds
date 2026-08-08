"""COA specification / result comparison utilities.

**Single source of truth for the store-zero convention.** Both COA doctypes and
every call site must IMPORT `effective_bounds()` from here rather than re-derive
the rule inline. The rule has already been re-derived in three separate places
once (`validate_test_parameters`, `validate_numeric_result`,
`check_parameter_compliance`) and two of the three were wrong for six weeks.

Provenance
----------
`derive_bounds_from_spec()` and `parse_result_value()` are HARVESTED from the
T142 branch (`3dc72f4`, `feature/t142-coa-uat`), whose parser is genuinely
better than the shipped one: tolerance notation, unicode ``≤``/``≥``,
spelled-out keywords and en-dash ranges. Two shipped behaviours are preserved
on top of the harvest — see `derive_bounds_from_spec`.

T142's `is_compliant()` is deliberately NOT harvested. It has three defects:
its stored-bounds fallback ignores the store-zero rule; it has four fail-open
``return True`` paths; and it matches specs by substring, so ``NOT NEGATIVE``
satisfies a ``NEGATIVE`` spec. `evaluate()` below is a re-implementation on the
shipped (500c1579) semantics instead.

Design rules this module obeys
------------------------------
1. **Never fail open.** There is no path that returns Pass because nothing
   matched. "No rule fired" is `UNEVALUATED`, a third status distinct from
   Pass and Fail.
2. **Record which rule fired.** Every verdict carries the rule name, so a
   disagreement between evaluators is diagnosable instead of merely visible.
3. **No frappe import.** This module is pure stdlib so it is unit-testable
   without a site — which matters while `bench run-tests --app amb_w_tds`
   discovers zero tests.
"""

import re
from typing import NamedTuple, Optional, Tuple

__all__ = [
    "PASS", "FAIL", "UNEVALUATED", "Verdict",
    "effective_bound", "effective_bounds",
    "derive_bounds_from_spec", "parse_result_value", "evaluate",
]

PASS = "Pass"
FAIL = "Fail"
UNEVALUATED = "Unevaluated"

#: Results that are an explicit rejection regardless of spec.
REJECT_TOKENS = frozenset({
    "FAIL", "REJECT", "REJECTED", "OUT OF SPEC", "OUT OF SPECIFICATION",
    "NON-CONFORMING", "NONCONFORMING", "DOES NOT CONFORM", "NOT CONFORM",
    "NON CONFORME", "RECHAZADO",
})

#: Tokens that invert the sense of whatever follows them. Checked BEFORE any
#: positive match, so 'NOT NEGATIVE' can never satisfy a 'NEGATIVE' spec.
NEGATION_TOKENS = ("NOT ", "NON-", "NON ", "NO ", "DOES NOT ", "DID NOT ")

#: A rejection is often decorated — 'FAIL - DID NOT PASS', 'REJECTED (note 3)'.
#: Matched only as a whole token at the START of the result, never mid-string:
#: a substring test would reject 'NO FAILURE DETECTED', and mid-string matching
#: is the same mistake that lets 'NOT NEGATIVE' satisfy 'NEGATIVE'.
_REJECT_PREFIX = re.compile(
    r"^(FAIL|REJECT|REJECTED|OUT OF SPEC|OUT OF SPECIFICATION|NON-CONFORMING"
    r"|NONCONFORMING|DOES NOT CONFORM|NOT CONFORM|NON CONFORME|RECHAZADO)\b")

_LEAD_NUM = re.compile(r"[-+]?\d*\.?\d+")
_RANGE = re.compile(
    r"([-+]?\d*\.?\d+)\s*(?:[-–—]|TO)\s*([-+]?\d*\.?\d+)", re.IGNORECASE)
_TOLERANCE = re.compile(
    r"([-+]?\d*\.?\d+)\s*(?:±|\+/-|\+\s*/\s*-)\s*([-+]?\d*\.?\d+)")
_EXACT = re.compile(r"\s*[-+]?\d*\.?\d+\s*%?\s*")
_KEYWORD = re.compile(
    r"NMT|NLT|NOT MORE THAN|NOT LESS THAN|\bMAX\b|\bMIN\b|≤|≥|<=|>=")
_UPPER_BOUND = re.compile(r"\bNMT\b|NOT MORE THAN|\bMAX\b|≤|<=")
_LOWER_BOUND = re.compile(r"\bNLT\b|NOT LESS THAN|\bMIN\b|≥|>=")


class Verdict(NamedTuple):
    """The outcome of one parameter evaluation.

    `status` is one of PASS / FAIL / UNEVALUATED. `rule` names the branch that
    decided it, so two evaluators disagreeing can be compared rule-for-rule.
    `detail` is human-readable and safe to surface in the UI.
    """
    status: str
    rule: str
    detail: str = ""

    @property
    def is_pass(self) -> bool:
        """True ONLY for an affirmative Pass. UNEVALUATED is not a pass."""
        return self.status == PASS


def _num(value) -> Optional[float]:
    """Leading number of a value, or None.

    '23.5%' -> 23.5 · '<10 CFU/G' -> 10.0 · 'NMT 100 CFU/G' -> 100.0 ·
    'Pass'/'NEGATIVE' -> None. Thousands separators are tolerated.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _LEAD_NUM.search(str(value).replace(",", ""))
    return float(m.group()) if m else None


# --------------------------------------------------------------------------
# THE STORE-ZERO PREDICATE — import this, never re-derive it
# --------------------------------------------------------------------------

def effective_bound(stored) -> Optional[float]:
    """Turn ONE stored bound into a real bound, or None meaning 'no bound'.

    The COA convention stores the unused side of a one-sided spec as 0:
    an ``NLT 10`` row stores ``min_value=10, max_value=0`` and an ``NMT 100``
    row stores ``min_value=0, max_value=100``. A stored 0 therefore means
    "unbounded on this side", NOT "the limit is zero".

    ``None`` and ``''`` mean the same thing. Any other non-numeric input is
    treated as no bound rather than raising, because this runs inside save.
    """
    if stored is None or stored == "":
        return None
    n = _num(stored)
    if n is None or n == 0:
        return None
    return n


def effective_bounds(min_value, max_value) -> Tuple[Optional[float], Optional[float]]:
    """Both stored bounds through `effective_bound`. Returns ``(lo, hi)``."""
    return effective_bound(min_value), effective_bound(max_value)


# --------------------------------------------------------------------------
# HARVESTED FROM T142 (3dc72f4), with two shipped behaviours preserved
# --------------------------------------------------------------------------

def derive_bounds_from_spec(spec) -> Optional[Tuple[Optional[float], Optional[float]]]:
    """Numeric ``(min, max)`` implied by a spec STRING, or None for text specs.

    A ``None`` on a side means unbounded there, so ``NMT 100`` -> ``(None, 100)``.
    Returning ``None`` (rather than a tuple) means "this spec carries no numeric
    criterion" and the caller should route to text handling.

    Preserved from the shipped parser on top of the T142 harvest:

    * ``<`` and ``>`` are only treated as bounds when the OTHER one is absent,
      so a spec mentioning both does not silently become one-sided.
    * ``to`` is accepted as a range separator alongside ``-`` and en/em dash.
    """
    if not spec:
        return None
    s = str(spec).strip()
    if not s:
        return None
    u = s.upper()
    has_keyword = bool(_KEYWORD.search(u))

    # Range: '20-25%', '3.5 – 5.0', '20 to 25'. Not applied when a keyword is
    # present, so 'NMT 20-25' is not misread as a range.
    if not has_keyword:
        m = _RANGE.search(s)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            return (lo, hi) if lo <= hi else (hi, lo)

    # Tolerance: 'N ± T', 'N +/- T'.
    m = _TOLERANCE.search(s)
    if m:
        target, tol = float(m.group(1)), float(m.group(2))
        tol = abs(tol)
        return (target - tol, target + tol)

    # One-sided. '<' / '>' only count when unambiguous (shipped behaviour).
    lone_lt = "<" in s and ">" not in s
    lone_gt = ">" in s and "<" not in s
    if _UPPER_BOUND.search(u) or lone_lt:
        n = _num(s)
        return (None, n) if n is not None else None
    if _LOWER_BOUND.search(u) or lone_gt:
        n = _num(s)
        return (n, None) if n is not None else None

    # Bare number: an exact target.
    if _EXACT.fullmatch(s):
        n = _num(s)
        return (n, n) if n is not None else None

    return None


def parse_result_value(result) -> Optional[float]:
    """Numeric value of an actual result, tolerating '<N' / '>=N' / '<10 CFU/G'."""
    return _num(result)


# --------------------------------------------------------------------------
# THE COMPARATOR — re-implemented on 500c1579 semantics, never fails open
# --------------------------------------------------------------------------

def _is_negated(text: str) -> bool:
    """True if `text` carries a negation token."""
    return any(tok in text for tok in NEGATION_TOKENS)


def _compare(value: float, lo: Optional[float], hi: Optional[float],
             rule: str, source: str) -> Verdict:
    """Compare a number against bounds where either side may be None.

    Asserts BOTH directions explicitly — a one-sided check is how this defect
    family keeps recurring.
    """
    if lo is not None and value < lo:
        return Verdict(FAIL, rule, f"{value} is below the minimum {lo} ({source})")
    if hi is not None and value > hi:
        return Verdict(FAIL, rule, f"{value} is above the maximum {hi} ({source})")
    bounds = []
    if lo is not None:
        bounds.append(f"min {lo}")
    if hi is not None:
        bounds.append(f"max {hi}")
    return Verdict(PASS, rule, f"{value} satisfies {' and '.join(bounds)} ({source})")


def evaluate(spec, result, min_value=None, max_value=None) -> Verdict:
    """Evaluate one COA parameter. Returns a `Verdict`, never a bare bool.

    Priority follows the shipped scorer (500c1579), so the stored bounds win
    over the spec text when both are present:

    1. stored ``min_value``/``max_value``, after the store-zero rule
    2. numeric bounds parsed out of the spec text
    3. qualitative spec text (negative-expected, exact match)
    4. explicit reject tokens in the result

    Anything that reaches the end is `UNEVALUATED` — never Pass. A parameter
    nobody could evaluate is not a compliant parameter; it is an unanswered
    question, and the caller must surface it as such.
    """
    result_text = ("" if result is None else str(result)).strip()
    result_upper = result_text.upper()
    spec_text = ("" if spec is None else str(spec)).strip()

    if not result_text:
        return Verdict(UNEVALUATED, "no-result", "No result recorded")

    # An explicit rejection outranks everything, including numeric bounds.
    # No negation guard is needed here and none is applied: several canonical
    # reject tokens legitimately contain a negation word ('NOT CONFORM',
    # 'NON CONFORME'), and the prefix rule is anchored, so 'NOT REJECTED' and
    # 'NO FAILURE DETECTED' cannot match it in the first place.
    if result_upper in REJECT_TOKENS or _REJECT_PREFIX.match(result_upper):
        return Verdict(FAIL, "reject-token", f"Result '{result_text}' is an explicit rejection")

    rnum = parse_result_value(result)

    # 1. Stored bounds, store-zero applied.
    lo, hi = effective_bounds(min_value, max_value)
    if lo is not None or hi is not None:
        if rnum is None:
            return Verdict(UNEVALUATED, "stored-bounds-unparsable-result",
                           f"Numeric bounds are set but result '{result_text}' has no number")
        return _compare(rnum, lo, hi, "stored-bounds", "stored")

    # 2. Numeric bounds implied by the spec text.
    if spec_text:
        derived = derive_bounds_from_spec(spec_text)
        if derived is not None:
            dlo, dhi = derived
            if rnum is None:
                return Verdict(UNEVALUATED, "spec-bounds-unparsable-result",
                               f"Spec '{spec_text}' is numeric but result '{result_text}' has no number")
            return _compare(rnum, dlo, dhi, "spec-bounds", f"spec '{spec_text}'")

        # 3. Qualitative spec.
        spec_upper = spec_text.upper()
        wants_absence = (
            "NEGATIVE" in spec_upper or "ABSENT" in spec_upper
            or spec_upper in ("NONE", "NIL")
        ) and not _is_negated(spec_upper)
        if wants_absence:
            if _is_negated(result_upper):
                return Verdict(FAIL, "negative-expected",
                               f"Result '{result_text}' negates the expected absence")
            absent = (
                "NEGATIVE" in result_upper or "ABSENT" in result_upper
                or result_upper in ("NONE", "NIL", "0")
                or (rnum is not None and rnum == 0)
            )
            return Verdict(PASS if absent else FAIL, "negative-expected",
                           f"Spec expects absence; result '{result_text}'")

        # Exact textual agreement. Equality only — substring matching is what
        # lets 'NOT NEGATIVE' satisfy 'NEGATIVE', so it is not used here.
        if result_upper == spec_upper:
            return Verdict(PASS, "text-exact", f"Result matches spec '{spec_text}'")

        return Verdict(UNEVALUATED, "text-no-criterion",
                       f"Spec '{spec_text}' carries no machine-checkable criterion")

    return Verdict(UNEVALUATED, "no-criterion",
                   f"No bounds and no specification for result '{result_text}'")
