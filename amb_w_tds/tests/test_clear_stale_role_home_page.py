# Copyright (c) 2026, AMB Wellness and Contributors
# See license.txt
"""Tests for the stale Role.home_page patch.

Everything runs inside a transaction that is rolled back, and the patch itself
never commits, so no Role is changed on the site by running these.
"""
import unittest

import frappe

from amb_w_tds.patches.clear_stale_role_home_page import STALE, _norm, execute

STALE_ROLE = "_Test Role HP Stale"
KEEP_ROLE = "_Test Role HP Keep"
SLASHED_ROLE = "_Test Role HP Slashed"


class TestClearStaleRoleHomePage(unittest.TestCase):
    def setUp(self):
        frappe.db.begin()
        for name, home in ((STALE_ROLE, "desktop"),
                           (KEEP_ROLE, "/custom-portal"),
                           (SLASHED_ROLE, "/app/stock-entry")):
            if not frappe.db.exists("Role", name):
                frappe.get_doc({"doctype": "Role", "role_name": name}).insert(
                    ignore_permissions=True)
            frappe.db.set_value("Role", name, "home_page", home,
                                update_modified=False)

    def tearDown(self):
        frappe.db.rollback()

    def home(self, role):
        return frappe.db.get_value("Role", role, "home_page")

    def test_desktop_is_cleared(self):
        execute()
        self.assertIsNone(self.home(STALE_ROLE))

    def test_custom_portal_is_untouched(self):
        # The patch must clear only STALE. A route it does not recognise is
        # somebody's deliberate landing page, not debris.
        execute()
        self.assertEqual(self.home(KEEP_ROLE), "/custom-portal")

    def test_slashed_value_is_matched(self):
        # The whole point: the DB stores "/app/stock-entry", the set says
        # "app/stock-entry". A raw compare misses this row.
        self.assertNotIn(self.home(SLASHED_ROLE), STALE)   # raw: no match
        execute()
        self.assertIsNone(self.home(SLASHED_ROLE))         # normalised: cleared

    def test_second_run_writes_nothing(self):
        first = execute()
        self.assertTrue(first, "first run should have cleared at least the fixtures")
        second = execute()
        self.assertEqual(second, [], "second run must be a no-op (idempotent)")

    def test_null_and_blank_never_match(self):
        # _norm("") must not collide with a STALE member, or a NULL row would be
        # "cleared" and counted as a write forever.
        self.assertEqual(_norm(None), "")
        self.assertEqual(_norm("   "), "")
        self.assertNotIn(_norm(None), STALE)

    def test_nothing_outside_the_stale_set_is_written(self):
        before = {r.name: r.home_page for r in frappe.db.sql(
            "select name, home_page from `tabRole`", as_dict=True)}
        execute()
        after = {r.name: r.home_page for r in frappe.db.sql(
            "select name, home_page from `tabRole`", as_dict=True)}
        for name, old in before.items():
            if _norm(old) in STALE:
                self.assertIsNone(after[name], f"{name} should have been cleared")
            else:
                self.assertEqual(after[name], old, f"{name} changed but was not stale")


if __name__ == "__main__":
    unittest.main()
