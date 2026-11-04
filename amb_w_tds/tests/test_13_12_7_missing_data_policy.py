"""13.12.7 (TASKS-282 Part B): the BOM Formula missing-data policy.

"No data" (default, as 281 built it): a lot without a usable number is left out of the estimate and named.
"TDS upper limit": such a lot is ASSUMED at the limit copied onto its own COA row — the max for a parameter
the TDS caps (NMT), the min for one it floors (NLT) — and the result says so (`assumed_at_limit`, row note);
a row without the needed bound, a two-sided range, and every qualitative parameter stay NO DATA. DB-free.
"""

import os
import unittest
from unittest import mock

import frappe

from amb_w_tds.formulation import engine
from amb_w_tds.formulation.engine import BlendMethod, Lot, Parameter, assume_at_limit, blend

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AS = Parameter("Arsenic", BlendMethod.MASS_AVG, max_value=3.0, uom="ppm", critical=True)        # NMT 3
ACE = Parameter("Acemannan", BlendMethod.MASS_AVG, min_value=15.0, uom="%")                      # NLT 15
RANGE = Parameter("pH", BlendMethod.MASS_AVG, min_value=3.5, max_value=5.0)                       # two-sided
PH = Parameter("pH", BlendMethod.PH_HPLUS, min_value=3.5, max_value=5.0, critical=True)
APC = Parameter("Aerobic Plate Count", BlendMethod.WORST_CASE, max_value=500, critical=True)
COLI = Parameter("Coliforms", BlendMethod.ALL_PASS, numeric=False, critical=True)


def lot(lot_id, kg, values=None, limits=None):
    return Lot(lot_id, kg, dict(values or {}), dict(limits or {}))


class TestAssumeAtLimit(unittest.TestCase):
    def test_hughs_example_under_both_policies(self):
        m1, m2 = 100, 300
        lots = [lot("A", m1, {"Arsenic": 1.7}, {"Arsenic": (None, 3.0)}), lot("B", m2, {}, {"Arsenic": (None, 3.0)})]
        # "No data": 1.7 over the lots with data, B named
        r = blend(lots, [AS])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, 1.7, places=9)
        self.assertEqual(r.lots_no_data, ["B"])
        # "TDS upper limit": B assumed at 3.0
        assumed = assume_at_limit(lots, [AS])
        self.assertEqual(assumed, {"Arsenic": {"value": 3.0, "bound": "max", "lots": ["B"], "mass_kg": 300.0}})
        r = blend(lots, [AS])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, (m1 * 1.7 + m2 * 3.0) / (m1 + m2), places=12)
        self.assertAlmostEqual(r.computed_value, 2.675, places=9)
        self.assertEqual(r.lots_no_data, [])                 # nothing is "no data" any more: it is assumed, and said
        self.assertIs(r.in_spec_estimate, True)

    def test_nd_text_and_bool_behave_like_blank(self):
        for bad in ("ND", "NO DISPONIBLE", "", None, False):
            lots = [lot("A", 100, {"Arsenic": 1.7}, {"Arsenic": (None, 3.0)}), lot("B", 100, {"Arsenic": bad}, {"Arsenic": (None, 3.0)})]
            assumed = assume_at_limit(lots, [AS])
            self.assertEqual(assumed["Arsenic"]["lots"], ["B"], repr(bad))
            self.assertAlmostEqual(blend(lots, [AS])["Arsenic"].computed_value, 2.35, places=9, msg=repr(bad))

    def test_no_limit_on_the_row_stays_no_data_under_both_policies(self):
        lots = [lot("A", 100, {"Arsenic": 1.7}, {"Arsenic": (None, 3.0)}), lot("B", 100, {}, {})]
        self.assertEqual(assume_at_limit(lots, [AS]), {})
        r = blend(lots, [AS])["Arsenic"]
        self.assertAlmostEqual(r.computed_value, 1.7, places=9)
        self.assertEqual(r.lots_no_data, ["B"])
        # a row that carries only the OTHER bound is "no limit" for this direction too
        lots = [lot("A", 100, {"Arsenic": 1.7}, {"Arsenic": (None, 3.0)}), lot("B", 100, {}, {"Arsenic": (0.5, None)})]
        self.assertEqual(assume_at_limit(lots, [AS]), {})

    def test_a_minimum_parameter_assumes_the_row_min(self):
        lots = [lot("A", 100, {"Acemannan": 20.0}, {"Acemannan": (15.0, None)}), lot("B", 100, {}, {"Acemannan": (15.0, None)})]
        assumed = assume_at_limit(lots, [ACE])
        self.assertEqual(assumed, {"Acemannan": {"value": 15.0, "bound": "min", "lots": ["B"], "mass_kg": 100.0}})
        self.assertAlmostEqual(blend(lots, [ACE])["Acemannan"].computed_value, 17.5, places=9)

    def test_a_two_sided_range_and_a_qualitative_parameter_are_never_assumed(self):
        lots = [lot("A", 100, {"pH": 4.0, "Coliforms": True}, {"pH": (3.5, 5.0), "Coliforms": (None, None)}),
                lot("B", 100, {}, {"pH": (3.5, 5.0)})]
        self.assertEqual(assume_at_limit(lots, [RANGE, COLI]), {})
        self.assertEqual(blend(lots, [RANGE])["pH"].lots_no_data, ["B"])
        self.assertIsNone(blend(lots, [COLI])["Coliforms"].computed_value)   # NO DATA as in 281

    def test_ph_hplus_and_worst_case_do_not_crash_and_are_not_assumed(self):
        lots = [lot("A", 100, {"pH": 4.0, "Aerobic Plate Count": 300}, {"pH": (3.5, 5.0), "Aerobic Plate Count": (None, 500.0)}),
                lot("B", 100, {}, {"pH": (3.5, 5.0), "Aerobic Plate Count": (None, 500.0)})]
        assumed = assume_at_limit(lots, [PH, APC])
        self.assertEqual(assumed, {"Aerobic Plate Count": {"value": 500.0, "bound": "max", "lots": ["B"], "mass_kg": 100.0}})
        res = blend(lots, [PH, APC])
        self.assertAlmostEqual(res["pH"].computed_value, 4.0, places=9)              # two-sided: B stays NO DATA
        self.assertEqual(res["pH"].lots_no_data, ["B"])
        self.assertEqual(res["Aerobic Plate Count"].computed_value, 500.0)             # worst case now includes the assumed lot
        self.assertEqual(res["Aerobic Plate Count"].lots_no_data, [])

    def test_lots_with_different_limits_are_reported_per_value(self):
        lots = [lot("A", 100, {}, {"Arsenic": (None, 3.0)}), lot("B", 100, {}, {"Arsenic": (None, 2.0)}), lot("C", 100, {"Arsenic": 1.0})]
        assumed = assume_at_limit(lots, [AS])
        self.assertEqual(assumed["Arsenic"], {"value": 3.0, "bound": "max", "lots": ["A"], "mass_kg": 100.0})
        self.assertEqual(assumed["Arsenic@2"], {"value": 2.0, "bound": "max", "lots": ["B"], "mass_kg": 100.0})
        self.assertAlmostEqual(blend(lots, [AS])["Arsenic"].computed_value, 2.0, places=9)

    def test_the_constants(self):
        self.assertEqual((engine.MISSING_NO_DATA, engine.MISSING_TDS_LIMIT), ("No data", "TDS upper limit"))
        import json
        with open(os.path.join(PKG, "amb_w_tds", "doctype", "bom_formula", "bom_formula.json"), encoding="utf8") as f:
            d = json.load(f)
        fld = next(x for x in d["fields"] if x["fieldname"] == "missing_data_policy")
        self.assertEqual((fld["fieldtype"], fld["options"], fld["default"]), ("Select", "No data\nTDS upper limit", "No data"))
        names = [x["fieldname"] for x in d["fields"]]
        self.assertEqual(names[names.index("target_tds") + 1], "missing_data_policy")


# ---- the reader carries the row limits; the preview applies the policy ----

def _formula(lines, policy=None):
    from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
    d = object.__new__(BOMFormula)
    d.__dict__["doctype"] = "BOM Formula"
    d.__dict__["mix_input_lines"] = [frappe._dict(l) for l in lines]
    d.__dict__["prediction_note"] = ""
    d.__dict__["missing_data_policy"] = policy
    return d


LINES = [dict(cunete_ref="C-1", item_code="IT-A", kg=100, batch_amb_sublot=None, source_coa_amb2="COA2-1", source_coa_doctype="COA AMB2"),
         dict(cunete_ref="C-2", item_code="IT-B", kg=300, batch_amb_sublot=None, source_coa_amb2="COA2-2", source_coa_doctype="COA AMB2")]
ROWS = {"COA2-1": [frappe._dict(specification="Arsenic", result="1.7", value="0", min_value=0, max_value=3.0)],
        "COA2-2": [frappe._dict(specification="Arsenic", result="", value="0", min_value=0, max_value=3.0)]}


class TestReaderAndPreview(unittest.TestCase):
    def test_build_lots_carries_the_row_limits(self):
        d = _formula(LINES)
        with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: ROWS[filters["parent"]]), \
                mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None)):
            lots, _, _ = d._build_lots([AS])
        self.assertEqual([(l.lot_id, l.values, l.limits) for l in lots],
                         [("C-1", {"Arsenic": 1.7}, {"Arsenic": (None, 3.0)}), ("C-2", {}, {"Arsenic": (None, 3.0)})])

    def _simulate(self, policy):
        from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
        d = _formula(LINES, policy)
        appended = []
        with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: ROWS[filters["parent"]]), \
                mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None, exists=lambda *a, **k: True)), \
                mock.patch.object(BOMFormula, "_build_parameters", lambda s: [AS]), \
                mock.patch.object(BOMFormula, "_recompute_mix_totals", lambda s: None), \
                mock.patch.object(BOMFormula, "save", lambda s, **k: None), \
                mock.patch.object(BOMFormula, "set", lambda s, k, v=None, *a, **kw: s.__dict__.__setitem__(k, v)), \
                mock.patch.object(BOMFormula, "append", lambda s, k, row: appended.append(row)), \
                mock.patch("frappe.msgprint", mock.Mock()):
            d.__dict__.update(total_input_kg=400, total_amount=0)
            res = d.simulate_blend()
        return res, appended[0]

    def test_default_policy_is_no_data(self):
        for policy in (None, "", "No data"):
            res, row = self._simulate(policy)
            self.assertEqual(row["computed_value"], "1.7", policy)
            self.assertEqual(res["no_data"]["Arsenic"]["lots"], ["C-2"])
            self.assertEqual((res["missing_data_policy"], res["assumed_at_limit"]), ("No data", {}))
            self.assertNotIn("ASSUMED", row["note"])

    def test_tds_upper_limit_policy_assumes_and_says_so(self):
        res, row = self._simulate("TDS upper limit")
        self.assertEqual(row["computed_value"], "2.675")            # (100*1.7 + 300*3.0)/400
        self.assertEqual(row["status"], "Pass")
        self.assertEqual(res["no_data"], {})                          # the assumed lot is not "no data"
        self.assertEqual(res["assumed_at_limit"], {"Arsenic": {"value": 3.0, "bound": "max", "lots": ["C-2"], "mass_kg": 300.0}})
        self.assertIn('ASSUMED at TDS limit 3 (max on the COA row) for C-2 (300 kg) — policy "TDS upper limit"', row["note"])


if __name__ == "__main__":
    unittest.main()
