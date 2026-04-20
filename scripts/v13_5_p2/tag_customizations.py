"""V13.5.0 P2: Tag untagged Custom Field / Property Setter / Workflow / Notification.
Dry-run first, then apply. Idempotent. No DB writes in dry_run.

Usage (as frappe user in ~/frappe-bench):
  bench --site sandbox.sysmayal.cloud execute scripts.v13_5_p2.tag_customizations.dry_run
  bench --site sandbox.sysmayal.cloud execute scripts.v13_5_p2.tag_customizations.apply
"""
import re
import json
import os
import frappe


# ---------------------------------------------------------------------------
# Authoritative mapping from orchestrator.
# Format: target_module -> list of (target_doctype_table, dt_regex)
# ---------------------------------------------------------------------------
MAPPING = {
    "AMBWTDS": [
        ("Custom Field", r"^(Quotation|Quotation Item|Sales Order|Sales Order Item|Sales Invoice|Sales Invoice Item|Customer|Customer Item|Item|Item Variant|Item Group|BOM|BOM Creator|Cost Center|TDS Product Specification|TDS Settings|COA AMB|COA AMB2|Shipping Rule|Incoterm|Freight Location|Print Format|Print Settings|Industry Type|CRM Lead|Shipment|Shipment Parcel|Asset Repair|Payment Term)$"),
        ("Property Setter", r"^(Quotation|Sales Order|Sales Invoice|Customer|Item|BOM|BOM Creator|Cost Center|TDS Product Specification|TDS Settings|COA AMB|Shipping Rule|Incoterm|Freight Location|Print Format|Industry Type|CRM Lead|Shipment|Shipment Parcel|Material Request|Supplier Quotation|Purchase Order|Purchase Receipt|Purchase Invoice|Delivery Note|Packed Item|Packing Slip|Quality Inspection|Quality Inspection Parameter|Quality Inspection Parameter Group|Quality Inspection Template|Quality Review|Quality Review Objective|Quality Goal|Quality Goal Objective|Quality Procedure|Item Quality Inspection Parameter|Operation|Workstation)$"),
        ("Workflow", r"^(Sales Order|Sales Invoice|Quotation|COA AMB|TDS Product Specification)$"),
        ("Notification", r"^(Quotation|Sales Order|Sales Invoice|COA AMB)$"),
    ],
    "SPC Quality Management": [
        ("Custom Field", r"^(Batch AMB|Sample Request AMB|Batch)$"),
        ("Property Setter", r"^(Batch AMB|Sample Request AMB|Batch)$"),
        ("Workflow", r"^(Batch AMB|Sample Request AMB)$"),
    ],
    "RND": [
        ("Custom Field", r"^(Work Order|Stock Entry|Warehouse|Movement Type)$"),
        ("Property Setter", r"^(Work Order|Stock Entry|Warehouse|Movement Type)$"),
        ("Workflow", r"^(Work Order|Stock Entry)$"),
    ],
    "Raven AI Agent": [
        ("Custom Field", r"^(Raven.*|Raven Webhook Handler)$"),
    ],
    "ERPNext Mexico Compliance": [
        ("Custom Field", r"^(Sales Invoice|Sales Invoice Item|Payment Entry|Customer|Employee|Company|Item|Item Group|Sales Taxes and Charges|Item Tax Template Detail|Mode of Payment|UOM|Subscription|Bank Account|Account|Payroll Entry|Payroll Employee Detail|Address|Contact)$"),
    ],
}


# Fieldname-level overrides: fieldname regex beats parent-doctype mapping.
# Useful for fields that live on a shared doctype (e.g. Sales Order) but
# logically belong to a specific app based on their fieldname prefix.
FIELDNAME_OVERRIDES = {
    "Raven AI Agent": {
        "Sales Order": r"^(poextract|poextracted|poextractiondata|customerpofile|po_extract|po_extraction)",
    },
    "ERPNext Mexico Compliance": {
        "*": r"^(mx_|sat_|cfdi_|einvoice_|payroll_|curp|rfc|zipcode|tax_regime)",
    },
}


# First match wins. Put more specific modules higher.
PRIORITY = [
    "Raven AI Agent",
    "ERPNext Mexico Compliance",
    "RND",
    "SPC Quality Management",
    "AMBWTDS",
]


ARTIFACT_DIR = "/home/frappe/archived/V13.5-P2"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pick_module(doctype, dt, fieldname=None):
    """Return owning module name, or None if no rule matches."""
    if fieldname:
        for mod in PRIORITY:
            rules = FIELDNAME_OVERRIDES.get(mod, {})
            pat = rules.get(dt) or rules.get("*")
            if pat and re.match(pat, fieldname):
                return mod
    for mod in PRIORITY:
        for entry_dt, regex in MAPPING.get(mod, []):
            if entry_dt != doctype:
                continue
            if re.match(regex, dt or ""):
                return mod
    return None


def _iter_targets():
    """Yield (doctype_table, name_field, dt_field, fieldname_field)."""
    yield "Custom Field", "name", "dt", "fieldname"
    yield "Property Setter", "name", "doc_type", "field_name"
    yield "Workflow", "name", "document_type", None
    yield "Notification", "name", "document_type", None


def _collect():
    """Collect all untagged rows and decide a target module for each."""
    changes = []
    for dtype, name_f, dt_f, fn_f in _iter_targets():
        fields = [name_f, dt_f, "module"] + ([fn_f] if fn_f else [])
        rows = frappe.get_all(
            dtype,
            filters={"module": ["in", ["", None]]},
            fields=fields,
            limit_page_length=0,
        )
        for r in rows:
            tgt = _pick_module(
                dtype,
                r.get(dt_f),
                r.get(fn_f) if fn_f else None,
            )
            changes.append({
                "doctype": dtype,
                "name": r[name_f],
                "dt": r.get(dt_f),
                "fieldname": r.get(fn_f) if fn_f else None,
                "target_module": tgt,
            })
    return changes


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def dry_run():
    """READ-ONLY. Produces 10-dry-run.json + prints summary."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    changes = _collect()
    tagged = [c for c in changes if c["target_module"]]
    untagged = [c for c in changes if not c["target_module"]]
    report = {
        "total": len(changes),
        "will_tag": len(tagged),
        "still_untagged": len(untagged),
        "by_target": {},
        "by_doctype": {},
        "still_untagged_sample": untagged[:100],
    }
    for c in tagged:
        report["by_target"].setdefault(c["target_module"], 0)
        report["by_target"][c["target_module"]] += 1
        report["by_doctype"].setdefault(c["doctype"], 0)
        report["by_doctype"][c["doctype"]] += 1
    print(json.dumps(report, indent=2, default=str))
    out = os.path.join(ARTIFACT_DIR, "10-dry-run.json")
    with open(out, "w") as f:
        json.dump({"report": report, "changes": changes},
                  f, indent=2, default=str)
    print(f"\nFull change set: {out}")


def apply():
    """WRITES to DB. Tags only rows where module IS NULL."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    changes = _collect()
    applied = 0
    skipped_unmapped = 0
    errors = []
    for c in changes:
        if not c["target_module"]:
            skipped_unmapped += 1
            continue
        try:
            frappe.db.set_value(
                c["doctype"], c["name"], "module",
                c["target_module"], update_modified=False,
            )
            applied += 1
        except Exception as e:
            errors.append({"change": c, "error": str(e)})
    frappe.db.commit()
    summary = {
        "applied": applied,
        "skipped_unmapped": skipped_unmapped,
        "errors_sample": errors[:100],
        "error_count": len(errors),
    }
    print(json.dumps(summary, indent=2, default=str))
    out = os.path.join(ARTIFACT_DIR, "11-apply-summary.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSummary written: {out}")