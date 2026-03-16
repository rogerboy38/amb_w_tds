#!/bin/bash
# v9.1.0 Test Script - Simplified Version
# Run: bash scripts/test_v9.1.0_simple.sh

SITE="v2.sysmayal.cloud"

echo "=========================================="
echo "  v9.1.0 Test Suite"
echo "=========================================="

echo ""
echo "Test 1: Version Check"
bench --site $SITE execute amb_w_tds.test_version

echo ""
echo "Test 2: BOM Agent Import"
bench --site $SITE execute amb_w_tds.raven.bom_tracking_agent.test_import 2>/dev/null || \
  python3 -c "import sys; sys.path.insert(0, '.'); from amb_w_tds.raven import bom_tracking_agent; print('✅ BOM agent imports OK')"

echo ""
echo "Test 3: Serial Agent Import"  
python3 -c "import sys; sys.path.insert(0, '.'); from amb_w_tds.raven import serial_minimal_working; print('✅ Serial agent imports OK')" 2>/dev/null || echo "❌ Serial agent import failed"

echo ""
echo "Test 4: Config Check"
python3 -c "
import sys; sys.path.insert(0, '.')
from amb_w_tds.raven.config import REGISTERED_AGENTS
print('Registered agents:', list(REGISTERED_AGENTS.keys()))
if 'serial' in REGISTERED_AGENTS and 'bom' in REGISTERED_AGENTS:
    print('✅ Both agents registered')
else:
    print('❌ Missing agents')
"

echo ""
echo "Test 5: BOM Health Check"
bench --site $SITE execute amb_w_tds.scripts.bom_status_manager.run_health_check_dry

echo ""
echo "Test 6: Hooks Check"
grep -c "bom_hooks" amb_w_tds/hooks.py && echo "✅ BOM hooks found" || echo "❌ BOM hooks missing"

echo ""
echo "=========================================="
echo "If tests fail, run:"
echo "  bench migrate"
echo "  bench clear-cache && bench restart"
echo "=========================================="
