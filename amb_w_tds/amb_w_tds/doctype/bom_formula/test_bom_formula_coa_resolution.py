# Copyright (c) 2026, AMB Wellness and Contributors
# See license.txt
"""G-0b-2a leg B — the line → lot → COA resolution ladder (A1 R3).

DB-backed, so it lives apart from `test_bom_formula.py`, which is pure-engine and
must stay runnable with no site. Everything here runs inside a transaction that
is rolled back; nothing persists.

The fixture is the REAL lot chain, not a synthetic one: golden 0307070264 is
Alicia's DORMECO case, and its three Batch AMB rows are a parent chain
(LOTE-26-34-0001 → -0002 → -0003), which is exactly the shape that made a
row-level count read as "ambiguous" when the lot-level answer is unique.
"""
import unittest

import frappe


GOLDEN = "0307070264"
ROOT = "LOTE-26-34-0001"
LEAF = "LOTE-26-34-0003"


class TestCOAResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = frappe.new_doc("BOM Formula")

    def setUp(self):
        frappe.db.begin()

    def tearDown(self):
        frappe.db.rollback()

    def line(self, **kw):
        base = dict(batch_amb_sublot=None, source_coa_amb2=None,
                    source_coa_doctype=None, cunete_ref=None, item_code=None, kg=100)
        base.update(kw)
        return frappe._dict(base)

    # --- step 1: an explicit link wins, in either doctype ---
    def test_explicit_coa_amb_wins(self):
        dt, name, res, _ = self.doc._resolve_coa(
            self.line(source_coa_amb2="COA-26-0021", source_coa_doctype="COA AMB"))
        self.assertEqual((dt, name, res), ("COA AMB", "COA-26-0021", "explicit"))

    def test_explicit_defaults_to_coa_amb2_when_doctype_blank(self):
        # Legacy rows carry a value with no companion doctype; they were all
        # COA AMB2 by construction, which is what the migration patch asserts.
        dt, _, res, _ = self.doc._resolve_coa(self.line(source_coa_amb2="X"))
        self.assertEqual((dt, res), ("COA AMB2", "explicit"))

    # --- the walk itself ---
    def test_batch_root_walks_the_chain_to_level_1(self):
        from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import _batch_root
        self.assertEqual(_batch_root(LEAF), ROOT)
        self.assertEqual(_batch_root(ROOT), ROOT, "a root resolves to itself")

    def test_batch_root_survives_a_cycle(self):
        # A broken parent chain must not hang the reader. Build a 2-cycle and
        # assert it terminates rather than asserting which node it stops on.
        from amb_w_tds.amb_w_tds.doctype.bom_formula.bom_formula import _batch_root
        frappe.db.set_value("Batch AMB", ROOT, "parent_batch_amb", LEAF)
        self.assertIsNotNone(_batch_root(LEAF))

    # --- step 2: the root's own link ---
    def test_batch_link_from_root_coa_amb(self):
        frappe.db.set_value("Batch AMB", ROOT, "coa_amb", "COA-26-0021")
        dt, name, res, detail = self.doc._resolve_coa(self.line(batch_amb_sublot=LEAF))
        self.assertEqual((dt, name, res), ("COA AMB", "COA-26-0021", "batch_link"))
        self.assertIn(ROOT, detail, "the note must name the root it walked to")

    # --- step 3: golden, from a SUBLOT, with the root's certificate ---
    def test_golden_match_from_a_sublot(self):
        dt, name, res, detail = self.doc._resolve_coa(self.line(batch_amb_sublot=LEAF))
        self.assertEqual(res, "golden_match")
        self.assertEqual(dt, "COA AMB")
        self.assertEqual(frappe.db.get_value("COA AMB", name, "custom_golden_number"), GOLDEN)
        self.assertIn(GOLDEN, detail)

    def test_draft_coa_never_resolves(self):
        # docstatus 1 only. Cancel the real one and the ladder must fall through
        # to `none`, not quietly pick a draft with the same golden.
        frappe.db.sql("update `tabCOA AMB` set docstatus=0 where custom_golden_number=%s", GOLDEN)
        _, name, res, _ = self.doc._resolve_coa(self.line(batch_amb_sublot=LEAF))
        self.assertIsNone(name)
        self.assertEqual(res, "none")

    def test_coa_amb2_is_never_queried_by_golden(self):
        # COA AMB2 has no golden column at all; a golden query against it would
        # raise. Reaching it by batch_reference must still work.
        self.assertIsNone(frappe.get_meta("COA AMB2").get_field("custom_golden_number"))
        _, _, res, _ = self.doc._resolve_coa(self.line(batch_amb_sublot=LEAF))
        self.assertIn(res, ("golden_match", "batch_link"))

    # --- step 4: nothing, and the note has to say why ---
    def test_none_names_the_line_and_the_failing_step(self):
        _, name, res, detail = self.doc._resolve_coa(self.line())
        self.assertEqual((name, res), (None, "none"))
        self.assertIn("no Batch AMB sublot", detail)

    def test_none_after_a_failed_golden_names_root_and_golden(self):
        frappe.db.sql("update `tabCOA AMB` set docstatus=0 where custom_golden_number=%s", GOLDEN)
        _, _, _, detail = self.doc._resolve_coa(self.line(batch_amb_sublot=LEAF))
        self.assertIn(ROOT, detail)
        self.assertIn(GOLDEN, detail)


class TestBackfillPlan(unittest.TestCase):
    def setUp(self):
        frappe.db.begin()

    def tearDown(self):
        frappe.db.rollback()

    def test_dry_run_plan_equals_apply_plan_and_is_idempotent(self):
        from amb_w_tds.patches import g0b2a_backfill_coa_batch_links as bf
        planned, _ = bf.plan()
        bf.execute(apply=True)          # commit=False: stays inside the test transaction
        after, _ = bf.plan()
        self.assertTrue(planned, "fixture should offer at least one write")
        self.assertEqual(after, [], "second run must plan zero writes (idempotent)")

    def test_never_touches_a_coa_that_already_points_somewhere(self):
        from amb_w_tds.patches import g0b2a_backfill_coa_batch_links as bf
        writes, skipped = bf.plan()
        for dt, name, field, old, new in writes:
            if field == "batch_reference":
                self.assertFalse(frappe.db.get_value(dt, name, "batch_reference"),
                                 f"{name} already had a batch_reference and was queued for a write")
        for row in skipped:
            self.assertTrue(row[3], "a skipped row must record the value it kept")


if __name__ == "__main__":
    unittest.main()
