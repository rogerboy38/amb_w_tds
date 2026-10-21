import frappe
import unittest


class TestCOAAMB2NumericRaiser(unittest.TestCase):
    """COA AMB2 carries its own copy of validate_numeric_result with the same
    zero-bound defect as COA AMB. It had no test file at all before this one.

    Scope note: COA AMB2's raiser also coerces row.result with flt(), so every
    qualitative result arrives as 0.0 and is compared numerically. That was a
    SEPARATE defect, deferred by this file to "the follow-up commit"; that
    commit is the D1/D2/D3/D5 port, and the qualitative cases now live in
    TestCOAAMB2Scorer below.
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


class TestCOAAMB2Scorer(unittest.TestCase):
    """The SCORER — check_parameter_compliance / parse_specification_compliance.

    The classes above exercise the raiser (validate_numeric_result), which
    throws; this one exercises the scorer, which returns Pass/Fail and is what
    writes a row's status. The seven cases are the set the port is warranted by,
    and three of them are FAIL cases on purpose: a suite that only asserts new
    passes cannot tell this fix from `return True`, which is precisely the
    fail-quiet shape the port exists to remove (D2 dropped an
    `except: return True`).

    COA AMB is scored on the identical row in every case. That equality is the
    real assertion — the port's warrant is one evaluator with one semantics, so
    a case where AMB2 and AMB disagree is a defect regardless of which one
    matches the expected value.
    """

    @classmethod
    def setUpClass(cls):
        cls.amb2 = frappe.new_doc("COA AMB2")
        cls.amb = frappe.new_doc("COA AMB")

    def row(self, specification, result, min_value=0.0, max_value=0.0):
        # min/max both 0 means "no numeric bound", which sends the row down the
        # specification-text ladder (D2) instead of the numeric compare (D1).
        return frappe._dict(parameter_name="TEST", specification=specification,
                            result=result, min_value=min_value,
                            max_value=max_value, numeric=1,
                            formula_based_criteria=0, acceptance_formula=None)

    def assertScores(self, row, expected):
        got2 = self.amb2.check_parameter_compliance(row)
        got1 = self.amb.check_parameter_compliance(row)
        self.assertEqual(got2, expected,
                         f"COA AMB2 scored {got2}, expected {expected}")
        self.assertEqual(got2, got1,
                         f"COA AMB2 ({got2}) disagrees with COA AMB ({got1})")

    # --- numeric, zero-bound: both polarities of the same NLT spec ---
    def test_nlt_passing_value_scores_pass(self):
        # 'NLT 10%' stores min=10, max=0; 12 clears the floor.
        self.assertScores(self.row("NLT 10%", "12", 10.0, 0.0), True)

    def test_nlt_failing_value_scores_fail(self):
        # The other polarity: the floor must still bite, or the zero-bound fix
        # would have bought a Pass for everything.
        self.assertScores(self.row("NLT 10%", "8", 10.0, 0.0), False)

    def test_nmt_with_zero_min_scores_pass(self):
        self.assertScores(self.row("NMT 100 CFU/G", "50", 0.0, 100.0), True)

    # --- qualitative: never flt()'d to 0.0 and compared as a number ---
    def test_negative_spec_with_negative_result_scores_pass(self):
        self.assertScores(self.row("NEGATIVE", "NEGATIVE"), True)

    def test_negative_spec_with_a_count_scores_fail(self):
        # A real count against a NEGATIVE spec is a failure, not a parse miss.
        self.assertScores(self.row("NEGATIVE", "30 CFU/G"), False)

    def test_less_than_count_against_nmt_scores_pass(self):
        self.assertScores(self.row("NMT 100 CFU/G", "<10 CFU/G"), True)

    # --- descriptive: a reject token is a Fail, not an unscored shrug ---
    def test_descriptive_reject_token_scores_fail(self):
        self.assertScores(self.row("Caracteristico", "RECHAZADO"), False)
