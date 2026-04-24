# -*- coding: utf-8 -*-
# amb_w_tds.doctype_events.tds_product_specification
# V13.6.0 P3 / TDS-M3 migration of Server Script "Fetch TDS Version Validation"
# Reference DocType: TDS Product Specification, Event: Before Insert
import frappe


def fetch_tds_version_validation(doc, method=None):
    # Migrated body (verbatim) from Server Script "Fetch TDS Version Validation"
    # Optional validation to ensure sequence numbers stay in sync
    def validate(doc, method):
        if doc.tds_sequence:
            # Get current sequence from TDS Settings
            current_seq = frappe.db.get_value("TDS Settings", {"item_code": doc.item_code}, "last_sequence_used") or 0

            # Ensure our sequence isn't higher than what's recorded
            if doc.tds_sequence > current_seq + 1:
                frappe.throw(f"Sequence number {doc.tds_sequence} is too high. Current sequence is {current_seq}")
