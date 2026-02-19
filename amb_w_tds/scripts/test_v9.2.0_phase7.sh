#!/bin/bash
# Phase 7 Test Script for BOM Creator Agent v9.2.0
# Tests: Mesh size parsing, Customer naming, Batch flags, Raven skill
#
# Usage: bash scripts/test_v9.2.0_phase7.sh
# Requires: bench --site <site> environment

set -e

SITE=${SITE:-"v2.sysmayal.cloud"}
echo "=========================================="
echo "Phase 7 Test Suite - BOM Creator Agent v9.2.0"
echo "Site: $SITE"
echo "Date: $(date)"
echo "=========================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

run_test() {
    local test_name="$1"
    local command="$2"
    local expected_field="$3"
    local expected_value="$4"
    
    echo ""
    echo "----------------------------------------"
    echo "TEST: $test_name"
    echo "----------------------------------------"
    
    # Run command and capture output
    output=$(bench --site $SITE execute $command 2>&1) || true
    
    echo "Command: $command"
    echo "Output (truncated):"
    echo "$output" | head -30
    
    # Check for expected value in output
    if echo "$output" | grep -q "$expected_value"; then
        echo -e "${GREEN}✅ PASSED${NC}: Found '$expected_value'"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}: Expected '$expected_value' not found"
        ((FAILED++))
        return 1
    fi
}

# ========================================
# T7.1 - Mesh Size Parsing (HIGHPOL)
# ========================================
echo ""
echo "=========================================="
echo "T7.1 - Mesh Size Parsing (HIGHPOL)"
echo "=========================================="

run_test "HIGHPOL 20/25 100 mesh parsing" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"Create HIGHPOL 20/25 100 mesh Aloe vera powder, fair trade, 25kg bags\", \"dry_run\": True}'" \
    "mesh_size" \
    "100M"

# ========================================
# T7.2 - Mesh Size Parsing (0307)
# ========================================
echo ""
echo "=========================================="
echo "T7.2 - Mesh Size Parsing (0307)"
echo "=========================================="

run_test "0307 200:1 powder 100 mesh parsing" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"0307 200:1 powder 100 mesh\", \"dry_run\": True}'" \
    "mesh_size" \
    "100M"

# ========================================
# T7.3 - Customer Naming Rule
# ========================================
echo ""
echo "=========================================="
echo "T7.3 - Customer Naming Rule"
echo "=========================================="

run_test "Customer XYZ naming pattern" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"0227 EU organic 30:1 for customer XYZ in 1000L IBC\", \"dry_run\": true}'" \
    "customer" \
    "XYZ"

# ========================================
# T7.4 - Batch Flag Check
# ========================================
echo ""
echo "=========================================="
echo "T7.4 - Batch Tracking (Implicit Check)"
echo "=========================================="

# This test verifies the code paths exist - actual batch flag verification
# requires creating an item and checking it
run_test "Batch tracking families defined" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"0227 fair trade 30:1 in IBC\", \"dry_run\": true}'" \
    "success" \
    "true"

# ========================================
# T7.5 - Raven Skill Import Check
# ========================================
echo ""
echo "=========================================="
echo "T7.5 - Raven BOM Creator Skill Import"
echo "=========================================="

bench --site $SITE console <<EOF
try:
    from amb_w_tds.raven.bom_creator_agent import get_agent_info, handle_raven_message, get_triggers
    info = get_agent_info()
    print(f"Agent Name: {info.get('name')}")
    print(f"Version: {info.get('version')}")
    print(f"Triggers: {get_triggers()[:3]}...")
    print("IMPORT_SUCCESS")
except Exception as e:
    print(f"IMPORT_FAILED: {e}")
exit()
EOF

# Check import result
if bench --site $SITE console <<< "from amb_w_tds.raven.bom_creator_agent import get_agent_info; print('SKILL_OK')" 2>&1 | grep -q "SKILL_OK"; then
    echo -e "${GREEN}✅ PASSED${NC}: Raven BOM Creator skill imports successfully"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}: Raven BOM Creator skill import failed"
    ((FAILED++))
fi

# ========================================
# T7.6 - Raven Skill Command Processing
# ========================================
echo ""
echo "=========================================="
echo "T7.6 - Raven Skill Command Processing"
echo "=========================================="

bench --site $SITE console <<EOF
from amb_w_tds.raven.bom_creator_agent import process_bom_command
result = process_bom_command("bom plan 0227 fair trade 30:1 in 1000L IBC")
print(f"Success: {result.get('success')}")
print(f"Command Type: {result.get('command_type')}")
if result.get('success'):
    print("COMMAND_PROCESSING_OK")
else:
    print(f"Error: {result.get('message', 'unknown')[:100]}")
exit()
EOF

if bench --site $SITE console <<< "from amb_w_tds.raven.bom_creator_agent import process_bom_command; r=process_bom_command('bom help'); print('HELP_OK' if r.get('success') else 'HELP_FAIL')" 2>&1 | grep -q "HELP_OK"; then
    echo -e "${GREEN}✅ PASSED${NC}: Raven skill command processing works"
    ((PASSED++))
else
    echo -e "${RED}❌ FAILED${NC}: Raven skill command processing failed"
    ((FAILED++))
fi

# ========================================
# Regression Tests
# ========================================
echo ""
echo "=========================================="
echo "Regression Tests"
echo "=========================================="

run_test "0227 variant parsing (existing)" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"0227 10X organic in drums\", \"dry_run\": true}'" \
    "variant" \
    "10X"

run_test "Certification mapping (ORG-EU)" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"0307 EU organic 200:1\", \"dry_run\": true}'" \
    "attribute" \
    "ORG-EU"

run_test "ACETYPOL family parsing" \
    "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{\"request_text\": \"ACETYPOL 15/20 fair trade\", \"dry_run\": true}'" \
    "family" \
    "ACETYPOL"

# ========================================
# Summary
# ========================================
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
TOTAL=$((PASSED + FAILED))
echo "Total: $TOTAL"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
