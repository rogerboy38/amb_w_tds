"""13.12.0 COA AMB2 Cut 1: permissions mirrored from COA AMB, the workflow, the submit email, the three Error Log fixes, the gate warning. DB-free.

A: the Custom DocPerm fixture rows for COA AMB2 and the workflow roles they must satisfy.
B: `notify_quality_team` with `frappe.sendmail` mocked: no mail can leave a test.
C: lines skipped for want of a COA are named; which lots feed the blend is unchanged.
The DB half (roles walking the workflow, the real simulate_blend) is proven on a scratch site; see the PR.
"""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import frappe  # noqa: E402

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NEW_ROLES = {"Manufacturing User", "Quality User", "Quality Engineer", "RND Manager", "Sales Manager CRM", "Stock User"}
FLAGS = ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import",
         "share", "print", "email", "mask", "impersonate"]


def _fixture():
	with open(os.path.join(PKG, "fixtures", "custom_docperm.json"), encoding="utf8") as f:
		return json.load(f)


def _amb2_rows():
	return [r for r in _fixture() if r["parent"] == "COA AMB2"]


class TestPermissionRows(unittest.TestCase):
	def test_the_six_mirrored_roles_and_only_those(self):
		roles = [r["role"] for r in _amb2_rows()]
		self.assertEqual(sorted(roles), sorted(NEW_ROLES))
		self.assertEqual(len(roles), len(set(roles)), "one row per role: the duplicates COA AMB carries are not copied")

	def test_existing_rows_stay_out_of_the_fixture(self):
		# Quality Manager / Quality Inspector / System Manager keep the rows the site already has
		roles = {r["role"] for r in _amb2_rows()}
		self.assertFalse(roles & {"Quality Manager", "Quality Inspector", "System Manager"})
		self.assertNotIn("Marketing Manager", roles)  # COA AMB has no Marketing Manager row

	def test_quality_engineer_reads_writes_creates_reports_and_prints_and_nothing_else(self):
		(row,) = [r for r in _amb2_rows() if r["role"] == "Quality Engineer"]
		self.assertEqual({f for f in FLAGS if row[f]}, {"read", "write", "create", "report", "print"})
		for f in ("submit", "cancel", "amend", "delete", "export", "email", "share", "import", "select", "mask", "impersonate"):
			self.assertEqual(row[f], 0, f)

	def test_quality_user_can_do_what_the_workflow_asks(self):
		(row,) = [r for r in _amb2_rows() if r["role"] == "Quality User"]
		self.assertEqual((row["read"], row["write"], row["create"], row["submit"]), (1, 1, 1, 1))
		self.assertEqual((row["cancel"], row["amend"]), (0, 0))

	def test_rows_are_well_formed_and_do_not_collide_with_bom_formula(self):
		rows = _fixture()
		names = [r["name"] for r in rows]
		self.assertEqual(len(names), len(set(names)))
		for r in _amb2_rows():
			self.assertEqual((r["doctype"], r["parenttype"], r["parentfield"], r["permlevel"], r["if_owner"]),
				("Custom DocPerm", "DocType", "permissions", 0, 0))
		self.assertEqual(sum(1 for r in rows if r["parent"] == "BOM Formula"), 7, "the BOM Formula rows are untouched")

	def test_fixture_filter_keeps_the_rows_on_a_re_export(self):
		# the six rows are selected BY NAME (a re-export never drags in the rows a site already has, nor the verifier test roles)
		from amb_w_tds import hooks
		(entry,) = [f for f in hooks.fixtures if isinstance(f, dict) and f.get("doctype") == "Custom DocPerm"]
		self.assertNotIn("filters", entry)
		flt = {tuple(x[:2]): x for x in entry["or_filters"]}
		self.assertEqual(flt[("parent", "=")][2], "BOM Formula")
		self.assertEqual(set(flt[("name", "in")][2]), {r["name"] for r in _amb2_rows()})
		self.assertEqual(len(flt[("name", "in")][2]), 6)

	def test_every_workflow_transition_has_a_permission_behind_it(self):
		with open(os.path.join(PKG, "fixtures", "workflow.json"), encoding="utf8") as f:
			wf = next(w for w in json.load(f) if w["name"] == "submit_and_start_workflow")
		with open(os.path.join(PKG, "amb_w_tds", "doctype", "coa_amb2", "coa_amb2.json"), encoding="utf8") as f:
			standard = json.load(f)["permissions"]
		# what the sites hold today (the DocType JSON equals prod's three non-test Custom DocPerm rows) + the new rows
		perms = {}
		for r in list(standard) + _amb2_rows():
			cur = perms.setdefault(r["role"], set())
			cur.update(f for f in FLAGS if r.get(f))
		docstatus = {s["state"]: int(s["doc_status"]) for s in wf["states"]}
		for t in wf["transitions"]:
			role = t["allowed"]
			need = "submit" if docstatus[t["next_state"]] == 1 else "write"
			self.assertIn(need, perms.get(role, set()),
				f"{t['state']} --{t['action']}--> {t['next_state']}: role {role} lacks '{need}'")


AMB2_TRANSITIONS = [  # prod's rows (state, action, next state, allowed role, condition, allow self approval), in order
	("Draft", "Review", "Validated", "Quality User", None, 1),
	("Validated", "Submit for Supervisor Approval", "Pending Supervisor", "Quality Manager", None, 1),
	("Pending Supervisor", "Approve", "Approved", "Quality Manager", None, 0),
	("Approved", "Submit for Sales Approval", "Certificate Shared", "Quality User", None, 1),
	("Validated", "Approve (Quality)", "Pending Supervisor", "Quality User", None, 1),
	("Auto Approved", "Reopen", "Draft", "Quality User", None, 1),
	("Pending Supervisor", "Reject", "Draft", "Quality Manager", None, 1),
	("Approved", "Reject", "Draft", "Quality Manager", None, 1),
]
STATES = [("Draft", "0", "All"), ("Validated", "0", "Quality User"), ("Pending Supervisor", "0", "Quality User"),
	("Approved", "0", "Quality Manager"), ("Certificate Shared", "1", "Quality User"), ("Auto Approved", "0", "Quality User"),
	("Saved", "0", "All")]


def _workflows():
	with open(os.path.join(PKG, "fixtures", "workflow.json"), encoding="utf8") as f:
		return {w["name"]: w for w in json.load(f)}


def _rows(w):
	return [(t["state"], t["action"], t["next_state"], t["allowed"], t.get("condition"), int(t.get("allow_self_approval") or 0))
		for t in w["transitions"]]


class TestWorkflowFixture(unittest.TestCase):
	def test_quality_manager_may_press_submit_for_sales_approval_and_quality_user_still_may(self):
		rows = _rows(_workflows()["submit_and_start_workflow"])
		submit = [r for r in rows if r[:3] == ("Approved", "Submit for Sales Approval", "Certificate Shared")]
		self.assertEqual(sorted(r[3] for r in submit), ["Quality Manager", "Quality User"])
		self.assertEqual({r[4:] for r in submit}, {(None, 1)})

	def test_the_other_seven_transitions_are_prods_rows_unchanged_and_in_order(self):
		rows = _rows(_workflows()["submit_and_start_workflow"])
		self.assertEqual(rows[:8], AMB2_TRANSITIONS)
		self.assertEqual(len(rows), 9)

	def test_states_and_the_workflow_flags_are_unchanged(self):
		w = _workflows()["submit_and_start_workflow"]
		self.assertEqual([(s["state"], str(s["doc_status"]), s["allow_edit"]) for s in w["states"]], STATES)
		self.assertEqual((w["document_type"], w["is_active"], w["workflow_state_field"], w["override_status"], w["send_email_alert"]),
			("COA AMB2", 1, "workflow_state", 0, 0))

	def test_the_coa_amb_twin_workflow_is_untouched(self):
		w = _workflows()["submit_and_start_workflow_1"]
		self.assertEqual(w["document_type"], "COA AMB")
		self.assertEqual(_rows(w), AMB2_TRANSITIONS)
		self.assertEqual([(s["state"], str(s["doc_status"]), s["allow_edit"]) for s in w["states"]], STATES)


class TestErrorLogFixes(unittest.TestCase):
	MOD = "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2"

	def doc(self):
		from amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2 import COAAMB2
		d = object.__new__(COAAMB2)
		d.__dict__.update(doctype="COA AMB2", name="COA2-26-0001", owner="o@x.test", approved_by=None, product_item="IT",
			item_name="I", item_code="IT", coa_number="N-1", approval_date="2026-10-25", batch_reference=None,
			overall_result="Pass", compliance_status="OK")
		d.add_comment = mock.Mock()
		return d

	# --- fix 1: Item columns that no site has ---
	def run_product(self, method, present):
		meta = mock.Mock(has_field=lambda f: f in present)
		set_value, log_error = mock.Mock(), mock.Mock()
		with mock.patch("frappe.get_meta", lambda dt: meta), mock.patch("frappe.db", mock.Mock(set_value=set_value)), \
				mock.patch("frappe.log_error", log_error), mock.patch(self.MOD + ".nowdate", lambda: "2026-10-25"):
			getattr(self.doc(), method)()
		return set_value, log_error

	def test_no_item_columns_means_no_write_and_no_error(self):
		for method in ("update_product_quality_status", "revert_product_quality_status"):
			set_value, log_error = self.run_product(method, present=())
			set_value.assert_not_called()
			log_error.assert_not_called()

	def test_only_the_columns_that_exist_are_written(self):
		set_value, log_error = self.run_product("update_product_quality_status", present=("last_coa_date", "last_coa_reference"))
		set_value.assert_called_once_with("Item", "IT", {"last_coa_date": "2026-10-25", "last_coa_reference": "COA2-26-0001"})
		set_value, _ = self.run_product("revert_product_quality_status", present=("last_coa_result",))
		set_value.assert_called_once_with("Item", "IT", {"last_coa_result": None})

	def test_all_three_columns_present_behaves_as_before(self):
		set_value, _ = self.run_product("update_product_quality_status", present=("last_coa_date", "last_coa_result", "last_coa_reference"))
		set_value.assert_called_once_with("Item", "IT", {"last_coa_date": "2026-10-25", "last_coa_result": "Pass",
			"last_coa_reference": "COA2-26-0001"})

	def test_a_real_write_failure_is_still_logged(self):
		meta = mock.Mock(has_field=lambda f: True)
		log_error = mock.Mock()
		with mock.patch("frappe.get_meta", lambda dt: meta), mock.patch("frappe.log_error", log_error), \
				mock.patch("frappe.db", mock.Mock(set_value=mock.Mock(side_effect=RuntimeError("boom")))):
			self.doc().update_product_quality_status()
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.args[1], "COA AMB2 - Product Update")

	# --- fix 2: the Quality Audit DocType that Frappe 16 does not have ---
	def test_audit_step_is_skipped_when_the_doctype_is_absent(self):
		get_doc, log_error = mock.Mock(), mock.Mock()
		with mock.patch("frappe.db", mock.Mock(exists=lambda dt, name=None: False)), mock.patch("frappe.get_doc", get_doc), \
				mock.patch("frappe.log_error", log_error):
			self.doc().create_quality_audit()
		get_doc.assert_not_called()
		log_error.assert_not_called()

	def test_audit_step_still_runs_when_the_doctype_exists(self):
		audit = mock.Mock(name="audit")
		audit.name = "QA-1"
		get_doc = mock.Mock(return_value=audit)
		with mock.patch("frappe.db", mock.Mock(exists=lambda dt, name=None: True)), mock.patch("frappe.get_doc", get_doc), \
				mock.patch(self.MOD + ".nowdate", lambda: "2026-10-25"):
			d = self.doc()
			d.approved_by = "appr@x.test"  # `audited_by` reads the session user otherwise, and there is no session here
			d.create_quality_audit()
		self.assertEqual(get_doc.call_args.args[0]["doctype"], "Quality Audit")
		audit.insert.assert_called_once()
		d.add_comment.assert_called_once_with("Info", "Quality audit record created: QA-1")

	def test_a_real_audit_failure_is_still_logged(self):
		log_error = mock.Mock()
		with mock.patch("frappe.db", mock.Mock(exists=lambda dt, name=None: True)), \
				mock.patch("frappe.get_doc", mock.Mock(side_effect=RuntimeError("boom"))), mock.patch("frappe.log_error", log_error):
			self.doc().create_quality_audit()
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.args[1], "COA AMB2 - Audit Creation")

	# --- fix 3: the comment type, after the mail has gone ---
	def notify(self, sendmail):
		d = self.doc()
		log_error = mock.Mock()
		manager = mock.Mock()
		manager.attach_mock(sendmail, "sendmail")
		manager.attach_mock(d.add_comment, "add_comment")
		with mock.patch.object(type(d), "_notification_recipients", lambda s: ["a@x.test"]), \
				mock.patch.object(type(d), "_form_link", lambda s: "http://test.invalid/app/coa-amb2/X"), \
				mock.patch("frappe.sendmail", sendmail), mock.patch("frappe.log_error", log_error):
			d.notify_quality_team()
		return d, log_error, manager

	def test_the_sent_note_is_an_info_comment_added_after_the_mail(self):
		d, log_error, manager = self.notify(mock.Mock())
		log_error.assert_not_called()
		d.add_comment.assert_called_once_with("Info", "Notification sent to 1 recipient(s)")
		self.assertEqual([c[0] for c in manager.mock_calls], ["sendmail", "add_comment"], "the comment comes after the mail")

	def test_a_failing_mail_is_still_logged_and_no_note_is_added(self):
		d, log_error, _ = self.notify(mock.Mock(side_effect=RuntimeError("smtp down")))
		d.add_comment.assert_not_called()
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.args[1], "COA AMB2 - Notification")


class TestSubmitEmail(unittest.TestCase):
	def doc(self, owner="owner@x.test", approved_by="appr@x.test"):
		from amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2 import COAAMB2
		d = object.__new__(COAAMB2)
		d.__dict__.update(doctype="COA AMB2", name="COA2-26-0001", owner=owner, approved_by=approved_by, batch_reference=None,
			overall_result="Pass", coa_number="N-1", item_name="I", item_code="IC", compliance_status="OK",
			approval_date="2026-10-24")
		d.add_comment = mock.Mock()
		return d

	USERS = {"qm1": ("qm1@x.test", 1), "qm2": ("QM2@X.test", 1), "qm_off": ("off@x.test", 0), "Administrator": ("admin@x.test", 1),
		"Guest": ("guest@x.test", 1), "owner@x.test": ("owner@x.test", 1), "appr@x.test": ("appr@x.test", 1), "qm_same": ("qm2@x.test", 1)}

	def run_notify(self, doc, qm_users=("qm1", "qm2", "qm_off", "Administrator", "Guest", "qm_same")):
		def get_all(doctype, filters=None, fields=None, order_by=None, **kw):
			self.assertEqual((doctype, filters["role"]), ("Has Role", "Quality Manager"), "no other role is queried")
			return [frappe._dict(parent=u) for u in qm_users]

		def get_value(doctype, name, fieldname, as_dict=False, **kw):
			email, enabled = self.USERS.get(name, (None, 0))
			if fieldname == "email":
				return email
			return frappe._dict(email=email, enabled=enabled) if as_dict else (email, enabled)

		sendmail = mock.Mock()
		mod = "amb_w_tds.amb_w_tds.doctype.coa_amb2.coa_amb2"
		with mock.patch("frappe.get_all", get_all), mock.patch("frappe.db", mock.Mock(get_value=get_value)), \
				mock.patch("frappe.sendmail", sendmail), \
				mock.patch(mod + ".get_url", lambda uri=None, *a, **k: "http://test.invalid" + (uri or "")):
			doc.notify_quality_team()
		return sendmail

	def test_link_is_the_doctypes_own_route(self):
		sm = self.run_notify(self.doc())
		sm.assert_called_once()
		msg = sm.call_args.kwargs["message"]
		self.assertIn('href="http://test.invalid/app/coa-amb2/COA2-26-0001"', msg)
		self.assertNotIn("/app/coa-amb/", msg)

	def test_recipients_are_enabled_quality_managers_plus_owner_and_approver_deduplicated(self):
		sm = self.run_notify(self.doc())
		rcpt = sm.call_args.kwargs["recipients"]
		self.assertIsInstance(rcpt, list)
		# qm1, qm2 (QM2@X.test), the disabled one is out, Administrator/Guest are out, qm_same is a duplicate of qm2
		# by address (case-insensitive), then owner and approved_by
		self.assertEqual([r.lower() for r in rcpt], ["qm1@x.test", "qm2@x.test", "owner@x.test", "appr@x.test"])
		self.assertEqual(len(rcpt), len({r.lower() for r in rcpt}))
		for banned in ("admin@x.test", "guest@x.test", "off@x.test"):
			self.assertNotIn(banned, [r.lower() for r in rcpt])

	def test_owner_or_approver_that_is_administrator_or_guest_is_dropped(self):
		sm = self.run_notify(self.doc(owner="Administrator", approved_by="Guest"), qm_users=("qm1",))
		self.assertEqual(sm.call_args.kwargs["recipients"], ["qm1@x.test"])

	def test_nobody_to_tell_sends_nothing(self):
		sm = self.run_notify(self.doc(owner="Administrator", approved_by=None), qm_users=())
		sm.assert_not_called()

	def test_it_never_asks_for_inspectors_or_analysts(self):
		self.run_notify(self.doc())  # run_notify asserts every get_all is for the Quality Manager role only


class TestGateWarning(unittest.TestCase):
	def formula(self, lines):
		from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
		d = object.__new__(BOMFormula)
		d.__dict__["doctype"] = "BOM Formula"
		d.__dict__["mix_input_lines"] = [frappe._dict(l) for l in lines]
		d.__dict__["prediction_note"] = ""
		return d

	LINES = [dict(cunete_ref="C-1", item_code="IT-A", kg=600, batch_amb_sublot=None, source_coa_amb2="COA2-1", source_coa_doctype="COA AMB2"),
		dict(cunete_ref="C-2", item_code="IT-B", kg=100, batch_amb_sublot=None, source_coa_amb2=None, source_coa_doctype=None),
		dict(cunete_ref="C-3", item_code="IT-C", kg=300, batch_amb_sublot=None, source_coa_amb2="COA2-3", source_coa_doctype="COA AMB2")]

	def build(self, lines):
		from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
		d = self.formula(lines)
		rows = {"COA2-1": [frappe._dict(specification="Acemannan", value="14", result=None)],
			"COA2-3": [frappe._dict(specification="Acemannan", value="18", result=None)]}
		with mock.patch("frappe.get_all", lambda dt, filters=None, fields=None, **k: rows[filters["parent"]]), \
				mock.patch("frappe.db", mock.Mock(get_value=lambda *a, **k: None)):
			out = d._build_lots()
		return d, out

	def test_a_line_without_a_coa_is_named_by_row_and_item(self):
		d, (lots, total, with_coa) = self.build(self.LINES)
		self.assertEqual((total, with_coa), (3, 2))
		self.assertEqual(d._skipped_no_coa, [{"line": 2, "item_code": "IT-B"}])
		w = d._skip_warning()
		self.assertIn("row 2 (IT-B)", w)
		self.assertIn("1 line(s)", w)

	def test_all_lines_linked_shows_no_warning(self):
		linked = [dict(l, source_coa_amb2="COA2-1", source_coa_doctype="COA AMB2") for l in self.LINES]
		d, (lots, total, with_coa) = self.build(linked)
		self.assertEqual((total, with_coa), (3, 3))
		self.assertEqual(d._skipped_no_coa, [])
		self.assertEqual(d._skip_warning(), "")

	def test_the_lots_that_feed_the_blend_are_exactly_the_linked_lines(self):
		_, (lots, _, _) = self.build(self.LINES)
		self.assertEqual([(l.lot_id, l.mass_kg, l.values) for l in lots],
			[("C-1", 600.0, {"Acemannan": 14.0}), ("C-3", 300.0, {"Acemannan": 18.0})])

	def run_simulate(self, skipped):
		from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import BOMFormula
		d = self.formula(self.LINES)

		def fake_build(self_):
			self_._skipped_no_coa = list(skipped)
			self_._resolutions = []
			return ["lot"], 3, 2
		P = frappe._dict(name="Acemannan", uom="%", numeric=1)
		msgprint = mock.Mock()
		with mock.patch.object(BOMFormula, "_build_lots", fake_build), \
				mock.patch.object(BOMFormula, "_build_parameters", lambda s: [P]), \
				mock.patch.object(BOMFormula, "_recompute_mix_totals", lambda s: None), \
				mock.patch.object(BOMFormula, "save", lambda s, **k: None), \
				mock.patch.object(BOMFormula, "set", lambda s, k, v=None, *a, **kw: s.__dict__.__setitem__(k, v)), \
				mock.patch("amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula.engine.blend", lambda lots, params: {}), \
				mock.patch("frappe.msgprint", msgprint):
			d.__dict__.update(total_input_kg=1000, total_amount=0)
			return d.simulate_blend(), msgprint

	def test_simulate_blend_raises_an_orange_warning_naming_the_line(self):
		res, msgprint = self.run_simulate([{"line": 2, "item_code": "IT-B"}])
		msgprint.assert_called_once()
		self.assertEqual(msgprint.call_args.kwargs.get("indicator"), "orange")
		self.assertIn("row 2 (IT-B)", msgprint.call_args.args[0])
		self.assertEqual(res["skipped_no_coa"], [{"line": 2, "item_code": "IT-B"}])
		self.assertIn("row 2 (IT-B)", res["warning"])

	def test_simulate_blend_stays_quiet_when_nothing_was_skipped(self):
		res, msgprint = self.run_simulate([])
		msgprint.assert_not_called()
		self.assertEqual((res["skipped_no_coa"], res["warning"]), ([], ""))


if __name__ == "__main__":
	unittest.main()
