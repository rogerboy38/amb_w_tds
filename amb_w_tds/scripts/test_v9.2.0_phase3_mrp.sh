#!/bin/bash
# v9.2.0 Phase 3 Test Script - MRP Integration & End-to-End Testing
# Run from: ~/frappe-bench/apps/amb_w_tds/
# WARNING: This creates REAL items and BOMs in the database!

SITE="${1:-v2.sysmayal.cloud}"
TEST_ITEM="TEST-0227-ORGANIC-VANILLA-1000L-IBC"

echo "=========================================="
echo "  v9.2.0 Phase 3 - MRP Integration Tests"
echo "  Site: $SITE"
echo "  Test Item: $TEST_ITEM"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will create REAL items and BOMs!"
echo "    Press Ctrl+C within 5 seconds to cancel..."
sleep 5
echo ""

# T3.1 & T3.2: Live BOM Creation Test
echo "=========================================="
echo "T3.1 & T3.2: Live BOM Creation (dry_run=False)"
echo "=========================================="
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
    --kwargs '{"request_text": "0227-ORGANIC-VANILLA-1000L-IBC", "dry_run": false}' 2>&1 | tail -20
echo ""

# T3.3: Verify Items Created
echo "=========================================="
echo "T3.3: Verify Items Created"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

# Check SFG items
sfgs = frappe.get_all("Item", filters={"item_code": ["like", "SFG-0227-STEP%"]}, fields=["item_code", "item_group", "stock_uom"])
print(f"✅ Found {len(sfgs)} SFG items:")
for s in sfgs:
    print(f"   - {s.item_code} ({s.item_group}, {s.stock_uom})")

# Check FG item
fg = frappe.db.exists("Item", "0227-ORGANIC-VANILLA-1000L-IBC")
if fg:
    print(f"✅ FG item exists: 0227-ORGANIC-VANILLA-1000L-IBC")
else:
    print(f"❌ FG item NOT found")
EOF
echo ""

# T3.4: Verify BOMs with bom_no Links
echo "=========================================="
echo "T3.4: Verify BOMs with Multi-Level Links"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

# Get all BOMs for our test items
boms = frappe.get_all("BOM", 
    filters={"item": ["like", "%0227%ORGANIC%VANILLA%"], "docstatus": 1},
    fields=["name", "item", "is_default", "is_active"])

if not boms:
    boms = frappe.get_all("BOM",
        filters={"item": ["like", "SFG-0227-STEP%"]},
        fields=["name", "item", "is_default", "is_active"])

print(f"✅ Found {len(boms)} BOMs:")
for b in boms:
    print(f"   - {b.name} -> {b.item} (default={b.is_default}, active={b.is_active})")
    
    # Check for sub-BOM links
    bom_items = frappe.get_all("BOM Item",
        filters={"parent": b.name},
        fields=["item_code", "qty", "bom_no"])
    for bi in bom_items:
        if bi.bom_no:
            print(f"      └─ {bi.item_code} (qty={bi.qty}) -> bom_no: {bi.bom_no}")
        else:
            print(f"      └─ {bi.item_code} (qty={bi.qty})")
EOF
echo ""

# T3.5: Verify Operations (if with_operations=1)
echo "=========================================="
echo "T3.5: Verify Operations on BOMs"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

boms = frappe.get_all("BOM",
    filters={"item": ["like", "SFG-0227-STEP%"], "docstatus": 1},
    fields=["name", "item", "with_operations"])

ops_found = 0
for b in boms:
    if b.with_operations:
        ops = frappe.get_all("BOM Operation",
            filters={"parent": b.name},
            fields=["operation", "workstation", "time_in_mins"])
        if ops:
            ops_found += len(ops)
            print(f"✅ {b.name} has {len(ops)} operations")
            for op in ops:
                print(f"   └─ {op.operation} @ {op.workstation} ({op.time_in_mins} mins)")

if ops_found == 0:
    print("ℹ️  No operations attached (with_operations=0 in templates)")
EOF
echo ""

# T3.6: Idempotency Test
echo "=========================================="
echo "T3.6 & T3.7: Idempotency Test (Re-run)"
echo "=========================================="
echo "Running engine again with same spec..."
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
    --kwargs '{"request_text": "0227-ORGANIC-VANILLA-1000L-IBC", "dry_run": false}' 2>&1 | tail -10
echo ""
echo "Expected: items_reused and boms_reused should be populated (no duplicates)"
echo ""

# T3.8: MRP Explosion Test (Optional - requires Sales Order)
echo "=========================================="
echo "T3.8: MRP Explosion Check (Info)"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

# Check if BOM can explode
fg_bom = frappe.db.get_value("BOM", {"item": "0227-ORGANIC-VANILLA-1000L-IBC", "is_default": 1, "docstatus": 1}, "name")
if fg_bom:
    from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
    try:
        exploded = get_bom_items_as_dict(fg_bom, qty=1, fetch_exploded=1)
        print(f"✅ BOM {fg_bom} can explode. Found {len(exploded)} items at leaf level.")
        for item_code, data in list(exploded.items())[:5]:
            print(f"   └─ {item_code}: {data.get('qty', 'N/A')} {data.get('stock_uom', '')}")
    except Exception as e:
        print(f"⚠️  BOM explosion error: {e}")
else:
    print("❌ No default BOM found for FG item")
EOF
echo ""

# Summary
echo "=========================================="
echo "  Phase 3 Tests Summary"
echo "=========================================="
echo ""
echo "T3.1: Live FG creation      - Check output above"
echo "T3.2: Live SFG creation     - Check output above"
echo "T3.3: Items verified        - Check output above"
echo "T3.4: BOMs with bom_no      - Check output above"
echo "T3.5: Operations            - Check output above"
echo "T3.6: Yield calculation     - Included in BOM"
echo "T3.7: Idempotency           - Check re-run output"
echo "T3.8: MRP explosion         - Check output above"
echo ""
echo "=========================================="
echo ""
echo "To cleanup test data, run:"
echo "  bench --site $SITE console"
echo "  >>> frappe.delete_doc('Item', '0227-ORGANIC-VANILLA-1000L-IBC', force=1)"
echo "  >>> # Delete SFGs and BOMs similarly"
echo ""
echo "To test full MRP cycle:"
echo "  1. Create Sales Order for 0227-ORGANIC-VANILLA-1000L-IBC"
echo "  2. Run Production Planning Tool"
echo "  3. Check Material Requests and Work Orders generated"
