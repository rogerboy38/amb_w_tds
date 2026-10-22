"""Propuestas de Formulación: the logic half, DB-free.

The DB half (the report on seeded proposals, the PDF and the Excel) is proven on a
scratch site; see the 13.9.0 PR. Here: headline picking, the compliance verdict
through the gate's comparator, the overall status, and the reading of the gate's
stored Predicted Analytic rows.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import frappe  # noqa: E402

from amb_w_tds.formulation import engine  # noqa: E402
from amb_w_tds.formulation.propuestas import (  # noqa: E402
	CUMPLE,
	INCOMPLETO,
	NO_CUMPLE,
	SIN_SIMULACION,
	SIN_TDS,
	TDS_CANCELADA,
	TDS_NO_EXISTE,
	_compliance,
	_overall,
	_predicted,
	headline_columns,
	mark,
	pick_headline,
	resolve_tds,
	shared_tds,
	tds_label,
)

P = engine.Parameter
OK = {"name": "TDS-A", "source": "target_tds", "status": "aprobada", "usable": True}
M = engine.BlendMethod


def _row(**kw):
	base = {"parameter": None, "computed_value": "", "predicted_value": 0, "is_estimate": 0, "blend_method": "mass_avg"}
	base.update(kw)
	return frappe._dict(base)


class FakeDoc:
	def __init__(self, rows):
		self._rows = rows

	def get(self, key):
		return self._rows if key == "predicted_analytics" else None


class TestHeadline(unittest.TestCase):
	def test_total_or_content_name_wins(self):
		names = ["pH", "Aloin A", "Aloin B", "Total Aloin A + Aloin B", "Arsenic",
			"Polysaccharides Measured As Acemannan"]
		h = pick_headline(names)
		self.assertEqual(h["aloina"], "Total Aloin A + Aloin B")
		self.assertEqual(h["arsenico"], "Arsenic")
		self.assertEqual(h["acemannan"], "Polysaccharides Measured As Acemannan")

	def test_first_match_in_tds_order_without_preferred_word(self):
		self.assertEqual(pick_headline(["Aloin A", "Aloin B"])["aloina"], "Aloin A")

	def test_accents_and_case_fold(self):
		self.assertEqual(pick_headline(["ARSÉNICO (ppm)"])["arsenico"], "ARSÉNICO (ppm)")

	def test_missing_parameter_is_none_not_a_guess(self):
		h = pick_headline(["pH"])
		self.assertIsNone(h["acemannan"])
		self.assertIsNone(h["aloina"])
		self.assertIsNone(h["arsenico"])


class TestPredicted(unittest.TestCase):
	def test_numeric_row_reads_predicted_value(self):
		d = FakeDoc([_row(parameter="Acemannan", computed_value="12.5", predicted_value=12.5, is_estimate=1)])
		self.assertEqual(_predicted(d)["Acemannan"]["value"], 12.5)

	def test_numeric_row_without_lot_data_is_none_not_zero(self):
		# predicted_value is a NOT NULL float: 0 there with an empty computed value means "no data"
		d = FakeDoc([_row(parameter="Arsenic", computed_value="", predicted_value=0, is_estimate=1)])
		self.assertIsNone(_predicted(d)["Arsenic"]["value"])

	def test_all_pass_and_descriptive_rows_are_text(self):
		d = FakeDoc([
			_row(parameter="Salmonella", computed_value="PASS", blend_method="all_pass"),
			_row(parameter="Color", computed_value="DESCRIPTIVE — lab confirms", predicted_value=0),
		])
		p = _predicted(d)
		self.assertIsNone(p["Salmonella"]["value"])
		self.assertEqual(p["Salmonella"]["text"], "PASS")
		self.assertIsNone(p["Color"]["value"])

	def test_unresolved_parameter_keeps_its_name(self):
		d = FakeDoc([_row(parameter=None, computed_value="UNRESOLVED: Foo", is_estimate=1, predicted_value=3)])
		self.assertIn("Foo", _predicted(d))
		self.assertIsNone(_predicted(d)["Foo"]["value"])


class TestCompliance(unittest.TestCase):
	params = [
		P("Acemannan", M.MASS_AVG, min_value=10.0, max_value=None, uom="%"),
		P("Arsenic", M.MASS_AVG, min_value=None, max_value=3.0, uom="ppm"),
		P("Salmonella", M.ALL_PASS, numeric=False),
		P("Color", M.MASS_AVG, numeric=False),
		P("Unbounded", M.MASS_AVG),
	]

	def _pred(self, **vals):
		out = {}
		for k, v in vals.items():
			out[k] = {"value": v, "text": "" if v is None else str(v), "numeric": True}
		return out

	def test_bounds_use_the_gate_comparator(self):
		pred = self._pred(Acemannan=12.0, Arsenic=3.5)
		pred["Salmonella"] = {"value": None, "text": "PASS", "numeric": False}
		c = {r["parameter"]: r for r in _compliance(self.params, pred)}
		self.assertTrue(c["Acemannan"]["ok"])
		self.assertFalse(c["Arsenic"]["ok"])
		self.assertTrue(c["Salmonella"]["ok"])
		self.assertEqual(c["Color"]["kind"], "descriptive")
		self.assertNotIn("Unbounded", c)  # no bound in the TDS: nothing to comply with
		self.assertEqual(_overall(OK, pred, list(c.values())), NO_CUMPLE)

	def test_boundary_value_is_inside(self):
		c = {r["parameter"]: r for r in _compliance(self.params, self._pred(Acemannan=10.0, Arsenic=3.0))}
		self.assertTrue(c["Acemannan"]["ok"])
		self.assertTrue(c["Arsenic"]["ok"])

	def test_missing_prediction_is_incomplete_not_a_pass(self):
		pred = self._pred(Acemannan=12.0)
		pred["Salmonella"] = {"value": None, "text": "PASS", "numeric": False}
		comp = _compliance(self.params, pred)
		self.assertIsNone({r["parameter"]: r for r in comp}["Arsenic"]["ok"])
		self.assertEqual(_overall(OK, pred, comp), INCOMPLETO)

	def test_no_data_on_a_contaminant_is_not_a_pass(self):
		pred = self._pred(Acemannan=12.0, Arsenic=1.0)
		pred["Salmonella"] = {"value": None, "text": "NO DATA", "numeric": False}
		comp = _compliance(self.params, pred)
		self.assertEqual(_overall(OK, pred, comp), INCOMPLETO)

	def test_all_in_spec_is_cumple(self):
		pred = self._pred(Acemannan=12.0, Arsenic=1.0)
		pred["Salmonella"] = {"value": None, "text": "PASS", "numeric": False}
		self.assertEqual(_overall(OK, pred, _compliance(self.params, pred)), CUMPLE)

	def test_no_tds_and_no_simulation(self):
		self.assertEqual(_overall(None, {"x": {}}, []), SIN_TDS)
		self.assertEqual(_overall(OK, {}, []), SIN_SIMULACION)

	def test_mark_survives_black_and_white(self):
		self.assertTrue(mark(True).startswith("✓"))
		self.assertTrue(mark(False).startswith("✗"))
		self.assertTrue(mark(None).startswith("—"))


class TestTdsResolution(unittest.TestCase):
	"""13.9.1: explicit filter > the proposal's own target_tds > SIN TDS. No Item-name lookup."""

	DS = {"TDS-A": 1, "TDS-DRAFT": 0, "TDS-CANC": 2}

	def r(self, filt, target):
		return resolve_tds(filt, target, self.DS.get)

	def test_filter_wins_over_target(self):
		info = self.r("TDS-A", "TDS-DRAFT")
		self.assertEqual((info["name"], info["source"], info["status"]), ("TDS-A", "filtro", "aprobada"))

	def test_no_filter_uses_the_proposal_target(self):
		info = self.r(None, "TDS-A")
		self.assertEqual((info["name"], info["source"]), ("TDS-A", "target_tds"))
		self.assertTrue(info["usable"])

	def test_empty_string_filter_is_no_filter(self):
		self.assertEqual(self.r("", "TDS-A")["source"], "target_tds")

	def test_neither_is_sin_tds(self):
		self.assertIsNone(self.r(None, None))
		self.assertEqual(_overall(None, {"x": {}}, []), SIN_TDS)
		self.assertEqual(tds_label(None), SIN_TDS)

	def test_draft_judges_and_is_labelled(self):
		info = self.r(None, "TDS-DRAFT")
		self.assertTrue(info["usable"])
		self.assertEqual(tds_label(info), "TDS-DRAFT (borrador)")

	def test_cancelled_and_missing_are_refused(self):
		canc, gone = self.r(None, "TDS-CANC"), self.r(None, "TDS-GONE")
		self.assertFalse(canc["usable"])
		self.assertFalse(gone["usable"])
		self.assertEqual(_overall(canc, {"x": {}}, []), TDS_CANCELADA)
		self.assertEqual(_overall(gone, {"x": {}}, []), TDS_NO_EXISTE)


class TestSpecBoxAndColumns(unittest.TestCase):
	def prop(self, tds, status="aprobada", aloin=("Aloin Content", "ppm")):
		box = None if tds is None else {"name": tds, "status": status}
		return {"tds": box, "headline": {
			"acemannan": {"spec": "Acemannan", "uom": "%"},
			"aloina": {"spec": aloin[0], "uom": aloin[1]},
			"arsenico": {"spec": None, "uom": ""}}}

	def test_one_header_only_when_all_share_name_and_status(self):
		self.assertEqual(shared_tds([self.prop("A"), self.prop("A")], None, lambda: None)["name"], "A")
		self.assertIsNone(shared_tds([self.prop("A"), self.prop("B")], None, lambda: None))
		self.assertIsNone(shared_tds([self.prop("A"), self.prop(None)], None, lambda: None))
		self.assertIsNone(shared_tds([self.prop("A"), self.prop("A", "borrador")], None, lambda: None))

	def test_no_proposals_shows_the_filter_tds(self):
		self.assertEqual(shared_tds([], "F", lambda: {"name": "F"}), {"name": "F"})
		self.assertIsNone(shared_tds([], None, lambda: {"name": "F"}))

	def test_column_uom_only_when_uniform(self):
		cols = {c["key"]: c for c in headline_columns(
			[self.prop("A"), self.prop("B", aloin=("Total Aloin A + Aloin B", "%"))])}
		self.assertTrue(cols["acemannan"]["uniform"])
		self.assertEqual(cols["acemannan"]["uom"], "%")
		self.assertFalse(cols["aloina"]["uniform"])
		self.assertEqual(cols["aloina"]["uom"], "")
		self.assertTrue(cols["arsenico"]["uniform"])  # nobody has it: nothing to disagree on


if __name__ == "__main__":
	unittest.main()
