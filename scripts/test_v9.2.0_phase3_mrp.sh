#!/bin/bash
# v9.2.0 Phase 3 Test Script - MRP Integration & End-to-End Testing
# ALIGNED WITH REAL PRODUCTION DATA
# Run from: ~/frappe-bench/apps/amb_w_tds/

SITE="${1:-v2.sysmayal.cloud}"
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

# T3.1: Test BOM Creation for 0307 (dry_run)
echo "=========================================="
echo "T3.1: Test BOM Creation for $TEST_FG (dry_run)"
echo "=========================================="
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0307", "dry_run": True}' 2>&1 | tail -30
echo ""

# T3.2: Check existing BOMs for 0307
echo "=========================================="
echo "T3.2: Check Existing BOMs for $TEST_FG"
echo "=========================================="
bench --site $SITE frappe.get_all BOM --filters '{"item": "0307"}' --fields '["name", "is_default", "is_active", "docstatus"]' 2>&1 || \
  bench --site $SITE execute frappe.client.get_list --kwargs '{"doctype": "BOM", "filters": {"item": "0307"}, "fields": ["name", "is_default", "is_active", "docstatus"]}' 2>&1 | tail -20
echo ""

# T3.3: Check existing BOMs for 0227
echo "=========================================="
echo "T3.3: Check Existing BOMs for $TEST_SFG"
echo "=========================================="
bench --site $SITE execute frappe.client.get_list --kwargs '{"doctype": "BOM", "filters": {"item": "0227"}, "fields": ["name", "is_default", "is_active", "docstatus"]}' 2>&1 | tail -20
echo ""

# T3.4: Get BOM Items for BOM-0307-004
echo "=========================================="
echo "T3.4: BOM-0307-004 Components"
echo "=========================================="
bench --site $SITE execute frappe.client.get_list --kwargs '{"doctype": "BOM Item", "filters": {"parent": "BOM-0307-004"}, "fields": ["item_code", "qty", "uom", "bom_no"]}' 2>&1 | tail -30
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
