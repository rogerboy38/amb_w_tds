"""Guard: `frappe.log_error()` must be given a CONSTANT title.

THE DEFECT THIS EXISTS TO PREVENT
---------------------------------
`frappe.log_error(title, message)` writes `title` into `Error Log.method`, which
is a `varchar(140)`. Passing the long detail string first puts it in that column.
frappe has a swap heuristic (`frappe/utils/error.py:48-52`) but it only fires
when the title contains a NEWLINE, so a single-line f-string is never rescued.

What follows is not hypothetical -- it was reproduced on this bench:

    Error Log.validate()      truncates method to 140      error_log.py:32-34
    document.py:792  _validate_length()   PASSES           140 == varchar(140)
    document.py:797  _sanitize_content()  -> 149           BeautifulSoup closes
                                                           the split-open tag
    => over by 9 -> (1406) Data too long

and the 1406 is raised from inside the `except` block that was written to
CONTAIN the original error, so it escapes the handler and can abort the caller.
That is exactly how a routine, contained error terminated roughly half of one
scheduled job's hourly runs in this fleet (172 occurrences in 14 days).

The trigger is narrow -- the 140-char boundary must land just after an unclosed
tag -- but the invariant here does not depend on the trigger: if the title is a
short literal, the column cannot overflow no matter what the payload does.

THE INVARIANT
-------------
The `title` argument (first positional, or `title=`) must be a string LITERAL of
at most 140 characters. Calls passing no title at all are fine: frappe defaults
to "Error" and captures the real traceback.

Deliberately mechanical, with no special cases. Some baselined calls below are
harmless in practice -- three pass `frappe.get_traceback()`, whose newlines DO
trigger frappe's swap -- but a checker that reasons about which unbounded titles
happen to be safe is a checker with holes in it. Constant or flagged.

THIS IS A RATCHET, NOT A CLEAN BILL OF HEALTH
---------------------------------------------
80 non-conforming calls across 26 files exist today and are frozen in
KNOWN_DEBT. The guard fails if any file gains one, if an unlisted file has one,
and ALSO if a file has fewer than its baseline -- because a stale baseline
overstates the debt and quietly stops being a measurement. Fix a file, lower its
number in the same commit; when it reaches zero, delete the entry.

Site-free (pure AST over the source tree), so it belongs in tier 1 of
`test_suite_integrity.PROTECTED_SUITES`.
"""

import ast
import collections
import pathlib
import unittest

#: Repo root: .../apps/amb_w_tds  (this file is <root>/amb_w_tds/amb_w_tds/)
APP_ROOT = pathlib.Path(__file__).resolve().parents[2]

MAX_TITLE_LEN = 140          # Error Log.method is varchar(140)

#: Coverage floors. A scan that silently walks nothing reports zero violations
#: and looks identical to a clean tree -- these make that impossible.
MIN_FILES_SCANNED = 200
MIN_CALLS_FOUND = 100

#: file (relative to APP_ROOT) -> number of non-conforming log_error titles.
#: Frozen 2026-08-10. Lower these as they are fixed; never raise one to go green.
KNOWN_DEBT = {
    "amb_w_tds/amb_w_tds/api/barrel_bulk_operations.py": 3,
    "amb_w_tds/amb_w_tds/api/batch_api.py": 2,
    "amb_w_tds/amb_w_tds/api/bom_integration.py": 4,
    "amb_w_tds/amb_w_tds/api/bom_tree_fix.py": 1,
    "amb_w_tds/amb_w_tds/api/container_api.py": 5,
    "amb_w_tds/amb_w_tds/api/plant_management.py": 4,
    "amb_w_tds/amb_w_tds/doctype/barrel/barrel.py": 1,
    "amb_w_tds/amb_w_tds/doctype/certification_document/certification_document.py": 2,
    "amb_w_tds/amb_w_tds/doctype/coa_amb2/coa_amb2.py": 15,
    "amb_w_tds/amb_w_tds/doctype/container_selection/container_selection.py": 2,
    "amb_w_tds/amb_w_tds/doctype/product_compliance/product_compliance.py": 2,
    "amb_w_tds/amb_w_tds/doctype/tds_product_specification/tds_product_specification.py": 1,
    "amb_w_tds/amb_w_tds/doctype/tds_settings/tds_settings.py": 5,
    "amb_w_tds/amb_w_tds/stock_entry_hooks.py": 2,
    "amb_w_tds/api/batch_api.py": 1,
    "amb_w_tds/api/bom_integration.py": 4,
    "amb_w_tds/api/container_api.py": 5,
    "amb_w_tds/api/plant_management.py": 4,
    "amb_w_tds/api/validate.py": 1,
    "amb_w_tds/bom_hooks.py": 4,
    "amb_w_tds/coa_qr.py": 3,
    "amb_w_tds/migrations/foxpro_migration.py": 2,
    "amb_w_tds/raven/serial_tracking_agent_final.py": 3,
    "amb_w_tds/scripts/bom_audit_agent.py": 1,
    "amb_w_tds/services/bom_service.py": 2,
    "scripts/create_innovaloe_boms.py": 1,
}

#: Files that must be and stay at zero. coa_amb.py was fixed in 45f00b8 (15
#: sites); naming it explicitly means a regression there fails with a message
#: about coa_amb.py rather than as an anonymous baseline delta.
MUST_BE_CLEAN = (
    "amb_w_tds/amb_w_tds/doctype/coa_amb/coa_amb.py",
)


def _title_node(call):
    """The AST node passed as `title`, or None when the call passes no title."""
    for keyword in call.keywords:
        if keyword.arg == "title":
            return keyword.value
    if call.args:
        return call.args[0]
    return None


def _is_conforming(node):
    """True when the title is a string literal within the column width."""
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and len(node.value) <= MAX_TITLE_LEN
    )


def scan_source(source):
    """Line numbers of non-conforming `log_error` titles, plus the total seen.

    Returns ``(violations, total_calls)``. Raises SyntaxError to its caller --
    an unparsable file must be loud, never silently counted as clean.
    """
    tree = ast.parse(source)
    violations, total = [], 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name)
            else None
        )
        if name != "log_error":
            continue
        total += 1
        title = _title_node(node)
        if title is None:                 # log_error() -> title defaults to "Error"
            continue
        if not _is_conforming(title):
            violations.append(node.lineno)
    return violations, total


#: Result of one walk of the app.
ScanResult = collections.namedtuple(
    "ScanResult", "per_file files_scanned calls_found unparsable"
)


def scan_app():
    """Walk the app.

    A file that will not parse is COLLECTED, not raised past: letting the
    SyntaxError escape aborts setUpClass, so the dedicated parse test never runs
    and the operator gets a stack trace instead of the filename. It is still a
    hard failure -- see `test_every_file_parses` -- but a precise one, and the
    other 17 assertions still report. An unparsable file contributes no
    violations, which is exactly why that test must stay loud.
    """
    per_file = collections.Counter()
    files_scanned = 0
    calls_found = 0
    unparsable = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if "/node_modules/" in str(path):
            continue
        files_scanned += 1
        source = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(APP_ROOT))
        try:
            violations, total = scan_source(source)
        except SyntaxError as exc:
            unparsable.append(f"{rel}: {exc.msg} (line {exc.lineno})")
            continue
        calls_found += total
        if violations:
            per_file[rel] = len(violations)
    return ScanResult(per_file, files_scanned, calls_found, unparsable)


class TestScannerItself(unittest.TestCase):
    """Positive controls. A guard whose detector is broken reports a clean tree.

    Every assertion below is paired: something that MUST be flagged, and
    something that MUST NOT be, so neither a dead detector nor a
    flag-everything detector can pass this class.
    """

    def test_fstring_title_is_flagged(self):
        src = 'frappe.log_error(f"failed: {e}", "Short Title")'
        self.assertEqual(scan_source(src)[0], [1])

    def test_variable_title_is_flagged(self):
        src = 'frappe.log_error(msg, "Short Title")'
        self.assertEqual(scan_source(src)[0], [1])

    def test_call_expression_title_is_flagged(self):
        src = 'frappe.log_error(frappe.get_traceback(), "Short Title")'
        self.assertEqual(scan_source(src)[0], [1])

    def test_single_argument_variable_title_is_flagged(self):
        """The form VM3 found 7 of in rnd_warehouse_management."""
        src = 'frappe.log_error(str(e))'
        self.assertEqual(scan_source(src)[0], [1])

    def test_overlong_literal_title_is_flagged(self):
        src = 'frappe.log_error("%s", "x")' % ("A" * (MAX_TITLE_LEN + 1))
        self.assertEqual(scan_source(src)[0], [1])

    def test_literal_title_positional_is_clean(self):
        src = 'frappe.log_error("COA Compliance Check", f"detail {e}")'
        self.assertEqual(scan_source(src)[0], [])

    def test_literal_title_keyword_is_clean(self):
        """The form coa_amb.py now uses at all 15 sites."""
        src = 'frappe.log_error(title="COA Compliance Check", message=f"detail {e}")'
        self.assertEqual(scan_source(src)[0], [])

    def test_no_title_is_clean(self):
        """`log_error()` bare is safe: title defaults to 'Error'."""
        src = 'frappe.log_error()'
        self.assertEqual(scan_source(src)[0], [])

    def test_keyword_title_wins_over_positional(self):
        src = 'frappe.log_error(f"long {e}", title="Short")'
        self.assertEqual(scan_source(src)[0], [])

    def test_unrelated_calls_are_ignored(self):
        src = 'frappe.msgprint(f"anything {e}")\nlogger.error(f"anything {e}")'
        self.assertEqual(scan_source(src), ([], 0))


class TestScanCoverage(unittest.TestCase):
    """The denominator. Zero violations from a scan of nothing is not a pass."""

    @classmethod
    def setUpClass(cls):
        cls.scan = scan_app()
        cls.per_file, cls.files, cls.calls = (
            cls.scan.per_file, cls.scan.files_scanned, cls.scan.calls_found
        )

    def test_app_root_resolves_to_the_app(self):
        self.assertTrue(
            (APP_ROOT / "amb_w_tds" / "hooks.py").is_file(),
            f"APP_ROOT {APP_ROOT} does not look like the amb_w_tds repo root; "
            f"the scan below would be measuring the wrong tree",
        )

    def test_enough_files_were_scanned(self):
        self.assertGreaterEqual(
            self.files, MIN_FILES_SCANNED,
            f"only {self.files} python files scanned (floor {MIN_FILES_SCANNED}). "
            f"A shrunken walk makes this guard silently vacuous.",
        )

    def test_enough_log_error_calls_were_found(self):
        self.assertGreaterEqual(
            self.calls, MIN_CALLS_FOUND,
            f"only {self.calls} log_error calls found (floor {MIN_CALLS_FOUND}). "
            f"If the detector stopped matching, every file reads as clean.",
        )

    def test_every_file_parses(self):
        """An unparsable file contributes no violations, so it must fail HERE.

        Without this, adding a file the scanner cannot read would reduce the
        measured debt and read as an improvement.
        """
        self.assertEqual(
            self.scan.unparsable, [],
            "python files the scanner could not parse (they are counted as "
            "having zero violations, so this is a hole, not a pass):\n  "
            + "\n  ".join(self.scan.unparsable),
        )


class TestLogErrorTitleRatchet(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.scan = scan_app()
        cls.per_file = cls.scan.per_file

    def test_named_files_are_clean(self):
        for rel in MUST_BE_CLEAN:
            with self.subTest(file=rel):
                self.assertEqual(
                    self.per_file.get(rel, 0), 0,
                    f"{rel} must pass a constant title to every frappe.log_error() "
                    f"call. It was fixed at 15 sites in 45f00b8; a long detail "
                    f"string in the title reaches Error Log.method (varchar 140) "
                    f"and can raise 1406 from inside the except block.",
                )

    def test_no_unlisted_file_has_violations(self):
        new = sorted(set(self.per_file) - set(KNOWN_DEBT) - set(MUST_BE_CLEAN))
        self.assertEqual(
            new, [],
            "new file(s) pass a non-constant title to frappe.log_error():\n  "
            + "\n  ".join(f"{f} ({self.per_file[f]})" for f in new)
            + "\nUse frappe.log_error(title='Short Constant', message=f'...detail...').",
        )

    def test_no_file_exceeds_its_baseline(self):
        worse = [
            (f, KNOWN_DEBT[f], self.per_file.get(f, 0))
            for f in KNOWN_DEBT
            if self.per_file.get(f, 0) > KNOWN_DEBT[f]
        ]
        self.assertEqual(
            worse, [],
            "log_error title debt INCREASED:\n  "
            + "\n  ".join(f"{f}: baseline {b} -> now {n}" for f, b, n in worse),
        )

    def test_baseline_is_not_stale(self):
        """Improvement must be recorded, or the baseline stops being a measurement.

        Failing here is good news: a file was fixed. Lower its number, or delete
        the entry when it reaches zero.
        """
        better = [
            (f, KNOWN_DEBT[f], self.per_file.get(f, 0))
            for f in KNOWN_DEBT
            if self.per_file.get(f, 0) < KNOWN_DEBT[f]
        ]
        self.assertEqual(
            better, [],
            "debt was REDUCED but KNOWN_DEBT still claims the old number:\n  "
            + "\n  ".join(f"{f}: baseline {b} -> now {n}" for f, b, n in better)
            + "\nLower the baseline in the same commit (delete the entry at 0).",
        )


if __name__ == "__main__":
    unittest.main()
