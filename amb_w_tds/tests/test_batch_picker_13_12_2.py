"""13.12.2: the one Batch Reference picker and the BOM Formula gate that counts only COA AMB at step 3. DB-free."""

import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import frappe  # noqa: E402

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCTYPES = os.path.join(PKG, "amb_w_tds", "doctype")
QUERY = "amb_w_tds.amb_w_tds.api.batch_picker.search_batches"
PICKER = "amb_w_tds.amb_w_tds.api.batch_picker"


class TestPickerTerms(unittest.TestCase):
	def search(self, txt="", rows=(), **kw):
		from amb_w_tds.amb_w_tds.api import batch_picker
		get_list = mock.Mock(return_value=[frappe._dict(r) for r in rows])
		with mock.patch.object(frappe, "get_list", get_list):
			out = batch_picker.search_batches("Batch AMB", txt, "name", **kw)
		return out, get_list

	def test_the_terms_are_pinned(self):
		from amb_w_tds.amb_w_tds.api import batch_picker
		self.assertEqual(batch_picker.picker_filters(), [
			["Batch AMB", "batch_status", "!=", "Cancelled"],
			["Batch AMB", "quality_status", "in", ["Pending", "Hold", ""]],
		])

	def test_no_item_filter_and_no_docstatus_term(self):
		from amb_w_tds.amb_w_tds.api import batch_picker
		text = repr(batch_picker.picker_filters())
		self.assertNotIn("item_to_manufacture", text)
		self.assertNotIn("docstatus", text)

	def test_no_text_means_no_or_filters_and_a_page(self):
		out, get_list = self.search(start=20, page_len=10)
		kw = get_list.call_args.kwargs
		self.assertIsNone(kw["or_filters"])
		self.assertEqual((kw["start"], kw["page_length"]), (20, 10))
		self.assertEqual(kw["order_by"], "creation desc, name desc")
		self.assertEqual(get_list.call_args.args, ("Batch AMB",))
		self.assertEqual(out, [])

	def test_text_searches_name_title_golden_and_item(self):
		out, get_list = self.search("abc")
		fields = [f[1] for f in get_list.call_args.kwargs["or_filters"]]
		self.assertEqual(fields, ["name", "title", "custom_golden_number", "item_to_manufacture"])
		self.assertTrue(all(f[2:] == ["like", "%abc%"] for f in get_list.call_args.kwargs["or_filters"]))

	def test_each_line_shows_batch_item_and_both_statuses(self):
		out, _ = self.search(rows=[
			dict(name="B1", item_to_manufacture="I1", quality_status="Pending", batch_status="Draft"),
			dict(name="B2", item_to_manufacture=None, quality_status=None, batch_status="In Progress"),
		])
		self.assertEqual(out, [("B1", "I1", "Pending / Draft"), ("B2", "-", "- / In Progress")])


class TestBothFormsUseIt(unittest.TestCase):
	def block(self, doctype):
		with open(os.path.join(DOCTYPES, doctype, doctype + ".js"), encoding="utf8") as f:
			text = f.read()
		start = text.index("frm.set_query('batch_reference'")
		return text[start:text.index("});", start) + 3]

	def test_both_call_the_shared_query_and_carry_no_filter_of_their_own(self):
		for dt in ("coa_amb", "coa_amb2"):
			block = self.block(dt)
			self.assertIn(QUERY, block, dt)
			for word in ("filters", "docstatus", "item_to_manufacture", "product_item"):
				self.assertNotIn(word, block, f"{dt} carries its own '{word}'")

	def test_the_query_is_whitelisted_and_exists(self):
		from amb_w_tds.amb_w_tds.api import batch_picker
		self.assertIn(batch_picker.search_batches, frappe.whitelisted)

	def test_only_one_batch_reference_query_per_form(self):
		for dt in ("coa_amb", "coa_amb2"):
			with open(os.path.join(DOCTYPES, dt, dt + ".js"), encoding="utf8") as f:
				text = f.read()
			self.assertEqual(len(re.findall(r"set_query\('batch_reference'", text)), 1, dt)


class TestGateStep3CountsOnlyCoaAmb(unittest.TestCase):
	"""`_resolve_coa` with the lookups mocked; the same four cases under both values of default_coa_source."""

	def resolve(self, setting, rows, line=None):
		from amb_w_tds.amb_w_tds.doctype.bom_formula import bom_formula as m
		doc = object.__new__(m.BOMFormula)
		line = frappe._dict(line or dict(batch_amb_sublot="LOT-A", source_coa_amb2=None, source_coa_doctype=None))
		asked = []

		def get_all(dt, filters=None, fields=None):
			asked.append(dt)
			return rows.get(dt, [])

		db = mock.Mock(get_value=lambda dt, name, field: None, get_single_value=mock.Mock(return_value=setting))
		with mock.patch.object(m, "_batch_root", lambda b: b), mock.patch.object(frappe, "db", db), \
				mock.patch.object(frappe, "get_all", get_all):
			out = doc._resolve_coa(line)
		db.get_single_value.assert_not_called()  # nothing reads default_coa_source
		return out, asked

	def each_setting(self, rows, line=None):
		results = [self.resolve(s, rows, line) for s in ("COA AMB", "COA AMB2")]
		self.assertEqual(results[0], results[1], "the result depends on default_coa_source")
		return results[0]

	def test_a_submitted_coa_amb2_of_another_product_is_ignored(self):
		(dt, name, res, _), asked = self.each_setting({"COA AMB2": [frappe._dict(name="C2-OTHER", creation=2)]})
		self.assertEqual((dt, name, res), (None, None, "none"))
		self.assertNotIn("COA AMB2", asked)

	def test_a_submitted_coa_amb2_of_the_same_product_is_not_a_step_3_candidate(self):
		(dt, name, res, _), _ = self.each_setting({"COA AMB2": [frappe._dict(name="C2-SAME", creation=2)]})
		self.assertEqual((dt, name, res), (None, None, "none"))

	def test_the_same_coa_amb2_resolves_through_the_explicit_line_link(self):
		line = dict(batch_amb_sublot="LOT-A", source_coa_amb2="C2-SAME", source_coa_doctype="COA AMB2")
		(dt, name, res, _), _ = self.each_setting({"COA AMB2": [frappe._dict(name="C2-SAME", creation=2)]}, line)
		self.assertEqual((dt, name, res), ("COA AMB2", "C2-SAME", "explicit"))

	def test_a_newer_wrong_coa_amb2_does_not_beat_an_older_correct_coa_amb(self):
		rows = {"COA AMB": [frappe._dict(name="C-RIGHT", creation=1)], "COA AMB2": [frappe._dict(name="C2-WRONG", creation=2)]}
		(dt, name, res, detail), _ = self.each_setting(rows)
		self.assertEqual((dt, name, res), ("COA AMB", "C-RIGHT", "golden_match"))
		self.assertNotIn("candidates", detail)

	def test_a_submitted_coa_amb_linked_to_the_batch_counts_as_before(self):
		(dt, name, res, _), asked = self.each_setting({"COA AMB": [frappe._dict(name="C-ONE", creation=1)]})
		self.assertEqual((dt, name, res), ("COA AMB", "C-ONE", "golden_match"))
		self.assertEqual(asked, ["COA AMB"])

	def test_two_coa_amb_still_pick_the_newest_and_name_the_runner_up(self):
		rows = {"COA AMB": [frappe._dict(name="C-OLD", creation=1), frappe._dict(name="C-NEW", creation=3)]}
		(dt, name, res, detail), _ = self.each_setting(rows)
		self.assertEqual((name, res), ("C-NEW", "golden_match"))
		self.assertIn("runner-up C-OLD", detail)


if __name__ == "__main__":
	unittest.main()
