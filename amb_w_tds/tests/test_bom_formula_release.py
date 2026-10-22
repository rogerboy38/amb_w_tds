"""13.11.0 BOM Formula approval + release: the logic half, DB-free.

The DB half (the workflow walk by role, the submitted BOM, the Work Order) is proven on a
scratch site; see the 13.11.0 PR.
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import frappe  # noqa: E402

from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import cost_approval_for_state  # noqa: E402
from amb_w_tds.formulation.release import plan_bom, resolve_line_item  # noqa: E402


class TestStateDrivesCostApproval(unittest.TestCase):
	def test_authorized_and_released_mean_approved(self):
		self.assertEqual(cost_approval_for_state("Autorizado", ""), "approved")
		self.assertEqual(cost_approval_for_state("Liberado", "requested"), "approved")

	def test_rejected_and_review(self):
		self.assertEqual(cost_approval_for_state("Rechazado", "approved"), "rejected")
		self.assertEqual(cost_approval_for_state("En Revisión", ""), "requested")

	def test_return_to_borrador_withdraws_approval_or_rejection(self):
		self.assertEqual(cost_approval_for_state("Borrador", "approved"), "")
		self.assertEqual(cost_approval_for_state("Borrador", "rejected"), "")
		self.assertEqual(cost_approval_for_state("Borrador", "not required"), "not required")

	def test_no_workflow_keeps_the_field(self):
		self.assertEqual(cost_approval_for_state(None, "approved"), "approved")


class TestLineItem(unittest.TestCase):
	def test_item_code_wins(self):
		self.assertEqual(resolve_line_item({"item_code": "A", "batch_amb_sublot": "S"}, lambda s: "B"), "A")

	def test_falls_back_to_the_sublot_item(self):
		self.assertEqual(resolve_line_item({"batch_amb_sublot": "S"}, lambda s: "B"), "B")

	def test_unresolvable_is_none_never_a_guess(self):
		self.assertIsNone(resolve_line_item({"batch_amb_sublot": "S"}, lambda s: None))
		self.assertIsNone(resolve_line_item({"cunete_ref": "C-1"}, lambda s: "B"))


class TestPlan(unittest.TestCase):
	ITEMS = {"FG": "Kg", "RM1": "Kg", "RM2": "Kg", "FG-NOS": "Nos"}

	def plan(self, formula):
		return plan_bom(frappe._dict(formula), batch_item_of=lambda s: {"S1": "RM2"}.get(s),
			item_exists=lambda c: c in self.ITEMS, stock_uom_of=lambda c: self.ITEMS.get(c))

	def test_plan_sums_kg_and_maps_rows(self):
		product, total, rows = self.plan({"name": "F", "product_sku": "FG", "mix_input_lines": [
			{"item_code": "RM1", "kg": 600}, {"batch_amb_sublot": "S1", "kg": 400}]})
		self.assertEqual((product, total), ("FG", 1000))
		self.assertEqual([(i, kg) for i, kg, _x in rows], [("RM1", 600), ("RM2", 400)])

	def _fails(self, formula):
		# outside a site frappe.throw cannot log: stand it in with a plain raise of the message
		def throw(msg, *a, **k):
			raise frappe.ValidationError(msg)
		# ... and _() (translation) needs the site cache: identity here
		with mock.patch("amb_w_tds.formulation.release.frappe.throw", side_effect=throw), \
				mock.patch("amb_w_tds.formulation.release._", side_effect=lambda m: m):
			with self.assertRaises(frappe.ValidationError) as ctx:
				self.plan(formula)
		return str(ctx.exception)

	def test_unresolvable_line_fails_the_whole_release(self):
		msg = self._fails({"name": "F", "product_sku": "FG", "mix_input_lines": [
			{"item_code": "RM1", "kg": 600}, {"cunete_ref": "C-X", "kg": 400}]})
		self.assertIn("línea 2", msg)

	def test_zero_kg_and_unknown_item_and_product_uom(self):
		self.assertIn("mayor que 0", self._fails({"name": "F", "product_sku": "FG", "mix_input_lines": [{"item_code": "RM1", "kg": 0}]}))
		self.assertIn("no existe", self._fails({"name": "F", "product_sku": "FG", "mix_input_lines": [{"item_code": "NOPE", "kg": 1}]}))
		self.assertIn("unidad de stock", self._fails({"name": "F", "product_sku": "FG-NOS", "mix_input_lines": [{"item_code": "RM1", "kg": 1}]}))
		self.assertIn("Mix Input", self._fails({"name": "F", "product_sku": "FG", "mix_input_lines": []}))


if __name__ == "__main__":
	unittest.main()
