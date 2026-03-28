#!/bin/bash
# git_manager_frappe.sh - Optimized for Frappe Cloud environments
# Fixes: SSH agent issues, health check false positives, ephemeral environments

set -euo pipefail

# ============================================
# CONFIGURATION
# ============================================
APP_NAME="rnd_nutrition"
GITHUB_USER="rogerboy38"
REPO_NAME="rnd_nutrition2"
REPO_URL="git@github.com:${GITHUB_USER}/${REPO_NAME}.git"
SSH_KEY_PATH="$HOME/.ssh/id_ed25519"
SCRIPT_VERSION="3.0.0-frappe"

# ============================================
# FIXED HEALTH CHECK FOR FRAPPE CLOUD
# ============================================
frappe_health_check() {
    echo "▶ Frappe Cloud System Health Check"
    
    # 1. Check SSH (Frappe Cloud optimized)
    echo "➤ Testing SSH connection..."
    
    # Method 1: Direct test with timeout
    local ssh_test
    ssh_test=$(timeout 5 ssh -T git@github.com 2>&1 || true)
    
    # Multiple success patterns for different SSH versions
    if echo "$ssh_test" | grep -q -E \
        "successfully authenticated|Hi ${GITHUB_USER}|authenticated successfully"; then
        echo "✓ SSH connection verified"
        local ssh_ok=true
    else
        echo "⚠ SSH check: '$ssh_test'"
        local ssh_ok=false
    fi
    
    # Method 2: Alternative test for Frappe Cloud
    if ! $ssh_ok; then
        echo "➤ Trying alternative SSH test..."
        if ssh -o BatchMode=yes -o ConnectTimeout=5 git@github.com 2>&1 | \
           grep -q "authenticated"; then
            echo "✓ SSH connection verified (alternative method)"
            ssh_ok=true
        fi
    fi
    
    # 2. Check Git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "✗ Not a git repository"
        return 1
    fi
    echo "✓ Git repository OK"
    
    # 3. Check remote
    if ! git remote get-url origin > /dev/null 2>&1; then
        echo "✗ No remote origin configured"
        return 1
    fi
    echo "✓ Git remote OK"
    
    # 4. Check branch state (common Frappe Cloud issue)
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "")
    if [[ -z "$current_branch" || "$current_branch" == "HEAD" ]]; then
        echo "⚠ Detached HEAD state (common after bench rebuild)"
        # Auto-fix for Frappe Cloud
        if git show-ref --verify --quiet refs/remotes/origin/main; then
            git checkout -b main origin/main --quiet 2>/dev/null && \
            echo "✓ Auto-fixed: checked out main branch"
        fi
    else
        echo "✓ On branch: $current_branch"
    fi
    
    if $ssh_ok; then
        echo "✅ All systems normal (Frappe Cloud optimized)"
        return 0
    else
        echo "⚠ SSH may need reconfiguration (common on Frappe Cloud)"
        echo "   Run: ./git_manager_frappe.sh --fix-ssh"
        return 1
    fi
}

# ============================================
# FRAPPE CLOUD SSH FIX
# ============================================
frappe_fix_ssh() {
    echo "▶ Frappe Cloud SSH Fix"
    
    # 1. Kill all existing agents (common issue on Frappe Cloud)
    echo "➤ Cleaning up SSH agents..."
    pkill -f "ssh-agent" 2>/dev/null || true
    unset SSH_AUTH_SOCK SSH_AGENT_PID
    
    # 2. Generate key if missing
    if [[ ! -f "$SSH_KEY_PATH" ]]; then
        echo "➤ Generating new SSH key..."
        mkdir -p ~/.ssh
        ssh-keygen -t ed25519 -C "${GITHUB_USER}@frappe.cloud" \
                   -f "$SSH_KEY_PATH" -N "" -q
    fi
    
    # 3. Set strict permissions (important for Frappe Cloud)
    chmod 700 ~/.ssh 2>/dev/null || true
    chmod 600 "$SSH_KEY_PATH" 2>/dev/null || true
    chmod 644 "$SSH_KEY_PATH.pub" 2>/dev/null || true
    
    # 4. Create minimal SSH config
    cat > ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
    chmod 600 ~/.ssh/config
    
    # 5. Start fresh agent (single instance)
    echo "➤ Starting SSH agent..."
    eval "$(ssh-agent -s)" > /dev/null 2>&1
    ssh-add "$SSH_KEY_PATH" 2>/dev/null || true
    
    # 6. Test
    echo "➤ Testing connection..."
    local test_result
    test_result=$(ssh -T git@github.com 2>&1)
    
    if echo "$test_result" | grep -q -E \
        "successfully authenticated|Hi ${GITHUB_USER}"; then
        echo "✅ SSH fixed and working"
        echo "   Output: $test_result"
        return 0
    else
        echo "⚠ SSH still having issues"
        echo "   Please add this key to GitHub:"
        echo "   https://github.com/settings/keys"
        echo ""
        echo "Public key:"
        cat "$SSH_KEY_PATH.pub"
        return 1
    fi
}

# ============================================
# FRAPPE CLOUD GIT SYNC
# ============================================
frappe_git_sync() {
    echo "▶ Frappe Cloud Git Sync"
    
    # Run health check first
    if ! frappe_health_check; then
        echo "➤ Attempting auto-fix..."
        frappe_fix_ssh
    fi
    
    # Check for changes
    if [[ -z "$(git status --porcelain)" ]]; then
        echo "✓ No changes to commit"
        return 0
    fi
    
    # Show changes
    echo "➤ Changes detected:"
    git status --short
    
    # Auto-stage with .gitignore respect
    echo "➤ Staging changes..."
    git add -A
    
    # Commit with Frappe Cloud context
    local commit_msg="Update: $(date '+%Y-%m-%d %H:%M:%S') - Frappe Cloud $(hostname)"
    echo "➤ Committing: $commit_msg"
    git commit -m "$commit_msg" --quiet
    
    # Push with retry logic
    local branch
    branch=$(git branch --show-current)
    echo "➤ Pushing to origin/$branch..."
    
    for i in {1..3}; do
        if git push origin "$branch" --quiet 2>/dev/null; then
            echo "✅ Successfully pushed to GitHub"
            echo "   Branch: $branch"
            echo "   Commit: $(git log --oneline -1)"
            return 0
        else
            echo "⚠ Push attempt $i/3 failed"
            sleep 2
        fi
    done
    
    echo "❌ Push failed after 3 attempts"
    echo "   Try: git pull origin $branch --rebase"
    return 1
}

# ============================================
# FRAPPE CLOUD SPECIFIC TOOLS
# ============================================
frappe_bench_info() {
    echo "=== FRAPPE CLOUD ENVIRONMENT ==="
    echo "Hostname: $(hostname)"
    echo "User: $(whoami)"
    echo "Home: $HOME"
    echo "Bench: $(pwd)"
    echo "SSH Agent: ${SSH_AUTH_SOCK:-Not set}"
    echo "Git Version: $(git --version 2>/dev/null || echo 'Not found')"
    echo ""
    echo "=== SSH KEYS ==="
    ls -la ~/.ssh/ 2>/dev/null || echo "No .ssh directory"
    echo ""
    echo "=== GIT STATUS ==="
    git status --short 2>/dev/null || echo "Not in git repo"
}

frappe_auto_fix() {
    echo "▶ Frappe Cloud Auto-Fix"
    echo "This will fix common Frappe Cloud issues:"
    echo "1. SSH agent conflicts"
    echo "2. Git remote configuration"
    echo "3. Branch state"
    echo ""
    
    read -p "Continue? [Y/n]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Nn]$ ]] && return
    
    # 1. Fix SSH
    frappe_fix_ssh
    
    # 2. Ensure git remote
    cd ~/frappe-bench/apps/rnd_nutrition 2>/dev/null || \
        cd ~/frappe-bench/apps/"$APP_NAME" 2>/dev/null || {
        echo "❌ Could not find app directory"
        return 1
    }
    
    if ! git remote get-url origin > /dev/null 2>&1; then
        echo "➤ Setting git remote..."
        git remote add origin "$REPO_URL" 2>/dev/null || \
        git remote set-url origin "$REPO_URL"
    fi
    
    # 3. Fix branch
    if ! git branch --show-current > /dev/null 2>&1; then
        echo "➤ Fixing branch state..."
        git checkout -b main 2>/dev/null || true
    fi
    
    echo "✅ Auto-fix complete"
    frappe_health_check
}

# ============================================
# MAIN MENU
# ============================================
show_frappe_menu() {
    while true; do
        clear
        echo "╔══════════════════════════════════════════════════════╗"
        echo "║           FRAPPE CLOUD GIT MANAGER v3.0              ║"
        echo "║           Optimized for Frappe Cloud                 ║"
        echo "╚══════════════════════════════════════════════════════╝"
        echo ""
        echo "App: $APP_NAME"
        echo "Repo: $REPO_URL"
        echo "User: $GITHUB_USER"
        echo ""
        echo "════════════════════════════════════════════════════════"
        echo "  1) 🔍 Health Check (Frappe Cloud optimized)"
        echo "  2) ⚡ Quick Sync (Auto-detect & push changes)"
        echo "  3) 🛠️  Fix SSH/Git (Common Frappe Cloud fixes)"
        echo "  4) 📊 Environment Info"
        echo "  5) 🚀 Auto-Fix All"
        echo "  6) 📤 Push Existing Changes"
        echo "  7) 📥 Pull Latest Changes"
        echo "  8) 🚪 Exit"
        echo "════════════════════════════════════════════════════════"
        
        read -r -p "Choice [1-8]: " choice
        
        case $choice in
            1) frappe_health_check ;;
            2) frappe_git_sync ;;
            3) frappe_fix_ssh ;;
            4) frappe_bench_info ;;
            5) frappe_auto_fix ;;
            6) 
                git add -A
                git commit -m "Update: $(date '+%Y-%m-%d %H:%M:%S')"
                git push origin $(git branch --show-current)
                ;;
            7) git pull origin $(git branch --show-current) ;;
            8) exit 0 ;;
            *) echo "Invalid option" ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# ============================================
# COMMAND LINE INTERFACE
# ============================================
case "${1:-}" in
    "--health"|"-h")
        frappe_health_check
        ;;
    "--sync"|"-s")
        frappe_git_sync
        ;;
    "--fix-ssh"|"-f")
        frappe_fix_ssh
        ;;
    "--info"|"-i")
        frappe_bench_info
        ;;
    "--auto-fix"|"-a")
        frappe_auto_fix
        ;;
    "--menu"|"-m"|"")
        show_frappe_menu
        ;;
    "--help")
        echo "Frappe Cloud Git Manager v$SCRIPT_VERSION"
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  --health, -h    Health check (Frappe Cloud optimized)"
        echo "  --sync, -s      Sync changes to GitHub"
        echo "  --fix-ssh, -f   Fix SSH issues (common on Frappe Cloud)"
        echo "  --info, -i      Show environment information"
        echo "  --auto-fix, -a  Auto-fix common issues"
        echo "  --menu, -m      Interactive menu (default)"
        echo "  --help          Show this help"
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
