"""Selling-edge §1c (design 2026-07-06): AMB Pack Plan child table on the AMB
tab of Quotation + Sales Order — extends the legacy single-slot packaging
fields into structured rows. Idempotent (create_custom_fields upserts)."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields({
        "Quotation": [
            {
                "fieldname": "custom_pack_plan",
                "label": "Pack Plan (per package group)",
                "fieldtype": "Table",
                "options": "AMB Pack Plan Item",
                "insert_after": "custom_individual_packaging",
                "description": "One row per package group; copied to the Sales "
                               "Order and read by WO-PACKAGE / container run / "
                               "packing slip / labels.",
            }
        ],
        "Sales Order": [
            {
                "fieldname": "custom_pack_plan",
                "label": "Pack Plan (per package group)",
                "fieldtype": "Table",
                "options": "AMB Pack Plan Item",
                "insert_after": "custom_embalaje",
                "description": "One or more rows per SO item row (so_item_row); "
                               "Σ group net per row must equal the row qty at "
                               "submit.",
            }
        ],
    }, ignore_validate=True, update=True)
