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


class TestBatchStepIsGone(unittest.TestCase):
	"""TASKS-384 B3 removed what this file pinned since 13.12.1: `update_batch_status` of COA AMB2, a guarded no-op
	(the lot's link refused a COA AMB2 name, so it only left a note), with `_batch_link_holds_this_doctype` and
	`BATCH_COA_FIELD`. The lot is now written when the certificate becomes Approved, by amb_w_spc; see
	tests/test_release_at_approved_b3.py. The eleven tests of the removed step went with it."""

	def test_the_controller_has_no_batch_step_and_writes_no_lot_field(self):
		import inspect

		from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2

		for name in ("update_batch_status", "_batch_link_holds_this_doctype", "BATCH_COA_FIELD"):
			self.assertFalse(hasattr(coa_amb2.COAAMB2, name), name)
		src = inspect.getsource(coa_amb2)
		self.assertNotIn(NOTE, src)
		for gone in ("batch.save(", "batch.quality_status", "coa_generated", "batch.last_coa_date"):
			self.assertNotIn(gone, src, gone)


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
