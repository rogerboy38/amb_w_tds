#!/usr/bin/env python3
"""
Fix for Frappe GitHub Issue #37799
Run this script after 'bench update' to prevent Workspace orphan deletion.

This patch removes 'Workspace' from the entities list in sync.py
that gets checked for orphans during migration.
"""

import os

def apply_patch():
    sync_py = "/home/frappe/frappe-bench/apps/frappe/frappe/model/sync.py"
    
    if not os.path.exists(sync_py):
        print(f"ERROR: {sync_py} not found")
        return False
    
    with open(sync_py, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'entites = ["Dashboard", "Page", "Report"]' in content:
        print("Workspace orphan fix already applied")
        return True
    
    # Apply patch
    if '"Workspace", "Dashboard"' in content:
        content = content.replace(
            'entites = ["Workspace", "Dashboard", "Page", "Report"]',
            'entites = ["Dashboard", "Page", "Report"]'
        )
        with open(sync_py, 'w') as f:
            f.write(content)
        print("Applied workspace orphan fix to sync.py")
        return True
    else:
        print("Could not find the line to patch")
        return False

if __name__ == "__main__":
    apply_patch()
