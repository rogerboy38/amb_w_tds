"""TASKS-397 (decision 350): a new variant takes its template's "Allow Sales" (`Item.is_sales_item`) once.

Wired in hooks.py as the Item's `before_insert` doc_event, and nowhere else: it runs once, when the variant is
inserted, never at a later save of the variant and never at a save of its template (a template has no `variant_of`;
ERPNext's `update_variants`, run in the template's `on_update`, saves the existing variants, which is no insert).

Why this place wins over ERPNext 16.17.0:
- `create_variant` (and `create_multiple_variants`, and the Item quick entry) builds the variant in memory, copying
  the template's fields that are on Item Variant Settings' copy list (`copy_attributes_to_variant`), and the insert
  follows. Frappe's `Document.insert` runs `before_insert` after the defaults are set (`is_sales_item` defaults to 1)
  and before `validate`; so this hook runs after ERPNext's copy and after the default, and it is the last writer:
  Item's `validate` and `before_save` do not write `is_sales_item`.
- A variant made by hand (a new Item with `variant_of` typed in) gets no copy from ERPNext at all; this hook gives it
  its template's value too.

So the value is the template's whether or not `is_sales_item` is still on the copy list (with it on, it is the same
value anyway). Item Variant Settings is not touched here (decision 347 is a settings step done later).

The template's value is read from the database, as stored, not from anything the caller sent. When the template
cannot be read (the framework's link check refuses a missing `variant_of` before this runs), nothing is changed.
After the insert the variant's check is its own: changing the template's check later does not touch it (with the
field off the copy list), and the certificate type reads the variant's own value (TASKS-385, decision 320)."""

import frappe
from frappe.utils import cint

ALLOW_SALES_FIELD = "is_sales_item"


def copy_allow_sales_from_template(doc, method=None):
	"""doc_events hook on Item, `before_insert`: a new variant starts with its template's stored `is_sales_item`."""
	template = doc.get("variant_of")
	if not template:
		return
	value = frappe.db.get_value("Item", template, ALLOW_SALES_FIELD)
	if value is None:
		return
	doc.set(ALLOW_SALES_FIELD, cint(value))
