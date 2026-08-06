import frappe
import unittest


class TestCOAAMB2NumericRaiser(unittest.TestCase):
    """COA AMB2 carries its own copy of validate_numeric_result with the same
    zero-bound defect as COA AMB. It had no test file at all before this one.

    Scope note: COA AMB2's raiser also coerces row.result with flt(), so every
    qualitative result arrives as 0.0 and is compared numerically. That is a
    SEPARATE defect and is deliberately not asserted here — see the follow-up
    commit, which adds the qualitative cases once the coercion is fixed.
    """

    @classmethod
    def setUpClass(cls):
        cls.coa = frappe.new_doc("COA AMB2")

    def row(self, result, min_value=None, max_value=None):
        return frappe._dict(result=result, min_value=min_value,
                            max_value=max_value, parameter_name="TEST")

    # --- zero means 'no bound' ---
    def test_nlt_zero_max_does_not_raise(self):
        # 'NLT 10%' -> min=10, max=0 (no upper bound). Result 12 is compliant.
        # On the current pin this raises "Result 12.0 is above maximum value 0.0".
        self.coa.validate_numeric_result(self.row("12", min_value=10, max_value=0), 1)

    def test_both_bounds_zero_does_not_raise(self):
        self.coa.validate_numeric_result(self.row("10", min_value=0, max_value=0), 1)

    # --- real bounds still enforced ---
    def test_real_min_still_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.coa.validate_numeric_result(self.row("8", min_value=10, max_value=0), 1)

    def test_real_max_still_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.coa.validate_numeric_result(self.row("40", min_value=0, max_value=35), 1)

    def test_range_within_does_not_raise(self):
        self.coa.validate_numeric_result(self.row("19.76", min_value=0, max_value=35), 1)
