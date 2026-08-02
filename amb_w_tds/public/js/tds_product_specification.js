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

// ─────────────────────────────────────────────────────────────────────────────
// T62 Path B4-Link — SHELF LIFE auto-fill driven by Preservative System.code
// ─────────────────────────────────────────────────────────────────────────────
// EXTEND (T62 wake-brief 2026-06-06): appended to the existing canonical script
// rather than replacing it. The SC4a customer auto-pop, Task #46 composition
// loader, and TDS Preservative override handlers above are preserved verbatim.
// These shelf_life handlers are ADDITIVE — Frappe merges frappe.ui.form.on()
// calls for the same doctype, so the second registration below coexists with
// (and fires alongside) the preservative_system / refresh handlers above.
// The existing preservative_system handler manages the tds_preservatives child
// table + custom_version; this one manages only the shelf_life field — disjoint
// targets, no collision.
//
// Doctrine anchors:
//   L153   — file-based JS via hooks.py doctype_js (already wired as a list:
//            "TDS Product Specification": [phase_1c_tab_v2.js, this file]),
//            NOT Customize-Form Custom Script. hooks.py needs NO change.
//   L221v2 — pre-flight substrate-verified before mutate (existing file read,
//            field names validated against doctype JSON + Custom Fields).
//   L231   — single SHA transports sandbox → vpt-docker → vpp.
//   L323   — authored at the authorship substrate (sandbox / VM3).
//   L357   — auto-detect Option C: preserve user manual edits via known-text check.
//   L358   — EXTEND (not REPLACE) confirmed: clobber would have lost SC4a + Task #46.
//
// Fact bank (LESSONS_DIGEST_2026-06-06_FoxPro_Q1_archaeology_L352_L356_banked.md):
//   F-Q1-16 — TEXT_1/TEXT_2/TEXT_3 verbatim from Alicia 2026-06-06
//   F-Q1-17 — Code → variant mapping ratified by Alicia 2026-06-06 ~13:30
//   F-Q1-18 — Path B4 architecture decision (single-field custom script)
//
// Probe verification 2026-06-06: Preservative System catalog = 15 systems,
//   all is_active=1. ORGANIC=H, COSMOS/ORGANIC=M → NO_PRES. The 13 others → PRES.
//   No Client Scripts / Property Setters touch shelf_life (clean).

const TEXT_1_NO_PRES = `6 months after date of production when refrigerated from 0°C - 2°C in an unopened container and out of the exposure of the sunlight to avoid oxidation.

Once the packaging of any Aloe Vera product is opened the product enters into contact with air's humidity and microbes, so it is recommended to use the whole product amount to avoid the spoilage of it. As it is natural product it may change color and precipitation can occur after a period of time.`;

const TEXT_2_PRES = `12 months after date of production when frozen at -18°C in an unopened container and out of the exposure of the sunlight to avoid oxidation.

Once the packaging of any Aloe Vera product is opened the product enters into contact with air's humidity and microbes, so it is recommended to use the whole product amount to avoid the spoilage of it. As it is natural product it may change color and precipitation can occur after a period of time.`;

const TEXT_3_BOTH = `6 months after date of production when refrigerated from 0°C - 2°C in an unopened container and out of the exposure of the sunlight to avoid oxidation. 12 months after date of production when frozen at -18°C in an unopened container and out of the exposure of the sunlight to avoid oxidation.

Once the packaging of any Aloe Vera product is opened the product enters into contact with air's humidity and microbes, so it is recommended to use the whole product amount to avoid the spoilage of it. As it is natural product it may change color and precipitation can occur after a period of time.`;

const NO_PRES_CODES = ['H', 'M'];
const PRES_CODES = ['C', 'D', 'F', 'E', 'O', 'A', 'B', 'I', 'N', 'S', 'V', 'R', 'G'];

// L359 — shelf_life is a Text Editor (Quill) field: frm.doc.shelf_life is HTML
// ('<div class="ql-editor read-mode"><p> 6 months ...</p></div>'), and legacy
// stored data is inconsistent (some plain text, some Quill HTML, stray whitespace
// like "oxidation . Once" / leading spaces). Exact string compare against plain
// constants can NEVER match, so the L357 hands-off check would fire every time and
// auto-fill would be dead (Comet Phase 1d: 1/6). Compare on tag-stripped,
// whitespace-free, lowercased text; write HTML so it renders + round-trips.
function _shelfNorm(s) {
  if (!s) return '';
  let txt = s;
  if (typeof document !== 'undefined') {
    const d = document.createElement('div');
    d.innerHTML = s;
    txt = d.textContent || d.innerText || '';
  }
  return txt.replace(/\s+/g, '').toLowerCase();
}

// Render a plain constant into Quill-NATIVE HTML. The Frappe Text Editor ingests
// via quill.clipboard.convert({html}) -> setContents; Quill's clipboard expects
// <p> paragraphs (stored data is '<p> 6 months ...</p>'). <div> wrapping was
// dropped by the converter -> empty editor (Comet retest 1/6). Use <p>.
function _toShelfHtml(plain) {
  return plain
    .split(/\n{2,}/)
    .map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('');
}

const HTML_1_NO_PRES = _toShelfHtml(TEXT_1_NO_PRES);
const HTML_2_PRES    = _toShelfHtml(TEXT_2_PRES);
const HTML_3_BOTH    = _toShelfHtml(TEXT_3_BOTH);
const KNOWN_NORMS    = [TEXT_1_NO_PRES, TEXT_2_PRES, TEXT_3_BOTH].map(_shelfNorm);

async function resolveShelfLife(frm) {
  // T62 stage 1: substrate gate. Powder specs never take liquid text.
  // Hands off until the powder norm is ratified (Alicia — two candidate texts
  // pending, prod 5ceb09b6… vs sandbox 24f7f695…).
  const sub = (frm.doc.item_substrate || '').toUpperCase();
  if (sub === 'PWD' || sub === 'PWDF') return null;

  // L357 auto-detect Option C: preserve user manual edits. A cleared Quill field
  // normalizes to '' (e.g. '<p><br></p>' -> ''), so it is NOT treated as custom.
  const curNorm = _shelfNorm(frm.doc.shelf_life);
  if (curNorm && !KNOWN_NORMS.includes(curNorm)) {
    return null;  // user typed something custom — hands off, leave field as-is
  }

  // No system selected → safe baseline (combined text)
  if (!frm.doc.preservative_system) {
    return HTML_3_BOTH;
  }

  // Catalog lookup: read the `code` field on the linked Preservative System
  try {
    const r = await frappe.db.get_value(
      'Preservative System',
      frm.doc.preservative_system,
      'code'
    );
    const code = r && r.message && r.message.code;
    if (NO_PRES_CODES.includes(code)) return HTML_1_NO_PRES;
    if (PRES_CODES.includes(code))    return HTML_2_PRES;
    return HTML_3_BOTH;  // unknown code → safe baseline
  } catch (e) {
    console.warn('[T62 Path B4] Preservative System lookup failed:', e);
    return HTML_3_BOTH;
  }
}

// Debug instrumentation gate. Toasts stay SILENT for end-users (Alicia) by default,
// and can be re-enabled at any substrate for ratification without a code change:
//   in the browser console run  localStorage.t62_debug = '1'  then reload the form.
// (Set to anything else / remove the key to silence again.) These toasts proved the
// 6/6 sandbox pass on 2026-06-06 — curKnown=true|empty|false maps to engage|re-engage|hands-off.
function _t62Debug() {
  try { return typeof localStorage !== 'undefined' && localStorage.getItem('t62_debug') === '1'; }
  catch (e) { return false; }
}

async function applyShelfLife(frm) {
  const target = await resolveShelfLife(frm);
  const curN = _shelfNorm(frm.doc.shelf_life);

  if (_t62Debug()) {
    frappe.show_alert({
      message: '[T62] sys=' + (frm.doc.preservative_system || '(none)')
        + ' | target=' + (target === null
            ? 'HANDS-OFF(null)'
            : (target ? target.replace(/<[^>]+>/g, ' ').trim().slice(0, 26) : '(EMPTY!)'))
        + ' | curKnown=' + (curN ? KNOWN_NORMS.includes(curN) : 'empty'),
      indicator: target ? 'blue' : 'orange'
    }, 7);
  }

  if (target === null) return;  // hands off — preserve manual edit
  if (curN === _shelfNorm(target)) return;  // already correct
  frm.set_value('shelf_life', target);

  if (_t62Debug()) {
    setTimeout(() => {
      const v = frm.doc.shelf_life || '';
      const after = _shelfNorm(v);
      frappe.show_alert({
        message: '[T62] after-set model: ' + (after
            ? ('len=' + after.length + ' "' + v.replace(/<[^>]+>/g, ' ').trim().slice(0, 22) + '"')
            : 'EMPTY in model'),
        indicator: after ? 'green' : 'red'
      }, 7);
    }, 600);
  }
}

// Additive registration — coexists with the canonical block above (Frappe merges).
frappe.ui.form.on('TDS Product Specification', {
  preservative_system: applyShelfLife,
  refresh: applyShelfLife
});
