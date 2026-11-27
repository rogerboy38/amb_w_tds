"""TASKS-335 / D-12, DB-free: an Approved COA AMB2 (docstatus 0) cannot be re-saved; a transition can."""

import unittest
from unittest import mock

import frappe

from amb_w_tds.amb_w_tds.doctype.coa_amb2 import coa_amb2 as mod


class _Doc:
	"""The slice of a Document that refuse_edit_of_approved touches."""

	refuse = mod.COAAMB2.refuse_edit_of_approved
	doctype = "COA AMB2"  # TASKS-384 B1: the lock reads the state field of the document's type

	def __init__(self, state, before_state, docstatus=0, new=False, has_before=True, before_docstatus=0):
		self.name, self.docstatus, self._state, self._new = "COA-1", docstatus, state, new
		self._before = {"workflow_state": before_state, "docstatus": before_docstatus} if has_before else None

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
		self.assertFalse(self.run_it(state="Approved", before_state="Approved", docstatus=1, before_docstatus=1)[0])
		self.assertFalse(self.run_it(state="Approved", before_state=None, has_before=False)[0])

	def test_a_submit_of_an_approved_certificate_is_refused(self):
		"""TASKS-365, VM3 D12-6: during a submit the document is already at docstatus 1; the lock used to return."""
		refused, t = self.run_it(state="Approved", before_state="Approved", docstatus=1)
		self.assertTrue(refused)
		self.assertIn("cannot be submitted", t.call_args.args[0])
		# also when the caller changes the state in the same call, and when the docstatus arrives as text
		self.assertTrue(self.run_it(state="Draft", before_state="Approved", docstatus=1)[0])
		self.assertTrue(self.run_it(state="Approved", before_state="Approved", docstatus="1")[0])

	def test_a_submit_from_any_other_state_is_not_this_locks_business(self):
		for s in ("Draft", "Validated", "Pending Supervisor", "Auto Approved", "Saved"):
			self.assertFalse(self.run_it(state=s, before_state=s, docstatus=1)[0], s)

	def test_the_lock_also_runs_before_validate(self):
		calls = []
		d = type("D", (), {"refuse_submit": lambda self: None, "refuse_edit_of_approved": lambda self: calls.append("lock")})()
		with mock.patch.object(mod, "refuse_taking_rows_of_approved", lambda doc: calls.append("rows")), \
				mock.patch.object(mod.certificate_rules, "before_validate", lambda doc: calls.append("rules")):
			mod.COAAMB2.before_validate(d)
		self.assertEqual(calls, ["lock", "rows", "rules"])


class _Row:
	"""A child row as the hook sees it."""

	doctype = "SPC Batch Parameter"

	def __init__(self, parenttype="COA AMB2", parent="COA-1", new=False, name="row-1"):
		self._d = {"parenttype": parenttype, "parent": parent, "name": name}
		self._new = new

	def get(self, key):
		return self._d.get(key)

	def is_new(self):
		return self._new


class _Db:
	"""Certificates by name, and where each row is STORED: the two things the hooks read."""

	def __init__(self, certs=None, rows=None):
		self.certs, self.rows, self.asked = certs or {}, rows or {}, []

	def get_value(self, doctype, name, fields, as_dict=False):
		self.asked.append((doctype, name))
		if doctype == "COA AMB2":
			c = self.certs.get(name)
			return frappe._dict(workflow_state=c[0], docstatus=c[1]) if c else None
		r = self.rows.get(name)
		return frappe._dict(parent=r[0], parenttype=r[1]) if r else None


def _run(fn, db, get_all=None):
	with (
		mock.patch.object(mod, "_", lambda s: s),
		mock.patch.object(mod.frappe, "db", db),
		mock.patch.object(mod.frappe, "get_all", get_all or (lambda *a, **k: [])),
		mock.patch.object(mod.frappe, "throw", side_effect=frappe.ValidationError) as t,
	):
		try:
			fn()
			return False, t
		except frappe.ValidationError:
			return True, t


class TestRowsOfApproved(unittest.TestCase):
	"""TASKS-361 decision 115, DB-free: a row of an Approved COA AMB2 cannot be changed, added or removed on its own,
	and an Approved certificate cannot be deleted. The real document paths are run on a scratch site (see the reply)."""

	def hook(self, row, state="Approved", docstatus=0, method="before_validate", exists=True, stored=None):
		db = _Db({"COA-1": (state, docstatus)} if exists else {}, {"row-1": stored} if stored else {})
		refused, t = _run(lambda: mod.refuse_row_of_approved(row, method), db)
		return refused, t, db

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
		# TASKS-384 B1: a row whose parent is a COA AMB is judged now (tests/test_certificate_rules_b1.py), so it
		# left this list of parents that are never read
		for row in (_Row(parenttype="SPC Batch Record"), _Row(parenttype=None), _Row(parent=None), _Row(parenttype="Batch AMB")):
			refused, _t, db = self.hook(row, stored=("BATCH-1", "Batch AMB"))
			self.assertFalse(refused)
			# the certificate is never read: only where the row itself is stored (one statement, TASKS-365)
			self.assertEqual(db.asked, [("SPC Batch Parameter", "row-1")])

	def test_a_row_is_judged_by_the_parent_it_has_in_the_database_too(self):
		"""TASKS-365, VM3 D12-4 b and c: `parent` or `parenttype` changed in the same save."""
		for sent in (
			_Row(parent="COA-2"),                      # another certificate, a Draft
			_Row(parenttype="COA AMB", parent="X"),    # another parent type
			_Row(parenttype="Batch AMB", parent="COA-1"),  # only the type changed
			_Row(parent=None),                         # the parent emptied
			_Row(parenttype=None, parent=None),
		):
			db = _Db({"COA-1": ("Approved", 0), "COA-2": ("Draft", 0)}, {"row-1": ("COA-1", "COA AMB2")})
			for method in ("before_validate", "on_trash"):
				self.assertTrue(_run(lambda: mod.refuse_row_of_approved(sent, method), db)[0], (sent._d, method))
		# a row stored under a Draft may go where the caller sends it, but not INTO an Approved one
		db = _Db({"COA-1": ("Approved", 0), "COA-2": ("Draft", 0)}, {"row-1": ("COA-2", "COA AMB2")})
		self.assertFalse(_run(lambda: mod.refuse_row_of_approved(_Row(parent="COA-2"), "before_validate"), db)[0])
		self.assertTrue(_run(lambda: mod.refuse_row_of_approved(_Row(parent="COA-1"), "before_validate"), db)[0])
		# a row stored under a submitted certificate, or under one whose state is not locked: not judged
		for cert in (("Approved", 1), ("Auto Approved", 0), ("Draft", 0)):
			db = _Db({"COA-1": cert}, {"row-1": ("COA-1", "COA AMB2")})
			self.assertFalse(_run(lambda: mod.refuse_row_of_approved(_Row(parent="COA-9"), "before_validate"), db)[0], cert)

	def test_a_row_whose_parent_is_gone_is_not_judged(self):
		self.assertFalse(self.hook(_Row(), exists=False)[0])

	def test_both_child_tables_of_the_certificate_are_hooked_at_the_two_events(self):
		import importlib

		hooks = importlib.import_module("amb_w_tds.hooks")
		path = "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2.refuse_row_of_approved"
		meta = __import__("json").load(open(mod.__file__.replace("coa_amb2.py", "coa_amb2.json"), encoding="utf-8"))
		tables = sorted(f["options"] for f in meta["fields"] if f["fieldtype"] == "Table")
		self.assertEqual(tables, ["COA Quality Test Parameter", "SPC Batch Parameter"])
		# TASKS-384 B1: the result rows carry a second function after the lock (who filled); the lock stays first
		filler = "amb_w_tds.certificate_rules.note_filler_of_row"
		self.assertEqual(hooks.doc_events["COA Quality Test Parameter"], {"before_validate": [path, filler], "on_trash": [path, filler]})
		self.assertEqual(hooks.doc_events["SPC Batch Parameter"], {"before_validate": path, "on_trash": path})
		self.assertEqual(sorted(mod.LOCKED_CHILD_DOCTYPES), tables)


class _Parent:
	"""A document that carries one of the two child tables."""

	def __init__(self, doctype, name, rows, options="SPC Batch Parameter"):
		self.doctype, self.name, self._rows = doctype, name, rows
		df = frappe._dict(fieldname="t", options=options)
		self.meta = type("M", (), {"get_table_fields": lambda self: [df, frappe._dict(fieldname="other", options="Something Else")]})()

	def get(self, key):
		return self._rows if key == "t" else [{"name": "never-read"}]


class TestRowsTakenByAnotherDocument(unittest.TestCase):
	"""TASKS-365, VM3 D12-4 a: a document saved with the name of an Approved certificate's row in its own table."""

	def take(self, parent, stored, certs):
		asked = []

		def get_all(doctype, filters=None, fields=None):
			asked.append((doctype, filters))
			return [frappe._dict(name=n, parent=p, parenttype="COA AMB2") for n, p in stored.items() if n in filters["name"][1]]

		refused, t = _run(lambda: mod.refuse_taking_rows_of_approved(parent), _Db(certs), get_all)
		return refused, t, asked

	def test_every_carrier_is_refused_the_row_of_an_approved_certificate(self):
		certs = {"COA-1": ("Approved", 0), "COA-2": ("Draft", 0)}
		for dt in ("COA AMB2", "COA AMB", "Batch AMB", "SPC Batch Record"):
			refused, t, asked = self.take(_Parent(dt, "OTHER", [{"name": "row-1"}, {"name": None}]), {"row-1": "COA-1"}, certs)
			self.assertTrue(refused, dt)
			# TASKS-384 B1: one query still, now for rows of either certificate type
			self.assertEqual(asked, [("SPC Batch Parameter", {"name": ["in", ["row-1"]], "parenttype": ["in", ["COA AMB2", "COA AMB"]]})])

	def test_what_is_not_judged(self):
		certs = {"COA-1": ("Approved", 0), "COA-2": ("Draft", 0), "COA-3": ("Approved", 1)}
		# the certificate's own rows (its own lock judges that save, and Reject must pass)
		self.assertFalse(self.take(_Parent("COA AMB2", "COA-1", [{"name": "row-1"}]), {"row-1": "COA-1"}, certs)[0])
		# rows of a Draft and of a submitted certificate; rows with no name; a table with no named row asks nothing
		self.assertFalse(self.take(_Parent("COA AMB2", "COA-9", [{"name": "row-1"}]), {"row-1": "COA-2"}, certs)[0])
		self.assertFalse(self.take(_Parent("Batch AMB", "B-1", [{"name": "row-1"}]), {"row-1": "COA-3"}, certs)[0])
		refused, _t, asked = self.take(_Parent("Batch AMB", "B-1", [{"name": None}, {}]), {}, certs)
		self.assertEqual((refused, asked), (False, []))
		# a COA AMB whose NAME equals the Approved certificate's is still another document
		self.assertTrue(self.take(_Parent("COA AMB", "COA-1", [{"name": "row-1"}]), {"row-1": "COA-1"}, certs)[0])

	def test_the_carriers_are_hooked(self):
		import importlib

		hooks = importlib.import_module("amb_w_tds.hooks")
		path = "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2.refuse_taking_rows_of_approved"
		for dt in ("COA AMB", "Batch AMB", "SPC Batch Record"):
			self.assertEqual(hooks.doc_events[dt]["before_validate"], path, dt)


class TestRenameOfApproved(unittest.TestCase):
	"""TASKS-365, VM3 D12-5."""

	def rename(self, old, new, merge=False):
		db = _Db({"COA-1": ("Approved", 0), "COA-2": ("Draft", 0), "COA-3": ("Approved", 1)})
		return _run(lambda: mod.COAAMB2.before_rename(type("D", (), {"doctype": "COA AMB2"})(), old, new, merge), db)[0]

	def test_an_approved_certificate_is_not_renamed_and_nothing_is_merged_into_it(self):
		self.assertTrue(self.rename("COA-1", "COA-X"))
		self.assertTrue(self.rename("COA-1", "COA-2", merge=True))
		self.assertTrue(self.rename("COA-2", "COA-1", merge=True))

	def test_a_draft_and_a_submitted_one_are_renamed_as_before(self):
		self.assertFalse(self.rename("COA-2", "COA-X"))
		self.assertFalse(self.rename("COA-3", "COA-X"))
		self.assertFalse(self.rename("COA-2", "COA-3", merge=True))


class TestDeleteOfApproved(unittest.TestCase):
	def trash(self, state, docstatus=0):
		d = type("D", (), {"doctype": "COA AMB2", "name": "COA-1", "docstatus": docstatus, "get": lambda self, k: state if k == "workflow_state" else None})()
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


class _Sub:
	"""The slice of a Document that refuse_submit touches."""

	def __init__(self, docstatus, action=None, new=False, before_docstatus=None):
		self.name, self.docstatus, self._new = "COA-1", docstatus, new
		if action:
			self._action = action
		self._before = None if before_docstatus is None else {"docstatus": before_docstatus}

	def is_new(self):
		return self._new

	def get_doc_before_save(self):
		return self._before


class TestNoSubmitInAnyState(unittest.TestCase):
	"""TASKS-366 decision 129: nothing of this type is submitted. The state is not even read."""

	def refused(self, **kw):
		with mock.patch.object(mod, "_", lambda s: s), mock.patch.object(mod.frappe, "throw", side_effect=frappe.ValidationError) as t:
			try:
				mod.COAAMB2.refuse_submit(_Sub(**kw))
				return False, t
			except frappe.ValidationError:
				return True, t

	def test_every_way_from_docstatus_zero_to_one_is_refused(self):
		refused, t = self.refused(docstatus=1, action="submit", before_docstatus=0)
		self.assertTrue(refused)
		self.assertIn("ends at Quality approval", t.call_args.args[0])
		self.assertTrue(self.refused(docstatus=1, before_docstatus=0)[0])            # a save that carries docstatus 1
		self.assertTrue(self.refused(docstatus="1", before_docstatus="0")[0])        # as text
		self.assertTrue(self.refused(docstatus=1, new=True)[0])                      # an insert that carries docstatus 1
		self.assertTrue(self.refused(docstatus=1, action="submit")[0])               # no stored copy at hand

	def test_a_draft_save_and_an_already_submitted_certificate_are_not_touched(self):
		self.assertFalse(self.refused(docstatus=0, action="save", before_docstatus=0)[0])
		self.assertFalse(self.refused(docstatus=0, new=True)[0])
		self.assertFalse(self.refused(docstatus=1, action="update_after_submit", before_docstatus=1)[0])
		self.assertFalse(self.refused(docstatus=2, action="cancel", before_docstatus=1)[0])
		self.assertFalse(self.refused(docstatus=1, action="update_after_submit")[0])

	def test_it_runs_first_in_before_validate_and_in_validate(self):
		calls = []
		d = type("D", (), {"refuse_submit": lambda self: calls.append("submit"), "refuse_edit_of_approved": lambda self: calls.append("lock")})()
		with mock.patch.object(mod, "refuse_taking_rows_of_approved", lambda doc: calls.append("rows")), \
				mock.patch.object(mod.certificate_rules, "before_validate", lambda doc: calls.append("rules")):
			mod.COAAMB2.before_validate(d)
		self.assertEqual(calls, ["submit", "lock", "rows", "rules"])
		import inspect

		src = inspect.getsource(mod.COAAMB2.validate)
		self.assertLess(src.index("self.refuse_submit()"), src.index("self.refuse_edit_of_approved()"))


class TestChildTablesDoNotTrackSeen(unittest.TestCase):
	"""TASKS-365, T-1: a child table has no `_seen` column; "track seen" on it makes every save of a row by itself fail."""

	def test_no_child_doctype_of_the_certificate_declares_track_seen(self):
		import glob, json, os

		root = os.path.dirname(os.path.dirname(os.path.dirname(mod.__file__)))
		seen = []
		for f in glob.glob(os.path.join(root, "doctype", "*", "*.json")):
			d = json.load(open(f, encoding="utf-8"))
			if isinstance(d, dict) and d.get("doctype") == "DocType" and d.get("istable") and d.get("track_seen"):
				seen.append(d["name"])
		self.assertEqual(seen, [])
