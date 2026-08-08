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

#: module path -> minimum number of tests that must actually EXECUTE and pass.
#: Raise a floor when you add tests; never lower one to make a run green.
PROTECTED_SUITES = {
    "amb_w_tds.amb_w_tds.test_coa_spec_utils": 50,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
