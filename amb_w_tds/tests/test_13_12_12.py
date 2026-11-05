"""13.12.12 (TASKS-291): a COA AMB2 draft refreshes its totals on every save, and an empty failure list clears
`failed_parameters`.

Two defects seen on prod after the 13.12.9 cut (neither caused by it):
 A. `validate()` returned early for a Draft (`docstatus == 0` and not a submit), BEFORE `evaluate_overall_result`, so a
    single-cell edit (the form saves the parent) left `pass_percentage`, `overall_result`, `failed_parameters` and the
    rows' `status` as the last "Validate All Tests" left them.
 B. `evaluate_overall_result` wrote `failed_parameters` only when something failed, so a re-score with 0 failures kept
    the old text.
DB-free: the controller is driven on an in-memory document, as test_13_12_8 does. The five documents are SYNTHETIC
fixtures with the row counts Hugh's anchors state (prod's own rows were not available to the sandbox).
"""

import os
import re
import unittest
from unittest import mock

import frappe

from amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2 import COAAMB2

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def row(name, result, spec="NMT 40%", mn=0.0, mx=40.0, status=None):
    return frappe._dict(parameter_name=name, result=result, specification=spec, min_value=mn, max_value=mx,
                        numeric=1, custom_is_title_row=0, value=None, status=status or "Pending",
                        formula_based_criteria=0, acceptance_formula=None)


def synthetic(npass, nfail, nna, prefix="P"):
    """Rows in the prod shape: parameter_name filled, acceptance text in `specification`, numeric bounds."""
    rows = [row(f"{prefix}-pass-{i}", "25.2") for i in range(npass)]
    rows += [row(f"{prefix}-fail-{i}", "61.0") for i in range(nfail)]
    rows += [row(f"{prefix}-na-{i}", "ND") for i in range(nna)]
    return rows


def coa(rows, **extra):
    d = object.__new__(COAAMB2)
    d.__dict__.update(doctype="COA AMB2", docstatus=0, coa_quality_test_parameter=rows, overall_result="Pending",
                      compliance_status="Pending", failed_parameters=None, pass_percentage=0, tested_percentage=0)
    d.__dict__.update(extra)
    return d


def save_draft(d):
    """What a Draft save runs: `validate()` (the controller hook), with the three light checks stubbed."""
    with mock.patch.object(COAAMB2, "validate_linked_tds", lambda s: None), \
            mock.patch.object(COAAMB2, "validate_batch_reference", lambda s: None), \
            mock.patch.object(COAAMB2, "check_mandatory_tds_link", lambda s: None):
        d.validate()
    return d


def button(d):
    """Validate All Tests: evaluate, then (the save is stubbed) the summary the dialog shows."""
    d.evaluate_overall_result()
    return d.get_test_summary()


# Hugh's anchors: (passed, failed, N/A, overall_result)
ANCHORS = {"COA2-26-0004": (29, 0, 6, "Pass"), "COA2-26-0005": (28, 0, 7, "Pass"), "COA2-26-0006": (26, 4, 5, "Fail"),
           "COA2-26-0007": (24, 3, 8, "Fail"), "COA2-26-0008": (24, 3, 8, "Fail")}


class TestAnchorsStayExactlyAsTheyAre(unittest.TestCase):
    def test_validate_all_tests_on_the_five_documents_gives_the_stated_counts(self):
        for name, (p, f, na, overall) in ANCHORS.items():
            d = coa(synthetic(p, f, na, name[-4:]))
            s = button(d)
            self.assertEqual((s["passed"], s["failed"], s["na"], s["pending"]), (p, f, na, 0), name)
            self.assertEqual(d.overall_result, overall, name)
            self.assertAlmostEqual(d.pass_percentage, p / (p + f) * 100, places=9, msg=name)

    def test_failed_parameters_names_exactly_the_failing_rows(self):
        d = coa(synthetic(26, 4, 5, "0006"))
        button(d)
        self.assertEqual(d.failed_parameters.split(", "), [f"0006-fail-{i}" for i in range(4)])


class TestDefectA_DraftSaveRefreshesTheTotals(unittest.TestCase):
    def test_a_single_cell_edit_on_0006_refreshes_the_parent_on_the_next_draft_save(self):
        d = coa(synthetic(26, 4, 5, "0006"))
        button(d)
        self.assertAlmostEqual(d.pass_percentage, 26 / 30 * 100, places=6)         # 86.67, the stale value of prod
        d.coa_quality_test_parameter[26].result = "25.2"                              # a failing row now in range
        save_draft(d)                                                                 # the form saves the parent
        self.assertAlmostEqual(d.pass_percentage, 90.0, places=9)                     # 27 pass / 3 fail
        self.assertEqual(d.failed_parameters.split(", "), ["0006-fail-1", "0006-fail-2", "0006-fail-3"])
        self.assertEqual(d.coa_quality_test_parameter[26].status, "Pass")
        self.assertEqual((d.overall_result, d.compliance_status), ("Fail", "Non-Compliant"))
        s = d.get_test_summary()
        self.assertEqual((s["passed"], s["failed"], s["na"]), (27, 3, 5))

    def test_a_single_cell_edit_on_0008_refreshes_88_89_to_92_59_and_names_two_not_three(self):
        d = coa(synthetic(24, 3, 8, "0008"))
        button(d)
        self.assertAlmostEqual(d.pass_percentage, 24 / 27 * 100, places=6)           # 88.89
        d.coa_quality_test_parameter[24].result = "25.2"
        save_draft(d)
        self.assertAlmostEqual(d.pass_percentage, 25 / 27 * 100, places=6)           # 92.59
        self.assertEqual(len(d.failed_parameters.split(", ")), 2)

    def test_the_last_failing_cell_fixed_flips_the_parent_to_pass_and_empties_the_list(self):
        d = coa(synthetic(29, 1, 6, "X"))
        button(d)
        self.assertEqual(d.overall_result, "Fail")
        d.coa_quality_test_parameter[29].result = "25.2"
        save_draft(d)
        self.assertEqual((d.overall_result, d.compliance_status, d.pass_percentage), ("Pass", "Compliant", 100.0))
        self.assertFalse(d.failed_parameters)

    def test_a_draft_save_does_not_change_the_scoring_of_a_row(self):
        # the 13.12.8 rules, through the draft path: ND and "<LOQ" = N/A, "<10" against NMT 500 passes
        rows = [row("a", "ND"), row("b", "<LOQ"), row("c", "<10 CFU/G", "NMT 500 CFU/G", 0, 500), row("d", "")]
        d = save_draft(coa(rows))
        self.assertEqual([r.status for r in d.coa_quality_test_parameter], ["N/A", "N/A", "Pass", "Pending"])

    def test_a_draft_with_no_rows_still_saves(self):
        d = save_draft(coa([]))
        self.assertEqual(d.overall_result, "No Tests")


class TestDefectB_AnEmptyFailureListIsWritten(unittest.TestCase):
    def test_zero_failures_clears_the_old_text_on_0004(self):
        d = coa(synthetic(29, 0, 6, "0004"), failed_parameters="Arsenic, Heavy Metals, Polysaccharides By Gpc",
                overall_result="Fail")
        d.evaluate_overall_result()
        self.assertEqual((d.overall_result, d.compliance_status, d.pass_percentage), ("Pass", "Compliant", 100.0))
        self.assertFalse(d.failed_parameters)

    def test_zero_failures_with_pending_or_all_na_also_clears_it(self):
        for rows in (synthetic(3, 0, 0) + [row("pending", "")], synthetic(0, 0, 4)):
            d = coa(rows, failed_parameters="stale")
            d.evaluate_overall_result()
            self.assertFalse(d.failed_parameters)

    def test_no_tests_clears_it_too(self):
        d = coa([], failed_parameters="stale")
        d.evaluate_overall_result()
        self.assertEqual(d.overall_result, "No Tests")
        self.assertFalse(d.failed_parameters)

    def test_failures_replace_the_text_not_append(self):
        d = coa(synthetic(2, 2, 0, "Z"), failed_parameters="old, older")
        d.evaluate_overall_result()
        self.assertEqual(d.failed_parameters, "Z-fail-0, Z-fail-1")


class TestSubmitPathUnchanged(unittest.TestCase):
    def test_a_submit_flow_validate_still_runs_the_full_sequence(self):
        d = coa(synthetic(2, 1, 0), docstatus=0, _action="submit")
        calls = []
        names = ("validate_linked_tds", "validate_batch_reference", "validate_test_parameters", "evaluate_overall_result",
                 "check_mandatory_tds_link", "validate_signature_on_submit", "evaluate_formula_parameters")
        patches = [mock.patch.object(COAAMB2, n, lambda s, _n=n: calls.append(_n)) for n in names]
        for p in patches:
            p.start()
        try:
            d.validate()
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(calls, list(names))

    def test_a_draft_runs_the_three_light_checks_then_the_evaluation_and_nothing_heavy(self):
        d = coa(synthetic(2, 1, 0))
        calls = []
        names = ("validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link", "evaluate_overall_result",
                 "validate_test_parameters", "validate_signature_on_submit", "evaluate_formula_parameters")
        patches = [mock.patch.object(COAAMB2, n, lambda s, _n=n: calls.append(_n)) for n in names]
        for p in patches:
            p.start()
        try:
            d.validate()
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(calls, ["validate_linked_tds", "validate_batch_reference", "check_mandatory_tds_link",
                                 "evaluate_overall_result"])


class TestVersion(unittest.TestCase):
    def test_version_is_13_12_12_or_later(self):
        with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
            ver = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)
        with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
            self.assertEqual(f.read().strip(), ver)
        self.assertGreaterEqual(tuple(int(x) for x in ver.split(".")), (13, 12, 12))


if __name__ == "__main__":
    unittest.main()
