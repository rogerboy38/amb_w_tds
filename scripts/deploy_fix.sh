#!/bin/bash
# Deploy fixed batch_amb.py to local Frappe installation

echo "🔧 Deploying fixed batch_amb.py file..."

# Create backup of current file
echo "📦 Creating backup..."
cp ~/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py ~/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py.backup_$(date +%Y%m%d_%H%M%S)

# Copy the fixed file (this is the 773-line version with all fixes)
echo "📋 Copying fixed file..."
cp /workspace/user_input_files/batch_amb_extracted/batch_amb/batch_amb_FIXED.py ~/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py

# Verify deployment
echo "🔍 Verifying deployment..."
cd ~/frappe-bench/apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb
echo "Line count: $(wc -l < batch_amb.py)"

if grep -q "planned_qty or batch.batch_quantity" batch_amb.py; then
    echo "✅ planned_qty fix found"
else
    echo "❌ planned_qty fix NOT found"
fi

if grep -q "def create_bom_with_wizard" batch_amb.py; then
    echo "✅ create_bom_with_wizard method found"
else
    echo "❌ create_bom_with_wizard method NOT found"
fi

echo "🎉 Deployment complete!"
echo ""
echo "📋 NEXT STEPS:"
echo "1. cd ~/frappe-bench"
echo "2. bench restart"
echo "3. Clear browser cache"
echo "4. Test Create BOM widget"