"""Phase 1A Step 2B — doc_events hooks for TDS Product Specification (form-derivation + flag-row handling).

Pattern A1: TDS Product Specification has `custom=1`, which means Frappe's `import_controller` returns the default `Document` class WITHOUT consulting `override_doctype_class` (see `frappe/model/base_document.py`). So the class-override pattern that worked for Step 2A's Quality Inspection Parameter Group (custom=0) cannot work here. We use `doc_events` function hooks instead — matches `amb_w_spc`'s existing Batch AMB customization pattern, which is also `custom=1`.

Two hooks:
- **`derive_form` (validate event)**: auto-set the `form` Custom Field (Link to Item Group) from the linked `product_item`'s `item_group` when `form` is empty. Current 124-doc dataset has `product_item.item_group` resolving directly to meaningful family groups that match the Step 2A QIP Group roots. If a future TDS spec links to a deeper item_group, an ancestry walk could refine this — current direct fetch covers the dataset.
- **`propagate_flag_row_groups` (before_save event)**: walk the child IQI Parameter rows in idx order; when a flag row (`custom_is_title_row=1`) sets a section context, propagate that section's `parameter_group` to following non-flag rows that have empty `parameter_group`. Title row's section identifier is its OWN `parameter_group` value (e.g., "Organoleptic LQD"), NOT its `specification` (which is a Quality Inspection Parameter name, not a QIP Group name).

Note on the kickoff's `row.parameter` reference: there is no `parameter` field on `Item Quality Inspection Parameter` — the kickoff letter used the user-visible LABEL ("Parameter") of the `specification` fieldname. Using the title row's `parameter_group` directly (as done here) preserves Link integrity with QIP Group; using `specification` would produce invalid QIP Group references.

Registered via `doc_events` in `amb_w_tds.hooks` (relocated from `amb_w_spc.hooks` during Phase 1A.5 — TDS family consolidated under amb_w_tds per Hugh's architectural call). The `form` Custom Field and backfill of existing 124 docs were installed by the migration patch `amb_w_spc.patches.v15.setup_tds_form_derivation` (DB-level effects survive the file relocation; patch path stays as historical record).
"""

import frappe


def derive_form(doc, method=None) -> None:
	"""doc_events `validate` hook on TDS Product Specification.

	Auto-set `form` (Link to Item Group) from product_item.item_group when empty.
	Idempotent: only writes if `form` is None/empty. No-op when product_item is unset.
	"""
	if doc.get("form"):
		return
	if not doc.get("product_item"):
		return
	item_group = frappe.db.get_value("Item", doc.product_item, "item_group")
	if item_group:
		doc.form = item_group


def propagate_flag_row_groups(doc, method=None) -> None:
	"""doc_events `before_save` hook on TDS Product Specification.

	Walk the child `item_quality_inspection_parameter` rows in idx order. When a flag row
	(`custom_is_title_row=1`) is encountered with a `parameter_group` set, that group becomes
	the section context. Following non-flag rows with empty `parameter_group` inherit it.

	Idempotent: re-running on a saved doc with all parameter_groups populated produces no
	changes. Non-flag rows with already-set parameter_group are left untouched (their leaf
	assignment, e.g., "Organoleptic LQD Appearance", is more specific than the section root).

	This is the live-on-save complement to Step 2C's bulk migration for existing data.
	"""
	current_group = None
	for row in doc.get("item_quality_inspection_parameter", []):
		if row.get("custom_is_title_row"):
			row_pg = row.get("parameter_group")
			if row_pg:
				current_group = row_pg
		elif current_group and not row.get("parameter_group"):
			row.parameter_group = current_group
