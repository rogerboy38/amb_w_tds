#!/bin/bash
echo "Fixing git state..."

# Save any changes
echo "1. Stashing any changes..."
git stash

# Get latest from remote
echo "2. Fetching from origin..."
git fetch origin

# Check if we're on a branch
current_branch=$(git branch --show-current 2>/dev/null)
if [ -z "$current_branch" ]; then
    echo "3. You're in detached HEAD. Switching to main..."
    git checkout -f main 2>/dev/null || git checkout -b main origin/main
else
    echo "3. You're on branch: $current_branch"
    if [ "$current_branch" != "main" ]; then
        echo "   Switching to main..."
        git checkout main
    fi
fi

# Update main
echo "4. Updating main branch..."
git pull origin main

# Apply stashed changes
echo "5. Applying stashed changes..."
git stash pop 2>/dev/null || echo "No stashed changes"

echo "✓ Git is now fixed! You're on main branch."
echo ""
git status
