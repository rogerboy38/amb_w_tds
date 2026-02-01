#!/bin/bash
cd ~/frappe-bench/apps/amb_w_tds

echo "=== Fixing amb_w_tds ==="

# Check remote
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
echo "Remote URL: $REMOTE_URL"

# Fetch from GitHub
echo "Fetching from GitHub..."
git fetch origin 2>/dev/null || {
    echo "⚠️  Could not fetch. Repository might not exist on GitHub."
    echo "Creating repository on GitHub..."
    echo ""
    echo "Go to: https://github.com/new"
    echo "Repository name: amb_w_tds"
    echo "Initialize with README: NO"
    echo "Click 'Create repository'"
    echo ""
    read -p "After creating repository, press Enter..."
    
    # Set remote
    git remote add origin git@github.com:rogerboy38/amb_w_tds.git 2>/dev/null || \
    git remote set-url origin git@github.com:rogerboy38/amb_w_tds.git
    
    # Push
    git push -u origin main
    exit 0
}

# Check if we can merge
echo "Checking differences..."
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main 2>/dev/null || echo "")

if [[ -z "$REMOTE_HASH" ]]; then
    echo "⚠️  No origin/main branch on GitHub"
    echo "Pushing initial commit..."
    git push -u origin main
elif [[ "$LOCAL_HASH" == "$REMOTE_HASH" ]]; then
    echo "✅ Local and remote are the same"
else
    echo "⚠️  Local and remote differ"
    echo "Local:  $LOCAL_HASH"
    echo "Remote: $REMOTE_HASH"
    echo ""
    echo "Options:"
    echo "  1) Force push (overwrite GitHub)"
    echo "  2) Pull and merge"
    echo "  3) Create new branch"
    echo ""
    read -p "Choice [1/2/3]: " choice
    
    case $choice in
        1)
            echo "Force pushing..."
            git push origin main --force
            ;;
        2)
            echo "Pulling and merging..."
            git pull origin main --allow-unrelated-histories
            git push origin main
            ;;
        3)
            echo "Creating new branch..."
            git checkout -b main-$(date +%Y%m%d)
            git push -u origin main-$(date +%Y%m%d)
            ;;
        *)
            echo "Invalid choice"
            ;;
    esac
fi
