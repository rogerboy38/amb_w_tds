"""13.12.6 (TASKS-280c): COA AMB2's workflow ends at Quality's approval.

`submit_and_start_workflow` (COA AMB2) loses the Sales step: the two `Submit for Sales Approval` transitions,
the `Certificate Shared` state (docstatus 1) and, with it, the 13.12.4.1 `Cancel` transition and the `Cancelled`
state (docstatus 2) that only that state could reach. `Approved` stays docstatus 0 and is the final state; the
Reject paths stay; nothing else in the file moves. DB-free: the fixture JSON, the hooks filter and the Python
controller are read from the checkout.
"""

import json
import os
import re
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fixture(name):
	with open(os.path.join(PKG, "fixtures", name), encoding="utf8") as f:
		return json.load(f)


def _workflows():
	return {w["name"]: w for w in _fixture("workflow.json")}


class TestApprovedIsTheEnd(unittest.TestCase):
	def setUp(self):
		self.w = _workflows()["submit_and_start_workflow"]
		self.states = {s["state"]: s for s in self.w["states"]}
		self.transitions = self.w["transitions"]

	def test_every_state_is_docstatus_0(self):
		self.assertEqual({s["state"] for s in self.w["states"]},
			{"Draft", "Validated", "Pending Supervisor", "Approved", "Auto Approved", "Saved"})
		self.assertEqual({str(s["doc_status"]) for s in self.w["states"]}, {"0"})

	def test_the_only_way_out_of_approved_is_reject(self):
		out = [(t["action"], t["next_state"], t["allowed"]) for t in self.transitions if t["state"] == "Approved"]
		self.assertEqual(out, [("Reject", "Draft", "Quality Manager")])

	def test_approve_is_the_last_forward_transition_and_needs_a_second_person(self):
		approve = [t for t in self.transitions if t["action"] == "Approve"]
		self.assertEqual(len(approve), 1)
		t = approve[0]
		self.assertEqual((t["state"], t["next_state"], t["allowed"], int(t["allow_self_approval"])),
			("Pending Supervisor", "Approved", "Quality Manager", 0))

	def test_the_reject_paths_stay(self):
		rej = sorted((t["state"], t["next_state"], t["allowed"]) for t in self.transitions if t["action"] == "Reject")
		self.assertEqual(rej, [("Approved", "Draft", "Quality Manager"), ("Pending Supervisor", "Draft", "Quality Manager")])

	def test_every_transition_references_a_state_of_this_workflow(self):
		# Frappe's Workflow.validate_docstatus throws "{0} not a valid State" on a dangling row, and the fixture import
		# (import_file_by_path with data_import=True) runs validate — a dangling row would fail the migrate.
		for t in self.transitions:
			self.assertIn(t["state"], self.states, t)
			self.assertIn(t["next_state"], self.states, t)

	def test_no_transition_frappe_would_refuse(self):
		# Workflow.validate_docstatus: no row out of a docstatus-2 state, no 1 -> 0, no 0 -> 2
		for t in self.transitions:
			a, b = str(self.states[t["state"]]["doc_status"]), str(self.states[t["next_state"]]["doc_status"])
			self.assertNotEqual(a, "2", t)
			self.assertFalse(a == "1" and b == "0", t)
			self.assertFalse(a == "0" and b == "2", t)

	def test_allow_edit_per_state_as_left(self):
		# quoted in REPLY-TASKS-280c: anyone with the state's role may still change a result after Approve
		self.assertEqual({s["state"]: s["allow_edit"] for s in self.w["states"]},
			{"Draft": "All", "Validated": "Quality User", "Pending Supervisor": "Quality User",
			 "Approved": "Quality Manager", "Auto Approved": "Quality User", "Saved": "All"})

	def test_workflow_head_fields_unchanged(self):
		w = self.w
		self.assertEqual((w["document_type"], w["is_active"], w["workflow_state_field"], w["override_status"],
			w["send_email_alert"], w["enable_action_confirmation"]), ("COA AMB2", 1, "workflow_state", 0, 0, 0))


class TestNothingElseMoved(unittest.TestCase):
	def test_the_coa_amb_twin_still_has_its_sales_step_and_cancel(self):
		w = _workflows()["submit_and_start_workflow_1"]
		self.assertEqual(w["document_type"], "COA AMB")
		self.assertIn("Certificate Shared", {s["state"] for s in w["states"]})
		self.assertIn("Cancelled", {s["state"] for s in w["states"]})
		rows = [(t["state"], t["action"], t["next_state"]) for t in w["transitions"]]
		self.assertIn(("Approved", "Submit for Sales Approval", "Certificate Shared"), rows)
		self.assertIn(("Certificate Shared", "Cancel", "Cancelled"), rows)
		self.assertEqual((len(w["states"]), len(w["transitions"])), (8, 9))

	def test_the_tds_and_bom_formula_workflows_keep_their_row_counts(self):
		ws = _workflows()
		self.assertEqual((len(ws["TDS Approval Workflow"]["states"]), len(ws["TDS Approval Workflow"]["transitions"])), (8, 7))
		self.assertIn("Cancelled", {s["state"] for s in ws["TDS Approval Workflow"]["states"]})
		self.assertEqual(ws["BOM Formula Aprobación"]["document_type"], "BOM Formula")

	def test_the_masters_stay_in_the_fixture_and_in_the_hooks_filter(self):
		# other workflows still link them; the fixture never deletes, and a fresh tier still needs the rows
		states = {s["name"] for s in _fixture("workflow_state.json")}
		actions = {a["name"] for a in _fixture("workflow_action_master.json")}
		self.assertTrue({"Certificate Shared", "Cancelled", "Approved"} <= states)
		self.assertTrue({"Submit for Sales Approval", "Cancel", "Approve", "Reject"} <= actions)
		with open(os.path.join(PKG, "hooks.py"), encoding="utf8") as f:
			hooks = f.read()
		for name in ("Certificate Shared", "Cancelled", "Submit for Sales Approval", "Cancel"):
			self.assertIn('"%s"' % name, hooks)


class TestNoCodeRodeAlong(unittest.TestCase):
	def test_validate_numeric_result_still_throws_above_the_maximum(self):
		# the guard is untouched: an out-of-limit result is refused on SUBMIT, and nothing submits any more
		with open(os.path.join(PKG, "amb_w_tds", "doctype", "coa_amb2", "coa_amb2.py"), encoding="utf8") as f:
			src = f.read()
		self.assertIn("is above maximum value", src)
		self.assertIn("if self.docstatus == 0 and not self._is_submit_flow():", src)

	def test_bom_formula_reader_changed_only_in_13_12_7(self):
		# task (c) landed as 13.12.7 (TASKS-281): `_build_lots` now reads the measured number, `result` first,
		# through `_lot_value`; the 13.12.6 fixture change itself carried no code (see test_13_12_7).
		with open(os.path.join(PKG, "amb_w_tds", "doctype", "bom_formula", "bom_formula.py"), encoding="utf8") as f:
			src = f.read()
		self.assertNotRegex(src, re.compile(r"v = _num\(p\.value\)"))
		self.assertRegex(src, re.compile(r"n = _lead_num\(result\)"))
		# 13.12.11 (TASKS-289): the row is typed by its parameter key (`_row_key`: parameter_name, else specification)
		self.assertRegex(src, re.compile(r"_lot_value\(p, kinds\.get\(key\)\)"))

	def test_version_is_13_12_6_or_later(self):
		def tup(s):
			return tuple(int(x) for x in s.strip().split("."))
		with open(os.path.join(PKG, "__init__.py"), encoding="utf8") as f:
			ver = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)
		with open(os.path.join(os.path.dirname(PKG), "version.txt"), encoding="utf8") as f:
			self.assertEqual(f.read().strip(), ver)
		self.assertGreaterEqual(tup(ver), (13, 12, 6))


if __name__ == "__main__":
	unittest.main()
