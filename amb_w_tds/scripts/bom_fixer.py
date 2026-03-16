"""
BOM Fixer - Fix flat BOMs with incorrect structure
Handles: BOM-0307-006 (self-reference), BOM-0301-001, BOM-0303-005, BOM-A0303-001

Run with:
  bench --site <site> execute amb_w_tds.scripts.bom_fixer.run_dry
  bench --site <site> execute amb_w_tds.scripts.bom_fixer.run_live
"""

import frappe
from datetime import datetime


# Reference BOM structure from activated BOMs (e.g., BOM-0308-001)
# Standard pattern: 0301 (1 Kg) + E003 (1 Nos) + LBLxxxx (1 Nos)
STANDARD_QTY = {
    "0301": 1.0,
    "E003": 1.0,
    "label": 1.0
}


def get_default_company():
    """Get company from user defaults, global defaults, or first available"""
    # 1. Try user's default company
    company = frappe.defaults.get_user_default("company")
    if company:
        return company
    
    # 2. Try global defaults
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if company:
        return company
    
    # 3. Fallback: get first company in system
    company = frappe.db.get_value("Company", {}, "name")
    return company or "Innovaloe LLC"


def get_raven_channel():
    """Get Raven channel for posting results"""
    channel = frappe.db.get_value(
        "Raven Channel",
        {"channel_name": "bom-hierarchy-audit"},
        "name"
    )
    return channel


def post_to_raven(message, channel=None):
    """Post message to Raven channel
    
    Args:
        message: The message text to post
        channel: Channel name (str) or channel ID. If None, uses default 'bom-hierarchy-audit'
    """
    # Resolve channel name to ID if needed
    if channel and not channel.startswith("raven-"):
        # Assume it's a channel name, look up the ID
        channel_id = frappe.db.get_value(
            "Raven Channel",
            {"channel_name": channel},
            "name"
        )
        if channel_id:
            channel = channel_id
        else:
            # Channel name not found, try using as-is
            pass
    
    if not channel:
        channel = get_raven_channel()
    if not channel:
        print("⚠️ Raven channel not found, skipping post")
        return False
    
    try:
        msg = frappe.get_doc({
            "doctype": "Raven Message",
            "channel_id": channel,
            "message_type": "Text",
            "text": message
        })
        msg.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"📨 Posted to Raven: {message[:50]}...")
        return True
    except Exception as e:
        print(f"⚠️ Failed to post to Raven: {e}")
        return False


def fix_bom_0307(dry_run=True):
    """
    Fix BOM-0307-006 - Self-reference bug
    Current: 0307 (self!) + LBL0307
    Correct: 0301 + E003 + LBL0307
    """
    result = {"bom": "BOM-0307-006", "item": "0307", "status": "pending", "action": ""}
    
    print("\n" + "=" * 60)
    print("Fixing BOM-0307-006 (Self-reference bug)")
    print("=" * 60)
    
    if not frappe.db.exists("BOM", "BOM-0307-006"):
        result["status"] = "skipped"
        result["action"] = "BOM does not exist"
        print(f"⏭️ BOM-0307-006 not found")
        return result
    
    bom = frappe.get_doc("BOM", "BOM-0307-006")
    print(f"Current items: {[d.item_code for d in bom.items]}")
    print(f"DocStatus: {bom.docstatus}, Is Active: {bom.is_active}, Is Default: {bom.is_default}")
    
    if dry_run:
        result["status"] = "would_fix"
        result["action"] = "Would cancel BOM-0307-006, create new BOM with 0301+E003+LBL0307"
        print(f"✅ DRY RUN: Would cancel and recreate with correct structure")
        return result
    
    try:
        # Step 1: Handle the old BOM based on docstatus
        company = bom.company or get_default_company()
        print(f"ℹ️ Using company: {company}")
        
        if bom.docstatus == 1:  # Submitted - need to cancel first
            bom.is_active = 0
            bom.is_default = 0
            bom.db_update()
            bom.cancel()
            frappe.db.commit()
            print(f"✅ Cancelled BOM-0307-006")
        
        if bom.docstatus == 2:  # Already cancelled - delete it
            frappe.delete_doc("BOM", "BOM-0307-006", force=True, ignore_permissions=True)
            frappe.db.commit()
            print(f"✅ Deleted cancelled BOM-0307-006")
        elif bom.docstatus == 0:  # Draft - just delete
            frappe.delete_doc("BOM", "BOM-0307-006", force=True, ignore_permissions=True)
            frappe.db.commit()
            print(f"✅ Deleted draft BOM-0307-006")
        
        # Step 2: Check if there's already an active correct BOM for 0307
        existing_correct = frappe.db.exists("BOM", {
            "item": "0307",
            "is_active": 1,
            "docstatus": 1
        })
        if existing_correct:
            result["status"] = "skipped"
            result["action"] = f"Active BOM {existing_correct} already exists for 0307"
            print(f"ℹ️ Active BOM {existing_correct} already exists, skipping creation")
            return result
        
        # Step 3: Create new BOM with correct structure
        new_bom = frappe.get_doc({
            "doctype": "BOM",
            "item": "0307",
            "company": company,
            "quantity": 1.0,
            "is_active": 1,
            "is_default": 1,
            "items": [
                {"item_code": "0301", "qty": STANDARD_QTY["0301"], "uom": "Kg"},
                {"item_code": "E003", "qty": STANDARD_QTY["E003"], "uom": "Nos"},
                {"item_code": "LBL0307", "qty": STANDARD_QTY["label"], "uom": "Nos"}
            ]
        })
        # Let ERPNext auto-generate the name
        new_bom.insert(ignore_permissions=True)
        new_bom.submit()
        frappe.db.commit()
        
        result["status"] = "fixed"
        result["action"] = f"Cancelled BOM-0307-006, created {new_bom.name} with 0301+E003+LBL0307"
        print(f"✅ Created and submitted {new_bom.name}")
        
    except Exception as e:
        result["status"] = "error"
        result["action"] = str(e)
        print(f"❌ Error: {e}")
    
    return result


def fix_bom_0301(dry_run=True):
    """
    Fix BOM-0301-001 - Missing parent 0227-PERMEADO
    Current: 0227-30X variant + labels + packaging
    Issue: The 0227 variant name doesn't match expected 0227-PERMEADO
    Action: This is a data verification issue - flag for manual review
    """
    result = {"bom": "BOM-0301-001", "item": "0301", "status": "pending", "action": ""}
    
    print("\n" + "=" * 60)
    print("Reviewing BOM-0301-001 (Missing parent verification)")
    print("=" * 60)
    
    if not frappe.db.exists("BOM", "BOM-0301-001"):
        result["status"] = "skipped"
        result["action"] = "BOM does not exist"
        print(f"⏭️ BOM-0301-001 not found")
        return result
    
    bom = frappe.get_doc("BOM", "BOM-0301-001")
    items = [d.item_code for d in bom.items]
    print(f"Current items: {items}")
    
    # Check if any 0227 variant exists
    has_0227 = any("0227" in item for item in items)
    
    if has_0227:
        result["status"] = "review_needed"
        result["action"] = f"Has 0227 variant but not named 0227-PERMEADO. Manual verification required. Current items: {items}"
        print(f"⚠️ REVIEW NEEDED: Has 0227 variant but naming doesn't match expected hierarchy")
        print(f"   Found: {[i for i in items if '0227' in i]}")
        print(f"   Expected: 0227-PERMEADO")
    else:
        result["status"] = "missing_parent"
        result["action"] = "No 0227 variant found. Needs 0227-PERMEADO added."
        print(f"❌ Missing 0227 parent entirely")
    
    return result


def fix_bom_0303(dry_run=True):
    """
    Fix BOM-0303-005 - Cost BOM, not manufacturing BOM
    Current: MAQ, TRANSP_LEAF, WATER, ELECTRIC, GAS, LABOR (utilities only)
    Issue: This is a cost tracking BOM, not a manufacturing BOM
    Action: Flag for manual review - may need separate manufacturing BOM
    """
    result = {"bom": "BOM-0303-005", "item": "0303", "status": "pending", "action": ""}
    
    print("\n" + "=" * 60)
    print("Reviewing BOM-0303-005 (Cost BOM structure)")
    print("=" * 60)
    
    if not frappe.db.exists("BOM", "BOM-0303-005"):
        result["status"] = "skipped"
        result["action"] = "BOM does not exist"
        print(f"⏭️ BOM-0303-005 not found")
        return result
    
    bom = frappe.get_doc("BOM", "BOM-0303-005")
    items = [d.item_code for d in bom.items]
    print(f"Current items: {items}")
    print(f"DocStatus: {bom.docstatus}, Is Active: {bom.is_active}")
    
    # This is a cost BOM - flag for review
    result["status"] = "review_needed"
    result["action"] = f"Cost BOM (utilities/labor only). May need separate manufacturing BOM with 0227-NORMAL. Items: {items}"
    print(f"⚠️ REVIEW NEEDED: This is a cost tracking BOM, not manufacturing")
    print(f"   Contains: {items}")
    print(f"   Missing: Raw material (0227-NORMAL)")
    
    return result


def fix_bom_a0303(dry_run=True):
    """
    Fix BOM-A0303-001 - Wrong expected parent in audit
    Current: 0303 + M016 + packaging items
    Issue: Audit expected 0227-NORMAL but should expect 0303
    Action: This BOM is actually CORRECT - update audit expectations
    """
    result = {"bom": "BOM-A0303-001", "item": "A0303", "status": "pending", "action": ""}
    
    print("\n" + "=" * 60)
    print("Reviewing BOM-A0303-001 (Audit expectation correction)")
    print("=" * 60)
    
    if not frappe.db.exists("BOM", "BOM-A0303-001"):
        result["status"] = "skipped"
        result["action"] = "BOM does not exist"
        print(f"⏭️ BOM-A0303-001 not found")
        return result
    
    bom = frappe.get_doc("BOM", "BOM-A0303-001")
    items = [d.item_code for d in bom.items]
    print(f"Current items: {items}")
    
    # Check if 0303 is in items (correct parent)
    has_0303 = "0303" in items
    
    if has_0303:
        result["status"] = "correct"
        result["action"] = "BOM structure is CORRECT. Has 0303 as sub-assembly. Audit expected wrong parent (0227-NORMAL instead of 0303)."
        print(f"✅ BOM structure is CORRECT")
        print(f"   Has 0303 as sub-assembly (correct)")
        print(f"   Audit expectation was wrong (expected 0227-NORMAL)")
    else:
        result["status"] = "missing_parent"
        result["action"] = f"Missing 0303 sub-assembly. Items: {items}"
        print(f"❌ Missing 0303 sub-assembly")
    
    return result


def run_fixes(dry_run=True):
    """Run all BOM fixes"""
    frappe.set_user("Administrator")
    
    mode = "DRY RUN" if dry_run else "LIVE MODE"
    print("\n" + "=" * 70)
    print(f"BOM FIXER - {mode}")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = []
    
    # Fix each BOM
    results.append(fix_bom_0307(dry_run))
    results.append(fix_bom_0301(dry_run))
    results.append(fix_bom_0303(dry_run))
    results.append(fix_bom_a0303(dry_run))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    fixed = [r for r in results if r["status"] == "fixed"]
    would_fix = [r for r in results if r["status"] == "would_fix"]
    review = [r for r in results if r["status"] == "review_needed"]
    correct = [r for r in results if r["status"] == "correct"]
    errors = [r for r in results if r["status"] == "error"]
    
    print(f"Fixed: {len(fixed)}")
    print(f"Would Fix (dry run): {len(would_fix)}")
    print(f"Review Needed: {len(review)}")
    print(f"Already Correct: {len(correct)}")
    print(f"Errors: {len(errors)}")
    
    for r in results:
        status_icon = {
            "fixed": "✅",
            "would_fix": "🔄",
            "review_needed": "⚠️",
            "correct": "✓",
            "error": "❌",
            "skipped": "⏭️"
        }.get(r["status"], "?")
        print(f"  {status_icon} {r['bom']}: {r['action'][:60]}...")
    
    # Post to Raven (only in live mode)
    if not dry_run:
        summary_msg = f"""**BOM Fixer Results** ({datetime.now().strftime('%Y-%m-%d %H:%M')})

Fixed: {len(fixed)}
Review Needed: {len(review)}
Correct: {len(correct)}
Errors: {len(errors)}

Details:
""" + "\n".join([f"- {r['bom']}: {r['status']} - {r['action'][:50]}" for r in results])
        
        post_to_raven(summary_msg)
    
    return results


def run_dry():
    """Run in dry-run mode (safe, no changes)"""
    return run_fixes(dry_run=True)


def run_live():
    """Run in live mode (makes actual changes)"""
    return run_fixes(dry_run=False)
