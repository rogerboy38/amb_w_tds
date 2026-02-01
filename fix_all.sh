#!/bin/bash
echo "=== COMPLETE FIX FOR FRESH BENCH ==="

# Step 1: SSH
echo "1. 🔑 Fixing SSH..."
mkdir -p ~/.ssh
if [[ ! -f ~/.ssh/id_ed25519 ]]; then
    ssh-keygen -t ed25519 -C "rogerboy38@github" -f ~/.ssh/id_ed25519 -N "" -q
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/id_ed25519
    
    echo ""
    echo "=== ADD TO GITHUB ==="
    cat ~/.ssh/id_ed25519.pub
    echo "=== END ==="
    echo ""
    echo "Go to: https://github.com/settings/keys"
    read -p "After adding, press Enter..."
else
    echo "✅ SSH key already exists"
fi

# Step 2: Git config
echo ""
echo "2. 📝 Setting Git config..."
git config --global user.name "rogerboy38"
git config --global user.email "rogerboy38@hotmail.com"

# Step 3: Test
echo ""
echo "3. 🔗 Testing connection..."
ssh -T git@github.com

# Step 4: Fix amb_w_tds
echo ""
echo "4. 🔧 Fixing amb_w_tds..."
cd ~/frappe-bench/apps/amb_w_tds

# Check if we're on main
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

if [[ -z "$CURRENT_BRANCH" ]]; then
    echo "   ⚠️  Detached HEAD detected"
    git checkout main 2>/dev/null || git checkout -b main
    echo "   ✅ Switched to main branch"
fi

# Set remote if missing
if ! git remote get-url origin > /dev/null 2>&1; then
    git remote add origin git@github.com:rogerboy38/amb_w_tds.git
    echo "   ✅ Added remote origin"
fi

# Push
echo "   📤 Pushing to GitHub..."
git push -u origin main && echo "   ✅ Success!" || echo "   ⚠️  Push failed"

# Step 5: Setup frappe-cloud-git-framework
echo ""
echo "5. 🚀 Setting up frappe-cloud-git-framework..."
cd ~/frappe-cloud-git-framework

if [[ ! -d .git ]]; then
    git init
    git remote add origin git@github.com:rogerboy38/frappe-cloud-git-framework.git
    echo "   ✅ Git initialized"
fi

echo ""
echo "✅ ALL FIXES COMPLETE!"
echo ""
echo "Quick commands:"
echo "  cd ~/frappe-bench/apps/amb_w_tds && git status"
echo "  ssh -T git@github.com"
