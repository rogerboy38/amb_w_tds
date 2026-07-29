"""SR-1 [post_model_sync] — remove the Sample Request AMB Custom DocPerm overlay.

FAIL-CLOSED by design. A Custom DocPerm overlay REPLACES the standard set rather
than adding to it, so removing the overlay before the doctype JSON has landed would
drop this doctype to a single `System Manager` row with no submit — Quality Manager,
Manufacturing Manager and the verifier would all lose access on the same migrate.
The guard therefore aborts and LEAVES THE OVERLAY IN PLACE unless the standard set
carries all four expected roles. A failed release leaves people working.

Scope: `Custom DocPerm` rows only. The `Sample Request AMB-naming_series-options`
Property Setter is a different overlay type and is deliberately untouched.

Spec: ec77f09c (SPEC v2 §5), correlation_id 7f0290b2.
"""

import frappe

DOCTYPE = "Sample Request AMB"
EXPECTED = {"Manufacturing Manager", "Quality Manager", "System Manager", "Verifier Read Only"}


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	std = set(frappe.db.get_all("DocPerm", filters={"parent": DOCTYPE}, pluck="role"))
	if not EXPECTED.issubset(std):
		frappe.log_error(
			title="SR-1 overlay removal ABORTED",
			message="Standard DocPerm does not carry the expected roles: %s" % sorted(std),
		)
		return  # JSON did not land — leave the overlay in place

	rows = frappe.db.get_all("Custom DocPerm", filters={"parent": DOCTYPE}, fields=["*"])
	if not rows:
		return  # already removed — idempotent

	frappe.log_error(title="SR-1 overlay removal snapshot", message=frappe.as_json(rows))
	for r in rows:
		frappe.delete_doc("Custom DocPerm", r.name, force=True, ignore_permissions=True)
	frappe.clear_cache(doctype=DOCTYPE)
