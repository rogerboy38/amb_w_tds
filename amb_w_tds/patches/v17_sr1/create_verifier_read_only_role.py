"""SR-1 [pre_model_sync] — ensure the `Verifier Read Only` role exists.

Runs BEFORE model sync so the Sample Request AMB permissions block in the doctype
JSON has a role to bind to. Idempotent: no-op where the role already exists (wsl,
where all four roles are already present); its real work is vpt and prod.

Spec: ec77f09c (SPEC v2 §4), correlation_id 7f0290b2.
"""

import frappe

ROLE = "Verifier Read Only"


def execute():
	if frappe.db.exists("Role", ROLE):
		return
	doc = frappe.new_doc("Role")
	doc.role_name = ROLE
	doc.desk_access = 1
	doc.disabled = 0
	doc.insert(ignore_permissions=True)
