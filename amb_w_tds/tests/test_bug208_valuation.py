"""BUG208 acceptance — the ONE valuation contract (Hugh's V-1/V-2/V-3).

Frappe-free: the whole money path lives in `amb_w_tds.valuation`, so these run
on a second interpreter with no bench. The RENDER layer is guarded separately in
`test_bug208_render_precision.py`, and that separation is deliberate — the
defect that survived two verifier passes lived exactly in the gap between them.

⭐ Every assertion here concerns a DECLARED CUSTOMS FIGURE.
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from amb_w_tds.valuation import (  # noqa: E402
    bag_count,
    lines_for,
    money,
    residual,
    to_decimal,
    total_bags,
    total_for,
    unit_for,
)


def rows(*counts):
    return [{"samples_count": c} for c in counts]


class TestTotalIsThePinnedScalar(unittest.TestCase):
    """V-1 — the total IS the stored scalar and does NOT scale with anything."""

    def test_total_equals_the_scalar(self):
        self.assertEqual(total_for("1.00", rows(3)), Decimal("1.00"))

    def test_total_is_independent_of_bag_count(self):
        """The defect V-1 removes: adding a sample used to change what the
        shipment declared to customs."""
        for r in (rows(1), rows(8), rows(5, 3), rows(14), []):
            self.assertEqual(total_for("1.00", r), Decimal("1.00"), r)

    def test_total_is_independent_of_row_count(self):
        self.assertEqual(total_for("2.50", rows(1, 1, 1, 1)), Decimal("2.50"))

    def test_the_old_multiplier_is_gone(self):
        """8 bags at a $1.00 total is $1.00, NOT the $8.00 the mode model gave."""
        self.assertEqual(total_for("1.00", rows(8)), Decimal("1.00"))
        self.assertNotEqual(total_for("1.00", rows(8)), Decimal("8.00"))

    def test_a_zero_total_stays_zero(self):
        """T-BUG208-6's arithmetic half: a deliberate zero declares nothing,
        and cannot be multiplied up into a declaration."""
        self.assertEqual(total_for(0, rows(8)), Decimal("0.00"))


class TestDerivedUnit(unittest.TestCase):
    """V-1/V-2 — the per-bag unit is DERIVED as total / Σbags, at 4dp."""

    def test_unit_divides_the_total_across_bags(self):
        self.assertEqual(unit_for("1.00", rows(4)), Decimal("0.2500"))

    def test_unit_of_a_repeating_fraction_is_four_decimals(self):
        self.assertEqual(unit_for("1.00", rows(3)), Decimal("0.3333"))

    def test_unit_spans_rows_not_just_one(self):
        """Σbags is the whole shipment: 5 + 3 bags of $8.00 -> $1.00 each."""
        self.assertEqual(unit_for("8.00", rows(5, 3)), Decimal("1.0000"))

    def test_no_bags_means_no_unit_rather_than_a_fabricated_one(self):
        self.assertIsNone(unit_for("1.00", []))
        self.assertIsNone(unit_for("1.00", rows(0)))

    def test_zero_bags_does_not_raise(self):
        """A print must not die on a shipment with no rows."""
        self.assertEqual(total_for("1.00", rows(0)), Decimal("1.00"))


class TestTotalAnchoredFooting(unittest.TestCase):
    """V-2 — the TOTAL wins the residual; footing is total-anchored."""

    def test_the_classic_third_case_totals_exactly_one_dollar(self):
        self.assertEqual(total_for("1.00", rows(3)), Decimal("1.00"))
        self.assertEqual(unit_for("1.00", rows(3)), Decimal("0.3333"))

    def test_residual_is_a_crumb_not_a_cent_for_awkward_divisors(self):
        """The residual is exposed so this is measured, not asserted in prose."""
        for n in (3, 6, 7, 9, 11, 13):
            r = residual("1.00", rows(n))
            self.assertLessEqual(abs(r), Decimal("0.01"), f"{n} bags left {r}")

    def test_multi_row_subtotals_sum_back_to_the_total_when_they_divide(self):
        lines = lines_for("8.00", rows(5, 3))
        summed = sum(money(ln["subtotal"]) for ln in lines)
        self.assertEqual(summed, Decimal("8.00"))
        self.assertEqual(residual("8.00", rows(5, 3)), Decimal("0.00"))

    def test_the_visible_one_cent_case_is_pinned_because_the_total_wins(self):
        """⛔ THE CASE A READER CAN SEE. $1.00 over 5+3 bags gives a unit of
        $0.125, so the rounded subtotals print $0.63 and $0.38 and SUM TO $1.01
        against a declared $1.00.

        This is V-2 working as ruled — footing is total-anchored, the total is
        the pinned scalar, and the cent is absorbed there rather than being
        distributed into a line. It is pinned here so that (a) nobody 'fixes'
        it by letting the total drift to the sum, which would re-break V-1, and
        (b) it is on the record that a reader adding the subtotal column can
        land one cent above the declared total.
        """
        lines = lines_for("1.00", rows(5, 3))
        self.assertEqual([ln["unit"] for ln in lines], [Decimal("0.1250")] * 2)
        self.assertEqual([money(ln["subtotal"]) for ln in lines],
                         [Decimal("0.63"), Decimal("0.38")])
        self.assertEqual(sum(money(ln["subtotal"]) for ln in lines), Decimal("1.01"))
        self.assertEqual(total_for("1.00", rows(5, 3)), Decimal("1.00"))  # ⭐ total wins
        self.assertEqual(residual("1.00", rows(5, 3)), Decimal("-0.01"))

    def test_money_never_travels_through_binary_float(self):
        self.assertEqual(to_decimal(0.1) + to_decimal(0.2), Decimal("0.3"))
        self.assertNotEqual(Decimal(0.1) + Decimal(0.2), Decimal("0.3"))


class TestNoModeModelSurvives(unittest.TestCase):
    """V-3 — ONE contract. Guards against the A/B/C model creeping back."""

    def test_valuation_module_exposes_no_mode_api(self):
        import amb_w_tds.valuation as v
        for gone in ("MODE_FLAT", "MODE_PER_ROW", "MODE_PER_SAMPLE",
                     "VALID_MODES", "default_mode_for", "normalize_mode", "line_for"):
            self.assertFalse(hasattr(v, gone), f"{gone} survived the V-3 drop")

    def test_total_for_ignores_rows_entirely(self):
        """`rows` is accepted and ignored so no caller can smuggle a multiplier
        back in by passing them."""
        self.assertEqual(total_for("1.00"), total_for("1.00", rows(99)))

    def test_the_controller_no_longer_derives_a_mode(self):
        path = os.path.join(os.path.dirname(__file__), "..", "amb_w_tds",
                            "doctype", "sample_request_amb", "sample_request_amb.py")
        src = open(os.path.abspath(path), encoding="utf-8").read()
        self.assertNotIn("set_valuation_mode", src)
        self.assertNotIn("custom_valuation_mode", src)


class TestZeroBagWarning(unittest.TestCase):
    """The zero-bag case Hugh asked to be warned about, at the arithmetic layer.

    ⭐ THE DEFECT DID NOT LEAVE, IT RELOCATED. Under the old multiply model a
    zero-bag Venta declared $0.00 (a value defect). Under V-1 the total is the
    pinned scalar, so the value is right — but the unit became a DIVISION, and
    the same two documents are still the special ones. Same witnesses, new
    layer: the guard now belongs on the unit RENDER, not on the value.

    The warning itself fires in the controller (`_warn_if_no_bags`, before_save)
    and is exercised live; what is pinned here is the property it warns about.
    """

    def test_zero_bags_produces_no_unit_rather_than_dividing(self):
        for r in ([], rows(0), rows(0, 0), [{"samples_count": None}]):
            self.assertIsNone(unit_for("1.00", r), r)

    def test_zero_bags_still_declares_the_scalar_total(self):
        """The warning exists because this is SILENT, not because it is wrong:
        the document correctly declares its value with no breakdown."""
        self.assertEqual(total_for("1.00", rows(0)), Decimal("1.00"))
        self.assertEqual(total_for("1.00", []), Decimal("1.00"))

    def test_a_zero_bag_row_beside_a_counted_row_is_not_the_zero_case(self):
        """The discriminating case: the SHIPMENT has bags, so no warning is due
        and the unit must still derive."""
        self.assertEqual(total_bags(rows(0, 5)), 5)
        self.assertEqual(unit_for("1.00", rows(0, 5)), Decimal("0.2000"))

    def test_subtotal_of_a_zero_bag_row_is_zero_not_none_when_a_unit_exists(self):
        lines = lines_for("1.00", rows(0, 5))
        self.assertEqual(lines[0]["subtotal"], Decimal("0.0000"))


class TestBagCounting(unittest.TestCase):

    def test_bag_count_floors_at_zero_and_survives_junk(self):
        for bad, expected in ((None, 0), ("", 0), ("abc", 0), (-4, 0), ("3", 3), (3, 3)):
            self.assertEqual(bag_count({"samples_count": bad}), expected, bad)

    def test_total_bags_sums_the_shipment(self):
        self.assertEqual(total_bags(rows(5, 3, 0)), 8)

    def test_lines_carry_one_entry_per_row_even_when_empty(self):
        self.assertEqual(len(lines_for("1.00", rows(1, 0, 2))), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
