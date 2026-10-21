"""Clear pre-v16 `Role.home_page` values that now 404 at the site root.

Nine rows carry routes that were valid before v16 and are not any more; a user
holding such a role lands on a 404 instead of the desk. Clearing the field makes
the role fall through to the site default, which is what the other 93 roles
already do (`home_page` NULL).

⚠ The comparison MUST be normalised. The stale set is written unslashed, but the
database stores `/app` and `/app/stock-entry` WITH a leading slash: a raw
equality test matches only 2 of the 9 rows and silently leaves 7 behind -- and,
used as a gate, would have reported 7 perfectly ordinary rows as values "outside
the set" (Node C, P1). So both sides are stripped of surrounding whitespace and
leading/trailing slashes before comparing. Normalising can only ever make MORE
values match the stale set; it can never pull in a route that is not in it.

Only members of STALE are touched. Anything else -- `/custom-portal`, a real
Workspace route, an app page -- is left exactly as found. The patch never
commits: `bench migrate` owns the transaction, and a patch that commits on its
own removes the caller's ability to roll back (learned the hard way on
g0b2a_backfill_coa_batch_links).
"""
import frappe

# Routes that pre-date v16 and now resolve to nothing.
STALE = frozenset({"app", "app/stock-entry", "app/stock", "desktop", "desk/stock"})


def _norm(value):
    """`/app/` -> `app`. Returns "" for NULL/blank so it can never match STALE."""
    return (value or "").strip().strip("/")


def execute():
    # NULL-safe: `home_page != ''` alone would drop NULL rows on some backends,
    # and `is not null` alone would keep empties. Both, explicitly.
    rows = frappe.db.sql("""
        select name, home_page
          from `tabRole`
         where home_page is not null
           and home_page != ''
    """, as_dict=True)

    log = []
    for row in rows:
        if _norm(row.home_page) not in STALE:
            continue
        frappe.db.set_value("Role", row.name, "home_page", None,
                            update_modified=False)
        log.append(f"Role {row.name} · home_page · {row.home_page!r} -> None")

    # No commit here -- see the module docstring.
    for line in log:
        print(line)
    print(f"clear_stale_role_home_page: {len(log)} cleared, "
          f"{len(rows) - len(log)} left untouched")
    return log
