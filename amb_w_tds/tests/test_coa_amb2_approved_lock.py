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
		with mock.patch.object(mod, "_", lambda s: s), mock.patch.object(mod.frappe, "throw", side_effect=frappe.ValidationError) as t:
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


if __name__ == "__main__":
	unittest.main()
