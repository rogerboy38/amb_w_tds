#!/bin/bash
# v9.2.0 Phase 2 Test Script - BOM Creator Agent Core Engine
# Run from: ~/frappe-bench/apps/amb_w_tds/

SITE="${1:-v2.sysmayal.cloud}"

echo "=========================================="
echo "  v9.2.0 Phase 2 Test Suite"
echo "  Site: $SITE"
echo "=========================================="
echo ""

# Test 1: Parser - Item Code
echo "Test 1: Parser - Item Code Parsing"
bench --site $SITE console <<EOF
from amb_w_tds.ai_bom_agent.parser import ProductSpecificationParser
parser = ProductSpecificationParser()
spec = parser.parse("0227-ORGANIC-NATURAL-1000L-IBC")
print(f"✅ Parsed: family={spec.family}, attr={spec.attribute}, flavor={spec.flavor}, pkg={spec.packaging}")
EOF
echo ""

# Test 2: Parser - Natural Language
echo "Test 2: Parser - Natural Language Parsing"
bench --site $SITE console <<EOF
from amb_w_tds.ai_bom_agent.parser import ProductSpecificationParser
parser = ProductSpecificationParser()
spec = parser.parse("Create organic 0227 juice in 200L drums")
print(f"✅ Parsed NL: family={spec.family}, attr={spec.attribute}, flavor={spec.flavor}, pkg={spec.packaging}")
EOF
echo ""

# Test 3: Template Loading
echo "Test 3: Template Loading"
bench --site $SITE console <<EOF
from amb_w_tds.ai_bom_agent.templates import MasterTemplateDB
db = MasterTemplateDB()
families = db.list_families()
print(f"✅ Available families: {families}")
if "0227" in families:
    t = db.get_template("0227")
    print(f"✅ Template 0227: {len(t.get('steps', []))} steps, version {t.get('version')}")
EOF
echo ""

# Test 4: Business Rules
echo "Test 4: Business Rules Loading"
bench --site $SITE console <<EOF
from amb_w_tds.ai_bom_agent.validators import ValidationRulesEngine
validator = ValidationRulesEngine()
rules = validator.list_rules()
print(f"✅ Loaded {len(rules)} business rules:")
for r in rules:
    print(f"   - {r['id']}: {r['name']}")
EOF
echo ""

# Test 5: Data Contracts
echo "Test 5: Data Contracts"
bench --site $SITE console <<EOF
from amb_w_tds.ai_bom_agent.data_contracts import ParsedSpec, PlannedItem, PlannedBOM, GenerationReport
from datetime import datetime
spec = ParsedSpec(family="0227", attribute="ORGANIC", flavor="NATURAL", packaging="1000L-IBC", target_uom="IBC", raw_request="test", parsed_at=datetime.now())
d = spec.to_dict()
print(f"✅ ParsedSpec.to_dict() works: {list(d.keys())}")
EOF
echo ""

# Test 6: API - Parse Only
echo "Test 6: API - Parse Product Spec"
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.parse_product_spec --kwargs '{"request_text": "0227-ORGANIC-NATURAL-1000L-IBC"}' 2>&1 | tail -5
echo ""

# Test 7: API - List Families
echo "Test 7: API - List Available Families"
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.list_available_families 2>&1 | tail -3
echo ""

# Test 8: API - Dry Run BOM Creation
echo "Test 8: API - Dry Run BOM Creation"
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec --kwargs '{"request_text": "0227-ORGANIC-NATURAL-1000L-IBC", "dry_run": True}' 2>&1 | tail -15
echo ""

# Test 9: Validate Item Code
echo "Test 9: API - Validate Item Code"
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.validate_item_code --kwargs '{"item_code": "0227-ORGANIC-NATURAL-1000L-IBC"}' 2>&1 | tail -5
echo ""

# Test 10: Get Business Rules via API
echo "Test 10: API - Get Business Rules"
bench --site $SITE execute amb_w_tds.ai_bom_agent.api.get_business_rules 2>&1 | tail -5
echo ""

echo "=========================================="
echo "  Phase 2 Tests Complete"
echo "=========================================="
echo ""
echo "Next: If all tests pass, proceed to Phase 3"
echo "      (actual BOM creation with dry_run=False)"
