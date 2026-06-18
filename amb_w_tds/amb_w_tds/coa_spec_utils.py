"""COA spec compliance utilities (T142).

Single source of truth for COA pass/fail = the human-readable specification text.
`derive_bounds_from_spec()` turns a spec string into numeric (min, max) bounds
(None on a side = unbounded; returns None for non-numeric/text specs).
`parse_result_value()` reads an actual result, tolerating '<N' / '>=N' notation
(e.g. '<10 CFU/G').  `is_compliant()` combines them, falling back to stored
min/max only when the spec yields no numeric bounds.

Handles: range ('20 -25%', '3.5-5.0'), NMT/NLT/MAX/MIN, </<=/>/>=, tolerance
'N +/- T', exact, and text equality. Proven against the full COA-26-0015
parameter set + edge cases (T142).
"""
import re


def _num(s):
    m = re.search(r'-?\d+\.?\d*', str(s))
    return float(m.group()) if m else None


def derive_bounds_from_spec(spec):
    """Return (min, max) numeric bounds from a spec string, or None for text specs.
    A None bound means unbounded on that side (e.g. NMT -> (None, N))."""
    if not spec:
        return None
    s = str(spec).strip()
    u = s.upper()
    has_kw = re.search(r'NMT|NLT|NOT MORE THAN|NOT LESS THAN|\bMAX\b|\bMIN\b|≤|≥|<=|>=', u)
    m = re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)', s)
    if m and not has_kw:
        return (float(m.group(1)), float(m.group(2)))
    m = re.search(r'(\d+\.?\d*)\s*(?:±|\+/-|\+\s*/\s*-)\s*(\d+\.?\d*)', s)
    if m:
        t, tol = float(m.group(1)), float(m.group(2))
        return (t - tol, t + tol)
    if re.search(r'\bNMT\b|NOT MORE THAN|\bMAX\b|≤|<=|<', u):
        n = _num(s)
        return (None, n) if n is not None else None
    if re.search(r'\bNLT\b|NOT LESS THAN|\bMIN\b|≥|>=|>', u):
        n = _num(s)
        return (n, None) if n is not None else None
    if re.fullmatch(r'\s*-?\d+\.?\d*\s*%?\s*', s):
        n = _num(s)
        return (n, n)
    return None


def parse_result_value(result):
    """Numeric value of an actual result, tolerating '<N'/'>=N'/'<10 CFU/G' notation."""
    if result is None:
        return None
    m = re.search(r'-?\d+\.?\d*', str(result).strip())
    return float(m.group()) if m else None


def is_compliant(spec, result, min_value=None, max_value=None):
    """True if `result` satisfies `spec`. Spec text is the source of truth;
    stored min/max are a fallback only when the spec has no numeric bounds."""
    rv = parse_result_value(result)
    if rv is not None:
        b = derive_bounds_from_spec(spec)
        if b is None and (min_value is not None or max_value is not None):
            b = (min_value, max_value)
        if b is not None:
            lo, hi = b
            if lo is not None and rv < lo:
                return False
            if hi is not None and rv > hi:
                return False
            return True
    if spec and result:
        a, sp = str(result).strip().upper(), str(spec).strip().upper()
        return a == sp or sp in a
    return True
