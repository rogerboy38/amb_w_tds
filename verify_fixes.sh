#!/bin/bash
echo "=== Verification of Controller Fixes ==="
echo ""

expected_classes=(
    "tds_settings:TDSSettings"
    "production_plant_amb:ProductionPlantAMB"
    "kpi_cost_breakdown:KPICostBreakdown"
    "coa_amb2:COAAMB2"
    "lote_amb:LoteAMB"
    "rnd_parent_doctype:RNDParentDocType"
    "third_party_api:ThirdPartyAPI"
)

for item in "${expected_classes[@]}"; do
    dir="${item%:*}"
    expected_class="${item#*:}"
    file="amb_w_tds/amb_w_tds/doctype/$dir/$dir.py"
    
    if [ -f "$file" ]; then
        actual_class=$(grep -oP 'class \K\w+' "$file")
        if [ "$actual_class" = "$expected_class" ]; then
            echo "✅ $dir: $actual_class (correct)"
        else
            echo "❌ $dir: $actual_class (should be $expected_class)"
            # Show the fix needed
            echo "   Fix: sed -i 's/class $actual_class/class $expected_class/' $file"
        fi
    else
        echo "⚠️  $dir: File not found"
    fi
done
