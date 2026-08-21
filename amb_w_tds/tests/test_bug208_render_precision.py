"""BUG208 V-2 — the guard on the RENDERED STRING, not the Decimal.

⭐⭐ WHY THIS FILE IS SEPARATE FROM THE ARITHMETIC TESTS.

Two independent verifier seats checked the per-bag unit, both found
`Decimal("0.3333")`, and both concluded the document was correct. It was not.
`fmt_money` defaults to the currency's precision, so the page printed:

    $ 0.33        and a reader computes 3 x 0.33 = 0.99
                  against a declared total of $ 1.00
                  ⇒ a FULL CENT of residue, visible on a customs document

The arithmetic was right the whole time and died one file later. So the money
path has an arithmetic guard (`test_bug208_valuation.py`) AND this one, and
this one is only allowed to assert **what a reader would see**. A test that
reaches for `unit_display()` here would re-open the exact gap.

⚠ Requires a bench (it calls `frappe.utils.fmt_money`); skips cleanly without
one, and the skip is loud rather than a silent pass.
"""

import unittest

try:
    import frappe
    from frappe.utils import fmt_money
    _HAVE_FRAPPE = True
except Exception:  # pragma: no cover - second interpreter has no bench
    _HAVE_FRAPPE = False

_CONNECTED = False


def setUpModule():
    """⚠ `fmt_money` needs a CONNECTED site to resolve the currency symbol.

    Unconnected it returns '1.00 USD' with no '$' — which would have made these
    tests assert a string the real document never shows. That is the same
    layer-confusion this file exists to catch, one level up: a guard on rendered
    output has to run where rendering actually happens.
    """
    global _CONNECTED
    if not _HAVE_FRAPPE:
        return
    try:
        frappe.init(site="v2.sysmayal.cloud", sites_path="/home/frappe/frappe-bench/sites")
        frappe.connect()
        _CONNECTED = True
    except Exception:
        _CONNECTED = False


def tearDownModule():
    if _CONNECTED:
        frappe.destroy()


@unittest.skipUnless(_HAVE_FRAPPE, "needs a bench: asserts frappe.utils.fmt_money output")
class TestRenderedPrecision(unittest.TestCase):

    def setUp(self):
        if not _CONNECTED:
            self.skipTest("frappe present but not connected — fmt_money would omit the currency symbol")

    def test_the_default_precision_is_what_caused_the_bug(self):
        """POSITIVE CONTROL, and the regression's own fingerprint. If this ever
        starts returning '$ 0.3333', fmt_money's defaults changed and the rest
        of this file needs re-reading rather than trusting."""
        self.assertEqual(fmt_money(0.3333, currency="USD"), "$ 0.33")

    def test_precision_4_prints_the_full_derived_unit(self):
        self.assertEqual(fmt_money(0.3333, currency="USD", precision=4), "$ 0.3333")

    def test_precision_4_self_trims_a_round_number(self):
        """The unit path must not pad $1.00 into '$ 1.0000'."""
        self.assertEqual(fmt_money(1.00, currency="USD", precision=4), "$ 1.00")

    def test_the_jinja_layer_emits_four_decimals_for_the_unit(self):
        from amb_w_tds.valuation_jinja import _fmt, UNIT_PRECISION
        self.assertEqual(UNIT_PRECISION, 4)
        self.assertEqual(_fmt(0.3333, "USD", precision=UNIT_PRECISION), "$ 0.3333 USD")

    def test_the_jinja_layer_keeps_money_at_two_decimals(self):
        from amb_w_tds.valuation_jinja import _fmt
        self.assertEqual(_fmt(1.00, "USD"), "$ 1.00 USD")
        self.assertEqual(_fmt(8.00, "USD"), "$ 8.00 USD")

    def test_the_reader_can_foot_the_line_from_what_is_printed(self):
        """The property in the reader's terms: parse the printed unit, multiply
        by the printed bag count, and land on the declared total."""
        from decimal import Decimal
        from amb_w_tds.valuation_jinja import _fmt, UNIT_PRECISION
        printed_unit = _fmt(Decimal("1.00") / 3, "USD", precision=UNIT_PRECISION)
        numeric = Decimal(printed_unit.replace("$", "").replace("USD", "").strip())
        self.assertEqual(numeric, Decimal("0.3333"))
        self.assertEqual(round(numeric * 3, 2), Decimal("1.00"))

    def test_an_unknown_currency_still_shows_four_decimals_and_no_duplicate_code(self):
        """fmt_money does NOT raise on an unknown currency — it prefixes the
        code instead of a symbol. The earlier version then appended the code a
        second time ("MXN 1.00 MXN")."""
        from amb_w_tds.valuation_jinja import _fmt
        out = _fmt(0.3333, "NOT_A_CURRENCY", precision=4)
        self.assertIn("0.3333", out)
        self.assertEqual(out.count("NOT_A_CURRENCY"), 1, out)

    def test_a_non_numeric_amount_degrades_instead_of_killing_the_print(self):
        """⛔ REGRESSION GUARD. The fallback used to call float(amount) inside
        BOTH the try and the except, so a non-numeric value raised twice and the
        exception escaped — a customs format would render a traceback where a
        value belongs. Measured before the fix: ValueError."""
        from amb_w_tds.valuation_jinja import _fmt
        for bad in ("abc", object(), [1, 2]):
            self.assertEqual(_fmt(bad, "USD"), "", repr(bad))

    def test_none_renders_as_empty_not_as_zero(self):
        """An absent value must not print as $0.00 — declaring zero and
        declaring nothing are different statements to customs."""
        from amb_w_tds.valuation_jinja import _fmt
        self.assertEqual(_fmt(None, "USD"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
