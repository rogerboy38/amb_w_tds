"""13.12.7 (TASKS-281): the blend uses the measured number; no number is not 0.

Ruling 1 — a lot whose OWN number is over its limit still enters the blend; only the blend (the
mass-weighted average, or the pH / worst-case aggregation) is judged against the specification.
Ruling 2 — a lot with no usable number for a parameter (blank, ND, free text) is NO DATA: left out
of the average, named in the result, never counted as 0. ND semantics are NOT decided here.

DB-free: the engine is pure Python; the reader (`_build_lots` / `_lot_value`) is driven with
frappe.get_all mocked, as test_coa_amb2_cut1.TestGateWarning does.
"""

import os
import unittest
from unittest import mock

import frappe

from amb_w_tds.formulation import engine
from amb_w_tds.formulation.engine import BlendMethod, Lot, Parameter, blend

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AS = Parameter("Arsenic", BlendMethod.MASS_AVG, max_value=3.0, uom="ppm", critical=True)
AS_NMT2 = Parameter("Arsenic", BlendMethod.MASS_AVG, max_value=2.0, uom="ppm", critical=True)
PH = Parameter("pH", BlendMethod.PH_HPLUS, min_value=3.5, max_value=5.0, critical=True)
APC = Parameter("Aerobic Plate Count", BlendMethod.WORST_CASE, max_value=500, uom="CFU/g", critical=True)
COLI = Parameter("Coliforms", BlendMethod.ALL_PASS, numeric=False, critical=True)


def lot(lot_id, kg, **values):
    return Lot(lot_id, kg, values)


class TestRuling1TheBlendDecides(unittest.TestCase):
    def test_hughs_example_equal_masses_1_7_and_2_22_blend_1_96_pass_against_nmt_3(self):
        r = blend([lot("A", 100, Arsenic=1.7), lot("B", 100, Arsenic=2.22)], [AS])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, 1.96, places=9)
        self.assertIs(r.in_spec_estimate, True)
        self.assertEqual((r.lots_used, r.lots_no_data), (["A", "B"], []))
        self.assertEqual((r.mass_used_kg, r.mass_no_data_kg), (200, 0))

    def test_the_same_pair_against_nmt_2_passes_although_the_2_22_lot_is_over_its_own_limit(self):
        r = blend([lot("A", 100, Arsenic=1.7), lot("B", 100, Arsenic=2.22)], [AS_NMT2])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, 1.96, places=9)
        self.assertIs(r.in_spec_estimate, True)
        self.assertEqual(r.lots_used, ["A", "B"])   # B is IN, not rejected for its own 2.22

    def test_unequal_masses_70_30_exact(self):
        r = blend([lot("A", 700, Arsenic=1.7), lot("B", 300, Arsenic=2.22)], [AS])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, (700 * 1.7 + 300 * 2.22) / 1000, places=12)
        self.assertAlmostEqual(r.computed_value, 1.856, places=9)

    def test_a_blend_over_the_limit_as_a_blend_fails_and_one_inside_passes(self):
        high = blend([lot("A", 100, Arsenic=3.4), lot("B", 100, Arsenic=3.1)], [AS])["Arsenic"]
        self.assertAlmostEqual(high.computed_value, 3.25, places=9)
        self.assertIs(high.in_spec_estimate, False)
        mixed = blend([lot("A", 100, Arsenic=1.0), lot("B", 100, Arsenic=3.4)], [AS])["Arsenic"]
        self.assertAlmostEqual(mixed.computed_value, 2.2, places=9)
        self.assertIs(mixed.in_spec_estimate, True)   # B alone is over 3; the blend is not

    def test_within_spec_is_the_only_judge_and_says_none_for_no_data(self):
        self.assertIsNone(engine._within_spec(None, 0, 3, "mass_avg"))
        self.assertIsNone(engine._within_spec(None, None, None, "all_pass"))
        self.assertIs(engine._within_spec(3.0, None, 3.0, "mass_avg"), True)
        self.assertIs(engine._within_spec(3.01, None, 3.0, "mass_avg"), False)


class TestRuling2NoDataIsNotZero(unittest.TestCase):
    def test_a_lot_without_a_number_is_left_out_and_named_and_the_average_of_the_others_is_unchanged(self):
        with_c = blend([lot("A", 100, Arsenic=1.7), lot("B", 100, Arsenic=2.22), lot("C", 300)], [AS])["Arsenic"]
        self.assertAlmostEqual(with_c.computed_value, 1.96, places=9)        # not (170+222+0)/500 = 0.784
        self.assertEqual(with_c.lots_no_data, ["C"])
        self.assertEqual(with_c.mass_no_data_kg, 300)
        self.assertEqual((with_c.lots_used, with_c.mass_used_kg), (["A", "B"], 200))
        self.assertIn("NO DATA on 1 of 3 lots (C; 300 kg not in this estimate)", with_c.note)
        self.assertIs(with_c.in_spec_estimate, True)

    def test_none_bool_and_text_in_values_are_no_data_for_a_numeric_rule(self):
        for bad in (None, False, True, "ND", "<LOQ", ""):
            r = blend([lot("A", 100, Arsenic=1.7), lot("B", 100, Arsenic=bad)], [AS])["Arsenic"]
            self.assertAlmostEqual(r.computed_value, 1.7, places=9, msg=repr(bad))
            self.assertEqual(r.lots_no_data, ["B"], repr(bad))

    def test_no_number_anywhere_is_no_data_neither_pass_nor_fail(self):
        r = blend([lot("A", 100), lot("B", 100, Arsenic=None)], [AS])["Arsenic"]
        self.assertIsNone(r.computed_value)
        self.assertIsNone(r.in_spec_estimate)
        self.assertEqual((r.lots_used, r.lots_no_data), ([], ["A", "B"]))
        self.assertEqual(r.mass_no_data_kg, 200)

    def test_ph_hplus_and_worst_case_tolerate_a_lot_without_data(self):
        ph = blend([lot("A", 700, pH=3.0), lot("B", 300, pH=5.0), lot("C", 100)], [PH])["pH"]
        self.assertAlmostEqual(ph.computed_value, 3.153, places=2)      # the engine's own self-test value, C left out
        self.assertEqual(ph.lots_no_data, ["C"])
        apc = blend([lot("A", 100, **{"Aerobic Plate Count": 300}), lot("B", 100), lot("C", 100, **{"Aerobic Plate Count": "ND"})], [APC])["Aerobic Plate Count"]
        self.assertEqual(apc.computed_value, 300)
        self.assertEqual(apc.lots_no_data, ["B", "C"])
        none = blend([lot("A", 100), lot("B", 100)], [PH, APC])
        self.assertIsNone(none["pH"].computed_value)
        self.assertIsNone(none["Aerobic Plate Count"].computed_value)
        self.assertIsNone(none["pH"].in_spec_estimate)

    def test_a_bool_never_enters_an_average(self):
        # before 13.12.7 True averaged as 1 and False as 0
        r = blend([lot("A", 100, Arsenic=2.0), lot("B", 100, Arsenic=True)], [AS])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, 2.0, places=9)


class TestQualitativeUnchanged(unittest.TestCase):
    def test_pass_token_and_fail_token_give_the_same_result_as_before(self):
        ok = blend([lot("A", 100, Coliforms=True), lot("B", 100, Coliforms=True)], [COLI])["Coliforms"]
        self.assertIs(ok.computed_value, True)
        self.assertIs(ok.in_spec_estimate, True)
        bad = blend([lot("A", 100, Coliforms=True), lot("B", 100, Coliforms=False)], [COLI])["Coliforms"]
        self.assertIs(bad.computed_value, False)
        self.assertIs(bad.in_spec_estimate, False)       # the per-lot rejection stays: one FAIL fails the blend
        self.assertEqual(bad.lots_used, ["A", "B"])

    def test_a_qualitative_lot_without_a_verdict_makes_the_parameter_no_data_never_a_vacuous_pass(self):
        # before 13.12.7 the engine passed over the lots that had a verdict while simulate_blend's
        # class 3 (_all_pass_state) said NO DATA for the same lots; now both say NO DATA.
        r = blend([lot("A", 100, Coliforms=True), lot("B", 100)], [COLI])["Coliforms"]
        self.assertIsNone(r.computed_value)
        self.assertIsNone(r.in_spec_estimate)
        self.assertEqual((r.lots_used, r.lots_no_data), (["A"], ["B"]))
        fail = blend([lot("A", 100, Coliforms=False), lot("B", 100)], [COLI])["Coliforms"]
        self.assertIsNone(fail.computed_value)             # NO DATA is decided before PASS/FAIL, as class 3 does
        none = blend([lot("A", 100), lot("B", 100)], [COLI])["Coliforms"]
        self.assertIsNone(none.computed_value)
        self.assertIsNone(none.in_spec_estimate)

    def test_the_engine_self_test_values_still_hold(self):
        params = [Parameter("Aloin", BlendMethod.MASS_AVG, min_value=0, max_value=0.1, critical=True, uom="ppm"),
                  PH, Parameter("AerobicPlate", BlendMethod.WORST_CASE, min_value=0, max_value=500, critical=True),
                  Parameter("Salmonella", BlendMethod.ALL_PASS, numeric=False, critical=True)]
        lots = [Lot("A", 700, {"Aloin": 0.08, "pH": 3.0, "AerobicPlate": 300, "Salmonella": True}),
                Lot("B", 300, {"Aloin": 0.12, "pH": 5.0, "AerobicPlate": 500, "Salmonella": True})]
        res = blend(lots, params)
        self.assertAlmostEqual(res["Aloin"].computed_value, 0.092, places=9)
        self.assertAlmostEqual(res["pH"].computed_value, 3.153, places=2)
        self.assertEqual(res["AerobicPlate"].computed_value, 500)
        self.assertIs(res["Salmonella"].computed_value, True)
        self.assertIs(blend(lots + [Lot("C", 50, {"Salmonella": False})], params)["Salmonella"].computed_value, False)


# ---- the reader: COA rows -> Lot.values, by the parameter's kind ----

def _formula(lines):
    from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
    d = object.__new__(BOMFormula)
    d.__dict__["doctype"] = "BOM Formula"
    d.__dict__["mix_input_lines"] = [frappe._dict(l) for l in lines]
    d.__dict__["prediction_note"] = ""
    return d


LINES = [dict(cunete_ref="C-1", item_code="IT-A", kg=100, batch_amb_sublot=None, source_coa_amb2="COA2-1", source_coa_doctype="COA AMB2"),
         dict(cunete_ref="C-2", item_code="IT-B", kg=100, batch_amb_sublot=None, source_coa_amb2="COA2-2", source_coa_doctype="COA AMB2")]
PARAMS = [AS, COLI, Parameter("Appearance", BlendMethod.MASS_AVG, numeric=False)]


def _build(rows, params=PARAMS):
    d = _formula(LINES)
    with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: rows[filters["parent"]]), \
            mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None)):
        lots, total, with_coa = d._build_lots(params)
    return {l.lot_id: l.values for l in lots}


def _row(spec, result=None, value=None):
    return frappe._dict(specification=spec, result=result, value=value)


class TestReaderResultFirst(unittest.TestCase):
    def test_result_wins_over_a_value_of_zero_and_over_a_value_of_anything(self):
        v = _build({"COA2-1": [_row("Arsenic", result="2.22", value="0")], "COA2-2": [_row("Arsenic", result="1.7", value="9")]})
        self.assertEqual(v, {"C-1": {"Arsenic": 2.22}, "C-2": {"Arsenic": 1.7}})

    def test_value_zero_with_empty_result_is_no_data_and_a_nonzero_value_is_used(self):
        v = _build({"COA2-1": [_row("Arsenic", result="", value="0")], "COA2-2": [_row("Arsenic", result=None, value="1.5")]})
        self.assertEqual(v, {"C-1": {}, "C-2": {"Arsenic": 1.5}})

    def test_blank_nd_free_text_and_loq_are_no_data_for_a_numeric_parameter(self):
        for res in ("", None, "ND", "not detected", "<LOQ", "NEGATIVE"):
            v = _build({"COA2-1": [_row("Arsenic", result=res, value="0")], "COA2-2": [_row("Arsenic", result="1.7")]})
            self.assertEqual(v["C-1"], {}, repr(res))
            self.assertEqual(v["C-2"], {"Arsenic": 1.7})

    def test_unit_suffixed_and_less_than_strings_give_the_leading_number(self):
        v = _build({"COA2-1": [_row("Arsenic", result="<10 ppm")], "COA2-2": [_row("Arsenic", result="23.5%")]})
        self.assertEqual(v, {"C-1": {"Arsenic": 10.0}, "C-2": {"Arsenic": 23.5}})

    def test_the_kind_comes_from_the_parameter_not_from_the_parse(self):
        # the same cells, read for a QUALITATIVE parameter: token test, never a number
        rows = {"COA2-1": [_row("Coliforms", result="NEGATIVE", value="0")], "COA2-2": [_row("Coliforms", result="<10", value="0")]}
        self.assertEqual(_build(rows), {"C-1": {"Coliforms": True}, "C-2": {"Coliforms": False}})
        # an EMPTY qualitative result is NO DATA; "ND" is NOT a pass token and keeps today's rejection
        rows = {"COA2-1": [_row("Coliforms", result="")], "COA2-2": [_row("Coliforms", result="ND")]}
        self.assertEqual(_build(rows), {"C-1": {}, "C-2": {"Coliforms": False}})
        # a descriptive parameter contributes nothing to the engine (the words stay in _raw_by_lot)
        rows = {"COA2-1": [_row("Appearance", result="FINE POWDER")], "COA2-2": [_row("Appearance", result="99% THROUGH NO.100 MESH")]}
        self.assertEqual(_build(rows), {"C-1": {}, "C-2": {}})

    def test_without_params_a_row_is_typed_by_its_content_as_before(self):
        rows = {"COA2-1": [_row("Acemannan", value="14", result=None)], "COA2-2": [_row("X", result="NEGATIVE"), _row("Y", result="ND")]}
        self.assertEqual(_build(rows, params=None), {"C-1": {"Acemannan": 14.0}, "C-2": {"X": True, "Y": False}})

    def test_lot_value_table(self):
        from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import _lot_value
        cases = [  # (kind, result, value) -> expected
            (("numeric", "2.22", "0"), 2.22), (("numeric", "", "0"), None), (("numeric", None, None), None),
            (("numeric", "ND", "0"), None), (("numeric", "<10", ""), 10.0), (("numeric", "<LOQ", ""), None),
            (("numeric", None, "1.5"), 1.5), (("numeric", "NEGATIVE", "3"), 3.0), (("numeric", 2, None), 2.0),
            # `value` on COA AMB rows is the ACCEPTANCE text: its digits are a limit, never a measurement
            (("numeric", "", "NMT 1 PPM"), None), (("numeric", None, "3.5 - 5.0"), None), (("numeric", "", "NMT 35%"), None),
            (("numeric", "", "Specification"), None), (("numeric", "ND", "NMT 1 PPM"), None), (("numeric", "2.22", "NMT 3 PPM"), 2.22),
            (("qualitative", "NEGATIVE", "0"), True), (("qualitative", "ND", "0"), False), (("qualitative", "", "0"), None),
            (("qualitative", "<10", ""), False), (("descriptive", "FINE POWDER", "0"), None),
            ((None, "2.22", "0"), 2.22), ((None, "NEGATIVE", "0"), True), ((None, "", "0"), None), ((None, "ND", ""), False),
        ]
        for (kind, result, value), exp in cases:
            got = _lot_value(frappe._dict(result=result, value=value), kind)
            self.assertEqual(got, exp, (kind, result, value))
            self.assertIs(type(got), type(exp), (kind, result, value))


class TestSimulateBlendShape(unittest.TestCase):
    def test_no_data_rows_and_the_return_structure(self):
        from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
        d = _formula(LINES + [dict(cunete_ref="C-3", item_code="IT-C", kg=300, batch_amb_sublot=None, source_coa_amb2="COA2-3", source_coa_doctype="COA AMB2")])
        rows = {"COA2-1": [_row("Arsenic", result="1.7"), _row("pH", result="4.0"), _row("Coliforms", result="NEGATIVE")],
                "COA2-2": [_row("Arsenic", result="2.22"), _row("pH", result="ND"), _row("Coliforms", result="NEGATIVE")],
                "COA2-3": [_row("Arsenic", result=""), _row("pH", result=""), _row("Coliforms", result="")]}
        appended = []
        with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: rows[filters["parent"]]), \
                mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None, exists=lambda *a, **k: True)), \
                mock.patch.object(BOMFormula, "_build_parameters", lambda s: [AS, PH, COLI]), \
                mock.patch.object(BOMFormula, "_recompute_mix_totals", lambda s: None), \
                mock.patch.object(BOMFormula, "save", lambda s, **k: None), \
                mock.patch.object(BOMFormula, "set", lambda s, k, v=None, *a, **kw: s.__dict__.__setitem__(k, v)), \
                mock.patch.object(BOMFormula, "append", lambda s, k, row: appended.append(row)), \
                mock.patch("frappe.msgprint", mock.Mock()):
            d.__dict__.update(total_input_kg=500, total_amount=0)
            res = d.simulate_blend()
        by = {r["parameter"]: r for r in appended}
        self.assertEqual(by["Arsenic"]["computed_value"], "1.96")
        self.assertEqual(by["Arsenic"]["status"], "Pass")
        self.assertEqual(by["pH"]["computed_value"], "4")       # only C-1 has a pH number
        self.assertEqual(res["no_data"]["Arsenic"], {"lots": ["C-3"], "mass_kg": 300, "lots_used": ["C-1", "C-2"], "mass_used_kg": 200})
        self.assertEqual(res["no_data"]["pH"], {"lots": ["C-2", "C-3"], "mass_kg": 400, "lots_used": ["C-1"], "mass_used_kg": 100})
        # class 3 with a blank lot: NO DATA (never a vacuous PASS), status neither Pass nor Fail, named in no_data too
        self.assertEqual((by["Coliforms"]["computed_value"], by["Coliforms"]["status"], by["Coliforms"]["per_lot_pass"]), ("NO DATA", "", 0))
        self.assertEqual(res["no_data"]["Coliforms"], {"lots": ["C-3"], "mass_kg": 300, "lots_used": ["C-1", "C-2"], "mass_used_kg": 200})
        self.assertEqual(res["no_data_estimate"], 1)   # Coliforms; Arsenic and pH have an estimate from the lots with data
        self.assertIn("NO DATA on 1 of 3 lots (C-3; 300 kg not in this estimate)", by["Arsenic"]["note"])

    def test_a_parameter_with_no_number_anywhere_is_a_no_data_row(self):
        from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
        d = _formula(LINES)
        rows = {"COA2-1": [_row("Arsenic", result="ND")], "COA2-2": [_row("Arsenic", result="")]}
        appended = []
        with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: rows[filters["parent"]]), \
                mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None, exists=lambda *a, **k: True)), \
                mock.patch.object(BOMFormula, "_build_parameters", lambda s: [AS]), \
                mock.patch.object(BOMFormula, "_recompute_mix_totals", lambda s: None), \
                mock.patch.object(BOMFormula, "save", lambda s, **k: None), \
                mock.patch.object(BOMFormula, "set", lambda s, k, v=None, *a, **kw: s.__dict__.__setitem__(k, v)), \
                mock.patch.object(BOMFormula, "append", lambda s, k, row: appended.append(row)), \
                mock.patch("frappe.msgprint", mock.Mock()):
            d.__dict__.update(total_input_kg=200, total_amount=0)
            res = d.simulate_blend()
        row = appended[0]
        self.assertEqual((row["computed_value"], row["status"], row["predicted_value"], row["in_spec_estimate"]), ("NO DATA", "", None, 0))
        self.assertEqual(res["no_data_estimate"], 1)
        self.assertEqual(res["out_of_spec_estimate"], 0)
        self.assertEqual(res["no_data"]["Arsenic"]["lots"], ["C-1", "C-2"])


class TestVersion(unittest.TestCase):
    def test_version(self):
        with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
            self.assertIn('__version__ = "13.12.7"', f.read())
        with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
            self.assertEqual(f.read().strip(), "13.12.7")


if __name__ == "__main__":
    unittest.main()
