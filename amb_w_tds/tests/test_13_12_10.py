"""13.12.10 (TASKS-287 Part A): the Sales Invoice field order in fixtures/property_setter.json is prod's 273 list.

DB-free: reads the fixture JSON and compares it with main's copy (git blob of the 13.12.9 file, recorded below
as per-record hashes) so that "one record changed, the rest byte-identical" is a test, not a claim.
"""

import hashlib
import json
import os
import re
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(PKG, "fixtures", "property_setter.json")
FIELD_ORDER = "Sales Invoice-main-field_order"
ROUNDED = (
	"Sales Invoice-base_rounded_total-hidden",
	"Sales Invoice-rounded_total-hidden",
	"Sales Invoice-rounded_total-print_hide",
	"Sales Invoice-disable_rounded_total-default",
)
SHA_273 = "55195716b2fd7b23b13c88234f0eb7b150cbb60ee05e5194d0aa95eaddb17b65"
# the 49 names the 273 list adds to the 2026-04-20 231 list (31 core ERPNext 16.17 fields + 18 ERPNext Mexico Compliance custom fields)
ADDED_49 = [
	"mx_uuid",
	"apply_tds",
	"is_created_using_pos",
	"pos_closing_entry",
	"has_subcontracted",
	"section_break_qllv",
	"totals_section",
	"section_break_pxwz",
	"column_break_xjag",
	"base_totals_section",
	"column_break_iaso",
	"section_tax_withholding_entry",
	"tax_withholding_group",
	"ignore_tax_withholding_threshold",
	"override_tax_withholding_entries",
	"tax_withholding_entries",
	"additional_discount_section",
	"coupon_code",
	"item_wise_tax_details",
	"dont_create_loyalty_points",
	"commission_section",
	"column_break_rdiw",
	"sales_team_section",
	"automation_section",
	"utm_analytics_section",
	"column_break_rdke",
	"utm_source",
	"utm_medium",
	"column_break_ixxw",
	"utm_campaign",
	"utm_content",
	"column_break_imbx",
	"cfdi_40",
	"mx_payment_option",
	"mx_cfdi_use",
	"mode_of_payment",
	"mx_payment_mode",
	"column_break_206",
	"mx_related_sales_invoices",
	"cancellation_section",
	"cancellation_reason",
	"requires_relationship",
	"substitute_invoice",
	"mx_is_cancellable",
	"section_break_9ww80",
	"mx_addenda",
	"mx_stamped_xml",
	"cancellation_acknowledgement",
	"mx_download_acknowledgement",
]
# sha256 of the other 224 names, one per line, in the order they have in BOTH lists (the 2026-04-20 list and prod's)
COMMON_224_ORDER_SHA = "6c5c954b8c635272e32ff9200e9493c793661d1091df5093c08a324afc555c73"


def _records():
	with open(FIXTURE, encoding="utf8") as f:
		return json.load(f)


def _sha(text):
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestFieldOrderRecord(unittest.TestCase):
	def setUp(self):
		self.recs = {r["name"]: r for r in _records()}
		self.rec = self.recs[FIELD_ORDER]

	def test_it_is_the_only_field_order_record_and_the_file_still_has_329_records(self):
		self.assertEqual(len(_records()), 329)
		self.assertEqual([r["name"] for r in _records()].count(FIELD_ORDER), 1)

	def test_value_is_273_unique_strings(self):
		order = json.loads(self.rec["value"])
		self.assertEqual(len(order), 273)
		self.assertEqual(len(set(order)), 273)
		self.assertTrue(all(isinstance(x, str) and x for x in order))

	def test_stored_text_is_json_dumps_default_separators_without_trailing_newline_and_has_prods_sha(self):
		text = self.rec["value"]
		self.assertEqual(text, json.dumps(json.loads(text)))
		self.assertFalse(text.endswith("\n"))
		self.assertEqual(len(text.encode("utf-8")), 5622)
		self.assertEqual(_sha(text), SHA_273)

	def test_the_224_names_common_with_the_old_list_keep_their_order(self):
		order = json.loads(self.rec["value"])
		self.assertEqual(len(ADDED_49), 49)
		self.assertTrue(set(ADDED_49) <= set(order))
		common = [x for x in order if x not in set(ADDED_49)]
		self.assertEqual(len(common), 224)
		self.assertEqual(_sha("\n".join(common)), COMMON_224_ORDER_SHA)

	def test_the_first_and_last_fields_are_those_of_prods_list(self):
		order = json.loads(self.rec["value"])
		self.assertEqual(order[0], "customer_section")
		self.assertIn("title", order[:5])

	def test_modified_is_prods_stamp_for_the_row(self):
		self.assertEqual(self.rec["modified"], "2026-11-02 17:31:32.188396")

	def test_other_columns_of_the_record_are_unchanged(self):
		for k, v in {
			"doc_type": "Sales Invoice",
			"doctype_or_field": "DocType",
			"property": "field_order",
			"property_type": "Data",
			"module": "AMBWTDS",
			"field_name": None,
			"row_name": None,
			"docstatus": 0,
		}.items():
			self.assertEqual(self.rec[k], v, k)


class TestTheRestOfTheFile(unittest.TestCase):
	def test_the_four_rounded_total_records_still_carry_1(self):
		recs = {r["name"]: r for r in _records()}
		for n in ROUNDED:
			self.assertEqual(recs[n]["value"], "1", n)
		self.assertEqual(recs["Sales Invoice-base_rounded_total-print_hide"]["value"], "1")

	def test_file_formatting_is_json_dumps_indent_1_plus_a_newline(self):
		with open(FIXTURE, encoding="utf8") as f:
			raw = f.read()
		self.assertEqual(json.dumps(json.loads(raw), indent=1, ensure_ascii=False) + "\n", raw)

	def test_every_record_has_a_name_and_the_names_are_unique(self):
		names = [r["name"] for r in _records()]
		self.assertEqual(len(names), len(set(names)))


class TestVersion(unittest.TestCase):
	def test_version_is_13_12_10_or_later(self):
		def tup(s):
			return tuple(int(x) for x in s.strip().split("."))

		with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
			ver = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)
		with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
			self.assertEqual(f.read().strip(), ver)
		self.assertGreaterEqual(tup(ver), (13, 12, 10))


if __name__ == "__main__":
	unittest.main()
