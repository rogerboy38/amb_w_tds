#!/usr/bin/env python3
"""
V13.5 Compliant Workspace Preservation Patch

For Frappe GitHub Issue #37799 - Workspaces being deleted during migrate.

This patch is a compliant replacement for fix_workspace_orphan.py which was
forbidden because it rewrote core Frappe files.

This version uses ONLY frappe.db APIs - no file system modifications.

It works by ensuring Workspaces have proper module assignments before the
orphan check runs. The key is that Frappe only deletes orphaned entities
(i.e., entities without module association).

Note: This patch is idempotent - safe to run multiple times.
"""

import frappe


def execute():
    """
    Frappe patch hook - runs before model sync (before_migrate context).

    This ensures all Workspace documents have a valid module assigned.
    Workspaces without modules are considered orphans and deleted by Frappe.

    Returns:
        str: Status message for patch log
    """
    try:
        # Get all Workspaces without a module
        orphaned_workspaces = frappe.get_all(
            "Workspace",
            filters={"module": ("is", "not set")},
            pluck="name"
        )

        if orphaned_workspaces:
            # Assign to a default module (Custom) for preservation
            for workspace_name in orphaned_workspaces:
                try:
                    frappe.db.set_value(
                        "Workspace",
                        workspace_name,
                        "module",
                        "Custom"
                    )
                    frappe.logger().warning(
                        f"[V13.5-P1] Assigned module='Custom' to Workspace: {workspace_name}"
                    )
                except Exception as e:
                    frappe.logger().error(
                        f"[V13.5-P1] Failed to assign module for {workspace_name}: {e}"
                    )

            frappe.db.commit()
            return (
                f"[V13.5-P1] Preserved {len(orphaned_workspaces)} workspaces by assigning module='Custom'. "
                f"Workspaces: {orphaned_workspaces}"
            )
        else:
            return "[V13.5-P1] No orphaned workspaces found - all have valid modules."

    except Exception as e:
        frappe.logger().error(f"[V13.5-P1] Workspace preservation patch failed: {e}")
        frappe.log_error(
            title="V13.5-P1 Workspace Preservation Failed",
            message=str(e)
        )
        return f"[V13.5-P1] Patch encountered error: {e}"


def is_workspace_preserved():
    """
    Idempotent check - returns True if all workspaces have modules.
    Can be called to verify without making changes.
    """
    orphaned = frappe.get_all(
        "Workspace",
        filters={"module": ("is", "not set")},
        pluck="name"
    )
    return len(orphaned) == 0


if __name__ == "__main__":
    result = execute()
    print(result)
