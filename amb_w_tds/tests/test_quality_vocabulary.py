"""TASKS-384 B1, DB-free: the one vocabulary of the quality release chain, and the test that fails when a list drifts.

This app's lists are compared with the option lists of this app's own DocTypes, and with amb_w_spc's module when that
app can be imported (it is skipped, and says so, when it cannot)."""

import importlib
import json
import os
import unittest

from amb_w_tds import quality_vocabulary as voc

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NAMES = ("LOT_STATUSES", "CERTIFICATE_RESULTS", "RESULT_TO_LOT_STATUS", "STATUS_SOURCES")


def _options(doctype, fieldname):
	path = os.path.join(PKG, "amb_w_tds", "doctype", doctype, doctype + ".json")
	with open(path, encoding="utf-8") as f:
		(field,) = [d for d in json.load(f)["fields"] if d["fieldname"] == fieldname]
	return field["options"].split("\n")


class TestVocabulary(unittest.TestCase):
	def test_the_values_of_decisions_303_and_315(self):
		self.assertEqual(list(voc.LOT_STATUSES), ["Pending", "Passed", "Failed", "Hold"])
		self.assertEqual(list(voc.CERTIFICATE_RESULTS), ["Pending", "Pass", "Fail", "Partial", "No Tests"])
		self.assertEqual(
			dict(voc.RESULT_TO_LOT_STATUS), {"Pass": "Passed", "Fail": "Failed", "Partial": "Hold"}
		)
		self.assertEqual(list(voc.STATUS_SOURCES), ["", "Own certificate", "Inherited", "Hold action"])

	def test_the_result_list_is_the_option_list_of_both_certificates(self):
		for doctype in ("coa_amb", "coa_amb2"):
			self.assertEqual(_options(doctype, "overall_result"), list(voc.CERTIFICATE_RESULTS), doctype)

	def test_the_map_speaks_only_of_known_results_and_known_statuses(self):
		self.assertLessEqual(set(voc.RESULT_TO_LOT_STATUS), set(voc.CERTIFICATE_RESULTS))
		self.assertLessEqual(set(voc.RESULT_TO_LOT_STATUS.values()), set(voc.LOT_STATUSES))
		# a certificate with one of these two results cannot be approved, so neither has a lot status
		for result in ("Pending", "No Tests"):
			self.assertNotIn(result, voc.RESULT_TO_LOT_STATUS)

	def test_the_lot_picker_speaks_the_same_lot_statuses(self):
		from amb_w_tds.amb_w_tds.api import batch_picker

		self.assertLessEqual({s for s in batch_picker.QUALITY_STATUSES if s}, set(voc.LOT_STATUSES))

	def test_the_other_app_carries_the_same_four_lists(self):
		try:
			spc = importlib.import_module("amb_w_spc.sfc_manufacturing.lot_quality")
		except ImportError as e:
			self.skipTest(f"amb_w_spc cannot be imported here ({e}); its own test compares from that side")
		for name in NAMES:
			mine, theirs = getattr(voc, name), getattr(spc, name)
			if isinstance(mine, dict):
				self.assertEqual(dict(theirs), mine, name)
			else:
				self.assertEqual(list(theirs), list(mine), name)

	def test_nothing_of_the_other_app_is_imported_by_this_module(self):
		with open(voc.__file__, encoding="utf-8") as f:
			code = [
				line for line in f.read().split('"""', 2)[2].splitlines() if not line.lstrip().startswith("#")
			]
		self.assertNotIn("import", "\n".join(code))


if __name__ == "__main__":
	unittest.main()
