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

