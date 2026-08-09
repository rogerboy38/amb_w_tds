"""Fleet invariant: Server Script duplicate-api_method arbitration must not silently swap.

Landed into the suite on Hugh's ruling (letter 832d28e9), after the repair to
`tests/test_agent.py` unblocked app-level test collection. Exercised by
`test_server_script_ordering.py`, which also asserts every one of these
assertions can FAIL.

WHAT IT GUARDS
--------------
When two enabled Server Scripts share an api_method, exactly one serves the
endpoint. The winner is decided by row order in a plain dict assign:

    frappe/core/doctype/server_script/server_script_utils.py:71-84
        enabled = frappe.get_all("Server Script", ..., filters={"disabled": 0})
        for script in enabled: ... else: script_map["_api"][api_method] = script.name

so the LAST row iterated wins. Today the order is `creation DESC`, hence the
OLDEST enabled row wins. Flip the ordering and every duplicated endpoint serves a
different body, with no error and no log line.

WHERE THE ORDER ACTUALLY COMES FROM  (corrected — see below)
------------------------------------------------------------
    frappe/__init__.py:1360      get_list -> frappe.model.qb_query.DatabaseQuery
    frappe/database/query.py     apply_order_by -> _apply_default_order_by
    frappe/database/utils.py:61  get_doctype_sort_info -> frappe.get_meta(dt).sort_field/sort_order

`frappe/model/db_query.py` is a PARALLEL LEGACY implementation and is NOT the
production path — `get_all`'s own docstring still claims otherwise, which is how
the wrong module got cited in the first place. The conclusion survives (the
doctype's own meta decides, not a library default); only the citation moved.

WHY THIS IS UNCONDITIONAL AND NOT TRIGGERED BY migration_hash
-------------------------------------------------------------
The hash is md5 of server_script.json. Of the ways the effective ordering can
change, it moves for exactly one — an upstream edit to that file — and that one
is already visible in a git diff. It does NOT move for: a Property Setter,
db.set_value on tabDocType, a developer-mode form edit, a DB restore from another
tier (which imports the source tier's hash AND sort_field together, pre-agreed),
reload_doc(force=True), or a fixture insert minting a fresh `creation`. Worse,
when drift arrives by a DB-side path the hash still matches the file, so
import_file.py:137 hits `continue` and migrate will never repair it.

A trigger that fires mostly when nothing is wrong and stays silent for most of
the ways things go wrong is not a detector. The hash is kept as a REPORTED
DIAGNOSTIC: hash-matches-file while an assertion fails is the loudest possible
signal, because it means drift entered by a route migrate now actively refuses to
heal.
"""

import frappe

DOCTYPE = "Server Script"
EXPECTED_SORT_FIELD = "creation"
EXPECTED_SORT_ORDER = "DESC"
EXPECTED_ORDER_BY_SUFFIX = "ORDER BY `creation` DESC"

#: api_methods with more than one ENABLED row, and the row that must win.
#: Pinned as a literal: a census that silently goes empty would make the
#: winner assertions vacuous.
EXPECTED_WINNERS = {
    "/api/method/sales_order_webhook.handler": "Sales Order Webhook Handler",
    "patch_raven_permissions": "Raven Channel Permission Patch - Global",
}

#: A doctype that really does carry a DocType-level sort_field Property Setter,
#: used to prove the Property-Setter detector can return a POSITIVE. A detector
#: that has only ever returned zero has no coverage denominator.
PS_POSITIVE_CONTROL_DOCTYPE = "Quality Inspection Parameter Group"


class InvariantViolation(AssertionError):
    """Raised on any violation. Never caught inside this module."""


def _fail(code, msg):
    raise InvariantViolation(f"[{code}] {msg}")


# --------------------------------------------------------------------------
# The assertions. Each returns a line for the report; each raises on failure.
# No try/except anywhere reaches a pass — an exception is a FAILURE, never a skip.
# --------------------------------------------------------------------------

def a1_emitted_sql(meta_provider=None, sql_provider=None):
    """PRIMARY. Assert the SQL frappe will actually emit for the resolver's own query.

    Downstream of sort_field, sort_order, the comma branch, Property Setters,
    the CORE_DOCTYPES short-circuit and the meta cache simultaneously. It cannot
    be satisfied by a value that merely looks right.
    """
    if sql_provider is not None:
        sql = sql_provider()
    else:
        import frappe.model.qb_query as qb
        sql = str(qb.DatabaseQuery(DOCTYPE).execute(
            fields=("name", "reference_doctype", "doctype_event", "api_method", "script_type"),
            filters={"disabled": 0}, ignore_permissions=True,
            limit_page_length=0, run=False))
    if "ORDER BY" not in sql.upper():
        _fail("A1", f"resolver query emits NO ORDER BY at all: {sql}")
    if not sql.rstrip().endswith(EXPECTED_ORDER_BY_SUFFIX):
        _fail("A1", f"emitted ordering is not {EXPECTED_ORDER_BY_SUFFIX!r}: {sql}")
    return f"A1 emitted SQL ends with {EXPECTED_ORDER_BY_SUFFIX!r}"


def a2_meta_pair(meta_provider=None):
    """Byte-exact on BOTH halves. sort_order is load-bearing: ASC reverses the winner.

    No .strip(), no .lower(). A trailing space in sort_order flips direction in
    the compat branch, and a normalising check would hide exactly that.
    """
    meta = (meta_provider or (lambda: frappe.get_meta(DOCTYPE)))()
    sf, so = meta.sort_field, meta.sort_order
    if sf != EXPECTED_SORT_FIELD:
        _fail("A2", f"sort_field is {sf!r}, expected {EXPECTED_SORT_FIELD!r}")
    if so != EXPECTED_SORT_ORDER:
        _fail("A2", f"sort_order is {so!r}, expected {EXPECTED_SORT_ORDER!r} (byte-exact)")
    return f"A2 meta pair == ({sf!r}, {so!r})"


def a3_explicitly_set(meta_provider=None):
    """DURABILITY, not correctness — and the distinction is stated, not blurred.

    An ABSENT sort_field is behaviourally IDENTICAL to 'creation': the
    `or "creation"` / `or "DESC"` defaults in get_doctype_sort_info make it so.
    Asserting that absence is a *correctness* failure would be asserting a
    distinction that does not exist, and the first reviewer to test it would
    rightly delete the check.

    It still fails here, for a different and defensible reason: an absent value
    means the fleet depends on a library default rather than on a stored,
    diffable, migration-visible one, and it produces no diff when that default
    changes upstream.
    """
    meta = (meta_provider or (lambda: frappe.get_meta(DOCTYPE)))()
    if not meta.sort_field:
        _fail("A3", "sort_field is absent/empty — behaviourally equal to 'creation' today, "
                    "but it makes the fleet depend on a library default that changes silently")
    if "," in meta.sort_field:
        _fail("A3", f"sort_field {meta.sort_field!r} is the multi-sort comma form, which takes a "
                    f"different branch and ignores sort_order entirely")
    return "A3 sort_field is explicitly set and single-term"


def a4_no_property_setter(count_provider=None):
    """A Property Setter overrides meta while tabDocType, the JSON and the hash all still read
    'creation'. Live precedent on this fleet, so this is not hypothetical."""
    counter = count_provider or (lambda dt: frappe.db.count(
        "Property Setter", {"doc_type": dt, "property": ["in", ("sort_field", "sort_order")]}))
    n = counter(DOCTYPE)
    if n:
        _fail("A4", f"{n} Property Setter(s) override sort_field/sort_order on {DOCTYPE} — "
                    f"these beat both the DocType row and the shipped JSON")
    # coverage denominator: prove the same query CAN return a positive
    if counter(PS_POSITIVE_CONTROL_DOCTYPE) < 1:
        _fail("A4", f"Property-Setter detector returned 0 for {PS_POSITIVE_CONTROL_DOCTYPE!r}, "
                    f"which is known to carry one. The detector is not working; its zero for "
                    f"{DOCTYPE} therefore means nothing.")
    return "A4 zero overriding Property Setters (detector positive-controlled)"


def a5_not_short_circuited(core_provider=None):
    """If the doctype ever joins CORE_DOCTYPES, get_doctype_sort_info returns a hardcoded
    ('creation','DESC') and never reads meta — every value assertion becomes a tautology."""
    core = (core_provider or (lambda: __import__(
        "frappe.database.query", fromlist=["CORE_DOCTYPES"]).CORE_DOCTYPES))()
    if DOCTYPE in core:
        _fail("A5", f"{DOCTYPE} is in CORE_DOCTYPES — sort_field is no longer consulted, "
                    f"so A2/A3 have become tautologies")
    return "A5 not short-circuited by CORE_DOCTYPES"


def a6_winner_map(map_provider=None):
    """The ONLY assertion that survives a change with no metadata footprint.

    Server Script is a fixture doctype in two installed apps and the exporter strips
    `creation`, so a fixture insert mints a FRESH creation stamp at migrate time.
    That reorders the winner while sort_field, sort_order, the JSON, the Property
    Setters and migration_hash are all untouched. Only pinning the resolved winner
    catches it.
    """
    from frappe.core.doctype.server_script.server_script_utils import get_server_script_map
    if map_provider is not None:
        api_map = map_provider()
    else:
        frappe.client_cache.delete_value("server_script_map")   # never trust the cached map
        api_map = get_server_script_map().get("_api", {})
    if not EXPECTED_WINNERS:
        _fail("A6", "EXPECTED_WINNERS is empty — the assertion would be vacuous")
    for api_method, expected in EXPECTED_WINNERS.items():
        actual = api_map.get(api_method)
        if actual != expected:
            _fail("A6", f"{api_method!r} now resolves to {actual!r}, expected {expected!r}")
    return f"A6 all {len(EXPECTED_WINNERS)} contested endpoints resolve to the pinned winner"


def a7_census_matches(rows_provider=None):
    """Guards A6 against going vacuous: if a `disabled` flip removes a contest, A6's loop
    would pass having verified nothing. NULL api_method excluded explicitly, not incidentally."""
    if rows_provider is not None:
        rows = rows_provider()
    else:
        rows = frappe.db.sql("""
            SELECT api_method, COUNT(*) c FROM `tabServer Script`
             WHERE disabled = 0 AND script_type = 'API'
               AND api_method IS NOT NULL AND api_method != ''
             GROUP BY api_method HAVING c > 1""", as_dict=True)
    contested = {r["api_method"] for r in rows}
    if contested != set(EXPECTED_WINNERS):
        _fail("A7", f"contested api_method set changed: {sorted(contested)} != "
                    f"{sorted(EXPECTED_WINNERS)}")
    return f"A7 contested set == pinned set ({len(contested)} entries)"


def a8_provenance_homogeneous(prov_provider=None):
    """Assert the PRECONDITION of the ratchet, not the failure.

    Fixture-shipped rows are delete+reinserted with a freshly minted `creation`
    (the exporter strips it; `Server Script` is not in import_file's ignore_values).
    So a contested api_method whose twins have DIFFERENT provenance — one
    fixture-shipped, one DB-only, or two different apps' fixture files — has its
    winner decided by import mechanics rather than by anything anyone chose, and
    the fixture-shipped twin is re-aged to *now* on every import.

    No such pair exists today (measured: 2 pairs both-DB-only, 2 pairs same-file),
    so this fires BEFORE the hazard has an instance rather than after it has fired
    once. That is the whole point of asserting the precondition.
    """
    import json, os
    if prov_provider is not None:
        prov = prov_provider()
    else:
        rosters = {}
        for app in frappe.get_installed_apps():
            p = os.path.join(frappe.get_app_path(app), "fixtures", "server_script.json")
            if os.path.exists(p):
                rosters[app] = {r.get("name") for r in json.load(open(p))}

        def provenance(name):
            for app, names in rosters.items():
                if name in names:
                    return app
            return "DB-ONLY"

        prov = {}
        for api in EXPECTED_WINNERS:
            names = frappe.db.sql_list(
                "SELECT name FROM `tabServer Script` WHERE api_method=%s", api)
            prov[api] = {n: provenance(n) for n in names}

    for api, twins in prov.items():
        sources = set(twins.values())
        if len(sources) > 1:
            _fail("A8", f"{api!r} has MIXED provenance {twins} — its winner is decided by import "
                        f"mechanics, and the fixture-shipped twin is re-aged on every import")
    return f"A8 all {len(prov)} contested endpoints have homogeneous provenance"


ASSERTIONS = (a1_emitted_sql, a2_meta_pair, a3_explicitly_set,
              a4_no_property_setter, a5_not_short_circuited, a6_winner_map,
              a7_census_matches, a8_provenance_homogeneous)


def run():
    """Run every assertion. Returns the report lines; raises InvariantViolation on any failure.

    Deliberately no try/except: a DB error, a missing doctype or a cold cache must
    surface as a hard failure, never as a pass and never as a skip.
    """
    lines = [fn() for fn in ASSERTIONS]
    # diagnostic only — never a gate, for the reasons in the module docstring
    import hashlib, os
    p = os.path.join(frappe.get_app_path("frappe"), "core", "doctype",
                     "server_script", "server_script.json")
    file_md5 = hashlib.md5(open(p, "rb").read(), usedforsecurity=False).hexdigest()
    stored = frappe.db.get_value("DocType", DOCTYPE, "migration_hash")
    lines.append(f"[diagnostic] migration_hash={stored} file_md5={file_md5} "
                 f"{'MATCH' if stored == file_md5 else 'DIFFER'}")
    return lines
