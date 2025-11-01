#!/bin/bash

# 🎉 PHASE A - GIT COMMIT & PUSH SCRIPT
# Container Selection System - Final Deployment
# Date: 2025-11-01

echo "📋 Phase A: Container Selection - Git Commit & Push"
echo "===================================================="
echo ""

# Navigate to amb_w_tds app
cd /home/frappe/frappe-bench-spc2/apps/amb_w_tds

echo "📁 Current directory: $(pwd)"
echo ""

# Check git status
echo "🔍 Checking git status..."
git status
echo ""

# Show what will be committed
echo "📝 Files to be committed:"
git diff --name-only HEAD
echo ""

# Add Container Selection files
echo "➕ Adding Container Selection files..."
git add amb_w_tds/amb_w_tds/doctype/container_selection/
echo "✅ Files staged for commit"
echo ""

# Show staged files
echo "📋 Staged files:"
git diff --cached --name-only
echo ""

# Commit with detailed message
echo "💾 Creating commit..."
git commit -m "Phase A: Container Selection DocType implementation

Features:
- Container Selection DocType with 9 fields
- Container ID (unique), Type, Status, Capacity tracking
- Batch assignment integration (links to Batch AMB)
- Assignment date and user tracking
- Status management (Available/In Use/Maintenance/Retired)

Technical Details:
- Module: amb_w_tds
- Server-side controller: container_selection.py
- DocType schema: container_selection.json
- Client-side: container_selection_client.js

Integration Points:
- Batch AMB integration ready
- Container Barrels relationship identified
- Batch Processing History tracking prepared

Testing:
- UI verified: All fields functional
- Database migration: Successful
- Form creation: Working correctly
- Environment: test-spc4

Status: Production-ready, Phase A complete
Quality: Tested and verified
Next: Phase B - Quality Management Integration"

echo "✅ Commit created successfully"
echo ""

# Push to remote
echo "🚀 Pushing to GitHub..."
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 Current branch: $BRANCH"

# Push to current branch
git push origin $BRANCH

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Phase A successfully pushed to GitHub!"
    echo "🎉 Repository updated: apps/amb_w_tds"
    echo "📍 Branch: $BRANCH"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. ✅ Phase A: Complete"
    echo "  2. 📝 Review Container-Batch integration logic"
    echo "  3. 🚀 Plan Phase B: Quality Management Integration"
else
    echo ""
    echo "❌ Push failed. Please check:"
    echo "  - GitHub SSH access"
    echo "  - Branch permissions"
    echo "  - Remote repository status"
fi
