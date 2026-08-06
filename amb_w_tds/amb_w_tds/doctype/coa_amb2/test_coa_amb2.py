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

    # --- qualitative results must not be coerced to 0.0 and scored numerically ---
    def test_qualitative_negative_does_not_raise(self):
        # flt('NEGATIVE') == 0.0, so on the previous code this raised
        # "Result 0.0 is below minimum value 10".
        self.coa.validate_numeric_result(self.row("NEGATIVE", min_value=10, max_value=0), 1)

    def test_micro_less_than_does_not_raise(self):
        self.coa.validate_numeric_result(self.row("<10 CFU/G", min_value=0, max_value=100), 1)

    def test_percent_suffix_reads_the_number_not_zero(self):
        # flt('23.5%') == 0.0 -> would have raised against a min of 20.
        self.coa.validate_numeric_result(self.row("23.5%", min_value=20, max_value=25), 1)


class TestMinMaxConsistencyGate(unittest.TestCase):
    """validate_test_parameters' min/max consistency gate — the THIRD site of the
    same zero-bound defect, and the one with the widest blast radius: unlike
    validate_numeric_result it is NOT behind the `row.numeric` guard, so it fires
    on every row that has both bounds set.
    """

    @classmethod
    def setUpClass(cls):
        cls.coa = frappe.new_doc("COA AMB2")

    def rows(self, min_value, max_value):
        self.coa.set("coa_quality_test_parameter", [])
        self.coa.append("coa_quality_test_parameter", dict(
            parameter_name="TEST", specification="NLT 10%", result="12",
            numeric=0, min_value=min_value, max_value=max_value))
        self.coa.docstatus = 0
        return self.coa

    def test_nlt_row_max_zero_is_not_inconsistent(self):
        # min=10, max=0 (no upper bound) is a well-formed NLT row, not an inversion.
        # Previously threw "Minimum value (10) cannot be greater than maximum value (0)".
        self.rows(10, 0).validate_test_parameters()

    def test_genuine_inversion_still_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.rows(25, 20).validate_test_parameters()
