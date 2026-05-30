// SC4a Part 2 + SC4a-v2 — TDS Product Specification form script
// - On product_item change: auto-populate custom_tds_customers from Item.custom_amb_customer_items
//   (only if target table empty — preserves user edits)
// - On refresh/load: same auto-populate if table empty + product_item set
//   (handles LEGACY TDS records created before SC4a deployment)
// - "Refresh Customers from Item" custom button under Actions: explicit re-fetch
//   (escape hatch — clears table and re-pulls from Item)
//
// Additive only: does not override the 5 existing TDS Client Scripts or phase_1c_tab.js
// (Frappe merges frappe.ui.form.on() calls across files; different event handlers, no collisions)

async function _populate_customers_from_item(frm, opts = {}) {
    const { force = false, silent = false } = opts;

    if (!frm.doc.product_item) return { populated: 0, reason: 'no product_item' };

    if (!force && (frm.doc.custom_tds_customers || []).length > 0) {
        return { populated: 0, reason: 'table not empty' };
    }

    try {
        // 'Customer Item' is a child table (istable=1) — direct get_list is permission-forbidden
        // even for Administrator. Fetch the parent Item doc and read its child table instead.
        const itemDoc = await frappe.db.get_doc('Item', frm.doc.product_item);
        const item_customers = (itemDoc.custom_amb_customer_items || []).map(r => ({
            customer: r.customer,
            custom_customer_name: r.custom_customer_name,
            custom_customer_part_number: r.custom_customer_part_number,
            custom_lead_time_days: r.custom_lead_time_days,
            custom_min_order_qty: r.custom_min_order_qty,
            custom_max_order_qty_: r.custom_max_order_qty_,
        }));

        if (force) {
            frm.clear_table('custom_tds_customers');
        }

        if (item_customers.length > 0) {
            item_customers.forEach(ic => {
                const row = frm.add_child('custom_tds_customers');
                Object.assign(row, ic);
            });
            frm.refresh_field('custom_tds_customers');

            if (!silent) {
                frappe.show_alert({
                    message: __('Pre-filled {0} customer(s) from Item', [item_customers.length]),
                    indicator: 'green'
                });
            }
            return { populated: item_customers.length, reason: 'ok' };
        }

        if (force && !silent) {
            frappe.show_alert({
                message: __('No customers found on Item {0}', [frm.doc.product_item]),
                indicator: 'orange'
            });
        }
        return { populated: 0, reason: 'item has no customers' };
    } catch (e) {
        console.warn('SC4a: could not auto-populate customers from Item', e);
        return { populated: 0, reason: 'error', error: e };
    }
}

frappe.ui.form.on('TDS Product Specification', {
    refresh: function(frm) {
        // SC4a-v2: legacy-record auto-pop on form load — only if table empty + product_item set
        // Silent mode (no toast) on refresh to avoid noise on every form open
        if (frm.doc.product_item && (frm.doc.custom_tds_customers || []).length === 0) {
            _populate_customers_from_item(frm, { silent: true });
        }

        // SC4a-v2: "Refresh Customers from Item" button under Actions menu
        // Explicit user action — toast feedback enabled; force=true clears table first
        frm.add_custom_button(__('Refresh Customers from Item'), function() {
            frappe.confirm(
                __('Clear the Customers table and re-fetch from Item {0}?', [frm.doc.product_item || '?']),
                function() {
                    _populate_customers_from_item(frm, { force: true, silent: false });
                }
            );
        }, __('Actions'));
    },

    product_item: function(frm) {
        // SC4a Part 2: on Item change, auto-pop if table empty (toast enabled)
        _populate_customers_from_item(frm, { silent: false });
    },

    // ─── Task #46 (2026-05-27) — Preservative System auto-populate ───
    // On Preservative System change: clear + repopulate tds_preservatives from the
    // system's composition table. Empty selection clears the table. Also updates the
    // custom_version field with the system's single-letter code suffix (V1.0705F).
    preservative_system: async function(frm) {
        if (!frm.doc.preservative_system) {
            frm.clear_table('tds_preservatives');
            frm.refresh_field('tds_preservatives');
            return;
        }
        try {
            const sys = await frappe.db.get_doc('Preservative System', frm.doc.preservative_system);
            frm.clear_table('tds_preservatives');
            (sys.composition || []).forEach(c => {
                const row = frm.add_child('tds_preservatives');
                row.compound = c.compound;
                row.percentage = c.percentage;
                row.compound_item = c.compound_item || null;
                row.e_number = c.e_number || null;
                row.is_override = 0;
            });
            frm.refresh_field('tds_preservatives');

            // Update custom_version with single-letter preservative code suffix.
            // Pattern: V<major>.<product_code>[<preservative.code>][<rest>]
            // e.g., V1.0705 → V1.0705F  (FOOD)
            //       V1.0705C → V1.0705F  (replace existing C with new F)
            if (frm.doc.custom_version && sys.code) {
                const match = frm.doc.custom_version.match(/^(V\d+\.\d+)([A-Z]?)(.*)$/);
                if (match) {
                    const newVersion = match[1] + sys.code + match[3];
                    if (newVersion !== frm.doc.custom_version) {
                        frm.set_value('custom_version', newVersion);
                    }
                }
            }

            frappe.show_alert({
                message: __('Loaded {0} compound(s) from {1}', [(sys.composition || []).length, sys.preservative_name]),
                indicator: 'green',
            });
        } catch (e) {
            console.error('Task #46: could not load Preservative System composition', e);
            frappe.msgprint({
                title: __('Error'),
                message: __('Could not load Preservative System composition: {0}', [e.message || e]),
                indicator: 'red',
            });
        }
    },

    tds_preservatives_remove: function(frm) {
        // User removed a row from auto-populated composition → mark remaining rows as override
        (frm.doc.tds_preservatives || []).forEach(r => { r.is_override = 1; });
        frm.refresh_field('tds_preservatives');
    },
});

// Per-row edit handler: any manual edit on TDS Preservative row → flag is_override
frappe.ui.form.on('TDS Preservative', {
    compound: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.is_override = 1;
        frm.refresh_field('tds_preservatives');
    },
    percentage: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.is_override = 1;
        frm.refresh_field('tds_preservatives');
    },
    e_number: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.is_override = 1;
        frm.refresh_field('tds_preservatives');
    },
    compound_item: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.is_override = 1;
        frm.refresh_field('tds_preservatives');
    },
});
