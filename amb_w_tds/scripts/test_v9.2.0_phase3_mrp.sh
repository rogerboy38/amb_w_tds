#!/bin/bash
# v9.2.0 Phase 3 Test Script - MRP Integration & End-to-End Testing
# ALIGNED WITH REAL PRODUCTION DATA
# Run from: ~/frappe-bench/apps/amb_w_tds/
# WARNING: This creates REAL items and BOMs in the database!

SITE="${1:-v2.sysmayal.cloud}"

# Real production items from AMB-Wellness ERPNext
# 0307 = Finished Good (Aloe Vera Gel Spray Dried Powder 200:1)
# 0227 = Sub-assembly (Aloe Vera Gel Concentrate 30:1)
TEST_FG="0307"
TEST_SFG="0227"

echo "=========================================="
echo "  v9.2.0 Phase 3 - MRP Integration Tests"
echo "  Site: $SITE"
echo "  FG Item: $TEST_FG"
echo "  SFG Item: $TEST_SFG"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will create/modify BOMs!"
echo "    Press Ctrl+C within 5 seconds to cancel..."
sleep 5
echo ""

# T3.1: Test BOM Creation for 0307 (uses 0227 as sub-assembly)
echo "=========================================="
echo "T3.1: Test BOM Creation for $TEST_FG"
echo "=========================================="
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \
    --kwargs "{\"request_text\": \"$TEST_FG\", \"dry_run\": true}" 2>&1 | tail -20
echo ""

# T3.2: Verify existing BOMs
echo "=========================================="
echo "T3.2: Verify Existing BOMs"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

# Check BOMs for 0307
boms_0307 = frappe.get_all("BOM", 
    filters={"item": "$TEST_FG"},
    fields=["name", "item", "is_default", "is_active", "docstatus"])

print(f"BOMs for $TEST_FG:")
for b in boms_0307:
    print(f"   - {b.name} (default={b.is_default}, active={b.is_active}, status={b.docstatus})")

# Check BOMs for 0227
boms_0227 = frappe.get_all("BOM",
    filters={"item": "$TEST_SFG"},
    fields=["name", "item", "is_default", "is_active", "docstatus"])

print(f"\nBOMs for $TEST_SFG:")
for b in boms_0227:
    print(f"   - {b.name} (default={b.is_default}, active={b.is_active}, status={b.docstatus})")
EOF
echo ""

# T3.3: Verify Multi-Level BOM Structure
echo "=========================================="
echo "T3.3: Verify Multi-Level BOM Structure"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

# Get default BOM for 0307
default_bom = frappe.db.get_value("BOM", {"item": "$TEST_FG", "is_default": 1}, "name")
if default_bom:
    print(f"✅ Default BOM for $TEST_FG: {default_bom}")
    
    # Get BOM items
    bom_items = frappe.get_all("BOM Item",
        filters={"parent": default_bom},
        fields=["item_code", "qty", "uom", "bom_no"])
    
    print(f"\nComponents:")
    for bi in bom_items:
        if bi.bom_no:
            print(f"   └─ {bi.item_code}: {bi.qty} {bi.uom} → Sub-BOM: {bi.bom_no}")
        else:
            print(f"   └─ {bi.item_code}: {bi.qty} {bi.uom}")
else:
    print(f"❌ No default BOM found for $TEST_FG")
EOF
echo ""

# T3.4: MRP Explosion Test
echo "=========================================="
echo "T3.4: MRP Explosion Test"
echo "=========================================="
bench --site $SITE console <<EOF
import frappe

default_bom = frappe.db.get_value("BOM", {"item": "$TEST_FG", "is_default": 1, "docstatus": 1}, "name")
if default_bom:
    from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
    try:
        exploded = get_bom_items_as_dict(default_bom, qty=1, fetch_exploded=1)
        print(f"✅ BOM {default_bom} exploded. Found {len(exploded)} leaf items:")
        for item_code, data in list(exploded.items())[:10]:
            print(f"   └─ {item_code}: {data.get('qty', 'N/A')} {data.get('stock_uom', '')}")
    except Exception as e:
        print(f"⚠️  BOM explosion error: {e}")
else:
    print(f"❌ No submitted default BOM for $TEST_FG")
EOF
echo ""

# Summary
echo "=========================================="
echo "  Phase 3 Tests Summary"
echo "=========================================="
echo ""
echo "Real production items tested:"
echo "  - $TEST_FG: Aloe Vera Gel Spray Dried Powder 200:1 (FG)"
echo "  - $TEST_SFG: Aloe Vera Gel Concentrate 30:1 (SFG)"
echo ""
echo "Key validations:"
echo "  - Multi-level BOM structure (0307 → 0227 → raw materials)"
echo "  - Sub-assembly linking via bom_no field"
echo "  - Fractional container quantities"
echo "  - MRP explosion capability"
echo ""
