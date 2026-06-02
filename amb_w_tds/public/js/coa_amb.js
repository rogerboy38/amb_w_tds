// SC4 Part 2 — COA AMB form script
// Dual-source auto-populate of custom_coa_customers:
//   Tier 1: linked_tds.custom_tds_customers (curated by Alicia, authoritative)
//   Tier 2: product_item / item_code .custom_amb_customer_items (broader fallback)
//
// 4 entry points:
//   - linked_tds change      → toast
//   - product_item change    → toast (only if no linked_tds path available)
//   - refresh (legacy COAs)  → silent
//   - "Refresh Customers"    → force + confirm dialog + toast
//
// Additive only — does NOT override the 8 existing Client Scripts or 7 Server Scripts on COA AMB.
// Frappe merges frappe.ui.form.on() calls across files; these handlers bind events
// (linked_tds, product_item, refresh) that the existing scripts don't.

// 'Customer Item' is a child table (istable=1) — direct get_list is permission-forbidden
// even for Administrator. Read child rows via the parent doc's child table accessor instead.
function _extract_customer_rows(parentDoc, childField) {
    return (parentDoc[childField] || []).map(r => ({
        customer: r.customer,
        custom_customer_name: r.custom_customer_name,
        custom_customer_part_number: r.custom_customer_part_number,
        custom_lead_time_days: r.custom_lead_time_days,
        custom_min_order_qty: r.custom_min_order_qty,
        custom_max_order_qty_: r.custom_max_order_qty_,
    }));
}

async function fetch_customers_for_coa(frm) {
    // Tier 1: from linked TDS's custom_tds_customers (curated, preferred)
    if (frm.doc.linked_tds) {
        try {
            const tdsDoc = await frappe.db.get_doc('TDS Product Specification', frm.doc.linked_tds);
            const tds_custs = _extract_customer_rows(tdsDoc, 'custom_tds_customers');
            if (tds_custs.length > 0) {
                return { source: 'linked_tds', source_ref: frm.doc.linked_tds, rows: tds_custs };
            }
        } catch (e) { console.warn('SC4 CAV: TDS fetch failed', e); }
    }

    // Tier 2: from Item's custom_amb_customer_items (broader fallback)
    const item_ref = frm.doc.product_item || frm.doc.item_code;
    if (item_ref) {
        try {
            const itemDoc = await frappe.db.get_doc('Item', item_ref);
            const item_custs = _extract_customer_rows(itemDoc, 'custom_amb_customer_items');
            if (item_custs.length > 0) {
                return { source: 'item', source_ref: item_ref, rows: item_custs };
            }
        } catch (e) { console.warn('SC4 CAV: Item fetch failed', e); }
    }

    return { source: null, source_ref: null, rows: [] };
}

async function _populate_customers_for_coa(frm, opts = {}) {
    const { force = false, silent = false } = opts;

    if (!force && (frm.doc.custom_coa_customers || []).length > 0) {
        return { populated: 0, reason: 'table not empty' };
    }

    const { source, source_ref, rows } = await fetch_customers_for_coa(frm);

    if (force) {
        frm.clear_table('custom_coa_customers');
    }

    if (rows.length > 0) {
        rows.forEach(ic => {
            const row = frm.add_child('custom_coa_customers');
            Object.assign(row, ic);
        });
        frm.refresh_field('custom_coa_customers');

        if (!silent) {
            const source_label = source === 'linked_tds'
                ? __('linked TDS {0}', [source_ref])
                : __('Item {0}', [source_ref]);
            frappe.show_alert({
                message: __('Pre-filled {0} customer(s) from {1}', [rows.length, source_label]),
                indicator: 'green'
            });
        }
        return { populated: rows.length, source: source };
    }

    if (force && !silent) {
        frappe.show_alert({
            message: __('No customers found on linked TDS or Item'),
            indicator: 'orange'
        });
    }
    return { populated: 0, reason: 'no rows from any tier' };
}

frappe.ui.form.on('COA AMB', {
    refresh: function(frm) {
        // SC4: legacy-record auto-pop on form load — silent
        if ((frm.doc.custom_coa_customers || []).length === 0
            && (frm.doc.linked_tds || frm.doc.product_item || frm.doc.item_code)) {
            _populate_customers_for_coa(frm, { silent: true });
        }

        // "Refresh Customers" button under Actions menu — force + confirm
        frm.add_custom_button(__('Refresh Customers'), function() {
            const src = frm.doc.linked_tds
                ? __('linked TDS {0}', [frm.doc.linked_tds])
                : (frm.doc.product_item || frm.doc.item_code || '?');
            frappe.confirm(
                __('Clear the Customers table and re-fetch from {0}?', [src]),
                function() {
                    _populate_customers_for_coa(frm, { force: true, silent: false });
                }
            );
        }, __('Actions'));
    },

    linked_tds: function(frm) {
        // SC4: on linked_tds change, auto-pop if table empty (TDS-preferred path)
        _populate_customers_for_coa(frm, { silent: false });
    },

    product_item: function(frm) {
        // SC4: on product_item change, auto-pop if table empty (Item fallback path)
        _populate_customers_for_coa(frm, { silent: false });
    }
});
