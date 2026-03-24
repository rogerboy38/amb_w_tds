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


def mark_doctypes_as_owned():
    """Mark custom DocTypes as owned by amb_w_tds to prevent orphan deletion."""
    custom_doctypes = [
        "RND Parent DocType",
        "Production Plant AMB",
        "Lote AMB",
        "Third Party API",
        "KPI Cost Breakdown",
        "COA AMB2",
    ]
    
    for dt_name in custom_doctypes:
        try:
            if frappe.db.exists("DocType", dt_name):
                frappe.db.sql("""
                    UPDATE `tabDocType` 
                    SET module = 'amb_w_tds' 
                    WHERE name = %s
                """, (dt_name,))
                frappe.logger().info(f"[amb_w_tds] Marked {dt_name} as owned by amb_w_tds")
        except Exception as e:
            frappe.logger().warning(f"[amb_w_tds] Could not mark {dt_name}: {e}")
    
    frappe.db.commit()
