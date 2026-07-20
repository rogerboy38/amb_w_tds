"""Sprint 2.1 REMAP — re-author the canonical 0307 tiers from the FoxPro
AUTORIZADO spec, per Alicia's five rulings (2026-07-20).

Ruling 1: the "30" is an artifact (a per-mL liquid limit landed on a per-gram
          powder) -> base micro is APC NMT 500 / M&Y NMT 100; retire the M30
          tier shapes.
Ruling 2: the AUTORIZADO text spec governs, NOT the migrated ERPNext numeric.
Ruling 3: key the deterministic customers (53 on 500/100, 11 on 50/50).
Ruling 4: Brenntag entities keyed individually, never by trading name.
Ruling 5: customer+order resolution for genuinely multi-tier customers, keyed
          provisionally with pending_alicia=1 and reported for one-shot confirm.

Evidence: enc_tdscli.dbf (67 live 0307 customer TDS headers, AUTORIZO =
Alicia Perez Medina on 66) joined to detanal_es.FOLIO. Re-derived by Node B
independently; matches vm3's parallel count exactly (53 / 11 / 3 incomplete).

Additive and reversible: touches ONLY the TDS-0307-* records created in P1
(the 72 legacy originals stay frozen at modified 2026-07-01) and two additive
Custom Fields on the Customer Item child table.
"""

import json
import sys

import frappe

RETIRE = ["TDS-0307-ASH35-M30", "TDS-0307-HM-M30"]  # the "30" artifact shapes (unkeyed)

# FoxPro tier id -> the canonical record that implements it.
FOX_TO_REC = {
    "TDS-0307-BASE": "TDS-0307-BASE",
    "TDS-0307-ASH35": "TDS-0307-ASH35",
    "TDS-0307-ASH35-M50": "TDS-0307-ASH35-M50",
    "TDS-0307-HM-ASH35-M50": "TDS-0307-HM-M50",
    "TDS-0307-ASH35-MOIST10-M50": "TDS-0307-MOIST10",
}

# Tiers with no AUTORIZADO support — kept (Alicia ruled pH/Moisture real) but
# deliberately left unkeyed until she names their customers.
UNSUPPORTED = ["TDS-0307-PH40", "TDS-0307-PH40-M50", "TDS-0307-ES"]

CUSTOM_FIELDS = [
    {
        "dt": "Customer Item",
        "fieldname": "custom_evidence_folio",
        "label": "Evidence Folio (legacy TDS)",
        "fieldtype": "Data",
        "insert_after": "customer",
        "description": "FoxPro enc_tdscli FOLIO whose AUTORIZADO spec justifies this keying.",
    },
    {
        "dt": "Customer Item",
        "fieldname": "custom_pending_alicia",
        "label": "Pending Alicia Confirm",
        "fieldtype": "Check",
        "insert_after": "custom_evidence_folio",
        "description": "Provisional keying: legacy evidence incomplete or ambiguous.",
    },
]


def norm(s):
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


LEGAL = ("SADECV", "SDERLDECV", "SAPIDECV", "GMBHCOKG", "GMBHCO", "GMBH", "LTDA", "LTD", "LLC",
         "INC", "CORP", "CORPORATION", "SARL", "SRO", "SPZOO", "SPZOO", "APS", "AS", "AB", "SL",
         "SLU", "SA", "SAS", "BV", "NV", "CO", "COMPANY", "PTELTD")


def _strip_legal(n):
    changed = True
    while changed:
        changed = False
        for suf in LEGAL:
            if n.endswith(suf) and len(n) > len(suf) + 3:
                n = n[: -len(suf)]
                changed = True
    return n


def match_customer(fox_name, erp_customers):
    """FoxPro NOM_CLI -> ERPNext Customer, ENTITY-level (Ruling 4).

    Never collapse a distinct legal entity onto a shorter trading-name customer:
    'BARENTZ IBERIA S.L.U' must not match a generic 'Barentz'. Prefix matching is
    therefore only allowed when the leftover is pure legal-form noise, never when
    it carries a geography or entity word.
    """
    n = norm(fox_name)
    if n in erp_customers:
        return erp_customers[n]
    ns = _strip_legal(n)
    for k, v in erp_customers.items():
        if _strip_legal(k) == ns:
            return v
    # last resort: same entity, trivial spelling delta only
    for k, v in erp_customers.items():
        if abs(len(k) - len(n)) <= 2 and (k.startswith(n[:12]) or n.startswith(k[:12])):
            return v
    return None


def main(apply_it):
    folio_tier = json.load(open("/mnt/e/Claude/sprint2/foxpro-0307-folio-tier.json"))
    erp = {norm(c.name): c.name for c in frappe.get_all("Customer", fields=["name"])}

    # ---- 1. custom fields (additive) -------------------------------------
    for cf in CUSTOM_FIELDS:
        if frappe.db.exists("Custom Field", f"{cf['dt']}-{cf['fieldname']}"):
            print(f"CF {cf['fieldname']}: exists")
        elif apply_it:
            frappe.get_doc(dict(doctype="Custom Field", **cf)).insert(ignore_permissions=True)
            print(f"CF {cf['fieldname']}: CREATED")
        else:
            print(f"CF {cf['fieldname']}: would create")

    # ---- 2. retire the "30" artifact tiers --------------------------------
    for name in RETIRE:
        if not frappe.db.exists("TDS Product Specification", name):
            print(f"RETIRE {name}: already absent")
            continue
        keyed = frappe.db.sql(
            """SELECT customer FROM `tabCustomer Item`
               WHERE parenttype='TDS Product Specification' AND parent=%s""",
            name,
        )
        keyed = [k[0] for k in keyed]
        print(f"RETIRE {name}: keyed customers={len(keyed)} {keyed}")
        # A customer keyed onto an artifact tier in P1 is re-keyed from the
        # AUTORIZADO evidence in step 3 of this same run; verify it has a
        # destination there before dropping the shape.
        dest_ok = True
        for c in keyed:
            dest = [f for f, i in folio_tier.items() if match_customer(i["cliente"], erp) == c]
            if not dest:
                dest_ok = False
                print(f"   !! {c} has NO AUTORIZADO destination — REFUSING to retire")
        if not dest_ok:
            continue
        if apply_it:
            if keyed:
                doc = frappe.get_doc("TDS Product Specification", name)
                doc.set("custom_tds_customers", [])
                doc.save(ignore_permissions=True)
                print(f"   cleared {len(keyed)} keying(s); re-keyed from AUTORIZADO below")
            frappe.delete_doc("TDS Product Specification", name, force=True, ignore_permissions=True)
            print(f"   deleted {name}")

    # ---- 3. re-key every surviving tier from the AUTORIZADO evidence ------
    by_rec = {}
    unmatched = []
    for folio, info in folio_tier.items():
        fox_tier = info["tier"]
        cust = match_customer(info["cliente"], erp)
        if not cust:
            unmatched.append((folio, info["cliente"]))
            continue
        rec = FOX_TO_REC.get(fox_tier)
        pending = 0
        if fox_tier == "INCOMPLETE":
            # legacy sheet lacks APC/M&Y — provisional, needs Alicia
            rec, pending = "TDS-0307-BASE", 1
        by_rec.setdefault(rec, []).append(
            {"customer": cust, "custom_evidence_folio": folio, "custom_pending_alicia": pending}
        )

    # a customer landing on >1 record is genuinely per-order -> all provisional
    seen = {}
    for rec, rows in by_rec.items():
        for r in rows:
            seen.setdefault(r["customer"], set()).add(rec)
    multi = {c for c, recs in seen.items() if len(recs) > 1}
    for rec, rows in by_rec.items():
        for r in rows:
            if r["customer"] in multi:
                r["custom_pending_alicia"] = 1

    for rec in sorted(set(list(FOX_TO_REC.values()) + UNSUPPORTED)):
        rows = by_rec.get(rec, [])
        # dedupe by (customer, folio)
        uniq = {(r["customer"], r["custom_evidence_folio"]): r for r in rows}
        rows = sorted(uniq.values(), key=lambda r: r["customer"])
        prov = sum(1 for r in rows if r["custom_pending_alicia"])
        print(f"\n{rec}: {len(rows)} customer rows ({prov} provisional)")
        for r in rows[:60]:
            flag = "  ⚠pending" if r["custom_pending_alicia"] else ""
            print(f"    {r['customer'][:44]:44s} folio={r['custom_evidence_folio']}{flag}")
        if rec in UNSUPPORTED and not rows:
            print("    (no AUTORIZADO support — intentionally left unkeyed)")
        if not apply_it or not frappe.db.exists("TDS Product Specification", rec):
            continue
        doc = frappe.get_doc("TDS Product Specification", rec)
        doc.set("custom_tds_customers", [])
        for r in rows:
            doc.append("custom_tds_customers", r)
        doc.save(ignore_permissions=True)

    print("\nunmatched FoxPro customers (no ERPNext Customer):", unmatched)
    print("multi-record customers (all rows flagged pending):", sorted(multi))
    if apply_it:
        frappe.db.commit()
        print("\nAPPLIED")
    else:
        print("\nDRY-RUN — nothing written.")


if __name__ == "__main__":
    apply_it = "apply=1" in sys.argv
    frappe.init(site="v2.sysmayal.cloud", sites_path="sites")
    frappe.connect()
    main(apply_it)
    frappe.destroy()
