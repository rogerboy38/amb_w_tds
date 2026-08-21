"""BUG208 acceptance — T-BUG208-1..10, against the ruled model.

Deliberately frappe-free: `amb_w_tds.valuation` holds the whole money path, so
these run on a second interpreter with no bench. The Jinja/controller layers are
covered separately by the live checks in the seal letter.

⭐ Every assertion here is about a DECLARED CUSTOMS FIGURE. Where a test only
pins a display string, it says so, because "renders $X" and "declares $X" are
different claims and this ticket exists because they had drifted apart.
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from amb_w_tds.valuation import (  # noqa: E402
    MODE_FLAT,
    MODE_PER_ROW,
    MODE_PER_SAMPLE,
    default_mode_for,
    line_for,
    money,
    normalize_mode,
    to_decimal,
    total_for,
)


def rows(*counts):
    return [{"samples_count": c} for c in counts]


class TestModeArithmetic(unittest.TestCase):
    """T-BUG208-3 / -10 — each mode's total, and the contrast between them."""

    def test_mode_c_is_per_sample_hughs_own_document(self):
        # SR-2026-00015 carries commercial_value_usd = 0.20 with 5 samples.
        self.assertEqual(total_for(MODE_PER_SAMPLE, "0.20", rows(5)), Decimal("1.00"))

    def test_mode_c_multi_row_sums_bags_not_rows(self):
        # The per-ROW rule (the superseded one) would give 2 x 1.00 = 2.00 here.
        self.assertEqual(total_for(MODE_PER_SAMPLE, "1.00", rows(5, 3)), Decimal("8.00"))

    def test_mode_b_is_per_row_regardless_of_sample_count(self):
        self.assertEqual(total_for(MODE_PER_ROW, "1.00", rows(3)), Decimal("1.00"))
        self.assertEqual(total_for(MODE_PER_ROW, "1.00", rows(3, 7)), Decimal("2.00"))

    def test_mode_a_is_flat_whatever_the_rows(self):
        self.assertEqual(total_for(MODE_FLAT, "1.00", rows(5, 3, 99)), Decimal("1.00"))
        self.assertEqual(total_for(MODE_FLAT, "1.00", []), Decimal("1.00"))

    def test_t_bug208_10_modes_differ_on_the_same_row(self):
        """The mode selector is load-bearing: same field, 3x apart."""
        r = rows(3)
        self.assertEqual(total_for(MODE_PER_ROW, "1.00", r), Decimal("1.00"))
        self.assertEqual(total_for(MODE_PER_SAMPLE, "1.00", r), Decimal("3.00"))


class TestRoundingDoctrine(unittest.TestCase):
    """T-BUG208-9 — the fraction case, and the drift the doctrine forbids."""

    def test_mode_b_three_samples_totals_exactly_one_dollar(self):
        """1/3 x 3 must be exactly $1.00 — never 3 x $0.33 = $0.99."""
        self.assertEqual(total_for(MODE_PER_ROW, "1.00", rows(3)), Decimal("1.00"))

    def test_two_fraction_rows_total_exactly_two_dollars(self):
        self.assertEqual(total_for(MODE_PER_ROW, "1.00", rows(3, 3)), Decimal("2.00"))

    def test_the_derived_unit_displays_at_four_decimals(self):
        ln = line_for(MODE_PER_ROW, "1.00", {"samples_count": 3})
        self.assertEqual(ln["unit"], Decimal("0.3333"))
        self.assertEqual(ln["quantity"], 3)

    def test_mode_b_line_foots_at_the_printed_precision(self):
        """T-BUG208-9, as ruled 2026-08-21: round to 2dp, so the reader's
        multiplication reproduces the declared subtotal.

        Both halves are asserted on purpose. The RAW product is 0.9999 and is
        NOT the subtotal -- that is a fact about 1/3, not a defect, and pinning
        it stops the claim "the line foots" from being read as exact equality.
        What foots is the 2dp figure the money is actually declared in.
        """
        ln = line_for(MODE_PER_ROW, "1.00", {"samples_count": 3})
        self.assertEqual(ln["subtotal"], Decimal("1.00"))
        self.assertEqual(ln["unit"] * 3, Decimal("0.9999"))          # raw: not equal
        self.assertNotEqual(ln["unit"] * 3, ln["subtotal"])
        self.assertEqual(money(ln["unit"] * 3), money(ln["subtotal"]))  # ⭐ ruled: foots at 2dp
        self.assertEqual(money(ln["unit"] * 3), Decimal("1.00"))

    def test_footing_at_2dp_holds_for_other_awkward_divisors(self):
        """A control against pinning one lucky case: 7 and 6 also foot at 2dp."""
        for n in (3, 6, 7, 9, 11):
            ln = line_for(MODE_PER_ROW, "1.00", {"samples_count": n})
            self.assertEqual(money(ln["unit"] * n), money(ln["subtotal"]), n)

    def test_sum_of_rounded_lines_is_not_how_the_total_is_built(self):
        """A third of a cent, thirty times: rounding each line first loses money."""
        r = rows(*([3] * 30))
        self.assertEqual(total_for(MODE_PER_ROW, "1.00", r), Decimal("30.00"))

    def test_money_never_travels_through_binary_float(self):
        self.assertEqual(to_decimal(0.1) + to_decimal(0.2), Decimal("0.3"))
        self.assertNotEqual(Decimal(0.1) + Decimal(0.2), Decimal("0.3"))  # the trap


class TestZeroHandling(unittest.TestCase):
    """T-BUG208-6 — a deliberate zero is a declaration, not a missing value."""

    def test_zero_value_totals_zero_under_every_mode(self):
        for mode in (MODE_FLAT, MODE_PER_ROW, MODE_PER_SAMPLE):
            self.assertEqual(total_for(mode, 0, rows(8)), Decimal("0.00"), mode)

    def test_zero_is_not_multiplied_up_into_a_declaration(self):
        """The defect this replaces: 0 -> 1.00 at save, then x 8 bags = $8.00."""
        self.assertNotEqual(total_for(MODE_PER_SAMPLE, 0, rows(8)), Decimal("8.00"))

    def test_a_zero_sample_row_contributes_nothing_under_mode_c(self):
        self.assertEqual(total_for(MODE_PER_SAMPLE, "1.00", rows(0)), Decimal("0.00"))


class TestDerivedDefaultMode(unittest.TestCase):
    """A2 — the default derives from shipment_nature."""

    def test_venta_defaults_to_per_sample(self):
        self.assertEqual(default_mode_for("Venta"), MODE_PER_SAMPLE)

    def test_sin_valor_defaults_to_flat(self):
        self.assertEqual(default_mode_for("Muestra sin valor"), MODE_FLAT)

    def test_the_two_unruled_natures_take_flat_and_are_pinned_here(self):
        """"Regalo" / "Muestra mutilada" are NOT named by the ruling. They are
        inferred to A. Pinned so the inference is visible if it is ever wrong."""
        self.assertEqual(default_mode_for("Regalo"), MODE_FLAT)
        self.assertEqual(default_mode_for("Muestra mutilada"), MODE_FLAT)

    def test_a_stored_mode_always_wins_over_the_derived_default(self):
        self.assertEqual(normalize_mode("B", "Venta"), MODE_PER_ROW)

    def test_a_blank_or_bad_mode_falls_back_and_never_raises(self):
        self.assertEqual(normalize_mode("", "Venta"), MODE_PER_SAMPLE)
        self.assertEqual(normalize_mode(None, "Muestra sin valor"), MODE_FLAT)
        self.assertEqual(normalize_mode("Z", "Venta"), MODE_PER_SAMPLE)

    def test_mode_is_case_insensitive(self):
        self.assertEqual(normalize_mode("c", None), MODE_PER_SAMPLE)


class TestLineRendering(unittest.TestCase):
    """T-BUG208-3 — Mode C lines self-check; Mode A prints no per-line money."""

    def test_mode_c_line_self_checks_exactly(self):
        ln = line_for(MODE_PER_SAMPLE, "0.20", {"samples_count": 5})
        self.assertEqual(ln["quantity"], 5)
        self.assertEqual(ln["unit"], Decimal("0.2000"))
        self.assertEqual(ln["subtotal"], Decimal("1.00"))
        self.assertEqual(money(ln["unit"] * ln["quantity"]), money(ln["subtotal"]))

    def test_mode_a_carries_no_per_line_value(self):
        ln = line_for(MODE_FLAT, "1.00", {"samples_count": 5})
        self.assertIsNone(ln["unit"])
        self.assertIsNone(ln["subtotal"])

    def test_a_single_sample_mode_b_row_prints_the_row_value(self):
        ln = line_for(MODE_PER_ROW, "1.00", {"samples_count": 1})
        self.assertEqual(ln["quantity"], 1)
        self.assertEqual(ln["unit"], Decimal("1.0000"))
        self.assertEqual(ln["subtotal"], Decimal("1.00"))

    def test_missing_or_junk_sample_counts_do_not_crash_a_print(self):
        for bad in (None, "", "abc", -4):
            ln = line_for(MODE_PER_SAMPLE, "1.00", {"samples_count": bad})
            self.assertEqual(ln["subtotal"], Decimal("0"), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
