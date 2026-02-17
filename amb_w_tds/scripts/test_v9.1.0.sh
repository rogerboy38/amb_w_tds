#!/bin/bash
# v9.1.0 Test Script for BOM Tracking Agent & Phase 6 Changes
# Run this on production: bash test_v9.1.0.sh

SITE="v2.sysmayal.cloud"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  v9.1.0 Test Suite - BOM Tracking Agent"
echo "=========================================="
echo ""

# Test 1: Version Check
echo -e "${YELLOW}Test 1: Version Check${NC}"
VERSION=$(bench --site $SITE console <<< "import amb_w_tds; print(amb_w_tds.__version__)" 2>/dev/null | grep -E "^[0-9]")
if [ "$VERSION" == "9.1.0" ]; then
    echo -e "${GREEN}✅ PASS: Version is $VERSION${NC}"
else
    echo -e "${RED}❌ FAIL: Expected 9.1.0, got $VERSION${NC}"
fi
echo ""

# Test 2: BOM Tracking Agent Import
echo -e "${YELLOW}Test 2: BOM Tracking Agent Import${NC}"
IMPORT_RESULT=$(bench --site $SITE console <<< "import amb_w_tds.raven.bom_tracking_agent; print('OK')" 2>&1 | grep -E "^OK$|Error|error")
if [ "$IMPORT_RESULT" == "OK" ]; then
    echo -e "${GREEN}✅ PASS: bom_tracking_agent imports successfully${NC}"
else
    echo -e "${RED}❌ FAIL: Import error - $IMPORT_RESULT${NC}"
fi
echo ""

# Test 3: Serial Agent Import
echo -e "${YELLOW}Test 3: Serial Tracking Agent Import${NC}"
SERIAL_RESULT=$(bench --site $SITE console <<< "import amb_w_tds.raven.serial_minimal_working; print('OK')" 2>&1 | grep -E "^OK$|Error|error")
if [ "$SERIAL_RESULT" == "OK" ]; then
    echo -e "${GREEN}✅ PASS: serial_minimal_working imports successfully${NC}"
else
    echo -e "${RED}❌ FAIL: Import error - $SERIAL_RESULT${NC}"
fi
echo ""

# Test 4: Raven Config Check
echo -e "${YELLOW}Test 4: Raven Config Agent Registration${NC}"
CONFIG_RESULT=$(bench --site $SITE console <<< "
from amb_w_tds.raven.config import REGISTERED_AGENTS
agents = list(REGISTERED_AGENTS.keys())
print(','.join(agents))
" 2>/dev/null | grep -E "serial|bom")
if [[ "$CONFIG_RESULT" == *"serial"* ]] && [[ "$CONFIG_RESULT" == *"bom"* ]]; then
    echo -e "${GREEN}✅ PASS: Both agents registered: $CONFIG_RESULT${NC}"
else
    echo -e "${RED}❌ FAIL: Missing agents in config - $CONFIG_RESULT${NC}"
fi
echo ""

# Test 5: BOM Health Check (Dry Run)
echo -e "${YELLOW}Test 5: BOM Health Check (Dry Run)${NC}"
HEALTH_RESULT=$(bench --site $SITE execute amb_w_tds.scripts.bom_status_manager.run_health_check_dry 2>&1)
if [[ "$HEALTH_RESULT" == *"error"* ]] || [[ "$HEALTH_RESULT" == *"Error"* ]] || [[ "$HEALTH_RESULT" == *"Traceback"* ]]; then
    echo -e "${RED}❌ FAIL: Health check error${NC}"
    echo "$HEALTH_RESULT" | tail -5
else
    echo -e "${GREEN}✅ PASS: Health check ran without errors${NC}"
fi
echo ""

# Test 6: Scheduled BOM Health Task
echo -e "${YELLOW}Test 6: Scheduled BOM Health Task${NC}"
SCHED_RESULT=$(bench --site $SITE execute amb_w_tds.scripts.scheduled_bom_health.run 2>&1)
if [[ "$SCHED_RESULT" == *"error"* ]] || [[ "$SCHED_RESULT" == *"Error"* ]] || [[ "$SCHED_RESULT" == *"Traceback"* ]]; then
    echo -e "${RED}❌ FAIL: Scheduled task error${NC}"
    echo "$SCHED_RESULT" | tail -5
else
    echo -e "${GREEN}✅ PASS: Scheduled task ran without errors${NC}"
fi
echo ""

# Test 7: BOM Known Issues JSON
echo -e "${YELLOW}Test 7: BOM Known Issues JSON${NC}"
JSON_CHECK=$(bench --site $SITE console <<< "
import json
import os
path = os.path.join(os.path.dirname(__file__), '..', 'apps', 'amb_w_tds', 'amb_w_tds', 'scripts', 'bom_known_issues.json')
# Alternative approach
import frappe
app_path = frappe.get_app_path('amb_w_tds')
json_path = os.path.join(app_path, 'scripts', 'bom_known_issues.json')
if os.path.exists(json_path):
    with open(json_path) as f:
        data = json.load(f)
    print(f'OK:{len(data.get(\"issues\", []))} issues')
else:
    print('NOT_FOUND')
" 2>/dev/null | grep -E "^OK|NOT_FOUND")
if [[ "$JSON_CHECK" == OK* ]]; then
    echo -e "${GREEN}✅ PASS: $JSON_CHECK${NC}"
else
    echo -e "${YELLOW}⚠️ WARNING: bom_known_issues.json not found (may need full path)${NC}"
fi
echo ""

# Test 8: Hooks Registration
echo -e "${YELLOW}Test 8: Hooks BOM Events${NC}"
HOOKS_CHECK=$(grep -c "bom_hooks" /home/frappe/frappe-bench/apps/amb_w_tds/amb_w_tds/hooks.py 2>/dev/null || echo "0")
if [ "$HOOKS_CHECK" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS: BOM hooks registered ($HOOKS_CHECK references)${NC}"
else
    echo -e "${RED}❌ FAIL: BOM hooks not found in hooks.py${NC}"
fi
echo ""

echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo "Run 'bench migrate' if any imports fail"
echo "Run 'bench clear-cache && bench restart' after updates"
echo ""
