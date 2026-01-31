#!/bin/bash
echo "🚀 FORCE PUSHING amb_w_tds to GitHub (local is truth)..."

# Ensure we're on main
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "⚠️  Not on main branch. Switching..."
    git checkout main
fi

echo "📝 Current branch: $current_branch"
echo "💪 Local version is considered TRUTH"

# Add all changes
echo "📦 Adding all changes..."
git add .

# Commit with timestamp
commit_msg="Update: $(date '+%Y-%m-%d %H:%M:%S') - Local truth"
if git diff --cached --quiet; then
    echo "📭 No changes to commit"
else
    git commit -m "$commit_msg"
    echo "✅ Changes committed: $commit_msg"
fi

# FORCE PUSH (overwrites remote)
echo "💥 FORCE PUSHING to origin/main..."
if git push origin main --force-with-lease; then
    echo "✅ SUCCESS! Remote overwritten with local truth"
else
    echo "🔄 Trying standard force push..."
    git push origin main --force
fi

echo "🎉 Local truth is now on GitHub!"
echo ""
echo "📊 Status:"
git status --short
