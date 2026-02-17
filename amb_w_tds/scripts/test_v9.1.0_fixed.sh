#!/bin/bash
# v9.1.0 Test Script - Fixed Version
# Run from frappe-bench: bash apps/amb_w_tds/scripts/test_v9.1.0_fixed.sh

SITE="v2.sysmayal.cloud"

echo "=========================================="
echo "  v9.1.0 Test Suite - Fixed"
echo "=========================================="

echo ""
echo "Test 1: Version Check"
bench --site $SITE execute "frappe.get_attr('amb_w_tds.__version__')" 2>&1 | tail -5
# Alternative direct check:
cat ~/frappe-bench/apps/amb_w_tds/version.txt

echo ""
echo "Test 2: BOM Agent Import (via bench console)"
bench --site $SITE console << 'EOF'
try:
    from amb_w_tds.raven.bom_tracking_agent import BOMTrackingAgent
    print(f"✅ BOM Agent: {BOMTrackingAgent.agent_name} v{BOMTrackingAgent.agent_version}")
except Exception as e:
    print(f"❌ BOM Agent import failed: {e}")
exit()
EOF

echo ""
echo "Test 3: Serial Agent Import"
bench --site $SITE console << 'EOF'
try:
    from amb_w_tds.raven.serial_minimal_working import MinimalSerialAgent
    print(f"✅ Serial Agent: {MinimalSerialAgent.agent_name} v{MinimalSerialAgent.agent_version}")
except Exception as e:
    print(f"❌ Serial Agent import failed: {e}")
exit()
EOF

echo ""
echo "Test 4: Config get_agents() Check"
bench --site $SITE console << 'EOF'
try:
    from amb_w_tds.raven.config import get_agents
    agents = get_agents()
    print(f"Registered agents: {list(agents.keys())}")
    if 'serial_tracking' in agents and 'bom_tracking' in agents:
        print("✅ Both agents registered")
    else:
        print("❌ Missing agents")
except Exception as e:
    print(f"❌ Config check failed: {e}")
exit()
EOF

echo ""
echo "Test 5: BOM Health Check (actual function)"
bench --site $SITE execute amb_w_tds.scripts.bom_status_manager.run_health_check --kwargs '{"verbose": false}' 2>&1 | tail -20

echo ""
echo "Test 6: Hooks Check"
grep -c "bom_hooks" ~/frappe-bench/apps/amb_w_tds/amb_w_tds/hooks.py && echo "✅ BOM hooks found" || echo "❌ BOM hooks missing"

echo ""
echo "=========================================="
echo "Done! If imports fail, run:"
echo "  bench migrate"
echo "  bench clear-cache && bench restart"
echo "=========================================="
