"""Selling-edge Pack Plan (§1c, design 2026-07-06 + 1b-FINAL amendments).

One SO, N rows (one per pack configuration), one WO per row-package. The
`AMB Pack Plan Item` child table (Quotation + Sales Order, field
`custom_pack_plan`) captures each package group once — SO → WO-PACKAGE →
L3 container run/serials → packing slip → labels all read it, never retype.

Hard rules implemented here:
  * per-SO-row sum: Σ group_net_kg of a row's plan groups == that row's qty
    (block on submit; 1b-FINAL — per row, not per order)
  * package/container links restricted to the packaging catalog Item Groups
    (#82 item; configurable via site_config `pack_plan_packaging_groups`)
  * taras are FETCHED from the Item master, never typed (F-8) — and
    weight_per_unit on packaging Items IS the tara, so it must never seed
    unit_net_kg (a 5 kg bag would silently become a 0.05 kg row)
  * Quotation→SO copy mapping carries the so_item_row association across
    (quotation row name → SO row via Sales Order Item.quotation_item)
"""

import frappe
from frappe import _
from frappe.utils import flt

# Until the #82 standard pack catalog lands, the packaging groups observed on
# dev: pails (CN0xx) live in Consumables, legacy bags (E0xx) in Raw Materials.
# Wide on purpose — the restriction's job today is to block product/transport/
# service items being picked as packaging; #82 tightens it via the site_config
# key `pack_plan_packaging_groups`.
DEFAULT_PACKAGING_GROUPS = [
    "FG Packaging Materials",
    "SFG Packaging Materials",
    "Sample Packaging Materials",
    "Consumables",
    "Raw Materials",
]

SUM_TOLERANCE_KG = 0.001


def packaging_groups():
    return frappe.conf.get("pack_plan_packaging_groups") or DEFAULT_PACKAGING_GROUPS


# --------------------------------------------------------------------------- #
# doc_events
# --------------------------------------------------------------------------- #

def validate_quotation(doc, method=None):
    _validate_plan_rows(doc)


def validate_sales_order(doc, method=None):
    copy_plan_from_quotation(doc)
    _validate_plan_rows(doc)


def before_submit_sales_order(doc, method=None):
    """1b-FINAL hard block: per SO row, Σ group_net_kg == row qty."""
    plan = doc.get("custom_pack_plan") or []
    if not plan:
        return
    sums = {}
    for row in plan:
        key = row.so_item_row
        if not key:
            frappe.throw(_(
                "Pack Plan row #{0}: SO Item Row is not set and the order has "
                "multiple item rows — every plan row must belong to exactly one "
                "SO row. / Fila del plan de empaque #{0}: falta la fila del "
                "pedido a la que pertenece."
            ).format(row.idx))
        sums[key] = sums.get(key, 0.0) + flt(row.group_net_kg)
    items_by_name = {i.name: i for i in doc.items}
    for key, total in sums.items():
        item_row = items_by_name.get(key)
        if item_row is None:
            frappe.throw(_(
                "Pack Plan references item row {0}, which is not on this "
                "Sales Order. / El plan de empaque referencia una fila "
                "inexistente."
            ).format(key))
        if abs(total - flt(item_row.qty)) > SUM_TOLERANCE_KG:
            frappe.throw(_(
                "Pack Plan mismatch on row {0} ({1}): plan groups total "
                "{2} kg but the row qty is {3} kg. Fix the plan or the row — "
                "they must reconcile exactly. / El plan de empaque de la fila "
                "{0} suma {2} kg pero la fila pide {3} kg."
            ).format(item_row.idx, item_row.item_code, total, flt(item_row.qty)))


# --------------------------------------------------------------------------- #
# row-level validation (Quotation + Sales Order)
# --------------------------------------------------------------------------- #

def _validate_plan_rows(doc):
    plan = doc.get("custom_pack_plan") or []
    if not plan:
        return
    allowed = set(packaging_groups())
    items = list(doc.get("items") or [])
    for row in plan:
        _restrict_to_catalog(row, "package_item", allowed)
        _restrict_to_catalog(row, "container_item", allowed)

        # F-8: taras come from the Item master, never typed
        row.unit_tara_kg = flt(frappe.db.get_value(
            "Item", row.package_item, "weight_per_unit")) if row.package_item else 0
        row.container_tara_kg = flt(frappe.db.get_value(
            "Item", row.container_item, "weight_per_unit")) if row.container_item else 0

        if flt(row.unit_net_kg) <= 0:
            frappe.throw(_(
                "Pack Plan row #{0}: Unit Net (kg) must be > 0 — it is entered "
                "from the PO, not fetched (weight_per_unit on packaging Items "
                "is the tara). / La fila #{0} necesita el neto por unidad."
            ).format(row.idx))

        row.group_net_kg = (
            flt(row.units_per_container) * flt(row.unit_net_kg) * flt(row.containers_qty or 1))

        # so_item_row: accept a row name; auto-fill on single-row orders
        if not row.so_item_row and len(items) == 1:
            row.so_item_row = items[0].name
        if row.so_item_row and items and row.so_item_row not in {i.name for i in items}:
            frappe.throw(_(
                "Pack Plan row #{0}: '{1}' does not match any Items row on "
                "this document. / La fila #{0} no corresponde a ninguna fila "
                "del documento."
            ).format(row.idx, row.so_item_row))


def _restrict_to_catalog(row, fieldname, allowed):
    item = row.get(fieldname)
    if not item:
        return
    group, disabled = frappe.db.get_value("Item", item, ["item_group", "disabled"]) \
        or (None, None)
    if group is None:
        frappe.throw(_("Pack Plan row #{0}: Item {1} not found.").format(row.idx, item))
    if disabled:
        frappe.throw(_(
            "Pack Plan row #{0}: Item {1} is disabled. / El artículo {1} está "
            "deshabilitado.").format(row.idx, item))
    if group not in allowed:
        frappe.throw(_(
            "Pack Plan row #{0}: {1} ({2}) is not in the packaging catalog "
            "groups {3} (#82). / La fila #{0}: {1} no pertenece al catálogo de "
            "empaque.").format(row.idx, item, group, ", ".join(sorted(allowed))))


# --------------------------------------------------------------------------- #
# Quotation -> Sales Order copy mapping (carries so_item_row across)
# --------------------------------------------------------------------------- #

def copy_plan_from_quotation(doc):
    """On a new SO mapped from a Quotation: pull the pack plan rows once and
    translate so_item_row (quotation row name -> new SO row name) via the SO
    item's quotation_item back-link. Never overwrites an existing plan."""
    if doc.get("custom_pack_plan"):
        return
    quotations = []
    q_row_to_so_row = {}
    for it in doc.get("items") or []:
        src_doc = it.get("prevdoc_docname")
        src_row = it.get("quotation_item")
        if src_doc and src_doc not in quotations:
            quotations.append(src_doc)
        if src_row:
            q_row_to_so_row[src_row] = it.name
    for q_name in quotations:
        if not frappe.db.exists("Quotation", q_name):
            continue
        q_plan = frappe.get_all(
            "AMB Pack Plan Item",
            filters={"parent": q_name, "parenttype": "Quotation"},
            fields=["so_item_row", "package_item", "units_per_container",
                    "unit_net_kg", "container_item", "containers_qty",
                    "label_source", "notes"],
            order_by="idx")
        for src in q_plan:
            row = dict(src)
            row["so_item_row"] = q_row_to_so_row.get(src["so_item_row"]) or ""
            doc.append("custom_pack_plan", row)


# --------------------------------------------------------------------------- #
# single-slot data migration (§1c amendment: fold the old one-slot fields in)
# --------------------------------------------------------------------------- #

SINGLE_SLOT_FIELDS = {
    # old single-slot field            -> plan meaning
    "custom_tipo_empaque_copy": "package_item",       # Link Item (primary pack)
    "custom_secondary_packaging_copy": "container_item",  # Link Item (container)
    "custom_peso_neto": "unit_net_kg",                # Data, net per package
}


def migrate_single_slot_data(dry_run=1, doctype="Sales Order", names=None):
    """Fold legacy single-slot packaging fields into pack plan rows.

    DRAFT documents only (docstatus 0) — submitted documents keep their
    single-slot fields as the historical record. Only migrates rows where the
    LINK fields are set (unambiguous); free-text Selects stay untouched.
    Dry-run by default; optionally scope with `names`. Run live via:

        bench --site <site> execute \
            amb_w_tds.selling_edge.pack_plan.migrate_single_slot_data \
            --kwargs "{'dry_run': 0}"
    """
    dry_run = int(dry_run)
    filters = {"docstatus": 0, "custom_tipo_empaque_copy": ["!=", ""]}
    if names:
        filters["name"] = ["in", names]
    names = frappe.get_all(doctype, filters=filters, pluck="name")
    report = {"doctype": doctype, "dry_run": bool(dry_run), "candidates": len(names),
              "migrated": 0, "skipped": []}
    for name in names:
        doc = frappe.get_doc(doctype, name)
        if doc.get("custom_pack_plan"):
            report["skipped"].append({"name": name, "reason": "plan already present"})
            continue
        package_item = doc.get("custom_tipo_empaque_copy")
        container_item = doc.get("custom_secondary_packaging_copy")
        try:
            unit_net = flt(str(doc.get("custom_peso_neto") or "").replace("kg", "").strip())
        except Exception:
            unit_net = 0
        if not package_item or unit_net <= 0:
            report["skipped"].append({"name": name, "reason": "no unambiguous link/net data"})
            continue
        items = list(doc.get("items") or [])
        qty = flt(items[0].qty) if len(items) == 1 else 0
        units = int(round(qty / unit_net)) if unit_net and qty and \
            abs(qty / unit_net - round(qty / unit_net)) < 1e-6 else 1
        row = {
            "so_item_row": items[0].name if len(items) == 1 else "",
            "package_item": package_item,
            "units_per_container": units,
            "unit_net_kg": unit_net,
            "container_item": container_item or "",
            "containers_qty": 1,
            "notes": "migrated from single-slot AMB packaging fields",
        }
        if dry_run:
            report["migrated"] += 1
            continue
        doc.append("custom_pack_plan", row)
        doc.save()
        report["migrated"] += 1
    if not dry_run and not frappe.flags.in_test:
        frappe.db.commit()
    return report
