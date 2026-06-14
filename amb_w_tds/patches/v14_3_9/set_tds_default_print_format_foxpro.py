"""P1.3 — set default_print_format = 'TDS AMB FoxPro' on TDS Product Specification.

Daniel-approved (2026-06-13). Old Print-Designer formats stay selectable; only the
DocType default changes. Implemented as a DocType-level Property Setter
('default_print_format') so it is fixture-capturable (hooks fixtures already export
Property Setter for _AMB_W_TDS_DOCTYPES) AND deterministically applied on migrate so
it rides the test->PROD gate. Idempotent: re-running just re-asserts the value.

Defensive: if 'TDS AMB FoxPro' is not installed on this site, leave the default
unchanged rather than point it at a missing format.
"""
import frappe

DOCTYPE = "TDS Product Specification"
TARGET = "TDS AMB FoxPro"
PS_NAME = f"{DOCTYPE}-main-default_print_format"


def execute():
    if not frappe.db.exists("Print Format", TARGET):
        frappe.logger().warning(
            f"P1.3 (T-finishing): '{TARGET}' Print Format absent — default_print_format left unchanged"
        )
        return

    if frappe.db.exists("Property Setter", PS_NAME):
        frappe.db.set_value("Property Setter", PS_NAME, "value", TARGET)
    else:
        frappe.get_doc(
            {
                "doctype": "Property Setter",
                "doctype_or_field": "DocType",
                "doc_type": DOCTYPE,
                "property": "default_print_format",
                "property_type": "Data",
                "value": TARGET,
            }
        ).insert(ignore_permissions=True)

    frappe.clear_cache(doctype=DOCTYPE)
    frappe.db.commit()
    print(f"P1.3: default_print_format for '{DOCTYPE}' set to '{TARGET}'")
