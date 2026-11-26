"""Which certificate a product gets, and the creation of a certificate from a lot (TASKS-384 B2; decision 317).

Two certificates by purpose: COA AMB is shared with a customer (finished goods); COA AMB2 is internal
(semi-finished goods and premix). The product decides the type, sales order or not.

THE CLASSIFICATION TABLE IS BELOW AND IS EMPTY. From the code and the fixtures of the three apps no rule could be
read that separates a finished product from a semi-finished one: the Item Groups named there ("Products Liquid",
"Products Powder", "FG Mix Powder Products", "RAW M Powders") class a product by its form, and a powder is both
sold and used as an input. Until the table is filled, every item is unclassed: `certificate_type_for_item` returns
None, no certificate is refused for its type, and `make_certificate_for_lot` says that it cannot decide.
"""

import frappe
from frappe import _

from amb_w_tds import certificate_rules

CUSTOMER_CERTIFICATE = "COA AMB"
INTERNAL_CERTIFICATE = "COA AMB2"

# Item Group name -> certificate type. An item is classed by the NEAREST Item Group of its ancestry (its own group
# first, then each parent) that is named here; an item with no such group is unclassed. To change how items are
# classed, change this table: for example {"<group of finished goods>": CUSTOMER_CERTIFICATE,
# "<group of semi-finished goods>": INTERNAL_CERTIFICATE}.
CERTIFICATE_TYPE_BY_ITEM_GROUP = {}

LOT_DOCTYPE = "Batch AMB"
# The lot's item is the Work Order's item, as the lot picker shows it.
LOT_ITEM_FIELD = "item_to_manufacture"


def certificate_type_for_item(item_code):
	""" "COA AMB", "COA AMB2", or None when the item is not classed (decision 317)."""
	if not item_code or not CERTIFICATE_TYPE_BY_ITEM_GROUP:
		return None
	group = frappe.db.get_value("Item", item_code, "item_group")
	seen = set()
	while group and group not in seen:
		if group in CERTIFICATE_TYPE_BY_ITEM_GROUP:
			return CERTIFICATE_TYPE_BY_ITEM_GROUP[group]
		seen.add(group)
		group = frappe.db.get_value("Item Group", group, "parent_item_group")
	return None


@frappe.whitelist()
def make_certificate_for_lot(lot):
	"""Insert a Draft certificate of the right type for the lot record `lot` (a Batch AMB) and return
	{"doctype", "name"}. Lot, Work Order, product and specification are filled; the customers list of a COA AMB is
	filled on the server by its `before_insert` (the specification's customers, else the Item's).

	The product is the specification's product when the lot names a specification (that is what the certificate
	carries after its insert), else the lot's item. The caller needs read on the lot and create on the certificate."""
	lot_doc = frappe.get_doc(LOT_DOCTYPE, lot)
	lot_doc.check_permission("read")
	level = certificate_rules.lot_level(lot_doc.get(certificate_rules.LOT_LEVEL_FIELD))
	if level not in certificate_rules.CERTIFICATE_LEVELS:
		frappe.throw(certificate_rules.lot_level_refusal(lot_doc.name, level), title=_("Certificate"))
	specification = lot_doc.get("tds_link")
	product = None
	if specification:
		product = frappe.db.get_value("TDS Product Specification", specification, "product_item")
	if not product and lot_doc.get(LOT_ITEM_FIELD) and frappe.db.exists("Item", lot_doc.get(LOT_ITEM_FIELD)):
		product = lot_doc.get(LOT_ITEM_FIELD)
	if not product:
		frappe.throw(
			_("Lot {0} names no specification and no item: a certificate cannot be made for it.").format(
				lot_doc.name
			),
			title=_("Certificate"),
		)
	doctype = certificate_type_for_item(product)
	if not doctype:
		frappe.throw(
			_(
				"Item {0} is not classed as a finished or a semi-finished product, so the type of its certificate cannot be decided here. Make the certificate from the list of its type."
			).format(product),
			title=_("Certificate"),
		)
	certificate = frappe.new_doc(doctype)
	certificate.batch_reference = lot_doc.name
	certificate.work_order = lot_doc.get(certificate_rules.LOT_WORK_ORDER_FIELD)
	certificate.product_item = product
	certificate.linked_tds = specification
	certificate.insert()
	return {"doctype": certificate.doctype, "name": certificate.name}
