import frappe
import unittest


class TestCOACompliance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coa = frappe.new_doc("COA AMB")

    def chk(self, spec=None, result=None, min_value=None, max_value=None):
        return self.coa.check_parameter_compliance(frappe._dict(
            specification=spec, result=result,
            min_value=min_value, max_value=max_value, parameter_name="TEST"))

    # --- range with unit suffix: the live acemannan bug ---
    def test_range_percent_result_passes(self):
        self.assertTrue(self.chk("20 - 25%", "23.5%"))
    def test_range_plain_result_passes(self):
        self.assertTrue(self.chk("20 - 25%", "23.5"))
    def test_range_out_of_range_fails(self):
        self.assertFalse(self.chk("20 - 25%", "26%"))
    def test_ph_range_passes(self):
        self.assertTrue(self.chk("3.5 - 5.0", "4.54"))

    # --- NMT limits ---
    def test_nmt_within_passes(self):
        self.assertTrue(self.chk("NMT 8%", "4.75%"))
    def test_nmt_over_fails(self):
        self.assertFalse(self.chk("NMT 8%", "9.2%"))
    def test_nmt_ppm_passes(self):
        self.assertTrue(self.chk("NMT 0.1 PPM", "0.0114 PPM"))

    # --- microbiology <10 CFU/G: the other live bug ---
    def test_micro_less_than_passes(self):
        self.assertTrue(self.chk("NMT 100 CFU/G", "<10 CFU/G"))
    def test_micro_plain_passes(self):
        self.assertTrue(self.chk("NMT 100 CFU/G", "10 CFU/G"))

    # --- qualitative / negative ---
    def test_negative_passes(self):
        self.assertTrue(self.chk("NEGATIVE", "NEGATIVE"))
    def test_descriptive_match_passes(self):
        self.assertTrue(self.chk("FINE HOMOGENEOUS POWDER", "FINE HOMOGENEOUS POWDER"))
    def test_pass_token_passes(self):
        self.assertTrue(self.chk("TYPICAL OF ALOE", "Pass"))

    # --- explicit bounds honored; 0/0 treated as 'unset' ---
    def test_minmax_bounds_pass_and_fail(self):
        self.assertTrue(self.chk("20 - 25%", "23.5%", min_value=20, max_value=25))
        self.assertFalse(self.chk("20 - 25%", "30", min_value=20, max_value=25))
    def test_zero_bounds_fall_through_to_spec(self):
        self.assertTrue(self.chk("20 - 25%", "23.5%", min_value=0, max_value=0))

    def test_descriptive_placeholder_passes(self):
        # human-inspected descriptive param with a placeholder result -> Pass (not Fail)
        self.assertTrue(self.chk("HAZE FREE", "0"))
        self.assertTrue(self.chk("TYPICAL OF ALOE", "0"))

    def test_explicit_reject_fails(self):
        self.assertFalse(self.chk("CLEAR", "FAIL"))

    # --- NLT/NMT zero-as-no-bound (task #21 regression) ---
    def test_nlt_min_only_passes(self):
        # NLT 10%: min=10, max=0 (no upper bound). 12 must PASS (was the bug).
        self.assertTrue(self.chk("NLT 10%", "12", min_value=10, max_value=0))
    def test_nlt_min_only_below_fails(self):
        self.assertFalse(self.chk("NLT 10%", "8", min_value=10, max_value=0))
    def test_nmt_max_only_passes(self):
        self.assertTrue(self.chk("NMT 35%", "19.76", min_value=0, max_value=35))
    def test_nmt_max_only_over_fails(self):
        self.assertFalse(self.chk("NMT 35%", "40", min_value=0, max_value=35))
    def test_range_both_bounds_passes(self):
        self.assertTrue(self.chk("1.002-1.020", "1.0048", min_value=1.002, max_value=1.020))
    def test_qualitative_with_stray_bound_passes(self):
        # qualitative result + stray numeric bound must not hard-fail (COA-26-0002 E.coli)
        self.assertTrue(self.chk("E.coli", "NEGATIVE", min_value=0, max_value=1))


class TestCOANumericRaiser(unittest.TestCase):
    """validate_numeric_result — the RAISER, which blocks the save with frappe.throw.

    Distinct from check_parameter_compliance (the SCORER), which only returns a
    boolean and which task #21 / 300ef9a already fixed. Before this class, no test
    in the suite called the raiser at all, which is why the scorer could be fixed
    and the raiser left carrying the same defect for six weeks.
    """

    @classmethod
    def setUpClass(cls):
        cls.coa = frappe.new_doc("COA AMB")

    def row(self, result, min_value=None, max_value=None):
        return frappe._dict(result=result, min_value=min_value,
                            max_value=max_value, parameter_name="TEST")

    # --- the reported failure: NLT stores max=0 and the raiser read it as a real bound ---
    def test_nlt_zero_max_does_not_raise(self):
        # 'NLT 10%' -> min=10, max=0 (no upper bound). Result 12 is compliant.
        # On the current pin this raises "Result 12.0 is above maximum value 0.0".
        self.coa.validate_numeric_result(self.row("12", min_value=10, max_value=0), 1)

    def test_reported_case_result_10_max_0(self):
        # the message seen in prod, verbatim: "Result 10.0 is above maximum value 0.0"
        self.coa.validate_numeric_result(self.row("10", min_value=0, max_value=0), 1)

    # --- and the bounds that ARE set must still be enforced; the fix must not disarm it ---
    def test_real_min_still_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.coa.validate_numeric_result(self.row("8", min_value=10, max_value=0), 1)

    def test_real_max_still_raises(self):
        with self.assertRaises(frappe.ValidationError):
            self.coa.validate_numeric_result(self.row("40", min_value=0, max_value=35), 1)

    def test_range_within_does_not_raise(self):
        self.coa.validate_numeric_result(self.row("19.76", min_value=0, max_value=35), 1)

    # --- qualitative results must never reach the numeric comparison ---
    def test_qualitative_does_not_raise(self):
        self.coa.validate_numeric_result(self.row("NEGATIVE", min_value=10, max_value=0), 1)
        self.coa.validate_numeric_result(self.row("<10 CFU/G", min_value=0, max_value=100), 1)



class TestMinMaxConsistencyGate(unittest.TestCase):
    """validate_test_parameters' min/max consistency gate — the THIRD site of the
    same zero-bound defect, and the one with the widest blast radius: unlike
    validate_numeric_result it is NOT behind the `row.numeric` guard, so it fires
    on every row that has both bounds set.
    """

    @classmethod
    def setUpClass(cls):
        cls.coa = frappe.new_doc("COA AMB")

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
