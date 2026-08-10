"""Suite-integrity guard — lives OUTSIDE the artifacts it certifies, and fails closed.

Replaces `TestSuiteIsNotEmpty`, which was refuted (VM3, 2026-08-08) on two grounds,
both reproduced before this file was written:

1. **It lived inside the module it certified.** If that module stops being
   collected, the class is never constructed and the assertion cannot fire.
   An import *break* is loud (unittest substitutes a `_FailedTest`), but a
   **rename or move** — the module no longer matching the `test_*.py` glob —
   removes it from discovery with nothing failing anywhere. That is the silent
   case, and it is the one a self-hosted assertion can never catch.

2. **It counted COLLECTABLE cases, not EXECUTED ones.** Measured:
   `python -m unittest ...TestSuiteIsNotEmpty` reported "Ran 1 test ... OK",
   exit 0, while asserting that 51 existed. One test executed, 51 certified.

The rule this file obeys: *a robust assertion lives outside the artifact it
checks, imports its target by name so absence is an error in the guard itself,
and asserts what actually RAN.*

Known limit, stated rather than papered over: this guard cannot certify its own
presence. If THIS file is deleted or renamed, nothing here fires. Closing that
last gap needs a check outside the test suite entirely — a committed file list
in CI — which is not this file's job and is not pretended here.
"""

import importlib
import io
import unittest

#: TIER 1 — module path -> minimum number of tests that must actually EXECUTE and pass.
#: These suites are RUN in-process here, so they must not need a site.
#: Raise a floor when you add tests; never lower one to make a run green.
PROTECTED_SUITES = {
    "amb_w_tds.amb_w_tds.test_coa_spec_utils": 50,
    "amb_w_tds.amb_w_tds.test_log_error_title": 18,
}

#: TIER 2 — module path -> minimum number of test METHODS that must EXIST.
#: These are imported and counted, NEVER RUN.
#:
#: Two questions were being answered by one mechanism — *did it run* and *is it
#: still there* — and only the first was guarded. A site-dependent suite cannot
#: join tier 1, because running it here would make this guard fail wherever no
#: site is bootstrapped; that would trade a working site-free instrument for a
#: tidier list. But excluding it from tier 1 is not a reason to leave it with no
#: floor at all: by this file's own rule it could then be renamed or emptied and
#: vanish from discovery with nothing failing anywhere.
#:
#: Importing is site-free even for a site-dependent suite — these modules import
#: `frappe` but call nothing at import time — so tier 2 closes the silent-vanish
#: gap without coupling the tiers.
PRESENT_SUITES = {
    "amb_w_tds.amb_w_tds.test_server_script_ordering": 25,
}


class TestSuiteIntegrity(unittest.TestCase):

    def test_protected_modules_are_importable(self):
        """Import by name. A rename, move or broken import fails HERE.

        This is the half the old self-hosted assertion could not do: the
        failure surfaces in a module that is still being collected.
        """
        for module_path in PROTECTED_SUITES:
            with self.subTest(module=module_path):
                try:
                    importlib.import_module(module_path)
                except Exception as exc:                    # noqa: BLE001
                    self.fail(
                        f"protected suite '{module_path}' is no longer importable "
                        f"({type(exc).__name__}: {exc}). It has been renamed, moved "
                        f"or broken, and would silently vanish from discovery."
                    )

    def test_protected_suites_actually_execute(self):
        """Run each protected suite and assert on tests that RAN, not that were found.

        `countTestCases()` is satisfied by collection alone, which is how the
        previous guard certified 51 while executing 1.
        """
        for module_path, floor in PROTECTED_SUITES.items():
            with self.subTest(module=module_path):
                module = importlib.import_module(module_path)
                suite = unittest.TestLoader().loadTestsFromModule(module)
                collected = suite.countTestCases()

                runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)
                result = runner.run(suite)

                self.assertTrue(
                    result.wasSuccessful(),
                    f"{module_path}: {len(result.failures)} failure(s), "
                    f"{len(result.errors)} error(s)",
                )
                # `testsRun` is incremented in startTest, which fires for SKIPPED
                # tests too, and wasSuccessful() is True when every outcome is a
                # skip. So testsRun alone still certifies a suite that executed
                # nothing — collected=50, testsRun=50, skipped=50 passes both
                # assertions above. Reproduced before this line was written.
                # Subtracting skips is what makes "executed" mean executed.
                # This matters concretely: @skipUnless is the standard repair for
                # the app-level discovery blocker, so the skip path is the one
                # this suite is most likely to meet.
                executed = result.testsRun - len(result.skipped)
                self.assertEqual(
                    len(result.skipped), 0,
                    f"{module_path}: {len(result.skipped)} of {result.testsRun} "
                    f"tests were SKIPPED. A protected suite must actually run; "
                    f"skips are the collected-but-not-executed failure mode.",
                )
                self.assertGreaterEqual(
                    executed, floor,
                    f"{module_path}: only {executed} tests EXECUTED "
                    f"(testsRun {result.testsRun}, skipped {len(result.skipped)}), "
                    f"floor is {floor} (collected {collected})",
                )
                self.assertEqual(
                    result.testsRun, collected,
                    f"{module_path}: collected {collected} but executed "
                    f"{result.testsRun} — some cases were not run at all",
                )


class TestPresentSuiteIntegrity(unittest.TestCase):
    """Tier 2: the suite still EXISTS and still has its tests. Never runs them."""

    def test_present_modules_are_importable(self):
        """A rename or move fails HERE, in a module that is still collected."""
        for module_path in PRESENT_SUITES:
            with self.subTest(module=module_path):
                try:
                    importlib.import_module(module_path)
                except Exception as exc:                    # noqa: BLE001
                    self.fail(
                        f"present suite '{module_path}' is no longer importable "
                        f"({type(exc).__name__}: {exc}). It has been renamed, moved "
                        f"or broken, and would silently vanish from discovery."
                    )

    def test_present_suites_still_have_their_tests(self):
        """Count test methods without running them.

        `loadTestsFromModule` only constructs cases — it does not execute them —
        so this stays site-free even for a suite that needs a site to run.

        A module that imports but is EMPTY must be RED, not green: present-and-zero
        is the same green-on-nothing shape one tier along, and it is what a
        half-completed deletion looks like.
        """
        for module_path, floor in PRESENT_SUITES.items():
            with self.subTest(module=module_path):
                module = importlib.import_module(module_path)
                found = unittest.TestLoader().loadTestsFromModule(module).countTestCases()
                self.assertGreater(
                    found, 0,
                    f"{module_path} imports but declares NO tests — present and empty "
                    f"is not present",
                )
                self.assertGreaterEqual(
                    found, floor,
                    f"{module_path} declares {found} tests, floor is {floor} — "
                    f"tests have been removed",
                )

    def test_tiers_are_disjoint(self):
        """A module in both tiers would be run by tier 1 and counted by tier 2 —
        the tier-2 floor would then silently duplicate a tier-1 guarantee and
        drift out of step with it."""
        overlap = set(PROTECTED_SUITES) & set(PRESENT_SUITES)
        self.assertEqual(overlap, set(), f"module registered in BOTH tiers: {overlap}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
