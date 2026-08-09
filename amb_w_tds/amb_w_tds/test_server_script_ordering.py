"""Suite wrapper for the Server Script ordering invariant.

Two halves, and the second is the one that makes the first mean anything:

  · THE INVARIANT      each assertion in server_script_ordering runs against the
                       live site and must hold.
  · THE CONTROLS       each assertion is handed an injected fault and must go RED.
                       A check that has never been shown to fail is not evidence.
                       Faults are injected IN-PROCESS through provider arguments —
                       nothing here writes to the database, creates a Property
                       Setter, or modifies a doctype.

Needs a site (it reads meta, Property Setters and the resolver map), so unlike
`test_coa_spec_utils` it does NOT run standalone — `bench run-tests --app amb_w_tds`
is its home. That is why it is deliberately NOT registered in
`test_suite_integrity.PROTECTED_SUITES`: that guard runs its protected suites
in-process to assert what executed, and coupling a site-free guard to a
site-dependent suite would make the guard fail wherever no site is bootstrapped.
"""

import types
import unittest

from amb_w_tds.amb_w_tds import server_script_ordering as C


def _meta(sort_field, sort_order):
    """A stand-in for frappe.get_meta(...) carrying an injected fault."""
    m = types.SimpleNamespace(sort_field=sort_field, sort_order=sort_order)
    return lambda: m


class TestServerScriptOrderingInvariant(unittest.TestCase):
    """The invariant itself, against the live site."""

    def test_a1_emitted_sql_orders_by_creation_desc(self):
        self.assertIn("ORDER BY", C.a1_emitted_sql())

    def test_a2_meta_pair_is_creation_desc(self):
        self.assertIn("creation", C.a2_meta_pair())

    def test_a3_sort_field_explicit_and_single_term(self):
        C.a3_explicitly_set()

    def test_a4_no_overriding_property_setter(self):
        C.a4_no_property_setter()

    def test_a5_not_short_circuited_by_core_doctypes(self):
        C.a5_not_short_circuited()

    def test_a6_contested_endpoints_resolve_to_pinned_winner(self):
        C.a6_winner_map()

    def test_a7_contested_set_matches_pinned_set(self):
        C.a7_census_matches()

    def test_a8_provenance_is_homogeneous(self):
        C.a8_provenance_homogeneous()

    def test_full_run_reports_every_assertion(self):
        lines = C.run()
        self.assertGreaterEqual(len(lines), len(C.ASSERTIONS))


class TestServerScriptOrderingControls(unittest.TestCase):
    """Every assertion must be able to FAIL. These are the coverage denominator."""

    def _refutes(self, fn):
        with self.assertRaises(C.InvariantViolation):
            fn()

    # --- the two modes the ruling named -----------------------------------
    def test_control_sort_field_modified(self):
        self._refutes(lambda: C.a2_meta_pair(_meta("modified", "DESC")))

    def test_control_sort_field_absent(self):
        """Durability, not correctness — absent is behaviourally identical to
        'creation' because of the or-defaults. It fails because depending on a
        library default is not the same as depending on a stored value."""
        self._refutes(lambda: C.a3_explicitly_set(_meta(None, "DESC")))

    # --- the modes that were NOT on the named list -------------------------
    def test_control_sort_order_asc_reverses_the_winner(self):
        self._refutes(lambda: C.a2_meta_pair(_meta("creation", "ASC")))

    def test_control_sort_order_trailing_space(self):
        """'DESC ' flips direction in the compat branch, so the check is
        deliberately less tolerant than the consumer: no strip(), no lower()."""
        self._refutes(lambda: C.a2_meta_pair(_meta("creation", "DESC ")))

    def test_control_multi_sort_comma_form(self):
        self._refutes(lambda: C.a3_explicitly_set(_meta("creation desc, name asc", "DESC")))

    def test_control_emitted_sql_has_no_order_by(self):
        self._refutes(lambda: C.a1_emitted_sql(
            sql_provider=lambda: "SELECT `name` FROM `tabServer Script` WHERE `disabled`=0"))

    def test_control_emitted_sql_orders_by_modified(self):
        self._refutes(lambda: C.a1_emitted_sql(
            sql_provider=lambda: "SELECT `name` FROM `tabServer Script` ORDER BY `modified` DESC"))

    def test_control_property_setter_override(self):
        self._refutes(lambda: C.a4_no_property_setter(count_provider=lambda dt: 1))

    def test_control_property_setter_detector_is_broken(self):
        """If the detector returns 0 for a doctype known to carry one, its zero
        for Server Script means nothing. A detector needs a positive."""
        self._refutes(lambda: C.a4_no_property_setter(count_provider=lambda dt: 0))

    def test_control_core_doctypes_tautology(self):
        self._refutes(lambda: C.a5_not_short_circuited(core_provider=lambda: {C.DOCTYPE}))

    def test_control_winner_swaps(self):
        swapped = dict(C.EXPECTED_WINNERS)
        swapped["patch_raven_permissions"] = "Raven Channel Permission Fix"
        self._refutes(lambda: C.a6_winner_map(map_provider=lambda: swapped))

    def test_control_a_contest_disappears(self):
        self._refutes(lambda: C.a7_census_matches(
            rows_provider=lambda: [{"api_method": "patch_raven_permissions", "c": 2}]))

    def test_control_a_new_contest_appears(self):
        self._refutes(lambda: C.a7_census_matches(
            rows_provider=lambda: [{"api_method": k, "c": 2}
                                   for k in list(C.EXPECTED_WINNERS) + ["brand_new_api"]]))

    def test_control_mixed_provenance_fixture_and_db_only(self):
        self._refutes(lambda: C.a8_provenance_homogeneous(prov_provider=lambda: {
            "patch_raven_permissions": {"Raven Channel Permission Patch - Global": "DB-ONLY",
                                        "Raven Channel Permission Fix": "amb_w_tds"}}))

    def test_control_split_provenance_across_two_apps(self):
        self._refutes(lambda: C.a8_provenance_homogeneous(prov_provider=lambda: {
            "x": {"a": "amb_w_tds", "b": "amb_w_spc"}}))

    def test_controls_cover_every_assertion(self):
        """Guards the control set itself: if an assertion is added to the module
        without a control, this fails. Otherwise the next assertion arrives
        unproven and nobody notices."""
        covered = {"a1_emitted_sql", "a2_meta_pair", "a3_explicitly_set",
                   "a4_no_property_setter", "a5_not_short_circuited",
                   "a6_winner_map", "a7_census_matches", "a8_provenance_homogeneous"}
        declared = {fn.__name__ for fn in C.ASSERTIONS}
        self.assertEqual(declared, covered,
                         f"assertions without a positive control: {declared - covered}")
