"""G-1a: seed Formulation Settings once, with every value written explicitly.

A Single doctype's defaults are not a fixture and must not be inherited from the
DocType JSON (fleet rule z: the value you intend is the value you write). Values
per CARD G-1a §3 / §6.2, Hugh's word 2026-09-09.
"""

import frappe

DEFAULTS = {
    "cost_target_per_kg": 600,
    "cost_hard_max_per_kg": 800,
    "currency": "MXN",
    "approver_roles": "Quality Manager, Sales Manager, Marketing Manager",
    "default_coa_source": "COA AMB2",
}


def execute():
    if not frappe.db.exists("DocType", "Formulation Settings"):
        return
    doc = frappe.get_single("Formulation Settings")
    written = {}
    for field, value in DEFAULTS.items():
        if field == "currency" and not frappe.db.exists("Currency", value):
            continue
        if not doc.get(field):
            doc.set(field, value)
            written[field] = value
    if written:
        doc.save(ignore_permissions=True)
    print(f"g1a_formulation_settings_defaults: wrote {written or 'nothing (already set)'}")
