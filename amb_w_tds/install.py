import frappe
import os


def before_migrate():
    """Run before bench migrate - minimal version to prevent breaking site."""
    try:
        print("[amb_w_tds] =======================================")
        print("[amb_w_tds] BEFORE_MIGRATE - Minimal Version")
        print("[amb_w_tds] =======================================")
        frappe.logger().info("[amb_w_tds] Running pre-migrate (minimal)...")
        
        # Just log - don't modify anything to avoid breaking site
        print("[amb_w_tds] before_migrate completed (minimal mode)")
    except Exception as e:
        print(f"[amb_w_tds] BEFORE_MIGRATE ERROR: {e}")
        frappe.logger().error(f"[amb_w_tds] before_migrate error: {e}")
