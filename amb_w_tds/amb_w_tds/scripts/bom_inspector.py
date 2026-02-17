#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOM Inspector - Safe inspection of BOM structures before repair.

Functions:
- inspect_inactive_boms(): Table view of all inactive BOMs (0304-0342)
- inspect_flat_boms(): Full BOM tree for flat BOMs (0301, 0303, 0307, A0303)

Run via:
    bench execute amb_w_tds.scripts.bom_inspector.inspect_inactive_boms
    bench execute amb_w_tds.scripts.bom_inspector.inspect_flat_boms
    bench execute amb_w_tds.scripts.bom_inspector.inspect_all
"""

import frappe
from frappe import _


def inspect_inactive_boms():
    """
    Inspect all inactive BOMs (0304-0342) and print their contents.
    Safe read-only operation.
    """
    print("=" * 100)
    print("INACTIVE BOM INSPECTION")
    print("=" * 100)
    
    # List of inactive BOMs from audit
    inactive_items = [f"0{i}" for i in range(304, 343)]
    
    results = []
    
    for item_code in inactive_items:
        bom_name = f"BOM-{item_code}-001"
        
        try:
            if not frappe.db.exists("BOM", bom_name):
                results.append({
                    "bom_name": bom_name,
                    "item_code": item_code,
                    "status": "NOT FOUND",
                    "docstatus": "-",
                    "is_active": "-",
                    "is_default": "-",
                    "num_items": 0,
                    "items": []
                })
                continue
            
            bom = frappe.get_doc("BOM", bom_name)
            items = frappe.get_all(
                "BOM Item",
                filters={"parent": bom_name},
                fields=["item_code", "qty", "uom"]
            )
            
            item_codes = [i["item_code"] for i in items]
            
            results.append({
                "bom_name": bom_name,
                "item_code": item_code,
                "status": "ACTIVE" if bom.is_active else "INACTIVE",
                "docstatus": bom.docstatus,
                "is_active": bom.is_active,
                "is_default": bom.is_default,
                "num_items": len(items),
                "items": item_codes
            })
            
        except Exception as e:
            results.append({
                "bom_name": bom_name,
                "item_code": item_code,
                "status": f"ERROR: {str(e)[:30]}",
                "docstatus": "-",
                "is_active": "-",
                "is_default": "-",
                "num_items": 0,
                "items": []
            })
    
    # Print table header
    print(f"\n{'BOM Name':<20} {'Item':<8} {'Status':<10} {'DocSt':<6} {'Active':<7} {'Default':<8} {'#Items':<7} {'Components'}")
    print("-" * 120)
    
    for r in results:
        items_str = ", ".join(r["items"][:5])
        if len(r["items"]) > 5:
            items_str += f"... (+{len(r['items'])-5})"
        
        print(f"{r['bom_name']:<20} {r['item_code']:<8} {r['status']:<10} {str(r['docstatus']):<6} {str(r['is_active']):<7} {str(r['is_default']):<8} {r['num_items']:<7} {items_str}")
    
    # Summary
    active_count = sum(1 for r in results if r["status"] == "ACTIVE")
    inactive_count = sum(1 for r in results if r["status"] == "INACTIVE")
    not_found = sum(1 for r in results if r["status"] == "NOT FOUND")
    
    print("\n" + "=" * 100)
    print(f"SUMMARY: {active_count} Active | {inactive_count} Inactive | {not_found} Not Found")
    print("=" * 100)
    
    return results


def inspect_flat_boms():
    """
    Inspect flat BOMs with full BOM tree details.
    Shows exactly what items are in each BOM.
    """
    print("=" * 100)
    print("FLAT BOM INSPECTION - Full BOM Tree")
    print("=" * 100)
    
    flat_boms = [
        {"bom_name": "BOM-0301-001", "item_code": "0301", "expected_parent": "0227-PERMEADO"},
        {"bom_name": "BOM-0303-005", "item_code": "0303", "expected_parent": "0227-NORMAL"},
        {"bom_name": "BOM-0307-006", "item_code": "0307", "expected_parent": "0301"},
        {"bom_name": "BOM-A0303-001", "item_code": "A0303", "expected_parent": "0227-NORMAL"},
    ]
    
    for bom_info in flat_boms:
        bom_name = bom_info["bom_name"]
        expected_parent = bom_info["expected_parent"]
        
        print(f"\n{'='*80}")
        print(f"BOM: {bom_name}")
        print(f"Item: {bom_info['item_code']}")
        print(f"Expected Parent: {expected_parent}")
        print(f"{'='*80}")
        
        try:
            if not frappe.db.exists("BOM", bom_name):
                print(f"  ❌ BOM NOT FOUND")
                continue
            
            bom = frappe.get_doc("BOM", bom_name)
            
            print(f"\n  Status: {'ACTIVE' if bom.is_active else 'INACTIVE'}")
            print(f"  DocStatus: {bom.docstatus} ({'Draft' if bom.docstatus == 0 else 'Submitted' if bom.docstatus == 1 else 'Cancelled'})")
            print(f"  Is Default: {bom.is_default}")
            print(f"  Quantity: {bom.quantity} {bom.uom if hasattr(bom, 'uom') else ''}")
            
            # Get BOM items with full details
            items = frappe.get_all(
                "BOM Item",
                filters={"parent": bom_name},
                fields=["item_code", "item_name", "qty", "uom", "rate", "amount"],
                order_by="idx"
            )
            
            print(f"\n  BOM Items ({len(items)} total):")
            print(f"  {'-'*70}")
            print(f"  {'#':<4} {'Item Code':<35} {'Qty':<10} {'UOM':<8} {'Rate':<10}")
            print(f"  {'-'*70}")
            
            has_expected_parent = False
            for idx, item in enumerate(items, 1):
                marker = ""
                if item["item_code"] == expected_parent:
                    marker = " ✅ PARENT FOUND"
                    has_expected_parent = True
                elif item["item_code"] == bom_info["item_code"]:
                    marker = " ⚠️  SELF-REFERENCE!"
                
                print(f"  {idx:<4} {item['item_code']:<35} {item['qty']:<10} {item['uom']:<8} {item.get('rate', 0):<10}{marker}")
            
            print(f"  {'-'*70}")
            
            if has_expected_parent:
                print(f"\n  ✅ CORRECT: Contains expected parent '{expected_parent}'")
            else:
                print(f"\n  ❌ MISSING: Expected parent '{expected_parent}' NOT in BOM")
                print(f"     ACTION NEEDED: Add '{expected_parent}' as component")
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
    
    return True


def inspect_missing_boms():
    """
    Check if items exist for missing BOMs and show their details.
    """
    print("=" * 100)
    print("MISSING BOM INSPECTION")
    print("=" * 100)
    
    missing_items = [
        {"item_code": "0302", "expected_parent": "0227-RETENIDO", "name": "Retenido Powder"},
        {"item_code": "0334", "expected_parent": "0301", "name": "Standard Variant 0334"},
        {"item_code": "0803-KOSHER-ORGANIC", "expected_parent": None, "name": "ORGANIC INNER LEAF POWDER"},
    ]
    
    for item_info in missing_items:
        item_code = item_info["item_code"]
        
        print(f"\n{'='*60}")
        print(f"Item: {item_code} - {item_info['name']}")
        print(f"{'='*60}")
        
        # Check if item exists
        if not frappe.db.exists("Item", item_code):
            print(f"  ❌ ITEM DOES NOT EXIST in system")
            print(f"     ACTION: Create Item '{item_code}' first, then create BOM")
            continue
        
        item = frappe.get_doc("Item", item_code)
        print(f"  ✅ Item exists: {item.item_name}")
        print(f"     Item Group: {item.item_group}")
        print(f"     Stock UOM: {item.stock_uom}")
        print(f"     Is Stock Item: {item.is_stock_item}")
        
        # Check for any BOMs (even cancelled)
        all_boms = frappe.get_all(
            "BOM",
            filters={"item": item_code},
            fields=["name", "docstatus", "is_active", "is_default"]
        )
        
        if all_boms:
            print(f"\n  Existing BOMs for this item:")
            for bom in all_boms:
                status = "Active" if bom["is_active"] else "Inactive"
                docstatus = "Draft" if bom["docstatus"] == 0 else "Submitted" if bom["docstatus"] == 1 else "Cancelled"
                print(f"     - {bom['name']}: {status}, {docstatus}, Default={bom['is_default']}")
        else:
            print(f"\n  No BOMs exist for this item")
        
        if item_info["expected_parent"]:
            parent_exists = frappe.db.exists("Item", item_info["expected_parent"])
            if parent_exists:
                print(f"\n  ✅ Expected parent '{item_info['expected_parent']}' exists")
            else:
                print(f"\n  ❌ Expected parent '{item_info['expected_parent']}' NOT FOUND")
        
        print(f"\n  ACTION: Create BOM with parent item(s) and other required components")
    
    return True


def inspect_all():
    """Run all inspections."""
    inspect_inactive_boms()
    print("\n\n")
    inspect_flat_boms()
    print("\n\n")
    inspect_missing_boms()


if __name__ == "__main__":
    inspect_all()
