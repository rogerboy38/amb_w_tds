"""13.12.13 (TASKS-298): the Propuestas report reads a COA row the way the BOM Formula reader does, and the reader's
QIP fallback compares names case-sensitively.

(1) `propuestas._coa_values` filtered `specification in (...)`, returned `{specification: ...}` and read `value` before
    `result`. On real COA AMB2 rows `specification` holds the acceptance text and `value` too, so the report showed the
    acceptance text of the limit as the lot's value, or nothing. It now keys through the reader's `_row_key`
    (`parameter_name` first, `specification` only when it names a parameter) and reads the cell the way the reader's
    `raw` does: `result` first, else `value`.
(2) `_row_key`'s fallback asked `frappe.db.exists("Quality Inspection Parameter", spec)`, which MariaDB's collation
    answers case-insensitively (literal `NONE` found the parameter `None`) and returns the STORED name; the fallback now
    takes the spec only when the stored name equals it exactly.
DB-free: `frappe.get_all` and `frappe.db` are mocked, as in test_13_12_11.
"""

import os
import re
import unittest
from unittest import mock

import frappe

from amb_w_tds.amb_w_tds.doctype.bom_formula import bom_formula as reader
from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import _row_key
from amb_w_tds.formulation import propuestas

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QIPS = {"Moisture", "pH", "Ash", "None", "Arsenic"}      # stored names (note: "None", not "NONE")


def fake_exists(calls=None):
    """MariaDB utf8mb4_unicode_ci: a case-insensitive match, answered with the STORED name (None when absent)."""
    def exists(dt, name=None, *a, **k):
        if calls is not None:
            calls.append(name)
        return next((q for q in QIPS if q.lower() == str(name).lower()), None)
    return exists


def row(parameter_name=None, specification=None, result=None, value=None, min_value=None, max_value=None):
    return frappe._dict(parameter_name=parameter_name, specification=specification, result=result,
                        value=value, min_value=min_value, max_value=max_value)


def coa_values(rows, specs, calls=None):
    seen = {}

    def get_all(dt, filters=None, fields=None, **k):
        seen.update(dt=dt, filters=filters, fields=fields, order_by=k.get("order_by"))
        return rows

    with mock.patch("frappe.get_all", get_all), mock.patch("frappe.db", mock.Mock(exists=fake_exists(calls))):
        out = propuestas._coa_values("COA AMB2", "COA2-1", set(specs))
    return out, seen


# the prod shape: the name in parameter_name, the acceptance text in specification AND in value, the measurement in result
PROD = [
    row("Moisture", "NMT 8%", result="5.6", value="NMT 8%", max_value=8),
    row("pH", "3.5 - 5.0", result="4.25", value="3.5 - 5.0", min_value=3.5, max_value=5.0),
    row("Ash", "NMT 40%", result="ND", value="NMT 40%", max_value=40),
]


class TestPropuestasCoaValues(unittest.TestCase):
    def test_prod_shape_rows_resolve_by_parameter_name_and_show_the_result(self):
        out, _ = coa_values(PROD, {"Moisture", "pH", "Ash"})
        self.assertEqual(out, {"Moisture": "5.6", "pH": "4.25", "Ash": "ND"})

    def test_the_acceptance_text_is_never_the_lots_value(self):
        out, _ = coa_values(PROD, {"Moisture", "pH"})
        self.assertNotIn("NMT 8%", out.values())
        self.assertNotIn("3.5 - 5.0", out.values())

    def test_old_shape_blank_parameter_name_resolves_by_specification(self):
        out, _ = coa_values([row(None, "Moisture", result="5.6"), row("", "pH", result="4.25")], {"Moisture", "pH"})
        self.assertEqual(out, {"Moisture": "5.6", "pH": "4.25"})

    def test_result_wins_over_value_and_value_is_the_fallback(self):
        # the precedence of the reader's `raw`: result if not empty, else value
        out, _ = coa_values([row("Moisture", "x", result="5.6", value="9"), row("pH", "x", result="", value="4.1"),
                             row("Ash", "x", result=None, value=None)], {"Moisture", "pH", "Ash"})
        self.assertEqual(out, {"Moisture": "5.6", "pH": "4.1", "Ash": None})

    def test_a_zero_in_result_is_a_result_not_an_empty_cell(self):
        out, _ = coa_values([row("Moisture", "x", result="0", value="8")], {"Moisture"})
        self.assertEqual(out, {"Moisture": "0"})

    def test_acceptance_text_equal_to_another_wanted_name_does_not_hijack(self):
        rows = [row("Ash", "pH", result="12"), row("pH", "3.5 - 5.0", result="4.25")]
        for order in (rows, list(reversed(rows))):
            out, _ = coa_values(order, {"pH", "Ash"})
            self.assertEqual(out, {"pH": "4.25", "Ash": "12"})

    def test_blank_parameter_name_with_acceptance_text_is_unkeyed(self):
        out, _ = coa_values([row(None, "NMT 8%", result="5.6")], {"Moisture"})
        self.assertEqual(out, {})

    def test_the_first_row_of_a_parameter_wins_as_before(self):
        out, _ = coa_values([row("Moisture", "a", result="5.6"), row("Moisture", "b", result="7.7")], {"Moisture"})
        self.assertEqual(out, {"Moisture": "5.6"})

    def test_only_the_wanted_parameters_are_returned_and_empty_input_is_empty(self):
        out, _ = coa_values(PROD, {"pH"})
        self.assertEqual(out, {"pH": "4.25"})
        with mock.patch("frappe.get_all", side_effect=AssertionError("no query for empty input")):
            self.assertEqual(propuestas._coa_values("COA AMB2", "C", set()), {})
            self.assertEqual(propuestas._coa_values("COA AMB2", "", {"pH"}), {})
            self.assertEqual(propuestas._coa_values(None, "C", {"pH"}), {})

    def test_the_query_fetches_parameter_name_and_is_not_filtered_by_specification(self):
        _, seen = coa_values(PROD, {"pH"})
        self.assertEqual(seen["filters"], {"parent": "COA2-1", "parenttype": "COA AMB2"})
        self.assertIn("parameter_name", seen["fields"])
        self.assertEqual(seen["order_by"], "idx asc")

    def test_one_source_of_truth_the_reader_functions_are_the_ones_used(self):
        # the key function and the float-strict number test are the reader's own objects, imported, not copied;
        # the reader keeps `_raw_text` for its own `raw` (TASKS-301: the report no longer uses it)
        self.assertIs(propuestas._row_key, reader._row_key)
        self.assertIs(propuestas._reader_num, reader._num)       # propuestas has its own unrelated `_num`; the helper uses the reader's
        self.assertTrue(hasattr(reader, "_raw_text"))
        self.assertFalse(hasattr(propuestas, "_raw_text"))

    def test_the_report_and_the_reader_agree_on_every_cell_that_has_a_result(self):
        rows = [row("Moisture", "NMT 8%", result="5.6", value="NMT 8%"), row("pH", "x", result="4.1", value="3.5 - 5.0")]
        out, _ = coa_values(rows, {"Moisture", "pH"})
        for r in rows:
            self.assertEqual(out[r.parameter_name], reader._raw_text(r))


class TestReportCellBlankRule(unittest.TestCase):
    """TASKS-301 (Hugh, 2026-11-05): a lot's cell is `result` when non-empty; else `value` ONLY if it is a pure
    non-zero number (the reader's float-strict test); else EMPTY (None). The acceptance text is never the value."""

    def cell(self, **kw):
        out, _ = coa_values([row("Moisture", "Moisture", **kw)], {"Moisture"})
        return out["Moisture"]

    def test_result_set_and_value_acceptance_text_gives_result(self):
        self.assertEqual(self.cell(result="5.6", value="NMT 8%"), "5.6")

    def test_result_empty_and_value_a_limit_or_text_gives_none(self):
        for v in ("NMT 8%", "3.5 - 5.0", " 1.002 - 1.020", "FINE HOMOGENEOUS POWDER", "Specification", "NEGATIVE",
                  "99% THROUGH NO. 100 MESH", "NMT 100 CFU/ML", "<10"):
            self.assertIsNone(self.cell(result="", value=v), v)
            self.assertIsNone(self.cell(result=None, value=v), v)

    def test_result_empty_and_value_a_pure_number_gives_the_value(self):
        self.assertEqual(self.cell(result="", value="0.099"), "0.099")
        self.assertEqual(self.cell(result=None, value="12"), "12")
        self.assertEqual(self.cell(result="", value="-3.5"), "-3.5")

    def test_zero_in_value_is_unset_not_a_value(self):
        for v in ("0", "0.0", "0.000", " 0 "):
            self.assertIsNone(self.cell(result="", value=v), v)

    def test_a_zero_in_result_is_a_result(self):
        self.assertEqual(self.cell(result="0", value="8"), "0")
        self.assertEqual(self.cell(result="0.0", value=None), "0.0")

    def test_whitespace_only_result_or_value_is_empty(self):
        self.assertIsNone(self.cell(result="   ", value="  "))
        self.assertEqual(self.cell(result="  ", value="0.5"), "0.5")        # an empty result falls back to a pure number
        self.assertIsNone(self.cell(result="  ", value="NMT 8%"))
        self.assertIsNone(self.cell(result=None, value=None))

    def test_the_number_test_is_the_readers_so_a_value_the_reader_would_not_take_is_not_shown(self):
        for v in ("1,5", "5 %", "~3", "3 ppm"):
            self.assertIsNone(reader._num(v), v)                    # not a pure number for the reader ...
            self.assertIsNone(self.cell(result="", value=v), v)     # ... so not shown by the report

    def test_the_first_row_of_a_parameter_still_wins_even_when_its_cell_is_blank(self):
        rows = [row("Moisture", "x", result="", value="NMT 8%"), row("Moisture", "y", result="5.6")]
        out, _ = coa_values(rows, {"Moisture"})
        self.assertEqual(out, {"Moisture": None})

    def test_the_helper_is_only_used_by_the_read_only_report_path(self):
        import inspect
        src = inspect.getsource(propuestas)
        self.assertEqual(src.count("_report_cell("), 2)     # its definition and its one call in _coa_values


class TestQipFallbackIsCaseSensitive(unittest.TestCase):
    def key(self, r, kinds=None, cache=None):
        with mock.patch("frappe.db", mock.Mock(exists=fake_exists())):
            return _row_key(r, kinds or {}, {} if cache is None else cache)

    def test_a_spec_that_equals_a_parameter_only_by_case_is_not_taken(self):
        self.assertIsNone(self.key(row(None, "NONE")))
        self.assertIsNone(self.key(row(None, "none")))
        self.assertIsNone(self.key(row("", "PH")))
        self.assertIsNone(self.key(row(None, "moisture")))

    def test_an_exact_case_match_is_still_taken(self):
        self.assertEqual(self.key(row(None, "None")), "None")
        self.assertEqual(self.key(row(None, "pH")), "pH")
        self.assertEqual(self.key(row(None, "Moisture")), "Moisture")

    def test_parameter_name_still_wins_and_is_not_looked_up(self):
        calls = []
        with mock.patch("frappe.db", mock.Mock(exists=fake_exists(calls))):
            self.assertEqual(_row_key(row("pH", "NONE"), {}, {}), "pH")
        self.assertEqual(calls, [])

    def test_a_name_the_tds_defines_is_taken_without_a_lookup_even_in_another_case_of_the_tds_spelling(self):
        calls = []
        with mock.patch("frappe.db", mock.Mock(exists=fake_exists(calls))):
            self.assertEqual(_row_key(row(None, "Moisture"), {"Moisture": "numeric"}, {}), "Moisture")
        self.assertEqual(calls, [])

    def test_no_new_query_per_row_the_answer_is_cached(self):
        calls, cache = [], {}
        with mock.patch("frappe.db", mock.Mock(exists=fake_exists(calls))):
            for _ in range(5):
                _row_key(row(None, "NONE"), {}, cache)
                _row_key(row(None, "pH"), {}, cache)
        self.assertEqual(sorted(calls), ["NONE", "pH"])

    def test_the_reader_does_not_take_acceptance_text_equal_to_a_parameter_by_case(self):
        d = object.__new__(reader.BOMFormula)
        d.__dict__.update(doctype="BOM Formula", prediction_note="", mix_input_lines=[frappe._dict(
            cunete_ref="C-1", item_code="X", kg=100, batch_amb_sublot=None, source_coa_amb2="COA2-1",
            source_coa_doctype="COA AMB2")])
        rows = [row(None, "NONE", result="NONE"), row("pH", "3.5 - 5.0", result="4.25")]
        with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: rows), \
                mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None, exists=fake_exists())):
            lots, _, _ = d._build_lots([reader.engine.Parameter("pH", reader.engine.BlendMethod.PH_HPLUS,
                                                                 min_value=3.5, max_value=5.0)])
        self.assertEqual(lots[0].values, {"pH": 4.25})
        self.assertNotIn("NONE", d._raw_by_lot[0])
        self.assertNotIn("None", d._raw_by_lot[0])


class TestVersion(unittest.TestCase):
    def test_version_is_13_12_13_or_later(self):
        with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
            ver = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)
        with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
            self.assertEqual(f.read().strip(), ver)
        self.assertGreaterEqual(tuple(int(x) for x in ver.split(".")), (13, 12, 13))


if __name__ == "__main__":
    unittest.main()
