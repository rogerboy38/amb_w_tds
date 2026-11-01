"""13.12.3: the TDS Parameter Selection picker's Customer-Specific Specification lookup is a POST that does not
carry the parameter catalog in the request. DB-free: reads the form script as text."""

import os
import re
import unittest

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(PKG, "public", "js", "phase_1c_tab_v2.js")


def function_body(src, name):
	"""The text of `async function <name>(...) { ... }` up to the next top-level function."""
	start = src.index(f"async function {name}(")
	nxt = re.search(r"\n(async )?function \w+\(", src[start + 1 :])
	return src[start : start + 1 + nxt.start()] if nxt else src[start:]


class TestCssLookupIsAPost(unittest.TestCase):
	def setUp(self):
		with open(SCRIPT, encoding="utf-8") as f:
			self.src = f.read()
		self.load_path = function_body(self.src, "sc5v2_fetchCAVMap")

	def test_the_load_path_lookup_goes_through_frappe_call(self):
		# frappe.db.get_list is a GET with the filters in the query string (frappe/public/js/frappe/db.js);
		# frappe.call without a type is a POST with the args in the body.
		self.assertNotIn("frappe.db.get_list", self.load_path)
		self.assertIn("frappe.call(", self.load_path)
		self.assertIn("method: 'frappe.client.get_list'", self.load_path)
		self.assertNotIn("type: 'GET'", self.load_path)
		self.assertNotIn('type: "GET"', self.load_path)

	def test_the_catalog_is_not_sent_as_a_filter(self):
		# the request asks for the customers' rows only; the catalog match is done in the browser
		self.assertNotRegex(self.load_path, r"parameter:\s*\[\s*['\"]in['\"]")
		self.assertRegex(self.load_path, r"customer:\s*\[\s*'in',\s*customers\s*\]")
		self.assertIn("status: 'Approved'", self.load_path)
		self.assertIn("is_active: 1", self.load_path)
		self.assertIn("new Set(qipNames)", self.load_path)

	def test_same_fields_and_no_page_limit(self):
		for field in ("name", "parameter", "customer", "value_type", "value_text", "value_min", "value_max",
		              "method", "unit_of_measurement", "regulatory_reference", "effective_from", "effective_to"):
			self.assertIn(f"'{field}'", self.load_path)
		self.assertIn("limit_page_length: 0", self.load_path)

	def test_the_lookup_still_filters_by_effective_dates(self):
		self.assertIn("effective_from > today", self.load_path)
		self.assertIn("effective_to < today", self.load_path)


if __name__ == "__main__":
	unittest.main()
