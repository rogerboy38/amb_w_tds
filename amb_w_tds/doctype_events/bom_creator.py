# -*- coding: utf-8 -*-
# amb_w_tds.doctype_events.bom_creator
# V13.6.0 P3 / TDS-M3 migration of Server Script "BOM Creator - Calculate Total Cost"
# Reference DocType: BOM Creator, Event: Before Save
import frappe


def calculate_total_cost(doc, method=None):
    # Migrated body (verbatim) from Server Script "BOM Creator - Calculate Total Cost"
    # Calculate total cost from all items
    total_cost = 0
    for item in doc.items:
        if item.qty and item.rate:
            total_cost += float(item.qty) * float(item.rate)

    # Calculate amount for each item and total cost
    total_cost = 0
    for item in doc.items:
        if item.qty and item.rate:
            amount = float(item.qty) * float(item.rate)
            item.amount = amount
            total_cost += amount

    doc.raw_material_cost = total_cost
