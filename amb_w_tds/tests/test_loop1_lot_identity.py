"""LOOP-1 acceptance — VMG-I I-1..I-10 (matrix-row render assertions deferred).

⭐ SPLIT DELIBERATELY, as in BUG208: the arithmetic/logic half runs frappe-free
on a second interpreter; anything asserting a DB fact or a RENDER is gated on a
connected bench and SKIPS LOUDLY without one. A skipped test is not a passing
one — that is the silence OPEN #11 exists to break.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from amb_w_tds.lot_identity import (  # noqa: E402
    DEFERRED_SURFACES,
    GOLDEN,
    HISTORIC_REAL,
    MATRIX,
    SYSTEM_NAME,
    amb_lot_identity,
    amb_lot_identity_kind,
    resolve,
    surface_status,
)


def doc(**kw):
    """A plain dict stands in for a Document — the resolver must never need
    more than `.get()`, which is what keeps it off the DB (I-5)."""
    return dict(kw)


class TestMatrixIsDataInCode(unittest.TestCase):
    """I-5 — the matrix is data in this module, not configuration."""

    def test_matrix_is_a_plain_dict_in_the_module(self):
        self.assertIsInstance(MATRIX, dict)
        self.assertTrue(MATRIX)

    def test_the_resolver_path_reads_no_config_and_no_db(self):
        """⛔ AST, not text — a docstring saying 'no db reads' is not a control.
        Asserts no frappe DB/config call appears anywhere in the module."""
        import ast
        import inspect
        import amb_w_tds.lot_identity as mod

        tree = ast.parse(inspect.getsource(mod))
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                parts = []
                while isinstance(f, ast.Attribute):
                    parts.append(f.attr)
                    f = f.value
                if isinstance(f, ast.Name):
                    parts.append(f.id)
                called.add(".".join(reversed(parts)))
        banned = {"frappe.get_doc", "frappe.get_value", "frappe.get_all",
                  "frappe.get_single", "frappe.db.sql", "frappe.db.get_value",
                  "frappe.get_meta", "frappe.get_cached_doc"}
        self.assertEqual(called & banned, set(), f"config/DB read in the resolver: {called & banned}")

    def test_the_module_does_not_even_import_frappe(self):
        """The strongest form of 'no DB read on a render path'."""
        import inspect
        import amb_w_tds.lot_identity as mod
        src = inspect.getsource(mod)
        self.assertNotIn("import frappe", src)


class TestFailVisible(unittest.TestCase):
    """I-6 — a surface with nothing honest to show shows NOTHING."""

    def test_a_deferred_surface_returns_empty_never_the_golden(self):
        d = doc(custom_golden_number="0227022211", name="LOTE-26-24-0004")
        for surface in DEFERRED_SURFACES:
            self.assertEqual(amb_lot_identity(d, surface), "",
                             f"{surface} substituted an identity it may not show")
            self.assertNotIn("0227022211", amb_lot_identity(d, surface))

    def test_customs_specifically_never_falls_back_to_the_golden(self):
        """⭐ The row this whole contract exists for: a customs surface must not
        print an internal number in a customer's place."""
        d = doc(custom_golden_number="0227022211")
        self.assertEqual(amb_lot_identity(d, "customs"), "")
        self.assertEqual(amb_lot_identity_kind(d, "customs"), "")

    def test_an_unknown_surface_is_empty_not_a_guess(self):
        self.assertEqual(amb_lot_identity(doc(custom_golden_number="X"), "nonsense"), "")

    def test_no_ruled_row_permits_substitution(self):
        for name, row in MATRIX.items():
            self.assertFalse(row["fallback"], f"{name} allows substitution")


class TestRuledRows(unittest.TestCase):
    """The rows matrix v1 actually rules."""

    def test_internal_prefers_the_golden(self):
        d = doc(custom_golden_number="0227022211",
                custom_historic_lot_real="0227022299", name="LOTE-26-24-0004")
        self.assertEqual(resolve(d, "internal"), (GOLDEN, "0227022211"))

    def test_internal_falls_through_to_historic_then_system(self):
        self.assertEqual(resolve(doc(custom_historic_lot_real="0227022299"), "internal"),
                         (HISTORIC_REAL, "0227022299"))
        self.assertEqual(resolve(doc(name="LOTE-26-24-0004"), "internal"),
                         (SYSTEM_NAME, "LOTE-26-24-0004"))

    def test_system_resolves_only_the_document_name(self):
        d = doc(custom_golden_number="0227022211", name="LOTE-26-24-0004")
        self.assertEqual(resolve(d, "system"), (SYSTEM_NAME, "LOTE-26-24-0004"))

    def test_blank_and_whitespace_are_absent_not_present(self):
        for bad in ("", "   ", None):
            self.assertEqual(resolve(doc(custom_golden_number=bad, name="N"), "internal"),
                             (SYSTEM_NAME, "N"))

    def test_surface_matching_is_case_and_space_insensitive(self):
        d = doc(name="LOTE-26-24-0004")
        self.assertEqual(amb_lot_identity(d, "  SYSTEM "), "LOTE-26-24-0004")


class TestDeferredIsDistinguishable(unittest.TestCase):
    """⚠ 'not yet ruled' must not look like 'you typed it wrong' — both return
    empty, and only `surface_status` tells them apart."""

    def test_status_separates_ruled_deferred_and_unknown(self):
        self.assertEqual(surface_status("internal"), "ruled")
        self.assertEqual(surface_status("customs"), "deferred")
        self.assertEqual(surface_status("banana"), "unknown")

    def test_no_surface_is_both_ruled_and_deferred(self):
        self.assertEqual(set(MATRIX) & set(DEFERRED_SURFACES), set())

    def test_every_deferred_row_states_a_reason(self):
        for surface, reason in DEFERRED_SURFACES.items():
            self.assertGreater(len(reason), 30, f"{surface} deferred without a reason")


class TestSalesLotFromChildRows(unittest.TestCase):
    """The child table is read off the loaded doc, never queried."""

    def test_rows_absent_or_empty_yield_nothing(self):
        for rows in (None, [], [{"sales_lot": ""}]):
            self.assertEqual(resolve(doc(custom_historic_sales_lots=rows, name="N"), "internal"),
                             (SYSTEM_NAME, "N"))

    def test_first_populated_row_wins_and_junk_rows_are_skipped(self):
        from amb_w_tds.lot_identity import _sales_lot
        self.assertEqual(_sales_lot(doc(custom_historic_sales_lots=[
            {"sales_lot": None}, {"sales_lot": "  "}, {"sales_lot": "LV-7"}])), "LV-7")


if __name__ == "__main__":
    unittest.main(verbosity=2)
