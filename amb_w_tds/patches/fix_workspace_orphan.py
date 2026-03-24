#!/usr/bin/env python3
"""
Fix for Frappe GitHub Issue #37799

This patch removes 'Workspace' from the entities list in sync.py
that gets checked for orphans during migration.

IMPORTANT: This must run BEFORE the orphan check (use before_migrate hook).
If run after_migrate, the workspaces will already be deleted.

Run this script after 'bench update' to prevent Workspace orphan deletion.
"""

import os

def apply_patch():
    """
    Apply the workspace orphan fix by patching frappe/model/sync.py
    
    Returns:
        bool: True if patch was applied or already present, False on error
    """
    # Try common bench locations
    possible_paths = [
        "/home/frappe/frappe-bench/apps/frappe/frappe/model/sync.py",
        "/opt/frappe/frappe-bench/apps/frappe/frappe/model/sync.py",
    ]
    
    sync_py = None
    for path in possible_paths:
        if os.path.exists(path):
            sync_py = path
            break
    
    if not sync_py:
        # Try to find it dynamically
        import subprocess
        try:
            result = subprocess.run(
                ["find", "/home", "-name", "sync.py", "-path", "*/frappe/model/*", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=10
            )
            for line in result.stdout.strip().split("\n"):
                if "frappe/model/sync.py" in line:
                    sync_py = line
                    break
        except:
            pass
    
    if not sync_py or not os.path.exists(sync_py):
        print(f"ERROR: Could not find frappe/model/sync.py")
        return False
    
    with open(sync_py, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'entites = ["Dashboard", "Page", "Report"]' in content:
        print("Workspace orphan fix already applied")
        return True
    
    # Apply patch - remove "Workspace" from the entities list
    if '"Workspace", "Dashboard"' in content:
        content = content.replace(
            'entites = ["Workspace", "Dashboard", "Page", "Report"]',
            'entites = ["Dashboard", "Page", "Report"]'
        )
        with open(sync_py, 'w') as f:
            f.write(content)
        print(f"Applied workspace orphan fix to {sync_py}")
        return True
    else:
        print("Could not find the line to patch - sync.py may already be modified")
        return False


def apply_patch_wrapper():
    """
    Wrapper function for Frappe hooks - catches and logs any errors
    """
    try:
        return apply_patch()
    except Exception as e:
        print(f"ERROR applying workspace orphan fix: {e}")
        return False


if __name__ == "__main__":
    apply_patch()
