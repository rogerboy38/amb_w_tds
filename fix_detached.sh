#!/bin/bash
echo "=== Fixing Detached HEAD ==="

# Check current state
echo "Current state:"
git branch --show-current 2>/dev/null || echo "DETACHED HEAD"

# Fix it
echo ""
echo "Fixing..."
git fetch origin 2>/dev/null

if git checkout -b main origin/main 2>/dev/null; then
    echo "✅ Switched to main branch from origin"
elif git checkout -b main 2>/dev/null; then
    echo "✅ Created new main branch"
else
    echo "❌ Failed to fix"
    exit 1
fi

# Push if there are commits
echo ""
echo "Pushing..."
git push -u origin main 2>/dev/null && echo "✅ Pushed to GitHub" || echo "⚠️  No commits to push"

echo ""
echo "Fixed! Current branch: $(git branch --show-current)"
