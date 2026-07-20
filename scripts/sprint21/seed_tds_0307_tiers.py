"""Sprint 2.1 P1 — seed the canonical 0307 TDS base + tier records (ADDITIVE).

Dry-run by default; pass apply=1 to write. Creates ONLY new TDS Product
Specification records — never reads-modify-writes an existing one. Reversible:
delete the 10 created names.

Base = Alicia's official 16-parameter 0307 contract. Tiers = base + sparse
overrides (only the differing params), materialized to a full contract so each
tier is directly scoreable by the solver.

Drift rule applied: the numeric bound is authoritative and the acceptance text
is REGENERATED from it. Records whose legacy text and numeric bound disagree are
NOT auto-resolved here — they are reported for Alicia (see the conflicts letter).
"""

import json
import sys

import frappe

BASE_PARAMS = [
    # (specification, value_text, numeric, min, max, uom, blend_method)
    ("Appearance", "FINE HOMOGENEOUS POWDER", 0, None, None, "", "all_pass"),
    ("Particle Size", "99% THROUGH NO.100 MESH", 0, None, None, "", "all_pass"),
    ("Color Visual", "OFF WHITE TO LIGHT BEIGE", 0, None, None, "", "all_pass"),
    ("Odor", "LIGHT VEGETABLE", 0, None, None, "", "all_pass"),
    ("Taste", "ACIDIC,SALTY", 0, None, None, "", "all_pass"),
    ("Color Gardner", "1-2", 1, 1.0, 2.0, "", "mass_avg"),
    ("Moisture", "NMT 8%", 1, 0.0, 8.0, "%", "mass_avg"),
    ("Ash", "NMT 40%", 1, 0.0, 40.0, "%", "mass_avg"),
    ("pH", "3.5-5.0", 1, 3.5, 5.0, "", "hplus_avg"),
    ("Specific Gravity", "1.002-1.020", 1, 1.002, 1.020, "", "mass_avg"),
    ("Aloin Content", "NMT 0.1 PPM", 1, 0.0, 0.1, "PPM", "mass_avg"),
    ("Aerobic Plate Count", "NMT 500 CFU/G", 1, 0.0, 500.0, "CFU/G", "worst_case"),
    ("Mold And Yeast", "NMT 100 CFU/G", 1, 0.0, 100.0, "CFU/G", "worst_case"),
    ("Coliforms", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Pathogens", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Preservatives", "NONE", 0, None, None, "", "all_pass"),
]

# Heavy-metals / pesticide block carried by the HM tiers (from the legacy exemplars).
HM_BLOCK = [
    ("Arsenic", "NMT 1 PPM", 1, 0.0, 1.0, "PPM", "mass_avg"),
    ("Lead", "NMT 1 PPM", 1, 0.0, 1.0, "PPM", "mass_avg"),
    ("Cadmium", "NMT 0.5 PPM", 1, 0.0, 0.5, "PPM", "mass_avg"),
    ("Mercury", "NMT 0.1 PPM", 1, 0.0, 0.1, "PPM", "mass_avg"),
    ("Heavy Metals", "NMT 10 PPM", 1, 0.0, 10.0, "PPM", "mass_avg"),
    ("Ddt", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Dieldrin", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Endrin", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Aldrin", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Bhc", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("E.coli", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Salmonella", "NEGATIVE", 0, None, None, "", "all_pass"),
    ("Staph. Aureus", "NEGATIVE", 0, None, None, "", "all_pass"),
]

ES_TEXT = {
    "Appearance": "POLVO FINO HOMOGENEO",
    "Particle Size": "99% PASA MALLA NO. 100",
    "Odor": "LIGERAMENTE VEGETAL",
    "Taste": "ACIDO,SALADO",
    "Color Visual": "BLANCO HUESO A BEIGE CLARO",
    "Coliforms": "NEGATIVO",
    "Pathogens": "NEGATIVO",
    "Preservatives": "NINGUNO",
}

UOM_TEXT = {"%": "NMT {v:g}%", "CFU/G": "NMT {v:g} CFU/G", "PPM": "NMT {v:g} PPM"}

TIERS = {
    "TDS-0307-BASE": {"desc": "Canonical 0307 contract (Alicia's official 16-parameter table)", "ov": {}},
    "TDS-0307-ASH35": {"desc": "Ash tightened to 35%", "ov": {"Ash": 35.0}},
    "TDS-0307-ASH35-M50": {"desc": "Ash 35% + microbial 50/50", "ov": {"Ash": 35.0, "Aerobic Plate Count": 50.0, "Mold And Yeast": 50.0}},
    "TDS-0307-ASH35-M30": {"desc": "Ash 35% + microbial 30/30 (Brenntag/Barentz UK)", "ov": {"Ash": 35.0, "Aerobic Plate Count": 30.0, "Mold And Yeast": 30.0}},
    "TDS-0307-HM-M30": {"desc": "Heavy-metals/pesticide block + Ash 35% + APC 30 / M&Y 50", "ov": {"Ash": 35.0, "Aerobic Plate Count": 30.0, "Mold And Yeast": 50.0}, "hm": True},
    "TDS-0307-HM-M50": {"desc": "Heavy-metals/pesticide block + Ash 35% + microbial 50/50", "ov": {"Ash": 35.0, "Aerobic Plate Count": 50.0, "Mold And Yeast": 50.0}, "hm": True},
    "TDS-0307-PH40": {"desc": "Ash 35% + pH 4.0-5.0 (release-gating, Alicia-confirmed real)", "ov": {"Ash": 35.0, "pH": (4.0, 5.0)}},
    "TDS-0307-PH40-M50": {"desc": "Ash 35% + pH 4.0-5.0 + microbial 50/50", "ov": {"Ash": 35.0, "Aerobic Plate Count": 50.0, "Mold And Yeast": 50.0, "pH": (4.0, 5.0)}},
    "TDS-0307-MOIST10": {"desc": "Ash 35% + Moisture 10% + microbial 50/50", "ov": {"Ash": 35.0, "Aerobic Plate Count": 50.0, "Mold And Yeast": 50.0, "Moisture": 10.0}},
    "TDS-0307-ES": {"desc": "Spanish-language contract, Ash 35%", "ov": {"Ash": 35.0}, "es": True},
}


def build_rows(tier):
    """Materialize base + sparse overrides into a full parameter contract."""
    spec = TIERS[tier]
    rows = []
    for name, text, numeric, lo, hi, uom, blend in BASE_PARAMS:
        ov = spec["ov"].get(name)
        if ov is not None:
            if isinstance(ov, tuple):  # range override (pH)
                lo, hi = ov
                text = f"{lo:g}-{hi:g}"
            else:  # max override — numeric governs, text REGENERATED from it
                hi = ov
                text = UOM_TEXT.get(uom, "NMT {v:g}").format(v=ov)
        if spec.get("es"):
            text = ES_TEXT.get(name, text)
        rows.append(
            {
                "specification": name,
                "value": text,
                "numeric": numeric,
                "min_value": lo,
                "max_value": hi,
                "custom_uom": uom,
                "custom_blend_method": blend,
            }
        )
    if spec.get("hm"):
        for name, text, numeric, lo, hi, uom, blend in HM_BLOCK:
            rows.append(
                {
                    "specification": name,
                    "value": text,
                    "numeric": numeric,
                    "min_value": lo,
                    "max_value": hi,
                    "custom_uom": uom,
                    "custom_blend_method": blend,
                }
            )
    return rows


def main(apply_it, cmap_path):
    cmap = json.load(open(cmap_path))
    tier2cust = cmap["tier2customers"]
    # A customer that maps to more than one tier is AMBIGUOUS — do not key it here.
    seen = {}
    for tier, custs in tier2cust.items():
        for c in custs:
            seen.setdefault(c, []).append(tier)
    ambiguous = {c: t for c, t in seen.items() if len(t) > 1}

    missing_specs = set()
    created = []
    for tier in TIERS:
        rows = build_rows(tier)
        for r in rows:
            if not frappe.db.exists("Quality Inspection Parameter", r["specification"]):
                missing_specs.add(r["specification"])
        custs = [c for c in tier2cust.get(tier, []) if c not in ambiguous]
        print(f"\n{tier}  ({TIERS[tier]['desc']})")
        print(f"   params={len(rows)}  overrides={TIERS[tier]['ov'] or 'NONE (base)'}")
        print(f"   customers keyed={len(custs)} {custs}")
        if frappe.db.exists("TDS Product Specification", tier):
            print("   !! ALREADY EXISTS — skipping (idempotent)")
            continue
        if not apply_it:
            continue
        doc = frappe.new_doc("TDS Product Specification")
        doc.name = tier
        # naming_series is a mandatory Data field the legacy rows fill with the
        # record's own name (autoname is `prompt`); follow that convention.
        doc.naming_series = tier
        doc.product_item = "0307"
        doc.item_code = "0307"
        doc.item_name = f"0307 — {TIERS[tier]['desc']}"
        doc.tds_version = "SPRINT2.1-P1"
        for r in rows:
            doc.append("item_quality_inspection_parameter", r)
        for c in custs:
            doc.append("custom_tds_customers", {"customer": c})
        doc.insert(ignore_permissions=True)
        created.append(doc.name)

    print("\n=== AMBIGUOUS customers (mapped to >1 tier — NOT keyed, for Alicia) ===")
    for c, t in sorted(ambiguous.items()):
        print(f"   {c}  ->  {t}")
    if missing_specs:
        print("\n!! Quality Inspection Parameter records MISSING (would break Link):", sorted(missing_specs))
    if apply_it:
        frappe.db.commit()
        print("\nCREATED:", created)
    else:
        print("\nDRY-RUN — nothing written. Pass apply=1 to write.")


if __name__ == "__main__":
    apply_it = "apply=1" in sys.argv
    frappe.init(site="v2.sysmayal.cloud", sites_path="sites")
    frappe.connect()
    main(apply_it, "/mnt/e/Claude/sprint2/tds-0307-collapse-map.json")
    frappe.destroy()
