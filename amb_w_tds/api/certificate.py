"""Which certificate a product gets, and the creation of a certificate from a lot (TASKS-384 B2; TASKS-385,
decision 320).

Two certificates by purpose: COA AMB is shared with a customer (finished goods); COA AMB2 is internal
(semi-finished goods and premix). Decision 320: the type follows the Item's own "Allow Sales" check
(`is_sales_item`), read on the item itself — a variant's own value, not its template's. On: COA AMB. Off: COA AMB2.
No item, or an item that does not exist: None.
"""

import frappe
from frappe import _
from frappe.utils import cint

from amb_w_tds import certificate_rules

CUSTOMER_CERTIFICATE = "COA AMB"
INTERNAL_CERTIFICATE = "COA AMB2"

# Decision 320: the Item field whose label is "Allow Sales" (ERPNext 16.17.0 `stock/doctype/item/item.json`).
ALLOW_SALES_FIELD = "is_sales_item"
ALLOW_SALES_LABEL = "Allow Sales"

LOT_DOCTYPE = "Batch AMB"
# The lot's item is the Work Order's item, as the lot picker shows it.
LOT_ITEM_FIELD = "item_to_manufacture"


def certificate_type_for_item(item_code):
	""" "COA AMB" when the Item's own "Allow Sales" check is on, "COA AMB2" when it is off, None when there is no
	item or no such Item (decision 320). One read, of that Item's row only: a variant's own value decides, its
	template is not read."""
	if not item_code:
		return None
	allow_sales = frappe.db.get_value("Item", item_code, ALLOW_SALES_FIELD)
	if allow_sales is None:  # no such Item: get_value returns None; a stored check is 0 or 1
		return None
	return CUSTOMER_CERTIFICATE if cint(allow_sales) else INTERNAL_CERTIFICATE


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
				'Item {0} does not exist, so the type of its certificate cannot be decided: it follows the "{1}" check on the Item. Correct the product on the specification or the item on the lot.'
			).format(product, ALLOW_SALES_LABEL),
			title=_("Certificate"),
		)
	certificate = frappe.new_doc(doctype)
	certificate.batch_reference = lot_doc.name
	certificate.work_order = lot_doc.get(certificate_rules.LOT_WORK_ORDER_FIELD)
	certificate.product_item = product
	certificate.linked_tds = specification
	certificate.insert()
	return {"doctype": certificate.doctype, "name": certificate.name}
