"""13.12.8 (TASKS-282 Part A): on a COA AMB2, ND / "not analysed" / "not available" is N/A — never Fail.

Hugh's ruling (2026-11-03): a COA AMB2 on a pure-powder lot is the analytical INPUT of a formulation, not a
verdict against a TDS; a cell with no data is N/A. DB-free: the controller is driven on an in-memory
document (`object.__new__`), as the Cut-1 tests do, so no site and no database.
"""

import os
import unittest

import frappe

from amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2 import COAAMB2, _NA_TOKENS, _is_na, _num

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def row(name, result, spec="", mn=0.0, mx=0.0, numeric=1, title=0, idx=None):
    return frappe._dict(parameter_name=name, result=result, specification=spec, min_value=mn, max_value=mx,
                        numeric=numeric, custom_is_title_row=title, value=None, status="Pending",
                        formula_based_criteria=0, acceptance_formula=None, idx=idx)


def coa(rows):
    d = object.__new__(COAAMB2)
    d.__dict__.update(doctype="COA AMB2", coa_quality_test_parameter=rows, overall_result="Pending",
                      compliance_status="Pending", failed_parameters=None, pass_percentage=0, tested_percentage=0)
    return d


def score(rows):
    d = coa(rows)
    d.evaluate_overall_result()
    return d


class TestTokens(unittest.TestCase):
    def test_the_tokens_and_their_spellings(self):
        for t in ("ND", "nd", " N/D ", "N.D.", "n.d", "Not Detected", "NO DETECTADO", "not  detectable", "No Disponible",
                  "NOT AVAILABLE", "Not Analyzed", "not analysed", "NO ANALIZADO", "N/A", "n.a.", "NA", "-", "—"):
            self.assertTrue(_is_na(t), t)

    def test_below_limit_cells_without_a_number_are_na_282a(self):
        for t in ("<LOQ", "< LOQ", "<LOD", "<MDL", "<DL", "≤LOQ", "<= LOQ", "< loq.", "BLQ", "BDL", "Below LOQ", "BELOW LOD",
                  "BELOW DETECTION LIMIT", "BELOW QUANTIFICATION LIMIT", "<LOQ (0.5% ST)".split(" (")[0]):
            self.assertTrue(_is_na(t), t)

    def test_what_is_not_a_token(self):
        for t in ("", None, "<10", "<10 CFU/G", "< 10", "<0.021 PPM", "≤10", "<1 PPM", "NEGATIVE", "NONE", "PASS", "2.22", "ND 2", "NDA",
                  "NOT DETECTED 0.1", "FINE HOMOGENEOUS POWDER", "0", "LOQ", "BLQ 2"):
            self.assertFalse(_is_na(t), repr(t))
        self.assertIsNone(_num("<LOQ"))
        self.assertEqual(_num("<10 CFU/G"), 10.0)
        self.assertEqual(_num("<0.021 PPM"), 0.021)


class TestScoring(unittest.TestCase):
    def test_nd_against_nmt_range_and_negative_is_na_not_fail(self):
        d = score([row("Arsenic", "ND", "NMT 3 PPM", 0, 3), row("pH", "N/D", "3.5-5.0", 3.5, 5.0),
                   row("Coliforms", "NOT DETECTED", "NEGATIVE", 0, 0, numeric=0)])
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["N/A", "N/A", "N/A"])
        self.assertEqual((d.overall_result, d.compliance_status), ("Pending", "Pending"))   # nothing measured
        self.assertEqual((d.pass_percentage, d.tested_percentage), (0, 0))
        self.assertEqual(d._na_tests, ["Arsenic", "pH", "Coliforms"])

    def test_the_34_nd_pure_powder_pattern_fails_only_because_of_the_number(self):
        # five lots' worth of rows: ND at idx 19, 21, 24, 25, 27, 28 of each block, one measured number out of bound
        rows = []
        for lot in range(5):
            for idx in range(17, 30):
                if idx in (19, 21, 24, 25, 27, 28):
                    rows.append(row(f"P{idx}", "ND", "NMT 1 PPM", 0, 1, idx=idx))
                else:
                    rows.append(row(f"P{idx}", "0.5", "NMT 1 PPM", 0, 1, idx=idx))
        self.assertEqual(sum(1 for r in rows if r.result == "ND"), 30)
        rows += [row("X1", "ND", "NMT 1", 0, 1), row("X2", "ND", "NMT 1", 0, 1), row("X3", "ND", "NMT 1", 0, 1), row("X4", "ND", "NMT 1", 0, 1)]
        self.assertEqual(sum(1 for r in rows if r.result == "ND"), 34)
        d = score(list(rows))
        self.assertEqual((d.overall_result, d.compliance_status), ("Pass", "Compliant"))     # 34 N/A, 35 Pass
        self.assertEqual(len(d._na_tests), 34)
        self.assertEqual(d.pass_percentage, 100)
        # now one measured number outside its bound in another row
        rows2 = list(rows) + [row("Arsenic", "2.22", "NMT 2 PPM", 0, 2)]
        d = score(rows2)
        self.assertEqual((d.overall_result, d.compliance_status, d.failed_parameters), ("Fail", "Non-Compliant", "Arsenic"))
        self.assertEqual(len(d._na_tests), 34)

    def test_all_nd_plus_all_pass_is_pass(self):
        d = score([row("Moisture", "6.0", "NMT 8%", 0, 8), row("Arsenic", "ND", "NMT 3 PPM", 0, 3), row("Coliforms", "NEGATIVE", "NEGATIVE", 0, 0, numeric=0)])
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["Pass", "N/A", "Pass"])
        self.assertEqual((d.overall_result, d.compliance_status), ("Pass", "Compliant"))
        self.assertEqual((d.pass_percentage, d.tested_percentage), (100, 100))

    def test_blank_stays_pending_and_partial_under_review_ignores_na(self):
        d = score([row("Moisture", "6.0", "NMT 8%", 0, 8), row("Ash", "", "NMT 40%", 0, 40), row("Arsenic", "ND", "NMT 3 PPM", 0, 3)])
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["Pass", "Pending", "N/A"])
        self.assertEqual((d.overall_result, d.compliance_status), ("Partial", "Under Review"))
        self.assertEqual((d.pass_percentage, d.tested_percentage), (50, 50))               # over the 2 scorable rows

    def test_less_than_a_number_is_scored_as_today_and_below_limit_without_a_number_is_na(self):
        # 282a rewrote this test: before it asserted '<LOQ' -> Fail (as before 13.12.8); Hugh ruled it N/A.
        d = score([row("APC", "<10 CFU/G", "NMT 100 CFU/G", 0, 100), row("APC2", "< 10", "NMT 100", 0, 100),
                   row("Lead", "<0.021 PPM", "NMT 1 PPM", 0, 1), row("Hi", "<10", "NMT 5", 0, 5),
                   row("Aloin", "<LOQ", "NMT 0.1 PPM", 0, 0.1), row("Aloin B", "< LOQ", "0.01-0.1", 0.01, 0.1),
                   row("Cd", "<LOD", "NMT 1 PPM", 0, 1), row("Hg", "BLQ", "NMT 0.1", 0, 0.1)])
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["Pass", "Pass", "Pass", "Fail", "N/A", "N/A", "N/A", "N/A"])
        self.assertEqual((d.overall_result, d.failed_parameters), ("Fail", "Hi"))     # the number 10 vs NMT 5, nothing else
        self.assertEqual(d._na_tests, ["Aloin", "Aloin B", "Cd", "Hg"])

    def test_the_34_nd_pattern_plus_a_loq_row_still_passes(self):
        rows = [row(f"P{i}", "ND", "NMT 1 PPM", 0, 1) for i in range(34)] + [row(f"M{i}", "0.5", "NMT 1 PPM", 0, 1) for i in range(35)]
        rows.append(row("Aloin", "<LOQ", "NMT 0.1 PPM", 0, 0.1))
        d = score(rows)
        self.assertEqual((d.overall_result, d.compliance_status), ("Pass", "Compliant"))
        self.assertEqual(len(d._na_tests), 35)
        self.assertEqual(d.get_test_summary()["na"], 35)

    def test_a_qualitative_fail_still_fails(self):
        d = score([row("Coliforms", "PRESENT", "NEGATIVE", 0, 0, numeric=0), row("Arsenic", "ND", "NMT 3", 0, 3)])
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["Fail", "N/A"])
        self.assertEqual((d.overall_result, d.failed_parameters), ("Fail", "Coliforms"))

    def test_a_measured_number_out_of_bound_still_fails_and_title_rows_are_untouched(self):
        d = score([row("Specification", "", "Specification", title=1), row("Arsenic", "2.22", "NMT 2 PPM", 0, 2), row("pH", "ND", "3.5-5.0", 3.5, 5.0)])
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["Title", "Fail", "N/A"])
        self.assertEqual(d.overall_result, "Fail")

    def test_summary_counts_and_names_na_rows_and_total_excludes_them(self):
        d = score([row("Moisture", "6.0", "NMT 8%", 0, 8), row("Arsenic", "ND", "NMT 3", 0, 3), row("Ash", "", "NMT 40", 0, 40), row("Lead", "NO DISPONIBLE", "NMT 1", 0, 1)])
        s = d.get_test_summary()
        self.assertEqual({k: s[k] for k in ("total", "passed", "failed", "pending", "na", "na_parameters")},
                         {"total": 2, "passed": 1, "failed": 0, "pending": 1, "na": 2, "na_parameters": ["Arsenic", "Lead"]})
        self.assertEqual(s["pass_rate"], 50)

    def test_calculate_child_table_status_mirrors_the_rule(self):
        d = coa([row("Arsenic", "ND", "NMT 3", 0, 3), row("Ash", "", "NMT 40", 0, 40), row("Moisture", "9.5", "NMT 8", 0, 8)])
        d.calculate_child_table_status()
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["N/A", "Pending", "Fail"])


class TestGuardAndTwinUntouched(unittest.TestCase):
    def test_the_submit_guard_is_as_before(self):
        with open(os.path.join(PKG, "amb_w_tds", "doctype", "coa_amb2", "coa_amb2.py"), encoding="utf8") as f:
            src = f.read()
        self.assertIn("if row.numeric and row.result:", src)
        self.assertIn("is above maximum value", src)
        self.assertIn("if self.docstatus == 0 and not self._is_submit_flow():", src)

    def test_coa_amb_v1_has_no_na_token_rule(self):
        with open(os.path.join(PKG, "amb_w_tds", "doctype", "coa_amb", "coa_amb.py"), encoding="utf8") as f:
            src = f.read()
        self.assertNotIn("_NA_TOKENS", src)
        self.assertNotIn("_is_na", src)

    def test_version(self):
        with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
            self.assertIn('__version__ = "13.12.8"', f.read())
        with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
            self.assertEqual(f.read().strip(), "13.12.8")


if __name__ == "__main__":
    unittest.main()
