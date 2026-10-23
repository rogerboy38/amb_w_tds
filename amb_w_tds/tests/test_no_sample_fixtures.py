"""13.11.3: the app ships NO BOM Formula data rows as fixtures, so a fresh install/migrate creates no demo
formulas. DB-free: reads the fixtures folder and hooks.py as files."""

import glob
import json
import os
import unittest

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES = os.path.join(APP, "fixtures")
SAMPLE_PREFIXES = ("FMIX-", "MEMCAL-")


def fixture_records():
	for path in sorted(glob.glob(os.path.join(FIXTURES, "*.json"))):
		with open(path, encoding="utf-8") as f:
			data = json.load(f)
		for rec in data if isinstance(data, list) else [data]:
			if isinstance(rec, dict):
				yield os.path.basename(path), rec


class TestNoSampleFormulaFixtures(unittest.TestCase):
	def test_bom_formula_fixture_file_is_gone(self):
		# Frappe imports EVERY fixtures/*.json regardless of hooks, so the file itself must not exist
		self.assertFalse(os.path.exists(os.path.join(FIXTURES, "bom_formula.json")))

	def test_no_fixture_file_carries_bom_formula_rows(self):
		rows = [(fname, rec.get("name")) for fname, rec in fixture_records() if rec.get("doctype") == "BOM Formula"]
		self.assertEqual(rows, [])

	def test_no_fixture_record_is_a_sample_formula(self):
		names = [(fname, rec.get("name")) for fname, rec in fixture_records()
			if str(rec.get("name", "")).startswith(SAMPLE_PREFIXES)]
		self.assertEqual(names, [])

	def test_hooks_do_not_export_bom_formula_as_a_fixture(self):
		ns = {}
		with open(os.path.join(APP, "hooks.py"), encoding="utf-8") as f:
			exec(compile(f.read(), "hooks.py", "exec"), ns)  # hooks.py has no imports; plain assignments
		doctypes = [fx.get("doctype") or fx.get("dt") if isinstance(fx, dict) else fx for fx in ns["fixtures"]]
		self.assertNotIn("BOM Formula", doctypes)

	def test_real_fixture_machinery_still_ships(self):
		files = {os.path.basename(p) for p in glob.glob(os.path.join(FIXTURES, "*.json"))}
		for keep in ("custom_field.json", "custom_docperm.json", "workflow.json", "workflow_state.json",
				"workflow_action_master.json", "mixing_equipment.json", "print_format.json"):
			self.assertIn(keep, files)
		self.assertTrue(any(rec.get("document_type") == "BOM Formula" for fname, rec in fixture_records() if fname == "workflow.json"))


if __name__ == "__main__":
	unittest.main()
