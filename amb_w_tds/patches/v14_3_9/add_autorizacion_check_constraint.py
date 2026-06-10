"""T98.2 — Bulletproof DB CHECK constraint for COA AMB signature requirement.

Adds a MariaDB CHECK constraint to tabCOA AMB that prevents any path
(including direct SQL UPDATE or frappe.db.set_value bypassing all Python
hooks) from setting docstatus=1 with NULL/empty autorizacion.

Context (2026-06-11):
    Initial T90 added two Python defenses (validate, before_submit). Both were
    bypassed by COA-26-0008 reaching docstatus=1 with autorizacion=NULL via an
    incomplete workflow action (forensic: workflow_action.status='Open',
    completed_by=NULL, yet doc reached Certificate Shared).
    T98 added a third Python defense (validate_submission_prerequisites in
    on_submit), but Python-only defenses cannot catch direct DB writes.
    This patch installs the bulletproof L4 layer.

Banked in lessons digest as L380 (4-layer defense pattern) and L382 (CHECK
constraint vs trigger decision matrix).

Idempotent: checks for existence first; safe to re-run.

Fail-fast: if pre-existing records would violate the invariant, throws with
a clear message listing offending record names so operator can resolve
(reset to draft, cancel, or fill placeholder) before re-running migrate.
"""

import frappe


def execute():
    constraint_name = "chk_autorizacion_required_on_submit"
    table_name = "tabCOA AMB"

    # Step 1: idempotency check — skip if constraint already present
    existing = frappe.db.sql(
        """
        SELECT 1
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = %s
        """,
        (table_name, constraint_name),
    )

    if existing:
        print(f"[T98.2] Constraint {constraint_name} already exists on {table_name}; skipping.")
        return

    # Step 2: pre-flight — bail with a useful message if any record would violate
    violators = frappe.db.sql(
        """
        SELECT name
        FROM `tabCOA AMB`
        WHERE docstatus = 1
          AND IFNULL(LENGTH(autorizacion), 0) = 0
        """,
        as_dict=True,
    )

    if violators:
        names = ", ".join(v.name for v in violators)
        frappe.throw(
            f"T98.2 patch cannot apply: {len(violators)} COA AMB record(s) violate "
            f"the constraint (docstatus=1 with NULL/empty autorizacion). "
            f"Resolve them first by resetting to Draft, cancelling (docstatus=2), "
            f"or filling a placeholder autorizacion. Violators: {names}"
        )

    # Step 3: apply the constraint
    frappe.db.sql(
        f"""
        ALTER TABLE `{table_name}`
        ADD CONSTRAINT {constraint_name}
        CHECK (docstatus != 1 OR IFNULL(LENGTH(autorizacion), 0) > 0)
        """
    )
    frappe.db.commit()

    print(f"[T98.2] Added CHECK constraint {constraint_name} on {table_name}.")
    print(
        "[T98.2] Any path (Python, frappe.db.set_value, raw SQL) that attempts to "
        "set docstatus=1 with NULL/empty autorizacion will now fail with "
        "MariaDB ERROR 4025 (constraint violation)."
    )
