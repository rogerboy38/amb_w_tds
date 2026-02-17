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
import json
from datetime import datetime


# BOMs with correct structure (0301 + E003 + LBL pattern)
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

# Excluded BOMs (wrong structure)
EXCLUDED = ["BOM-0307-001", "BOM-0323-001"]


def validate_bom_structure(bom_doc):
    """Verify BOM has expected 0301 + E003 + LBL structure"""
    items = [d.item_code for d in bom_doc.items]
    
    has_0301 = "0301" in items
    has_e003 = "E003" in items
    has_label = any(item.startswith("LBL") for item in items)
    
    # Allow M016 as optional additive (for 0304, 0306)
    allowed_items = {"0301", "E003", "M016"} | {i for i in items if i.startswith("LBL")}
    unexpected = set(items) - allowed_items
    
    return {
        "has_0301": has_0301,
        "has_e003": has_e003,
        "has_label": has_label,
        "unexpected_items": list(unexpected),
        "is_valid": has_0301 and has_e003 and has_label and len(unexpected) == 0
    }


def activate_boms(dry_run=True):
    """
    Activate inactive BOMs with correct structure.
    
    Args:
        dry_run: If True, only report what would be done without making changes
    """
    frappe.set_user("Administrator")
    
    results = {
        "mode": "DRY RUN" if dry_run else "LIVE",
        "timestamp": datetime.now().isoformat(),
        "activated": [],
        "skipped": [],
        "errors": []
    }
    
    print("=" * 80)
    print(f"BOM ACTIVATOR - {'DRY RUN' if dry_run else 'LIVE MODE'}")
    print("=" * 80)
    print(f"Target BOMs: {len(SAFE_TO_ACTIVATE)}")
    print(f"Excluded: {EXCLUDED}")
    print("-" * 80)
    
    for bom_name in SAFE_TO_ACTIVATE:
        try:
            if not frappe.db.exists("BOM", bom_name):
                results["skipped"].append({
                    "bom": bom_name,
                    "reason": "Does not exist"
                })
                print(f"⏭️  {bom_name}: SKIP - Does not exist")
                continue
            
            bom = frappe.get_doc("BOM", bom_name)
            
            # Check if already active
            if bom.is_active:
                results["skipped"].append({
                    "bom": bom_name,
                    "reason": "Already active"
                })
                print(f"⏭️  {bom_name}: SKIP - Already active")
                continue
            
            # Validate structure
            validation = validate_bom_structure(bom)
            if not validation["is_valid"]:
                results["skipped"].append({
                    "bom": bom_name,
                    "reason": f"Invalid structure: {validation}"
                })
                print(f"⏭️  {bom_name}: SKIP - Invalid structure: {validation['unexpected_items']}")
                continue
            
            # Check docstatus
            if bom.docstatus != 1:
                results["skipped"].append({
                    "bom": bom_name,
                    "reason": f"DocStatus={bom.docstatus} (not Submitted)"
                })
                print(f"⏭️  {bom_name}: SKIP - DocStatus={bom.docstatus} (needs to be 1)")
                continue
            
            # Activate
            if dry_run:
                results["activated"].append({
                    "bom": bom_name,
                    "item": bom.item,
                    "items": [d.item_code for d in bom.items],
                    "action": "Would activate"
                })
                print(f"✅ {bom_name} ({bom.item}): WOULD ACTIVATE")
            else:
                bom.is_active = 1
                bom.is_default = 1
                bom.db_update()
                frappe.db.commit()
                
                results["activated"].append({
                    "bom": bom_name,
                    "item": bom.item,
                    "action": "Activated"
                })
                print(f"✅ {bom_name} ({bom.item}): ACTIVATED")
                
        except Exception as e:
            results["errors"].append({
                "bom": bom_name,
                "error": str(e)
            })
            print(f"❌ {bom_name}: ERROR - {str(e)}")
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Activated: {len(results['activated'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"Errors: {len(results['errors'])}")
    
    if results["skipped"]:
        print("\nSkipped Details:")
        for skip in results["skipped"]:
            print(f"  - {skip['bom']}: {skip['reason']}")
    
    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err['bom']}: {err['error']}")
    
    return results


def run_dry():
    """Run in dry-run mode (safe, no changes)"""
    return activate_boms(dry_run=True)


def run_live():
    """Run in live mode (makes actual changes)"""
    return activate_boms(dry_run=False)


if __name__ == "__main__":
    run_dry()
