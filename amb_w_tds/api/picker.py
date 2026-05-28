"""Picker support API — whitelisted methods consumed by phase_1c_tab_v2.js.

Frappe forbids `frappe.db.get_list` on child doctypes from client JS (REST guard).
This module exposes server-side aggregations for child-doctype data the picker needs.
"""
import frappe
from frappe import _


@frappe.whitelist()
def get_substrate_map():
    """Return a map of {QIPG_name: [substrate_codes]} for all QIPGs that have
    applicable_substrates rows. Used by the Parameter Selection picker (SC5 v2)
    to filter parameters by the auto-detected substrate from the Item Group form.

    Returns: dict[str, list[str]]
    """
    rows = frappe.db.sql(
        """
        SELECT parent, substrate
        FROM `tabParameter Group Substrate`
        WHERE parenttype = 'Quality Inspection Parameter Group'
          AND parentfield = 'applicable_substrates'
        """,
        as_dict=True,
    )
    result = {}
    for r in rows:
        result.setdefault(r["parent"], []).append(r["substrate"])
    return result


@frappe.whitelist()
def get_acceptance_choices_map():
    """Return a map of {QIP_name: [choice_rows]} for all Acceptance Choice child
    rows on Quality Inspection Parameter. Used by the Parameter Selection picker
    (Task #33) to render per-choice radio buttons under each parameter.

    Child rows are istable=1 — JS can't `frappe.db.get_list` them (REST guard),
    so this method does the lookup server-side and returns the aggregated map.

    Returns: dict[str, list[dict]] — each dict has: name, text_label, min_value,
             max_value, target_value, unit, sub_spec, reconstituted_to_05_solids,
             is_default, idx
    """
    rows = frappe.db.sql(
        """
        SELECT parent AS qip, name, text_label, min_value, max_value, target_value,
               unit, sub_spec, reconstituted_to_05_solids, is_default, idx
        FROM `tabAcceptance Choice`
        WHERE parenttype = 'Quality Inspection Parameter'
          AND parentfield = 'acceptance_choices'
        ORDER BY parent, idx
        """,
        as_dict=True,
    )
    result = {}
    for r in rows:
        result.setdefault(r["qip"], []).append(r)
    return result


@frappe.whitelist()
def add_acceptance_choices(qip_name, lines):
    """Append free-text acceptance-choice lines to a QIP's `acceptance_choices`
    child table. Used by the picker's "Edit Posibles Valores" dialog (Task #33 v3)
    so Alicia can quickly add new choice text from the picker without leaving
    the TDS form.

    Behavior:
      * Permission-checked against `Quality Inspection Parameter` write
        (whitelisted methods bypass the REST guard but NOT permission checks
         when we call has_permission ourselves).
      * Dedupes new lines against existing `text_label` values, case-insensitive
        (MariaDB collation is CI; matching the friendlier compare here).
      * New rows get: text_label=<line>, min_value/max_value/sub_spec None,
        is_default=0 (existing default is preserved), legacy_text_match None
        (these are NEW rows, not migration backfill).
      * The QIP's `l4_migration_status` is NOT auto-flipped — text-only choices
        still need min/max before ratification. Explicit ratification is a
        separate path (full QIP form).

    Args:
        qip_name: QIP doctype name (Link target).
        lines: newline-separated string OR list of strings.

    Returns:
        dict with keys: added (int), skipped_duplicates (int),
                        skipped_empty (int), total_now (int),
                        l4_migration_status (str)
    """
    if not frappe.has_permission("Quality Inspection Parameter", "write", qip_name):
        frappe.throw(
            _("Insufficient permission to edit Acceptance Choices on {0}").format(qip_name),
            frappe.PermissionError,
        )

    if isinstance(lines, str):
        candidate_lines = [ln.strip() for ln in lines.split("\n")]
    elif isinstance(lines, (list, tuple)):
        candidate_lines = [str(ln).strip() for ln in lines]
    else:
        frappe.throw(_("`lines` must be a string or list"))

    qip = frappe.get_doc("Quality Inspection Parameter", qip_name)
    existing_lower = {(c.text_label or "").strip().lower() for c in (qip.acceptance_choices or [])}

    added = 0
    skipped_duplicates = 0
    skipped_empty = 0
    seen_in_payload = set()  # also dedupe within the same submission

    for line in candidate_lines:
        if not line:
            skipped_empty += 1
            continue
        key = line.lower()
        if key in existing_lower or key in seen_in_payload:
            skipped_duplicates += 1
            continue
        seen_in_payload.add(key)
        qip.append("acceptance_choices", {
            "text_label": line[:200],
            "min_value": None,
            "max_value": None,
            "sub_spec": None,
            "is_default": 0,
            "reconstituted_to_05_solids": 0,
            "legacy_text_match": None,
        })
        added += 1

    if added > 0:
        qip.save(ignore_permissions=False)
        frappe.db.commit()

    return {
        "added": added,
        "skipped_duplicates": skipped_duplicates,
        "skipped_empty": skipped_empty,
        "total_now": len(qip.acceptance_choices or []),
        "l4_migration_status": qip.l4_migration_status,
    }
