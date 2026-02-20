"""
BOM Activator - Safely activate inactive BOMs with correct structure
Only activates BOMs matching Pattern A: 0301 + E003 + LBLxxxx

SAFE LIST (35 BOMs):
0304-0306, 0308-0322, 0324-0333, 0335-0342

EXCLUDED:
- BOM-0307-001 (Cancelled, wrong structure)
- BOM-0323-001 (Draft, wrong structure - juice production BOM)
"""

import frappe
from datetime import datetime

SAFE_TO_ACTIVATE = [
    "BOM-0304-001", "BOM-0305-001", "BOM-0306-001",
    "BOM-0308-001", "BOM-0309-001", "BOM-0310-001", "BOM-0311-001",
    "BOM-0312-001", "BOM-0313-001", "BOM-0314-001", "BOM-0315-001",
    "BOM-0316-001", "BOM-0317-001", "BOM-0318-001", "BOM-0319-001",
    "BOM-0320-001", "BOM-0321-001", "BOM-0322-001",
    "BOM-0324-001", "BOM-0325-001", "BOM-0326-001", "BOM-0327-001",
    "BOM-0328-001", "BOM-0329-001", "BOM-0330-001", "BOM-0331-001",
    "BOM-0332-001", "BOM-0333-001",
    "BOM-0335-001", "BOM-0336-001", "BOM-0337-001", "BOM-0338-001",
    "BOM-0339-001", "BOM-0340-001", "BOM-0341-001", "BOM-0342-001"
]

def validate_bom_structure(bom_doc):
    items = [d.item_code for d in bom_doc.items]
    has_0301 = "0301" in items
    has_e003 = "E003" in items
    has_label = any(item.startswith("LBL") for item in items)
    allowed_items = {"0301", "E003", "M016"} | {i for i in items if i.startswith("LBL")}
    unexpected = set(items) - allowed_items
    return {"is_valid": has_0301 and has_e003 and has_label and len(unexpected) == 0, "unexpected": list(unexpected)}

def activate_boms(dry_run=True):
    frappe.set_user("Administrator")
    activated, skipped = [], []
    print("=" * 60)
    print(f"BOM ACTIVATOR - {'DRY RUN' if dry_run else 'LIVE MODE'}")
    print("=" * 60)
    for bom_name in SAFE_TO_ACTIVATE:
        if not frappe.db.exists("BOM", bom_name):
            skipped.append(f"{bom_name}: Not found")
            continue
        bom = frappe.get_doc("BOM", bom_name)
        if bom.is_active:
            skipped.append(f"{bom_name}: Already active")
            continue
        v = validate_bom_structure(bom)
        if not v["is_valid"]:
            skipped.append(f"{bom_name}: Invalid structure {v['unexpected']}")
            continue
        if bom.docstatus != 1:
            skipped.append(f"{bom_name}: DocStatus={bom.docstatus}")
            continue
        if dry_run:
            activated.append(bom_name)
            print(f"✅ {bom_name} ({bom.item}): WOULD ACTIVATE")
        else:
            bom.is_active = 1
            bom.is_default = 1
            bom.db_update()
            frappe.db.commit()
            activated.append(bom_name)
            print(f"✅ {bom_name} ({bom.item}): ACTIVATED")
    print("=" * 60)
    print(f"Activated: {len(activated)} | Skipped: {len(skipped)}")
    for s in skipped:
        print(f"  ⏭️ {s}")
    return activated

def run_dry():
    return activate_boms(dry_run=True)

def run_live():
    return activate_boms(dry_run=False)
