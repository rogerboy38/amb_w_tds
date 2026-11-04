"""13.12.11 (TASKS-289): the BOM Formula reader files a COA row under `parameter_name`, not `specification`.

On real COA AMB2 documents `specification` holds the ACCEPTANCE text ('NMT 40%', '3.5 - 5.0', 'NONE') and
`parameter_name` the Quality Inspection Parameter; the 13.12.9 reader keyed on `specification`, so the measured
pH read NO DATA. DB-free: `frappe.get_all` and `frappe.db` are mocked, as test_13_12_7 does. The rows are
synthetic shapes, not real documents.
"""

import os
import re
import unittest
from unittest import mock

import frappe

from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula, _row_key
from amb_w_tds.formulation import engine
from amb_w_tds.formulation.engine import BlendMethod, Parameter, blend

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AS = Parameter("Arsenic", BlendMethod.MASS_AVG, max_value=3.0, uom="ppm", critical=True)
PH = Parameter("pH", BlendMethod.PH_HPLUS, min_value=3.5, max_value=5.0, critical=True)
COLI = Parameter("Coliforms", BlendMethod.ALL_PASS, numeric=False, critical=True)
PRES = Parameter("Preservatives", BlendMethod.ALL_PASS, numeric=False, critical=True)
APC = Parameter("Aerobic Plate Count", BlendMethod.WORST_CASE, max_value=500, uom="CFU/g", critical=True)
PARAMS = [AS, PH, COLI, PRES, APC]
QIPS = {"Arsenic", "pH", "Coliforms", "Preservatives", "Aerobic Plate Count", "NONE", "Aloin"}

LINE = dict(cunete_ref="C-1", item_code="IT-A", kg=100, batch_amb_sublot=None,
            source_coa_amb2="COA2-1", source_coa_doctype="COA AMB2")


def _row(parameter_name=None, specification=None, result=None, value=None, min_value=None, max_value=None):
    return frappe._dict(parameter_name=parameter_name, specification=specification, result=result,
                        value=value, min_value=min_value, max_value=max_value)


def _build(rows, params=PARAMS, qips=QIPS):
    d = object.__new__(BOMFormula)
    d.__dict__["doctype"] = "BOM Formula"
    d.__dict__["mix_input_lines"] = [frappe._dict(LINE)]
    d.__dict__["prediction_note"] = ""
    seen = {}

    def get_all(dt, filters=None, fields=None, **k):
        seen["fields"] = fields
        return rows

    with mock.patch("frappe.get_all", get_all), \
            mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None,
                                              exists=lambda dt, name=None, *a, **k: name in qips)):
        lots, total, with_coa = d._build_lots(params)
    return lots[0], d._raw_by_lot[0], seen["fields"]


# The shape of the three real submitted COA AMB2 documents' pH row (synthetic): result 4.25, acceptance text in
# `specification`, the name in `parameter_name`.
REAL_SHAPE = [
    _row("pH", "3.5 - 5.0", "4.25", "0", 3.5, 5.0),
    _row("Arsenic", "NMT 3 PPM", "1.96", "0", None, 3),
    _row("Coliforms", "NEGATIVE", "NEGATIVE"),
    _row("Aerobic Plate Count", "NMT 500 CFU/G", "<10 CFU/G", None, None, 500),
]


class TestRealCoaAmb2Shape(unittest.TestCase):
    def test_the_measured_ph_and_arsenic_are_read_from_the_row_named_by_parameter_name(self):
        lot, raw, _ = _build(REAL_SHAPE)
        self.assertEqual(lot.values["pH"], 4.25)
        self.assertEqual(lot.values["Arsenic"], 1.96)
        self.assertEqual(lot.values["Coliforms"], True)
        self.assertEqual(lot.values["Aerobic Plate Count"], 10)       # '<10' -> 10, as in 13.12.7

    def test_acceptance_text_is_never_a_key(self):
        lot, raw, _ = _build(REAL_SHAPE)
        for k in ("3.5 - 5.0", "NMT 3 PPM", "NEGATIVE", "NMT 500 CFU/G"):
            self.assertNotIn(k, lot.values)
            self.assertNotIn(k, raw)
            self.assertNotIn(k, lot.limits)

    def test_the_limits_are_filed_under_the_parameter(self):
        lot, _, _ = _build(REAL_SHAPE)
        self.assertEqual(lot.limits["pH"], (3.5, 5.0))
        self.assertEqual(lot.limits["Arsenic"], (None, 3.0))

    def test_the_query_fetches_parameter_name(self):
        _, _, fields = _build(REAL_SHAPE)
        self.assertIn("parameter_name", fields)
        self.assertTrue({"specification", "value", "result", "min_value", "max_value"} <= set(fields))

    def test_ph_4_25_and_coliforms_no_data_under_both_missing_data_policies(self):
        lines = [dict(LINE), dict(LINE, cunete_ref="C-2", source_coa_amb2="COA2-2")]
        rows = {"COA2-1": [_row("pH", "3.5 - 5.0", "4.25"), _row("Coliforms", "NEGATIVE", "NEGATIVE"),
                           _row("Arsenic", "NMT 3 PPM", "1.96")],
                "COA2-2": [_row("pH", "3.5 - 5.0", ""), _row("Coliforms", "NEGATIVE", ""),
                           _row("Arsenic", "NMT 3 PPM", "")]}
        for policy in (engine.MISSING_NO_DATA, engine.MISSING_TDS_LIMIT):
            d = object.__new__(BOMFormula)
            d.__dict__.update(doctype="BOM Formula", mix_input_lines=[frappe._dict(l) for l in lines],
                              prediction_note="", missing_data_policy=policy, total_input_kg=200, total_amount=0)
            appended = []
            with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: rows[filters["parent"]]), \
                    mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None,
                                                      exists=lambda dt, name=None, *a, **k: name in QIPS)), \
                    mock.patch.object(BOMFormula, "_build_parameters", lambda s: [AS, PH, COLI]), \
                    mock.patch.object(BOMFormula, "_recompute_mix_totals", lambda s: None), \
                    mock.patch.object(BOMFormula, "save", lambda s, **k: None), \
                    mock.patch.object(BOMFormula, "set", lambda s, k, v=None, *a, **kw: s.__dict__.__setitem__(k, v)), \
                    mock.patch.object(BOMFormula, "append", lambda s, k, row: appended.append(row)), \
                    mock.patch("frappe.msgprint", mock.Mock()):
                res = d.simulate_blend()
            by = {r["parameter"]: r for r in appended}
            self.assertEqual(by["pH"]["computed_value"], "4.25", policy)       # two-sided: never assumed at a limit
            self.assertEqual(by["Coliforms"]["computed_value"], "NO DATA", policy)   # qualitative: never assumed
            self.assertEqual(res["no_data"]["Coliforms"]["lots"], ["C-2"], policy)
            self.assertEqual(res["no_data"]["pH"]["lots"], ["C-2"], policy)
            self.assertEqual(res["missing_data_policy"], policy)
            self.assertIn("assumed_at_limit", res)
            self.assertEqual(by["Arsenic"]["computed_value"], "1.96" if policy == engine.MISSING_NO_DATA else by["Arsenic"]["computed_value"])

    def test_arsenic_1_96_blend_of_the_pair_1_7_and_2_22(self):
        a = _build([_row("Arsenic", "NMT 3 PPM", "1.7")])[0]
        b = _build([_row("Arsenic", "NMT 3 PPM", "2.22")])[0]
        a.mass_kg = b.mass_kg = 100
        self.assertAlmostEqual(blend([a, b], [AS])["Arsenic"].computed_value, 1.96, places=9)


class TestParameterNameWins(unittest.TestCase):
    def test_a_none_acceptance_row_is_filed_under_its_parameter_not_under_NONE(self):
        lot, raw, _ = _build([_row("Preservatives", "NONE", "NONE")])
        self.assertNotIn("NONE", lot.values)
        self.assertIn("Preservatives", lot.values)

    def test_acceptance_text_equal_to_another_qips_name_does_not_hijack_that_parameter(self):
        # the Coliforms row's acceptance text is 'pH' (a QIP name); the pH row must stay the pH row
        rows = [_row("pH", "3.5 - 5.0", "4.25"), _row("Coliforms", "pH", "")]
        for order in (rows, list(reversed(rows))):
            lot, raw, _ = _build(order)
            self.assertEqual(lot.values["pH"], 4.25)
            self.assertEqual(raw["pH"], "4.25")
            self.assertNotIn("Coliforms", lot.values)       # empty result -> NO DATA, never guessed

    def test_parameter_name_wins_even_when_specification_is_a_different_known_name(self):
        lot, _, _ = _build([_row("Arsenic", "pH", "1.96")])
        self.assertEqual(lot.values, {"Arsenic": 1.96})


class TestFallbackToSpecification(unittest.TestCase):
    def test_sandbox_shape_name_in_both_columns(self):
        lot, _, _ = _build([_row("Arsenic", "Arsenic", "1.96"), _row("pH", "pH", "4.0")])
        self.assertEqual(lot.values, {"Arsenic": 1.96, "pH": 4.0})

    def test_v1_shape_parameter_name_blank_and_specification_is_the_name(self):
        lot, raw, _ = _build([_row(None, "Arsenic", "1.96"), _row("", "pH", "4.0")])
        self.assertEqual(lot.values, {"Arsenic": 1.96, "pH": 4.0})
        self.assertEqual(raw["Arsenic"], "1.96")

    def test_blank_parameter_name_and_acceptance_text_stays_unkeyed(self):
        lot, raw, _ = _build([_row(None, "NMT 3 PPM", "1.96"), _row("", "3.5 - 5.0", "4.25")])
        self.assertEqual(lot.values, {})
        self.assertEqual(raw, {})

    def test_blank_parameter_name_with_a_name_the_tds_defines_is_kept_without_a_db_lookup(self):
        self.assertEqual(_row_key(_row(None, "Arsenic"), {"Arsenic": "numeric"}, {}), "Arsenic")

    def test_both_blank_is_unkeyed(self):
        self.assertIsNone(_row_key(_row(None, None), {}, {}))
        self.assertIsNone(_row_key(_row("", "  "), {}, {}))
        self.assertIsNone(_row_key(_row("  ", "  "), {}, {}))


class TestKeptBehaviour(unittest.TestCase):
    def test_no_data_is_never_zero(self):
        lot, _, _ = _build([_row("pH", "3.5 - 5.0", "ND", "0"), _row("Arsenic", "NMT 3 PPM", "<LOQ")])
        self.assertNotIn("pH", lot.values)
        self.assertNotIn("Arsenic", lot.values)

    def test_two_sided_ph_and_a_qualitative_row_are_not_assumed_at_the_limit(self):
        lot, _, _ = _build([_row("pH", "3.5 - 5.0", ""), _row("Coliforms", "NEGATIVE", "")])
        res = blend([lot], [PH, COLI])
        self.assertIsNone(res["pH"].computed_value)
        self.assertIsNone(res["Coliforms"].computed_value)

    def test_value_column_acceptance_text_is_still_never_a_number(self):
        lot, _, _ = _build([_row("Arsenic", "NMT 3 PPM", "", "NMT 1 PPM")])
        self.assertNotIn("Arsenic", lot.values)

    def test_the_child_doctype_really_has_the_column(self):
        import json
        with open(os.path.join(PKG, "amb_w_tds", "doctype", "coa_quality_test_parameter",
                               "coa_quality_test_parameter.json"), encoding="utf8") as f:
            fields = {x["fieldname"]: x for x in json.load(f)["fields"]}
        self.assertEqual(fields["parameter_name"]["fieldtype"], "Link")
        self.assertEqual(fields["parameter_name"]["options"], "Quality Inspection Parameter")
        for dn in ("coa_amb", "coa_amb2"):
            with open(os.path.join(PKG, "amb_w_tds", "doctype", dn, dn + ".json"), encoding="utf8") as f:
                opts = [x.get("options") for x in json.load(f)["fields"]]
            self.assertIn("COA Quality Test Parameter", opts)

    def test_no_doctype_json_is_touched_so_no_migrate_is_needed(self):
        # the reader fetches a column that already exists; the shipped DocType JSON is read, not changed
        self.assertTrue(os.path.exists(os.path.join(PKG, "amb_w_tds", "doctype", "coa_quality_test_parameter",
                                                    "coa_quality_test_parameter.json")))


class TestVersion(unittest.TestCase):
    def test_version_is_13_12_11_or_later(self):
        with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
            ver = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)
        with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
            self.assertEqual(f.read().strip(), ver)
        self.assertGreaterEqual(tuple(int(x) for x in ver.split(".")), (13, 12, 11))


if __name__ == "__main__":
    unittest.main()
