"""M3.5 substrate baseline install — Task #67 (2026-05-29).

Formalizes the in-DB substrate tagging on leaf Quality Inspection Parameter Group
rows that was built up incrementally via Tasks #32 + #43 (initial M3.5) and
expanded in Task #65 (LQD → PWD bulk backfill).

Idempotent: only adds Parameter Group Substrate rows that don't already exist
on each QIPG. Running twice produces zero new rows on the second pass.

Policy:
  - Default: all 5 substrates apply (LQD, LQDC, LQDF, PWD, PWDF)
  - Exception (5 QIPGs matching Specific Gravity / Total Solids name pattern):
    LQD family only (LQD, LQDC, LQDF) — liquid-only parameters per Alicia's
    2026-05-27 substrate model

VM3 ↔ vpt intentional divergence (Hugh, 2026-05-29):
  VM3 currently has the 5 SG/TS QIPGs with all 5 substrates (legacy state).
  This patch leaves VM3 unchanged on those leaves: target=LQD_FAMILY,
  existing={all 5} → missing=LQD_FAMILY - {all 5} = ∅, no rows added.
  On vpt fresh install, the same QIPGs land with LQD_FAMILY only — the
  "correct future state" pending Alicia retroactive ratification.

Anomaly: 4 untagged leaf QIPGs (per Task #67 Phase A audit, 403/407 tagged).
The patch will tag them with ALL_SUBSTRATES on first run.
"""
import frappe


LQD_FAMILY = ["LQD", "LQDC", "LQDF"]
ALL_SUBSTRATES = ["LQD", "LQDC", "LQDF", "PWD", "PWDF"]

# Name-pattern keywords (lowercase compare) — matches both accented and
# unaccented Spanish + English variants found in production data.
LIQUID_ONLY_KEYWORDS = (
    "specific gravity",
    "gravedad específica",
    "gravedad especifica",
    "total solids",
    "sólidos totales",
    "solidos totales",
)


def execute():
    # T117 guard: skip if the QIPG NestedSet schema isn't present on this site
    if not frappe.db.table_exists("Quality Inspection Parameter Group") or \
       "is_group" not in frappe.db.get_table_columns("Quality Inspection Parameter Group"):
        frappe.logger().warning("M3.5 baseline (T117): QIPG.is_group absent — skipping")
        return
    leaves = frappe.db.sql(
        """
        SELECT name
        FROM `tabQuality Inspection Parameter Group`
        WHERE is_group = 0
        ORDER BY name
        """,
        as_dict=True,
    )

    added = 0
    unchanged = 0
    exception_count = 0

    for q in leaves:
        existing = set(
            frappe.db.sql(
                """
                SELECT substrate
                FROM `tabParameter Group Substrate`
                WHERE parent = %s
                  AND parenttype = 'Quality Inspection Parameter Group'
                  AND parentfield = 'applicable_substrates'
                """,
                (q.name,),
                pluck="substrate",
            )
            or []
        )

        name_lower = (q.name or "").lower()
        if any(kw in name_lower for kw in LIQUID_ONLY_KEYWORDS):
            target = set(LQD_FAMILY)
            exception_count += 1
        else:
            target = set(ALL_SUBSTRATES)

        missing = target - existing
        if not missing:
            unchanged += 1
            continue

        qipg = frappe.get_doc("Quality Inspection Parameter Group", q.name)
        for sub_code in sorted(missing):
            qipg.append("applicable_substrates", {"substrate": sub_code})
        qipg.save(ignore_permissions=True)
        added += len(missing)

    frappe.db.commit()

    print(
        f"M3.5 substrate baseline: "
        f"{len(leaves)} leaf QIPGs scanned, "
        f"{exception_count} matched liquid-only name pattern, "
        f"{unchanged} already at target, "
        f"{added} new Parameter Group Substrate rows added"
    )
