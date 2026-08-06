"""D5 — the JSON owns fetch_if_empty, so the overlay must go.

`coa_amb.json` and `coa_amb2.json` now set `fetch_if_empty = 1` on the six legend
fields. A Property Setter carrying the same property would win over the JSON on every
`clear_cache`, so the doctype change alone is not the fix: the overlay has to be
deleted in the SAME change, or it silently resurrects the old behaviour.

Deletion is BY PREDICATE, not by hardcoded name. Node B has no prod seat and cannot
observe the rows it is deleting — this sandbox carries ZERO `fetch_if_empty` Property
Setters on either doctype (the only one in the whole database is on `Batch.batch_id`,
which this patch must not touch). Naming four rows we cannot see would be guessing;
matching the predicate deletes exactly what contradicts the JSON, whatever it is
called, and deletes nothing if prod turns out to be clean.

Idempotent: re-running finds nothing and reports 0.
"""

import frappe

DOCTYPES = ("COA AMB", "COA AMB2")
LEGEND_FIELDS = (
	"cas_number",
	"inci_name",
	"shelf_life",
	"packaging",
	"storage_and_handling_conditions",
	"formula_based_criteria",
)


def execute():
	rows = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": ["in", DOCTYPES],
			"field_name": ["in", LEGEND_FIELDS],
			"property": "fetch_if_empty",
		},
		fields=["name", "doc_type", "field_name", "value"],
	)

	if not rows:
		frappe.log_error(
			title="D5 fetch_if_empty overlay",
			message="No fetch_if_empty Property Setters on COA AMB / COA AMB2. "
			"Nothing to delete; the JSON is already the only owner.",
		)
		return

	for r in rows:
		# Log BEFORE deleting: this is the only before-image of a row we are removing
		# on a tier whose contents we could not inspect when the patch was written.
		frappe.log_error(
			title="D5 deleting fetch_if_empty Property Setter",
			message=f"{r.name} | {r.doc_type}.{r.field_name} | value={r.value!r}",
		)
		frappe.delete_doc("Property Setter", r.name, force=True, ignore_permissions=True)

	frappe.clear_cache(doctype="COA AMB")
	frappe.clear_cache(doctype="COA AMB2")
