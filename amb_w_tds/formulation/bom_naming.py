"""BOM naming that counts amendments (13.11.2).

ERPNext's BOM.autoname (erpnext/manufacturing/doctype/bom/bom.py) picks the next BOM-<item>-NNN
from the existing names but EXCLUDES amended BOMs. With Document Naming Settings set to
"Default Naming" for amendments, an amended BOM takes a plain number (e.g. BOM-0307-006 is an
amendment of -005), so the picker re-proposes that number and the insert fails with
"Duplicate Name". This module computes the next free number counting EVERY BOM-<item>-NNN,
amended or not, and is used by:
  - the formula release builder (formulation/release.py), which names its BOM explicitly;
  - the BOM "autoname" doc_event (hooks.py), which corrects ERPNext's proposal ONLY when the
    proposed name already exists, so the manual "New BOM" dialog stops colliding too.
Existing BOMs are never renamed; names that would not collide are left exactly as ERPNext set them.
"""

import re

import frappe

PREFIX = "BOM"
WIDTH = 3  # ERPNext's "%.3i"
MAX_LEN = 140


def next_bom_name(item, existing_names):
	"""BOM-<item>-NNN with NNN = max numeric suffix among `existing_names` that match
	BOM-<item>-<digits> exactly (amended ones included) + 1; at least 001. Pure."""
	pattern = re.compile(rf"^{re.escape(PREFIX)}-{re.escape(item)}-(\d+)$")
	nums = [int(m.group(1)) for m in (pattern.match(n) for n in existing_names) if m]
	width = max([WIDTH] + [len(m.group(1)) for m in (pattern.match(n) for n in existing_names) if m])
	return f"{PREFIX}-{item}-{(max(nums) + 1 if nums else 1):0{width}d}"


def existing_bom_names(item):
	"""Every BOM named BOM-<item>-..., amended or not (filtered to the exact pattern by next_bom_name)."""
	like = f"{PREFIX}-{item}-".replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
	return frappe.get_all("BOM", filters={"name": ("like", like)}, pluck="name")


def next_free_bom_name(item):
	name = next_bom_name(item, existing_bom_names(item))
	return name if len(name) <= MAX_LEN else None


def correct_colliding_autoname(doc, method=None):
	"""doc_events BOM "autoname": runs right after ERPNext's BOM.autoname. If the proposed name
	already exists (the amendment collision), move it to the next free BOM-<item>-NNN counting
	amendments. A name that does not collide is left as ERPNext set it."""
	if not doc.name or not doc.get("item") or not frappe.db.exists("BOM", doc.name):
		return
	name = next_free_bom_name(doc.item)
	if name:
		doc.name = name
