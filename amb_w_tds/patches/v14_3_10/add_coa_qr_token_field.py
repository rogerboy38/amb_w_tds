"""P1.4 — add the opaque QR token field to COA AMB (idempotent).

Stores the per-lot opaque token minted on submit (amb_w_tds.coa_qr). Hidden/read-only/no-copy:
it is machine data, never user-edited, and must not be carried by Amend/Copy. Custom Field is
also fixture-captured by the existing hooks filter, so this rides the test->PROD gate either way.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "COA AMB": [
                {
                    "fieldname": "qr_token",
                    "label": "QR Token",
                    "fieldtype": "Data",
                    "insert_after": "coa_language",
                    "read_only": 1,
                    "no_copy": 1,
                    "print_hide": 1,
                    "hidden": 1,
                    "allow_on_submit": 1,
                }
            ]
        },
        ignore_validate=True,
    )
    frappe.db.commit()
    print("P1.4: COA AMB.qr_token custom field ensured")
