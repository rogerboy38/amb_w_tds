import frappe

@frappe.whitelist(allow_guest=False)
def create_or_get_quotation_amb(payload: dict):
    """
    Idempotent quotation creator
    Steps:
      1. normalize payload
      2. lookup existing quotation AMB
      3. create header + child rows if not exists
    """

    custom_folio = payload.get("custom_folio")

    if not custom_folio:
        frappe.throw("custom_folio required")

    existing = frappe.db.get_value(
        "Quotation AMB",
        {"custom_folio": custom_folio},
        "name",
    )

    if existing:
        return {
            "status": "exists",
            "name": existing,
        }

    doc = frappe.new_doc("Quotation AMB")
    doc.update(payload)
    doc.insert(ignore_permissions=True)

    return {
        "status": "created",
        "name": doc.name,
    }
