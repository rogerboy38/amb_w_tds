"""BOM Formula release (13.11.0): "Liberar a producción" builds a standard ERPNext BOM from the
released formula, so a Work Order can use it (formula -> BOM -> Work Order -> production).

- A small dedicated builder on ERPNext's own BOM doctype. It does not reuse BOMService /
  create_standard_bom: those copy an MRP BOM tied to a Batch AMB, force is_default = 1 and
  commit inside, which would break a clean failure inside a workflow transition.
- Every Mix Input row must resolve to an Item and a positive kg BEFORE anything is written:
  one unresolvable row fails the whole release with a message naming the rows.
- No commit here: the BOM is inserted and submitted inside the formula's own save, so any
  failure rolls the BOM back together with the transition.
- Idempotent on the formula's OWN back-reference (`bom_liberada`): a release-created BOM that
  is still submitted and active is reused. Other BOMs that merely carry `bom_formula` (some
  were tagged by hand) are never searched, reused or touched.
- 13.11.2: the BOM is named explicitly BOM-<item>-NNN counting amended BOMs (formulation/bom_naming.py;
  ERPNext's own picker skips amendments and collided: "Duplicate Name: BOM BOM-0307-006"), with one
  retry. It becomes the item's default ("first plan"; this reverses 13.11.0's is_default = 0): ERPNext's
  manage_default_bom unticks the previous default on submit, and the demotion is logged.
- Permissions: the builder runs with ignore_permissions, and is only called from the
  controller on the workflow transition to "Liberado", which Frappe's workflow allows only
  to the role on that transition. No general BOM create/submit right is granted.
"""

import frappe
from frappe import _
from frappe.utils import flt

RELEASED = "Liberado"
KG = "Kg"


def resolve_line_item(line, batch_item_of):
	"""The Item a Mix Input row consumes: the row's own item_code, else its Batch AMB sublot's
	item (`batch_item_of(sublot)`). None when neither resolves. Pure, so it is unit-tested."""
	if line.get("item_code"):
		return line.get("item_code")
	if line.get("batch_amb_sublot"):
		return batch_item_of(line.get("batch_amb_sublot")) or None
	return None


def _batch_item(sublot):
	row = frappe.db.get_value("Batch AMB", sublot, ["item_on_batch", "main_item"], as_dict=True)
	return (row.item_on_batch or row.main_item) if row else None


def plan_bom(formula, batch_item_of=_batch_item, item_exists=None, stock_uom_of=None):
	"""Validate the formula and return (product, total_kg, [(item, kg, line_idx)]), or throw
	listing every problem. Writes nothing."""
	item_exists = item_exists or (lambda code: bool(frappe.db.exists("Item", {"name": code, "disabled": 0})))
	stock_uom_of = stock_uom_of or (lambda code: frappe.db.get_value("Item", code, "stock_uom"))
	problems = []
	product = formula.get("product_sku")
	if not product:
		problems.append(_("la fórmula no tiene producto (Product SKU)"))
	elif not item_exists(product):
		problems.append(_("el producto {0} no existe o está deshabilitado").format(product))
	elif stock_uom_of(product) != KG:
		# BOM.quantity is in the product's stock UOM; the formula is in kg
		problems.append(_("el producto {0} tiene unidad de stock {1}, no {2}").format(product, stock_uom_of(product), KG))
	rows = []
	lines = formula.get("mix_input_lines") or []
	if not lines:
		problems.append(_("la fórmula no tiene líneas de Mix Input"))
	for idx, line in enumerate(lines, start=1):
		item = resolve_line_item(line, batch_item_of)
		kg = flt(line.get("kg"))
		if not item:
			problems.append(_("línea {0}: no se pudo resolver el Item (sin item_code ni sublote Batch AMB con artículo)").format(idx))
		elif not item_exists(item):
			problems.append(_("línea {0}: el Item {1} no existe o está deshabilitado").format(idx, item))
		if kg <= 0:
			problems.append(_("línea {0}: cantidad (kg) debe ser mayor que 0").format(idx))
		rows.append((item, kg, idx))
	if problems:
		frappe.throw(_("No se puede liberar {0}: {1}").format(formula.get("name"), "; ".join(problems)),
			title=_("Liberación rechazada"))
	return product, sum(kg for _i, kg, _x in rows), rows


def _reusable(bom_name):
	if not bom_name:
		return False
	row = frappe.db.get_value("BOM", bom_name, ["docstatus", "is_active"], as_dict=True)
	return bool(row and row.docstatus == 1 and row.is_active)


def _current_default(item):
	"""The item's current default BOM (submitted, active), or None."""
	return frappe.db.get_value("BOM", {"item": item, "is_default": 1, "docstatus": 1, "is_active": 1}, "name")


def _comment(doctype, name, text):
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": doctype,
		"reference_name": name, "content": text}).insert(ignore_permissions=True)


def _insert_named(doc_dict, item):
	"""Insert + submit the BOM under an explicit, collision-proof name (bom_naming), retrying ONCE
	with a recomputed name on a duplicate; a second collision fails the release cleanly."""
	from amb_w_tds.formulation.bom_naming import next_free_bom_name

	for attempt in (1, 2):
		name = next_free_bom_name(item)
		bom = frappe.get_doc(dict(doc_dict))
		bom.flags.ignore_permissions = True
		frappe.db.savepoint("bom_release_insert")
		try:
			bom.insert(set_name=name) if name else bom.insert()
			bom.submit()
			return bom, attempt
		except frappe.DuplicateEntryError:
			frappe.db.rollback(save_point="bom_release_insert")
			frappe.clear_last_message()  # the "Duplicate Name" notice queued by the failed insert
			if attempt == 2:
				frappe.throw(_("No se pudo asignar un nombre libre a la BOM de {0} (colisión repetida). Intente de nuevo.").format(item),
					title=_("Liberación rechazada"))


def build_release_bom(formula):
	"""Return {"bom", "path": "reused" | "built", ...}. Called on the transition to Liberado.

	13.11.2: the BOM is named explicitly BOM-<item>-NNN counting amended BOMs (bom_naming), and the
	released BOM becomes the item's default ("first plan"): ERPNext's own manage_default_bom unticks
	the previous default on submit; the demotion is logged on the formula and on the new BOM. The
	reuse path never touches defaults, so a planner's later choice is never overridden."""
	if _reusable(formula.get("bom_liberada")):
		return {"bom": formula.get("bom_liberada"), "path": "reused"}
	product, total_kg, rows = plan_bom(formula)
	previous_default = _current_default(product)
	bom, attempt = _insert_named({
		"doctype": "BOM",
		"item": product,
		"quantity": total_kg,
		"is_active": 1,
		"is_default": 1,
		"bom_formula": formula.name,
		"rm_cost_as_per": "Valuation Rate",
		"items": [{"item_code": item, "qty": kg, "uom": KG} for item, kg, _idx in rows],
	}, product)
	defaults = frappe.get_all("BOM", filters={"item": product, "is_default": 1, "docstatus": 1}, pluck="name")
	if defaults != [bom.name]:
		frappe.throw(_("La BOM liberada {0} no quedó como única predeterminada de {1} ({2}).").format(
			bom.name, product, ", ".join(defaults) or "ninguna"), title=_("Liberación rechazada"))
	if previous_default and previous_default != bom.name:
		text = _("Liberación de {0}: {1} es ahora la BOM predeterminada de {2}; la predeterminada anterior era {3} "
			"y fue desmarcada por la liberación (un planificador puede volver a marcarla).").format(
			formula.name, bom.name, product, previous_default)
	else:
		text = _("Liberación de {0}: {1} es ahora la BOM predeterminada de {2} (no había una predeterminada).").format(
			formula.name, bom.name, product)
	_comment("BOM Formula", formula.name, text)
	_comment("BOM", bom.name, text)
	return {"bom": bom.name, "path": "built", "previous_default": previous_default, "name_attempts": attempt}
