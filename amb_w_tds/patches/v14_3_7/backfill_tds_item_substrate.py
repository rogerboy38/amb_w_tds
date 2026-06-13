"""Task #74 backfill — populate item_substrate on existing TDS Product Specification records.

Bundle 1 added the item_substrate Data field with fetch_from='product_item.substrate'.
fetch_from triggers on insert / on product_item change, but NOT retroactively for
existing records. This patch is a one-shot backfill: read Item.substrate for each
existing TDS record's product_item and set item_substrate accordingly.

NULL semantics preserved:
  - Items with NULL substrate (LBL / MAQ / orphans, ~687 items) → item_substrate stays NULL → picker shows ALL parameters
  - Items with substrate set (PWD/LQD/LQDC/LQDF/PWDF, ~1088 items) → item_substrate gets populated

Idempotent: only processes rows where item_substrate IS NULL or empty.
Cheap: SET-only writes via set_value with update_modified=False; no doc.save() overhead.

Defensive reload_doc per brief note — guarantees Bundle 1 schema is live before WRITE
even if patch order edge-case on some bench layouts.
"""
import frappe


def execute():
    # Defensive: ensure Bundle 1 doctype change is loaded before we write to the new field.
    # No-op if already loaded; insurance against patch-order variance across bench layouts.
    try:
        frappe.reload_doc("amb_w_tds", "doctype", "tds_product_specification")
    except Exception as e:
        frappe.logger().warning(f"Task #74 backfill: reload_doc raised (continuing): {e}")

    # T117 guard: skip if Item.substrate column isn't present on this site
    if "substrate" not in frappe.db.get_table_columns("Item"):
        frappe.logger().warning("Task #74 backfill (T117): Item.substrate absent — skipping")
        return

    tds_recs = frappe.db.sql(
        """
        SELECT name, product_item FROM `tabTDS Product Specification`
        WHERE (item_substrate IS NULL OR item_substrate = '')
          AND product_item IS NOT NULL
        """,
        as_dict=True,
    )

    written = 0
    skipped_null = 0
    for tds in tds_recs:
        substrate = frappe.db.get_value("Item", tds.product_item, "substrate")
        if substrate:
            frappe.db.set_value(
                "TDS Product Specification",
                tds.name,
                "item_substrate",
                substrate,
                update_modified=False,
            )
            written += 1
        else:
            skipped_null += 1

    frappe.db.commit()
    frappe.logger().info(
        f"Task #74 backfill: scanned {len(tds_recs)} TDS records — "
        f"populated item_substrate on {written}; "
        f"left NULL on {skipped_null} (Item.substrate is NULL for those)"
    )
