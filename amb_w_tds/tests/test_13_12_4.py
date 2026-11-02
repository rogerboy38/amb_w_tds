"""13.12.4 (TASKS-266), DB-free: C18 dead calls gone; the TDS Version client script never writes TDS Settings and
Generate Version writes custom_version; the two production-only DocTypes stay out of the fixture export filter."""

import importlib.util
import json
import os
import re
import unittest

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TDS_JS = os.path.join(
	PKG, "amb_w_tds", "doctype", "tds_product_specification", "tds_product_specification.js"
)
CLIENT_SCRIPTS = os.path.join(PKG, "fixtures", "client_script.json")
HOOKS = os.path.join(PKG, "hooks.py")
CALL_TO = re.compile(r"""method:\s*['"]([\w.]+)['"]""")


def read(path):
	with open(path, encoding="utf-8") as f:
		return f.read()


def hooks_module():
	spec = importlib.util.spec_from_file_location("amb_w_tds_hooks_under_test", HOOKS)
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


class TestC18DeadCallsRemoved(unittest.TestCase):
	def test_no_call_goes_to_your_app(self):
		for root, _dirs, files in os.walk(PKG):
			for fn in files:
				if fn.endswith(".js") and "node_modules" not in root:
					src = read(os.path.join(root, fn))
					targets = [m for m in CALL_TO.findall(src) if m.startswith("your_app")]
					self.assertEqual(targets, [], f"{fn} still calls {targets}")

	def test_the_four_dead_functions_and_two_buttons_are_gone(self):
		src = TDS_JS and read(TDS_JS)
		for name in (
			"fetch_item_details",
			"fetch_latest_tds_version",
			"create_new_tds_version",
			"copy_from_latest_version",
		):
			self.assertNotRegex(src, r"function\s+" + name + r"\(")
			self.assertNotRegex(src, r"^\s*" + name + r"\(frm\);", msg=name)
		self.assertNotIn("__('Create New Version')", src)
		self.assertNotIn("__('Copy from Latest')", src)
		# what stays: the inspection-template and COA buttons, the naming-series rewrite rule
		self.assertIn("__('Create Inspection Template')", src)
		self.assertIn("__('Generate COA AMB')", src)
		self.assertIn("function update_naming_series(frm)", src)
		self.assertIn("frm.doc.naming_series.startsWith(base_name)", src)


class TestTdsVersionClientScript(unittest.TestCase):
	def setUp(self):
		with open(CLIENT_SCRIPTS, encoding="utf-8") as f:
			rows = [c for c in json.load(f) if c["name"] == "TDS Version"]
		self.assertEqual(len(rows), 1)
		self.row = rows[0]
		self.src = self.row["script"]

	def test_it_is_the_tds_form_script_and_enabled(self):
		self.assertEqual(
			(self.row["dt"], self.row["view"], self.row["enabled"]), ("TDS Product Specification", "Form", 1)
		)

	def test_it_never_writes_tds_settings(self):
		calls = CALL_TO.findall(self.src)
		for c in calls:
			self.assertNotIn(
				c,
				(
					"frappe.client.insert",
					"frappe.client.set_value",
					"frappe.client.save",
					"frappe.client.submit",
				),
				c,
			)
		self.assertNotRegex(self.src, r"doctype:\s*['\"]TDS Settings['\"]")

	def test_generate_version_writes_custom_version(self):
		body = self.src[self.src.index("function generate_version(frm)") :]
		body = body[: body.index("\r\n}") if "\r\n}" in body else body.index("\n}")]
		self.assertIn("frm.set_value('custom_version', version)", body)
		self.assertIn("frm.set_value('tds_version', version)", body)
		self.assertIn("V1.${frm.doc.item_code}-Date:", self.src)

	def test_sequence_suggestion_reads_tds_records_only(self):
		body = self.src[self.src.index("function suggest_sequence(frm)") :]
		self.assertIn("frappe.db.get_list('TDS Product Specification'", body[:600])
		self.assertIn("if (frm.doc.tds_sequence) return;", body[:900])


class TestProductionOnlyDoctypesStayOutOfExport(unittest.TestCase):
	def test_filter_lists(self):
		h = hooks_module()
		self.assertEqual(
			sorted(h._PRODUCTION_ONLY_DOCTYPES), ["AMB Cost Factors", "Quotation Item Escalated"]
		)
		for dt in h._PRODUCTION_ONLY_DOCTYPES:
			self.assertNotIn(dt, h._AMB_W_TDS_DOCTYPES)
			for entry in h.fixtures:
				if isinstance(entry, dict):
					for flt in list(entry.get("filters") or []) + list(entry.get("or_filters") or []):
						vals = flt[2] if len(flt) > 2 else None
						self.assertFalse(
							isinstance(vals, list | tuple) and dt in vals,
							f"{dt} in a filter of {entry.get('doctype')}",
						)

	def test_wording_names_gunicorn_not_nginx(self):
		for path in (
			os.path.join(PKG, "public", "js", "phase_1c_tab_v2.js"),
			os.path.join(PKG, "..", "CHANGELOG.md"),
			os.path.join(PKG, "..", "README.md"),
		):
			src = read(path)
			self.assertNotRegex(src, r"nginx on prod answers|prod nginx returned", os.path.basename(path))
			self.assertIn("limit_request_line", src, os.path.basename(path))


if __name__ == "__main__":
	unittest.main()
