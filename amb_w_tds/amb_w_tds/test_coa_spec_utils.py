"""Tests for `coa_spec_utils`.

Deliberately pure stdlib — no frappe import, no site required:

    python -m unittest amb_w_tds.amb_w_tds.test_coa_spec_utils -v
    python amb_w_tds/amb_w_tds/test_coa_spec_utils.py

`bench run-tests --app amb_w_tds` currently discovers ZERO tests (one
unimportable module kills the whole collection), so a test that needs the
bench harness to run is a test that does not run. These do.

Every bound assertion is made in BOTH directions. The zero-bound family of
defects survived six weeks precisely because only one side was ever asserted.
"""

import unittest

from amb_w_tds.amb_w_tds.coa_spec_utils import (
    PASS, FAIL, UNEVALUATED,
    derive_bounds_from_spec, effective_bound, effective_bounds,
    evaluate, parse_result_value,
)


class TestStoreZeroPredicate(unittest.TestCase):
    """A stored 0 means 'no bound', not 'the limit is zero'."""

    def test_zero_is_no_bound(self):
        self.assertIsNone(effective_bound(0))
        self.assertIsNone(effective_bound(0.0))
        self.assertIsNone(effective_bound("0"))

    def test_blank_is_no_bound(self):
        self.assertIsNone(effective_bound(None))
        self.assertIsNone(effective_bound(""))

    def test_real_bounds_survive(self):
        self.assertEqual(effective_bound(10), 10.0)
        self.assertEqual(effective_bound("10"), 10.0)
        self.assertEqual(effective_bound(0.5), 0.5)
        self.assertEqual(effective_bound(-3), -3.0)

    def test_non_numeric_is_no_bound_not_a_crash(self):
        self.assertIsNone(effective_bound("N/A"))
        self.assertIsNone(effective_bound("none"))

    def test_nlt_row_shape(self):
        """NLT 10 stores min=10, max=0."""
        self.assertEqual(effective_bounds(10, 0), (10.0, None))

    def test_nmt_row_shape(self):
        """NMT 100 stores min=0, max=100."""
        self.assertEqual(effective_bounds(0, 100), (None, 100.0))

    def test_two_sided_row_shape(self):
        self.assertEqual(effective_bounds(20, 25), (20.0, 25.0))

    def test_unbounded_row_shape(self):
        self.assertEqual(effective_bounds(0, 0), (None, None))


class TestParseResultValue(unittest.TestCase):

    def test_plain_and_suffixed(self):
        self.assertEqual(parse_result_value("23.5%"), 23.5)
        self.assertEqual(parse_result_value("<10 CFU/G"), 10.0)
        self.assertEqual(parse_result_value("50"), 50.0)
        self.assertEqual(parse_result_value(50), 50.0)

    def test_thousands_separator(self):
        self.assertEqual(parse_result_value("1,200 CFU"), 1200.0)

    def test_negative(self):
        self.assertEqual(parse_result_value("-3.2"), -3.2)

    def test_non_numeric_is_none(self):
        for v in ("NEGATIVE", "Pass", "TNTC", "", None):
            self.assertIsNone(parse_result_value(v), v)

    def test_bool_is_not_a_number(self):
        """True must not silently become 1.0."""
        self.assertIsNone(parse_result_value(True))


class TestDeriveBoundsFromSpec(unittest.TestCase):

    def test_ranges(self):
        self.assertEqual(derive_bounds_from_spec("20-25%"), (20.0, 25.0))
        self.assertEqual(derive_bounds_from_spec("3.5 – 5.0"), (3.5, 5.0))
        self.assertEqual(derive_bounds_from_spec("20 to 25"), (20.0, 25.0))

    def test_reversed_range_is_normalised(self):
        self.assertEqual(derive_bounds_from_spec("25 - 20"), (20.0, 25.0))

    def test_upper_bound_keywords(self):
        for spec in ("NMT 100", "NOT MORE THAN 100", "MAX 100", "≤ 100", "<= 100", "< 100"):
            self.assertEqual(derive_bounds_from_spec(spec), (None, 100.0), spec)

    def test_lower_bound_keywords(self):
        for spec in ("NLT 10", "NOT LESS THAN 10", "MIN 10", "≥ 10", ">= 10", "> 10"):
            self.assertEqual(derive_bounds_from_spec(spec), (10.0, None), spec)

    def test_tolerance(self):
        self.assertEqual(derive_bounds_from_spec("100 ± 5"), (95.0, 105.0))
        self.assertEqual(derive_bounds_from_spec("100 +/- 5"), (95.0, 105.0))

    def test_keyword_beats_range_reading(self):
        """'NMT 20-25' must not be read as the range 20..25."""
        self.assertEqual(derive_bounds_from_spec("NMT 20-25"), (None, 20.0))

    def test_ambiguous_angle_brackets_are_not_a_bound(self):
        """Shipped behaviour preserved: '<' only counts when '>' is absent."""
        self.assertIsNone(derive_bounds_from_spec("value <x> 5"))

    def test_exact_number(self):
        self.assertEqual(derive_bounds_from_spec("7"), (7.0, 7.0))
        self.assertEqual(derive_bounds_from_spec("7.5%"), (7.5, 7.5))

    def test_text_specs_have_no_bounds(self):
        for spec in ("NEGATIVE", "Clear amber liquid", "Characteristic", "", None):
            self.assertIsNone(derive_bounds_from_spec(spec), spec)


class TestZeroBoundRegression(unittest.TestCase):
    """The defect this whole lane exists for. Both directions, every time."""

    def test_nlt_passing_result(self):
        """NLT 10 (min=10, max=0), result 12 -> Pass. This is the bug."""
        v = evaluate("NLT 10%", "12", min_value=10, max_value=0)
        self.assertEqual(v.status, PASS, v.detail)

    def test_nlt_failing_result(self):
        """Guard-rail: the real bound must still bite."""
        v = evaluate("NLT 10%", "8", min_value=10, max_value=0)
        self.assertEqual(v.status, FAIL, v.detail)

    def test_nmt_passing_result(self):
        v = evaluate("NMT 100 CFU/G", "50", min_value=0, max_value=100)
        self.assertEqual(v.status, PASS, v.detail)

    def test_nmt_failing_result(self):
        v = evaluate("NMT 100 CFU/G", "150", min_value=0, max_value=100)
        self.assertEqual(v.status, FAIL, v.detail)

    def test_two_sided_bounds_both_directions(self):
        self.assertEqual(evaluate("20-25%", "22", 20, 25).status, PASS)
        self.assertEqual(evaluate("20-25%", "19", 20, 25).status, FAIL)
        self.assertEqual(evaluate("20-25%", "26", 20, 25).status, FAIL)

    def test_boundary_values_are_inclusive(self):
        self.assertEqual(evaluate("20-25%", "20", 20, 25).status, PASS)
        self.assertEqual(evaluate("20-25%", "25", 20, 25).status, PASS)

    def test_less_than_notation_result(self):
        """'<10 CFU/G' against NMT 100 -> 10.0 -> Pass."""
        v = evaluate("NMT 100 CFU/G", "<10 CFU/G", min_value=0, max_value=100)
        self.assertEqual(v.status, PASS, v.detail)

    def test_rule_is_recorded(self):
        self.assertEqual(evaluate("NLT 10", "12", 10, 0).rule, "stored-bounds")
        self.assertEqual(evaluate("NLT 10", "12").rule, "spec-bounds")


class TestNeverFailsOpen(unittest.TestCase):
    """No path may return Pass because nothing matched."""

    def test_no_bounds_no_spec(self):
        v = evaluate(None, "whatever")
        self.assertEqual(v.status, UNEVALUATED, v.detail)
        self.assertFalse(v.is_pass)

    def test_unparseable_spec_and_no_bounds(self):
        v = evaluate("Characteristic odour", "Strong")
        self.assertEqual(v.status, UNEVALUATED, v.detail)

    def test_both_bounds_zero_is_unbounded_not_pass(self):
        v = evaluate("", "999999", min_value=0, max_value=0)
        self.assertEqual(v.status, UNEVALUATED, v.detail)

    def test_numeric_bounds_with_text_result(self):
        """Bounds are set but the result has no number: unanswerable, not Pass."""
        v = evaluate("NMT 100", "TNTC", min_value=0, max_value=100)
        self.assertEqual(v.status, UNEVALUATED, v.detail)

    def test_no_result(self):
        for r in (None, "", "   "):
            self.assertEqual(evaluate("NMT 100", r, 0, 100).status, UNEVALUATED)

    def test_alarming_results_do_not_pass(self):
        """TNTC / PRESENT / CONTAMINATED must never come back Pass."""
        for r in ("TNTC", "PRESENT", "CONTAMINATED"):
            self.assertNotEqual(evaluate("Characteristic", r).status, PASS, r)

    def test_unevaluated_is_not_a_pass(self):
        self.assertFalse(evaluate(None, "x").is_pass)


class TestInvertedResults(unittest.TestCase):
    """Substring matching is how an inverted result sneaks through."""

    def test_not_negative_fails_a_negative_spec(self):
        v = evaluate("NEGATIVE", "NOT NEGATIVE")
        self.assertEqual(v.status, FAIL, v.detail)

    def test_negative_passes_a_negative_spec(self):
        self.assertEqual(evaluate("NEGATIVE", "NEGATIVE").status, PASS)

    def test_absent_spec_both_directions(self):
        self.assertEqual(evaluate("ABSENT", "ABSENT").status, PASS)
        self.assertEqual(evaluate("ABSENT", "PRESENT").status, FAIL)

    def test_did_not_pass_is_not_a_pass(self):
        v = evaluate("PASS", "FAIL - DID NOT PASS")
        self.assertEqual(v.status, FAIL, v.detail)

    def test_explicit_reject_tokens_fail(self):
        for r in ("FAIL", "REJECTED", "OUT OF SPEC", "RECHAZADO", "NON CONFORME"):
            self.assertEqual(evaluate("Characteristic", r).status, FAIL, r)

    def test_decorated_rejections_fail(self):
        """A rejection is usually annotated; it is still a rejection."""
        for r in ("FAIL - DID NOT PASS", "REJECTED (see note 3)", "OUT OF SPEC by 4%"):
            self.assertEqual(evaluate("Characteristic", r).status, FAIL, r)

    def test_reject_prefix_does_not_overreach(self):
        """Only a whole token at the START counts — no substring matching."""
        v = evaluate("Characteristic", "NO FAILURE DETECTED")
        self.assertNotEqual(v.status, FAIL, v.detail)

    def test_negated_rejection_is_not_a_rejection(self):
        v = evaluate("Characteristic", "NOT REJECTED")
        self.assertNotEqual(v.status, FAIL, v.detail)

    def test_reject_token_outranks_numeric_bounds(self):
        v = evaluate("NMT 100", "REJECTED", min_value=0, max_value=100)
        self.assertEqual(v.status, FAIL, v.detail)

    def test_exact_text_match_passes(self):
        self.assertEqual(evaluate("Clear liquid", "clear liquid").status, PASS)


class TestSpecTextPathWhenNoStoredBounds(unittest.TestCase):
    """With bounds unset, the harvested parser carries the decision."""

    def test_spec_bounds_used(self):
        self.assertEqual(evaluate("NMT 100", "50").status, PASS)
        self.assertEqual(evaluate("NMT 100", "150").status, FAIL)
        self.assertEqual(evaluate("NLT 10", "12").status, PASS)
        self.assertEqual(evaluate("NLT 10", "8").status, FAIL)

    def test_tolerance_spec(self):
        self.assertEqual(evaluate("100 +/- 5", "97").status, PASS)
        self.assertEqual(evaluate("100 +/- 5", "94").status, FAIL)

    def test_stored_bounds_take_priority_over_spec(self):
        """500c1579 semantics: stored bounds win when both are present."""
        v = evaluate("NMT 100", "150", min_value=0, max_value=200)
        self.assertEqual(v.status, PASS, v.detail)
        self.assertEqual(v.rule, "stored-bounds")


if __name__ == "__main__":
    unittest.main(verbosity=2)
