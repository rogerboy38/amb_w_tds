import frappe
import os
import glob


def after_migrate():
    """Re-sync amb_w_tds DocTypes after migrate to prevent orphan deletion."""
    try:
        frappe.logger().info("[amb_w_tds] Running post-migrate DocType sync...")
        from frappe.modules.import_file import import_file_by_path

        app_path = frappe.get_app_path("amb_w_tds")
        doctype_path = os.path.join(app_path, "amb_w_tds", "doctype")
        count = 0
        for dt_dir in glob.glob(os.path.join(doctype_path, "*")):
            json_file = os.path.join(dt_dir, os.path.basename(dt_dir) + ".json")
            if os.path.exists(json_file):
                try:
                    import_file_by_path(json_file, force=True)
                    count += 1
                except Exception as e:
                    frappe.logger().warning(
                        f"[amb_w_tds] Could not sync {json_file}: {e}"
                    )
        frappe.logger().info(
            f"[amb_w_tds] Post-migrate sync complete: {count} DocTypes synced."
        )
    except Exception as e:
        frappe.logger().error(f"[amb_w_tds] after_migrate error: {e}")
