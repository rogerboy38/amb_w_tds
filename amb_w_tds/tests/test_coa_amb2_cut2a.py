"""13.12.1 COA AMB2 Cut 2a: the batch step of a submit, and the wording of the six permission rows. DB-free."""

import json
import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import frappe  # noqa: E402

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(PKG, ".."))
MOD = "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2"
NOTE = "Batch not updated: link to COA AMB2 not available yet"


class Batch:
	"""A stand-in Batch AMB that remembers what was assigned (a Mock would invent attributes)."""

	def __init__(self):
		self.__dict__["assigned"] = {}
		self.save = mock.Mock()
		self.add_comment = mock.Mock()

	def __setattr__(self, k, v):
		if k not in ("save", "add_comment"):
			self.__dict__["assigned"][k] = v
		object.__setattr__(self, k, v)


def _meta(options, fieldtype="Link"):
	field = frappe._dict(fieldtype=fieldtype, options=options) if options is not None else None
	return mock.Mock(get_field=lambda name: field if name == "coa_reference" else None)


class TestBatchStep(unittest.TestCase):
	def doc(self, batch_reference="LOTE-1"):
		from amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2 import COAAMB2
		d = object.__new__(COAAMB2)
		d.__dict__.update(doctype="COA AMB2", name="COA2-26-0001", batch_reference=batch_reference, overall_result="Pass",
			approval_date="2026-10-25", approved_by=None)
		d.add_comment = mock.Mock()
		return d

	def run_step(self, options, status=None, batch=None, fieldtype="Link", get_doc_effect=None):
		batch = batch or Batch()
		get_doc = mock.Mock(return_value=batch, side_effect=get_doc_effect)
		log_error = mock.Mock()
		d = self.doc()
		with mock.patch("frappe.get_meta", lambda dt: _meta(options, fieldtype)), mock.patch("frappe.get_doc", get_doc), \
				mock.patch("frappe.log_error", log_error), mock.patch(MOD + ".nowdate", lambda: "2026-10-25"):
			d.update_batch_status(status)
		return d, batch, get_doc, log_error

	# --- skip when the Link points elsewhere ---
	def test_a_link_to_coa_amb_means_no_write_one_note_no_error(self):
		d, batch, get_doc, log_error = self.run_step("COA AMB")
		get_doc.assert_not_called()
		batch.save.assert_not_called()
		log_error.assert_not_called()
		d.add_comment.assert_called_once_with("Info", NOTE)

	def test_a_missing_field_or_another_field_type_is_skipped_the_same_way(self):
		for options, fieldtype in ((None, "Link"), ("COA AMB2", "Data"), ("COA AMB2", "Dynamic Link")):
			d, batch, get_doc, log_error = self.run_step(options, fieldtype=fieldtype)
			get_doc.assert_not_called()
			log_error.assert_not_called()
			d.add_comment.assert_called_once_with("Info", NOTE)

	# --- write when the Link points to COA AMB2 (a stub meta: no schema change anywhere) ---
	def test_a_link_to_coa_amb2_writes_the_reference_and_never_quality_status(self):
		d, batch, get_doc, log_error = self.run_step("COA AMB2")
		get_doc.assert_called_once_with("Batch AMB", "LOTE-1")
		self.assertEqual(batch.assigned, {"coa_generated": 1, "coa_reference": "COA2-26-0001", "last_coa_date": "2026-10-25"})
		self.assertNotIn("quality_status", batch.assigned, "'Pass' is not an option of quality_status and nobody chose a mapping")
		batch.save.assert_called_once_with(ignore_permissions=True)
		log_error.assert_not_called()
		d.add_comment.assert_not_called()

	# --- a real failure of the step is still logged ---
	def test_a_real_failure_still_reaches_log_error(self):
		d, batch, get_doc, log_error = self.run_step("COA AMB2", get_doc_effect=RuntimeError("boom"))
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.args[1], "COA AMB2 - Batch Update")
		self.assertIn("boom", log_error.call_args.args[0])

	def test_a_failing_save_is_logged_too(self):
		b = Batch()
		b.save.side_effect = frappe.ValidationError("refused")
		d, batch, get_doc, log_error = self.run_step("COA AMB2", batch=b)
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.args[1], "COA AMB2 - Batch Update")

	# --- what does not change ---
	def test_no_batch_reference_touches_nothing(self):
		from amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2 import COAAMB2
		d = self.doc(batch_reference=None)
		get_meta = mock.Mock()
		with mock.patch("frappe.get_meta", get_meta), mock.patch("frappe.get_doc", mock.Mock()) as get_doc:
			d.update_batch_status()
		get_meta.assert_not_called()
		get_doc.assert_not_called()
		d.add_comment.assert_not_called()

	def test_the_cancel_path_is_unchanged(self):
		d, batch, get_doc, log_error = self.run_step("COA AMB", status="COA Cancelled")
		get_doc.assert_called_once()
		self.assertEqual(batch.assigned, {"quality_status": "COA Cancelled"})
		batch.add_comment.assert_called_once_with("Info", "COA Status: COA Cancelled - COA2-26-0001")
		batch.save.assert_called_once_with(ignore_permissions=True)
		d.add_comment.assert_not_called()


class TestWordingMatchesRows(unittest.TestCase):
	FLAGS = ["read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "print", "email", "share"]
	OTHER = ["select", "import", "mask", "impersonate", "if_owner", "permlevel"]

	def docs_table(self, path="docs/coa-amb2-cut1.md"):
		text = open(os.path.join(REPO, path), encoding="utf8").read()
		sec = text.split("## The six rows shipped", 1)[1].split("\n#", 1)[0]
		rows = [l.strip().strip("|").split("|") for l in sec.splitlines() if l.strip().startswith("|")]
		head = [c.strip() for c in rows[0]]
		self.assertEqual(head, ["role"] + self.FLAGS)
		return {r[0].strip(): {f: int(v) for f, v in zip(self.FLAGS, [c.strip() for c in r[1:]])} for r in rows[2:]}

	def fixture_rows(self):
		with open(os.path.join(PKG, "fixtures", "custom_docperm.json"), encoding="utf8") as f:
			return {r["role"]: r for r in json.load(f) if r["parent"] == "COA AMB2"}

	def test_the_docs_table_equals_the_six_fixture_rows(self):
		docs, rows = self.docs_table(), self.fixture_rows()
		self.assertEqual(sorted(docs), sorted(rows))
		self.assertEqual(len(docs), 6)
		for role, flags in docs.items():
			self.assertEqual({f: int(rows[role][f]) for f in self.FLAGS}, flags, role)
			for f in self.OTHER:
				self.assertEqual(int(rows[role][f]), 0, f"{role}.{f}")

	def test_the_table_says_what_the_changelog_says(self):
		docs = self.docs_table()
		self.assertEqual({f for f, v in docs["Quality Engineer"].items() if v}, {"read", "write", "create", "report", "print"})
		self.assertEqual({f for f, v in docs["Quality User"].items() if v},
			{"read", "write", "create", "delete", "submit", "report", "export", "print", "email", "share"})
		self.assertEqual(sum(docs["RND Manager"].values()), 12)
		for role in ("Manufacturing User", "Sales Manager CRM", "Stock User"):
			self.assertEqual({f for f, v in docs[role].items() if v}, {"read", "report", "export", "print", "email", "share"})

	def test_the_changelog_names_each_row_with_its_flags(self):
		text = open(os.path.join(REPO, "CHANGELOG.md"), encoding="utf8").read().split("## 13.12.0", 1)[1].split("\n## 13.11", 1)[0]
		for needle in ("**Quality Engineer** read / write / create / report / print",
				"**Quality User** read / write / create / delete / submit / report / export / print / email / share",
				"**RND Manager** all twelve",
				"**Manufacturing User**, **Sales Manager CRM** and **Stock User** read / report / export / print / email / share"):
			self.assertIn(needle, text)


if __name__ == "__main__":
	unittest.main()
