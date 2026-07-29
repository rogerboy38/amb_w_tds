"""SR-1 (b): AMB Control Number on the Sample Request samples child.

Idempotent (create_custom_fields upserts); reversible by dropping the field.
The controller (SampleRequestAMB.before_save._assign_control_numbers) fills it
forward on new sample rows from the global series AMB-.#####.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Sample Request AMB Item": [{
            "fieldname": "control_number",
            "label": "AMB Control Number",
            "fieldtype": "Data",
            "read_only": 1,
            "no_copy": 1,
            "print_hide": 1,
            "insert_after": "total_qty",
        }]
    }, update=True)
