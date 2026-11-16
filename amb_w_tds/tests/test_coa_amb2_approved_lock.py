"""TASKS-335 / D-12, DB-free: an Approved COA AMB2 (docstatus 0) cannot be re-saved; a transition can."""

import unittest
from unittest import mock

import frappe

from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as mod


class _Doc:
	"""The slice of a Document that refuse_edit_of_approved touches."""

	refuse = mod.COAAMB2.refuse_edit_of_approved

	def __init__(self, state, before_state, docstatus=0, new=False, has_before=True):
		self.name, self.docstatus, self._state, self._new = "COA-1", docstatus, state, new
		self._before = {"workflow_state": before_state} if has_before else None

	def is_new(self):
		return self._new

	def get_doc_before_save(self):
		return self._before

	def get(self, key):
		return self._state if key == "workflow_state" else None


class TestApprovedLock(unittest.TestCase):
	def run_it(self, **kw):
		d = _Doc(**kw)
		with (
			mock.patch.object(mod, "_", lambda s: s),
			mock.patch.object(mod.frappe, "throw", side_effect=frappe.ValidationError) as t,
		):
			try:
				d.refuse()
				return False, t
			except frappe.ValidationError:
				return True, t

	def test_resave_of_approved_is_refused(self):
		refused, _ = self.run_it(state="Approved", before_state="Approved")
		self.assertTrue(refused)

	def test_reject_to_draft_is_a_transition_and_passes(self):
		self.assertFalse(self.run_it(state="Draft", before_state="Approved")[0])

	def test_the_approve_that_reaches_approved_passes(self):
		self.assertFalse(self.run_it(state="Approved", before_state="Pending Supervisor")[0])

	def test_other_states_are_untouched(self):
		for s in ("Draft", "Validated", "Pending Supervisor", "Auto Approved", "Saved"):
			self.assertFalse(self.run_it(state=s, before_state=s)[0], s)

	def test_new_document_and_submitted_document_are_untouched(self):
		self.assertFalse(self.run_it(state="Approved", before_state="Approved", new=True)[0])
		self.assertFalse(self.run_it(state="Approved", before_state="Approved", docstatus=1)[0])
		self.assertFalse(self.run_it(state="Approved", before_state=None, has_before=False)[0])


class _Row:
	"""A child row as the hook sees it."""

	def __init__(self, parenttype="COA AMB2", parent="COA-1", new=False):
		self._d = {"parenttype": parenttype, "parent": parent}
		self._new = new

	def get(self, key):
		return self._d.get(key)

	def is_new(self):
		return self._new


class TestRowsOfApproved(unittest.TestCase):
	"""TASKS-361 decision 115, DB-free: a row of an Approved COA AMB2 cannot be changed, added or removed on its own,
	and an Approved certificate cannot be deleted. The real document paths are run on a scratch site (see the reply)."""

	def hook(self, row, state="Approved", docstatus=0, method="before_validate", exists=True):
		parent = frappe._dict(workflow_state=state, docstatus=docstatus) if exists else None
		with (
			mock.patch.object(mod, "_", lambda s: s),
			mock.patch.object(mod.frappe, "db", mock.MagicMock()) as db,
			mock.patch.object(mod.frappe, "throw", side_effect=frappe.ValidationError) as t,
		):
			db.get_value.return_value = parent
			gv = db.get_value
			try:
				mod.refuse_row_of_approved(row, method)
				return False, t, gv
			except frappe.ValidationError:
				return True, t, gv

	def test_a_row_of_an_approved_certificate_cannot_be_changed_added_or_removed(self):
		for method, new, word in (("before_validate", False, "changed"), ("before_validate", True, "added"), ("on_trash", False, "removed")):
			refused, t, _gv = self.hook(_Row(new=new), method=method)
			self.assertTrue(refused, method)
			self.assertIn(word, t.call_args.args[0].format("COA-1", word) if "{" in t.call_args.args[0] else t.call_args.args[0])

	def test_rows_of_a_certificate_in_any_other_state_are_not_judged(self):
		for state in ("Draft", "Validated", "Pending Supervisor", "Auto Approved", "Saved", None):
			self.assertFalse(self.hook(_Row(), state=state)[0], state)

	def test_rows_of_a_submitted_certificate_are_frappes_own_business(self):
		self.assertFalse(self.hook(_Row(), docstatus=1)[0])

	def test_rows_of_another_parent_type_are_never_read_or_judged(self):
		for row in (_Row(parenttype="COA AMB"), _Row(parenttype=None), _Row(parent=None), _Row(parenttype="Batch AMB")):
			refused, _t, gv = self.hook(row)
			self.assertFalse(refused)
			gv.assert_not_called()

	def test_a_row_whose_parent_is_gone_is_not_judged(self):
		self.assertFalse(self.hook(_Row(), exists=False)[0])

	def test_both_child_tables_of_the_certificate_are_hooked_at_the_two_events(self):
		import importlib

		hooks = importlib.import_module("amb_w_tds.hooks")
		path = "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2.refuse_row_of_approved"
		meta = __import__("json").load(open(mod.__file__.replace("coa_amb2.py", "coa_amb2.json"), encoding="utf-8"))
		tables = sorted(f["options"] for f in meta["fields"] if f["fieldtype"] == "Table")
		self.assertEqual(tables, ["COA Quality Test Parameter", "SPC Batch Parameter"])
		for dt in tables:
			self.assertEqual(hooks.doc_events[dt], {"before_validate": path, "on_trash": path}, dt)


class TestDeleteOfApproved(unittest.TestCase):
	def trash(self, state, docstatus=0):
		d = type("D", (), {"name": "COA-1", "docstatus": docstatus, "get": lambda self, k: state if k == "workflow_state" else None})()
		with mock.patch.object(mod, "_", lambda s: s), mock.patch.object(mod.frappe, "throw", side_effect=frappe.ValidationError):
			try:
				mod.COAAMB2.on_trash(d)
				return False
			except frappe.ValidationError:
				return True

	def test_an_approved_certificate_cannot_be_deleted(self):
		self.assertTrue(self.trash("Approved"))

	def test_a_draft_and_every_other_state_can(self):
		for s in ("Draft", "Validated", "Pending Supervisor", "Auto Approved", "Saved"):
			self.assertFalse(self.trash(s), s)


if __name__ == "__main__":
	unittest.main()
