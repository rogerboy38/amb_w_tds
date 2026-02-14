# bom_analysis.py
# Save this file in: ~/frappe-bench/apps/amb_w_tds/amb_w_tds/scripts/bom_analysis.py
# Run with: bench --site v2.sysmayal.cloud execute amb_w_tds.scripts.bom_analysis.py

import frappe
import json
from frappe.utils import cint, flt

def get_bom_tree(item_code, level=0, max_level=5, visited=None):
    """Recursively build BOM tree, with circular reference protection"""
    if visited is None:
        visited = set()
    if item_code in visited or level > max_level:
        return {"item": item_code, "level": level, "circular": True}
    visited.add(item_code)
    
    result = {
        "item": item_code, 
        "level": level, 
        "children": [],
        "item_name": frappe.db.get_value("Item", item_code, "item_name") or "N/A"
    }
    
    # Get default active BOM
    bom = frappe.db.get_value("BOM",
        {"item": item_code, "is_active": 1, "is_default": 1},
        ["name", "item"], as_dict=True)
    if not bom:
        bom = frappe.db.get_value("BOM",
            {"item": item_code, "is_active": 1},
            ["name", "item"], as_dict=True)
    
    if not bom:
        result["bom"] = None
        return result
    
    result["bom"] = bom.name
    
    children = frappe.db.sql("""
        SELECT item_code, item_name, qty, uom, bom_no
        FROM `tabBOM Item`
        WHERE parent = %s 
        ORDER BY idx
    """, bom.name, as_dict=True)
    
    for c in children:
        child = {
            "item_code": c.item_code,
            "item_name": c.item_name,
            "qty": flt(c.qty) if c.qty else 0,
            "uom": c.uom,
            "has_sub_bom": bool(c.bom_no),
            "bom_no": c.bom_no or None
        }
        if c.bom_no and level < max_level:
            # Recursive call - this works because function is defined
            child["sub_tree"] = get_bom_tree(c.item_code, level + 1, max_level, visited.copy())
        result["children"].append(child)
    
    return result

def check_sub_assemblies(node):
    """Recursively check if node has any sub-assemblies"""
    if not node or not node.get("children"):
        return False
    for child in node["children"]:
        if child.get("has_sub_bom"):
            return True
        if child.get("sub_tree") and check_sub_assemblies(child["sub_tree"]):
            return True
    return False

def collect_sub_assemblies(node, subs_list=None):
    """Collect all sub-assemblies recursively"""
    if subs_list is None:
        subs_list = []
    for child in node.get("children", []):
        if child.get("has_sub_bom"):
            subs_list.append({
                "item_code": child["item_code"],
                "item_name": child["item_name"],
                "bom_no": child["bom_no"]
            })
        if child.get("sub_tree"):
            collect_sub_assemblies(child["sub_tree"], subs_list)
    return subs_list

def main():
    """Main function to run the analysis"""
    print("\n" + "=" * 70)
    print("BOM ANALYSIS REPORT - START")
    print("=" * 70)

    # --- STEP 1: Get ALL Finished Goods items that have active BOMs ---
    print("\n" + "=" * 70)
    print("STEP 1: ALL FINISHED GOODS WITH ACTIVE BOMs")
    print("=" * 70)

    fg_items = frappe.db.sql("""
        SELECT DISTINCT b.item, b.item_name, b.name as bom_name,
               i.item_group, i.stock_uom
        FROM `tabBOM` b
        JOIN `tabItem` i ON i.name = b.item
        WHERE b.is_active = 1 AND b.is_default = 1
        ORDER BY b.item
    """, as_dict=True)

    print(f"\nFound {len(fg_items)} items with active default BOMs:\n")
    for fg in fg_items:
        print(f"  {fg.item} | {fg.item_name} | Group: {fg.item_group} | BOM: {fg.bom_name}")

    # --- STEP 2: Full BOM trees for ALL FG items ---
    print("\n" + "=" * 70)
    print("STEP 2: FULL BOM TREES (recursive)")
    print("=" * 70)

    all_trees = {}
    items_with_sub_assemblies = []

    for fg in fg_items:
        print(f"\n--- Processing {fg.item} ---")
        try:
            tree = get_bom_tree(fg.item)
            all_trees[fg.item] = tree
            
            # Check if any child has a sub-BOM (is a sub-assembly)
            if check_sub_assemblies(tree):
                items_with_sub_assemblies.append(fg.item)
                print(f"  ✓ {fg.item} has sub-assemblies")
            else:
                print(f"  ✗ {fg.item} is flat (no sub-assemblies)")
                
        except Exception as e:
            print(f"  ✗ Error processing {fg.item}: {str(e)}")

    # Print a sample tree (first item)
    if all_trees:
        first_item = list(all_trees.keys())[0]
        print(f"\nSample tree for {first_item}:")
        print(json.dumps(all_trees[first_item], indent=2, default=str))

    # --- STEP 3: Summary - items WITH sub-assemblies ---
    print("\n" + "=" * 70)
    print("STEP 3: ITEMS WITH SUB-ASSEMBLIES (multi-level BOMs)")
    print("=" * 70)

    if items_with_sub_assemblies:
        for item in items_with_sub_assemblies:
            tree = all_trees[item]
            subs = collect_sub_assemblies(tree)
            print(f"\n  {item} ({tree.get('item_name', 'N/A')})")
            for sub in subs:
                print(f"    → {sub['item_code']} ({sub['item_name']}) - BOM: {sub['bom_no']}")
    else:
        print("  ** NO items have multi-level BOMs (all are flat/single-level) **")

    # --- STEP 4: Work Orders and their relationships ---
    print("\n" + "=" * 70)
    print("STEP 4: WORK ORDERS (recent 30)")
    print("=" * 70)

    wos = frappe.db.sql("""
        SELECT name, production_item, bom_no, sales_order, project,
               status, qty, produced_qty, creation
        FROM `tabWork Order`
        ORDER BY creation DESC
        LIMIT 30
    """, as_dict=True)

    for wo in wos:
        print(f"  {wo.name} | item={wo.production_item} | bom={wo.bom_no} | "
              f"SO={wo.sales_order or 'None'} | project={wo.project or 'None'} | "
              f"status={wo.status} | qty={wo.qty}")

    # --- STEP 5: Sales Orders with linked Work Orders ---
    print("\n" + "=" * 70)
    print("STEP 5: SALES ORDERS -> WORK ORDERS MAPPING")
    print("=" * 70)

    sos_with_wos = frappe.db.sql("""
        SELECT DISTINCT wo.sales_order, wo.project,
               GROUP_CONCAT(DISTINCT wo.production_item) as items,
               GROUP_CONCAT(wo.name) as work_orders,
               COUNT(wo.name) as wo_count
        FROM `tabWork Order` wo
        WHERE wo.sales_order IS NOT NULL AND wo.sales_order != ''
        GROUP BY wo.sales_order, wo.project
        ORDER BY wo.sales_order DESC
        LIMIT 20
    """, as_dict=True)

    if sos_with_wos:
        for so in sos_with_wos:
            print(f"  SO: {so.sales_order} | Project: {so.project or 'None'} | "
                  f"Items: {so.items} | WOs({so.wo_count}): {so.work_orders}")
    else:
        print("  ** No Sales Orders linked to Work Orders **")

    # --- STEP 6: Item Groups summary ---
    print("\n" + "=" * 70)
    print("STEP 6: ITEM GROUPS OF BOM ITEMS")
    print("=" * 70)

    groups = frappe.db.sql("""
        SELECT i.item_group, COUNT(*) as cnt,
               GROUP_CONCAT(DISTINCT i.name ORDER BY i.name) as items
        FROM `tabItem` i
        WHERE i.name IN (SELECT DISTINCT item FROM `tabBOM` WHERE is_active = 1)
        GROUP BY i.item_group
        ORDER BY cnt DESC
    """, as_dict=True)

    for g in groups:
        if g.items:
            items_list = g.items.split(',')
            print(f"  {g.item_group} ({g.cnt} items): {', '.join(items_list[:5])}" + 
                  (f" ... and {len(items_list)-5} more" if len(items_list) > 5 else ""))

    print("\n" + "=" * 70)
    print("BOM ANALYSIS REPORT - COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
