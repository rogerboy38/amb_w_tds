// SC5 v2 — Parameter Selection picker rewrite, BULLETPROOFED edition
//
// This is a parallel candidate to phase_1c_tab.js (V14.3.3-live currently in prod).
// Architecture: Common Root → 7 ratified L2 → QIP leaves (same as SC5 v1).
// Key fixes vs v1 (which hung at "Loading parameter catalog..."):
//   - REMOVED frappe.db.get_value('DocType', ...) probe (System Manager-only)
//   - Every await wrapped in try/catch with explicit fallback render
//   - 10s watchdog: if main render hasn't completed, replace loader with error panel
//   - Top-level try/catch in refresh handler — never leaves "Loading..." state
//
// To test: edit hooks.py doctype_js entry for "TDS Product Specification" — replace
// "public/js/phase_1c_tab.js" with "public/js/phase_1c_tab_v2.js", bench restart, browser
// hard-refresh. To roll back: revert the hooks.py line + restart.
//
// USES SAME container IDs as v1 (#phase-1c-tree-picker, #phase-1c-action-bar) so the
// existing form HTML works unchanged.


const SC5V2_COMMON_ROOT = 'Common Root';
const SC5V2_L2_CATEGORIES = [
    { key: 'organoleptic',        qipg: 'Organoleptic',        en: 'Organoleptic',        es: 'Análisis Organoléptico' },
    { key: 'physicochemical',     qipg: 'Physicochemical',     en: 'Physicochemical',     es: 'Análisis Fisicoquímico' },
    { key: 'microbiological',     qipg: 'Microbiological',     en: 'Microbiological',     es: 'Análisis Microbiológico' },
    { key: 'pesticides',          qipg: 'Pesticides',          en: 'Pesticides',          es: 'Pesticidas' },
    { key: 'contaminant',         qipg: 'Contaminant',         en: 'Contaminants',        es: 'Contaminantes' },
    { key: 'other_analysis',      qipg: 'Other Analysis',      en: 'Other Analysis',      es: 'Otros Análisis' },
    { key: 'aloe_vera_nutrients', qipg: 'Aloe Vera Nutrients', en: 'Aloe Vera Nutrients', es: 'Nutrientes de Aloe Vera' },
];


// ─── IQI value-change handler (preserved verbatim from V14.3.3) ───
frappe.ui.form.on('Item Quality Inspection Parameter', {
    value: function(frm, cdt, cdn) {
        const row = locals[cdt] && locals[cdt][cdn];
        if (!row || !row.value) return;
        const formula = sc5v2_parseValueFormula(row.value);
        if (formula) {
            const newMin = (formula.min === null || formula.min === undefined) ? 0 : formula.min;
            const newMax = (formula.max === null || formula.max === undefined) ? 0 : formula.max;
            if (row.min_value !== newMin) frappe.model.set_value(cdt, cdn, 'min_value', newMin);
            if (row.max_value !== newMax) frappe.model.set_value(cdt, cdn, 'max_value', newMax);
            if (formula.isNumeric && row.numeric !== 1) frappe.model.set_value(cdt, cdn, 'numeric', 1);
        } else if ((row.min_value && row.min_value !== 0) || (row.max_value && row.max_value !== 0)) {
            frappe.model.set_value(cdt, cdn, 'min_value', 0);
            frappe.model.set_value(cdt, cdn, 'max_value', 0);
        }
    }
});


// ─── Refresh handler — TOP-LEVEL try/catch + watchdog ───
frappe.ui.form.on('TDS Product Specification', {
    refresh: async function(frm) {
        const pickerEl = document.getElementById('phase-1c-tree-picker');
        const actionEl = document.getElementById('phase-1c-action-bar');
        if (!pickerEl || !actionEl) return;  // containers not on this form

        if (frm.is_new() || !frm.doc.product_item) {
            pickerEl.innerHTML = `<i class="text-muted">${__('Save the document and set a Product Item to enable Parameter Selection.')}</i>`;
            actionEl.innerHTML = '';
            return;
        }

        // Task #33 v2 (2026-05-27): submitted docs reject child-table writes
        // (IQI field has allow_on_submit=0). Without this guard the picker lets the user
        // click Add Selected, shows a misleading toast, and save() silently no-ops — the
        // anomaly Comet flagged on 0705 TDS BASE. Block clearly + point to Amend.
        if (frm.doc.docstatus === 1) {
            pickerEl.innerHTML = `
                <div style="background:#fff3e0; border-left:4px solid #ff9800; padding:12px 16px; border-radius:6px; color:#5d4037; font-size:13px;">
                    🔒 ${__('This document is submitted. Parameter changes are not allowed on a submitted TDS.')}<br>
                    <span style="font-size:12px; color:#7f6e63;">${__('To add or modify parameters: open the Menu and click <b>Amend</b>, then use the picker on the amended draft.')}</span>
                </div>`;
            actionEl.innerHTML = '';
            return;
        }
        if (frm.doc.docstatus === 2) {
            pickerEl.innerHTML = `<i class="text-muted">${__('This document is cancelled. Parameter Selection is disabled.')}</i>`;
            actionEl.innerHTML = '';
            return;
        }

        // Show loader
        pickerEl.innerHTML = `<div class="text-muted" id="sc5v2-loading">${__('Loading parameter catalog...')} <span style="opacity:0.6">(SC5 v2)</span></div>`;
        actionEl.innerHTML = '';

        // 10s watchdog — if render doesn't replace the loader, show an error panel
        const watchdogId = setTimeout(() => {
            const stillLoading = document.getElementById('sc5v2-loading');
            if (stillLoading) {
                pickerEl.innerHTML = sc5v2_renderErrorPanel(
                    __('Catalog load timed out (10s)'),
                    __('The picker took too long to load. Check the browser console for errors.')
                );
            }
        }, 10000);

        try {
            await sc5v2_renderParameterPicker(frm);
            sc5v2_renderActionBar(frm);
        } catch (err) {
            console.error('SC5 v2: top-level render failed', err);
            pickerEl.innerHTML = sc5v2_renderErrorPanel(
                __('Parameter picker failed to render'),
                String(err && err.message ? err.message : err)
            );
        } finally {
            clearTimeout(watchdogId);
        }
    }
});


function sc5v2_renderErrorPanel(title, detail) {
    return `
        <div style="border:1px solid #e57373; background:#ffebee; padding:14px 16px; border-radius:6px; color:#c62828;">
            <div style="font-weight:600; margin-bottom:6px;">⚠ ${frappe.utils.escape_html(title)}</div>
            <div style="font-size:12px; color:#7f0000; margin-bottom:10px;">${frappe.utils.escape_html(detail || '')}</div>
            <button type="button" class="btn btn-xs btn-default" onclick="cur_frm && cur_frm.refresh()">${__('Reload picker')}</button>
        </div>`;
}


// ─── Substrate detection — M3.5 v2 (2026-05-27): walk Item Group parent chain ───
//
// The leaf Item Group (e.g., 'FG 0300') has zero substrate-related fields. The substrate
// is encoded in the PARENT chain naming convention (Powder / Liquid / Formulated tokens).
// This function walks up the Item Group ancestry until it finds a substrate-bearing
// ancestor; returns the matched substrate code or null (substrate-agnostic → no filter).
//
// Token map: Powder/Mix Powder → 'PWD'; Liquid → 'LQD'; <prefix> Concentrated → 'LQDC';
//            <prefix> Formulated → 'LQDF' / 'PWDF' (form depends on liquid vs powder branch).
//
// Returns: { itemGroup, substrateCode, chain } — chain is the walked ancestry for debug.
async function sc5v2_deriveItemGroup(frm) {
    if (!frm.doc.product_item) return { itemGroup: null, substrateCode: null, chain: [] };
    try {
        const r = await frappe.db.get_value('Item', frm.doc.product_item, ['item_group']);
        const ig = r && r.message && r.message.item_group;
        if (!ig) return { itemGroup: null, substrateCode: null, chain: [] };

        // Walk up the Item Group hierarchy (max 6 levels — generous bound)
        let current = ig;
        const chain = [current];
        for (let depth = 0; depth < 6; depth++) {
            const token = sc5v2_parseSubstrateToken(current);
            if (token) return { itemGroup: ig, substrateCode: token, chain };
            const groupRes = await frappe.db.get_value('Item Group', current, ['parent_item_group']);
            const parent = groupRes && groupRes.message && groupRes.message.parent_item_group;
            if (!parent || parent === current) break;
            current = parent;
            chain.push(current);
        }
        // No substrate-bearing ancestor found — substrate-agnostic (template/raw material)
        return { itemGroup: ig, substrateCode: null, chain };
    } catch (e) {
        console.warn('SC5 v2: item_group derivation failed', e);
        return { itemGroup: null, substrateCode: null, chain: [] };
    }
}

function sc5v2_parseSubstrateToken(name) {
    if (!name) return null;
    const lc = String(name).toLowerCase();
    if (lc.includes('powder formulated')) return 'PWDF';
    if (lc.includes('liquid concentrated')) return 'LQDC';
    if (lc.includes('liquid formulated')) return 'LQDF';
    if (lc.includes('mix powder') || lc.includes('powder')) return 'PWD';
    if (lc.includes('liquid') || lc.includes('juice') || lc.includes('gel')) return 'LQD';
    return null;
}


// ─── Substrate-tag map fetch — M3.5 (2026-05-27) ───
//
// The `applicable_substrates` Table MultiSelect on QIPG was populated by the M3.5
// patch (427 leaves × ~5 substrates = 2087 child rows in `tabParameter Group Substrate`).
// Frappe forbids `frappe.db.get_list` on child doctypes from client JS (REST guard),
// so we go through a whitelisted server method that returns the full map in one call.
//
// Returns: { qipg_name: ['LQD','PWD',...], ... }  OR {} on any failure (graceful no-op).
async function sc5v2_fetchSubstrateMap() {
    try {
        const r = await frappe.call({
            method: 'amb_w_tds.api.picker.get_substrate_map',
            type: 'GET',
        });
        return (r && r.message) || {};
    } catch (e) {
        console.warn('SC5 v2 M3.5: substrate map fetch failed (continuing without filter)', e);
        return {};
    }
}


// ─── Acceptance-choices map fetch — Task #33 (2026-05-27) ───
//
// L4 acceptance choices live as `tabAcceptance Choice` child rows on QIP. JS can't
// query istable=1 doctypes directly, so a server-side whitelisted method aggregates
// them: { qip_name: [choice_row, ...] }. Empty result → fall back to legacy
// custom_choices Long Text line-count display.
async function sc5v2_fetchAcceptanceChoicesMap() {
    try {
        const r = await frappe.call({
            method: 'amb_w_tds.api.picker.get_acceptance_choices_map',
            type: 'GET',
        });
        return (r && r.message) || {};
    } catch (e) {
        console.warn('SC5 v2 #33: acceptance choices map fetch failed (using legacy text fallback)', e);
        return {};
    }
}


// ─── Data fetch — wrapped per call ───
//
// M3.5 (2026-05-27): if `substrateCode` is provided, filter QIPs whose parameter_group's
// applicable_substrates includes that code. Empty substrate map (no M3.5 data, or server
// method failed) → no filtering, all QIPs returned. Returns `substrateMapPresent` so the
// caller can render an "M3.5 not yet" banner when the map is empty.
async function sc5v2_fetchTreeData(substrateCode) {
    let qipgs = [];
    let qips = [];

    try {
        qipgs = await frappe.db.get_list('Quality Inspection Parameter Group', {
            fields: ['name', 'is_group', 'lft', 'rgt', 'custom_parameter_group_child'],
            order_by: 'lft asc', limit: 0,
        });
    } catch (e) {
        console.error('SC5 v2: QIPG fetch failed', e);
        throw new Error(__('Could not load parameter groups: {0}', [String(e.message || e)]));
    }

    try {
        qips = await frappe.db.get_list('Quality Inspection Parameter', {
            fields: ['name', 'parameter', 'parameter_group', 'custom_choices',
                     'custom_is_numeric', 'custom_method', 'custom_unit',
                     'custom_value_text', 'custom_value_min', 'custom_value_max',
                     'l4_migration_status'],
            order_by: 'parameter asc', limit: 0,
        });
    } catch (e) {
        console.error('SC5 v2: QIP fetch failed', e);
        throw new Error(__('Could not load parameters: {0}', [String(e.message || e)]));
    }

    // M3.5 substrate map (whitelisted server method — returns {} on any failure)
    const substrateMap = await sc5v2_fetchSubstrateMap();
    const substrateMapPresent = Object.keys(substrateMap).length > 0;

    // Task #33: L4 acceptance-choices map (whitelisted server method — returns {} on failure)
    const acceptanceChoicesMap = await sc5v2_fetchAcceptanceChoicesMap();

    const byName = {};
    qipgs.forEach(n => { byName[n.name] = n; });

    const rootNode = byName[SC5V2_COMMON_ROOT];
    if (!rootNode) {
        throw new Error(__("Common Root parameter group not found. Tree cannot render."));
    }

    const hierarchy = SC5V2_L2_CATEGORIES.map(cat => {
        const catNode = byName[cat.qipg];
        if (!catNode) return { ...cat, params: [], missing: true };
        let params = qips.filter(qip => {
            const pg = byName[qip.parameter_group];
            return pg && pg.lft >= catNode.lft && pg.rgt <= catNode.rgt;
        });

        // M3.5 substrate filter — only when the map is populated AND a substrate is detected
        if (substrateMapPresent && substrateCode) {
            params = params.filter(qip => {
                const subs = substrateMap[qip.parameter_group];
                if (!subs) return true;  // leaf not yet tagged → show (graceful default)
                return subs.includes(substrateCode);
            });
        }

        return { ...cat, params, missing: false };
    });

    return {
        hierarchy,
        totalParams: hierarchy.reduce((s, c) => s + c.params.length, 0),
        substrateMapPresent,
        acceptanceChoicesMap,
    };
}


// ─── CAV map fetch — wrapped, returns empty on any failure ───
async function sc5v2_fetchCAVMap(customers, qipNames) {
    if (!customers || !customers.length || !qipNames || !qipNames.length) return {};
    try {
        const rows = await frappe.db.get_list('Customer Acceptable Value', {
            filters: {
                parameter: ['in', qipNames],
                customer: ['in', customers],
                status: 'Approved',
                is_active: 1,
            },
            fields: ['name', 'parameter', 'customer', 'value_type', 'value_text',
                     'value_min', 'value_max', 'method', 'unit_of_measurement',
                     'regulatory_reference', 'effective_from', 'effective_to'],
            limit: 0,
        });
        const today = frappe.datetime.get_today();
        const map = {};
        rows.forEach(cav => {
            if (cav.effective_from && cav.effective_from > today) return;
            if (cav.effective_to && cav.effective_to < today) return;
            if (!map[cav.parameter]) map[cav.parameter] = [];
            map[cav.parameter].push(cav);
        });
        return map;
    } catch (e) {
        console.warn('SC5 v2 CAV: fetch failed, continuing without CAV badges', e);
        return {};
    }
}


// ─── Top-level render ───
//
// All 4 awaits below are inside their own try/catch even though the helper functions
// already self-protect. Belt-and-suspenders: if a future refactor breaks an internal
// guard, the rejection still doesn't bubble past this layer. fetchTreeData is the
// only helper allowed to throw (with a meaningful message) — its rethrow propagates
// to the refresh handler's top-level catch, which renders the error panel.
async function sc5v2_renderParameterPicker(frm) {
    const pickerEl = document.getElementById('phase-1c-tree-picker');

    let itemGroup = null, substrateCode = null;
    try { ({ itemGroup, substrateCode } = await sc5v2_deriveItemGroup(frm)); }
    catch (e) { console.warn('SC5 v2: deriveItemGroup threw (using nulls)', e); }

    // fetchTreeData rethrows with a meaningful error if tree can't load — that's
    // intentional (no tree = no picker, surface to user via the top-level catch).
    // M3.5 (2026-05-27): fetchTreeData now takes substrateCode + returns substrateMapPresent.
    // Task #33 (2026-05-27): also returns acceptanceChoicesMap for L4 picker rendering.
    const { hierarchy, totalParams, substrateMapPresent, acceptanceChoicesMap } = await sc5v2_fetchTreeData(substrateCode);

    const customers = (frm.doc.custom_tds_customers || []).map(r => r.customer).filter(Boolean);
    const qipNames = hierarchy.flatMap(c => c.params.map(p => p.name));
    let cavMap = {};
    if (customers.length > 0) {
        try { cavMap = await sc5v2_fetchCAVMap(customers, qipNames); }
        catch (e) { console.warn('SC5 v2: CAV map threw (continuing without badges)', e); }
    }
    const cavCount = Object.keys(cavMap).length;

    let html = '';
    html += sc5v2_renderHeader({ itemGroup, substrateCode, totalParams, customers, cavCount });

    if (!substrateMapPresent) {
        html += `<div style="background:#fff3e0; border-left:4px solid #ff9800; padding:10px 14px; margin:10px 0; border-radius:4px; color:#5d4037; font-size:13px;">
            ⚠ ${__('Substrate filtering not yet active. Showing all parameters; pending M3.5 substrate tagging.')}
        </div>`;
    } else if (substrateCode) {
        html += `<div style="background:#e8f5e9; border-left:4px solid #4caf50; padding:8px 14px; margin:10px 0; border-radius:4px; color:#1b5e20; font-size:13px;">
            🧪 ${__('Substrate filter active: {0} — showing {1} applicable parameter(s)', [substrateCode, totalParams])}
        </div>`;
    }

    html += sc5v2_renderMasterControls();
    html += '<div style="margin-top:8px;">';
    hierarchy.forEach(cat => { html += sc5v2_renderL2Section(cat, cavMap, acceptanceChoicesMap); });
    html += '</div>';

    pickerEl.innerHTML = html;
    sc5v2_attachHandlers();
    sc5v2_updateSummary();
}


function sc5v2_renderHeader({ itemGroup, substrateCode, totalParams, customers, cavCount }) {
    const headerLabel = itemGroup
        ? `${frappe.utils.escape_html(itemGroup)}${substrateCode ? ' (' + substrateCode + ')' : ''}`
        : __('Unknown Item Group');
    const cavBlurb = customers.length > 0
        ? ` · 🎯 ${__('{0} customer(s), {1} active CAV(s)', [customers.length, cavCount])}`
        : '';
    return `
        <div style="padding:10px 14px; background:#f5f6f8; border:1px solid #d1d8dd; border-radius:6px; margin-bottom:10px; font-size:13px;">
            <b>${__('Form (L1)')}:</b> ${headerLabel}
            · ${__('{0} L2 categories', [SC5V2_L2_CATEGORIES.length])}
            · ${__('{0} parameters', [totalParams])}${cavBlurb}
        </div>`;
}


function sc5v2_renderMasterControls() {
    return `
        <div style="padding:8px 14px; background:#f5f6f8; border:1px solid #d1d8dd; border-radius:6px; font-size:13px;">
            <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-weight:600;">
                <input type="checkbox" id="sc5v2-master-select-all">
                <span>${__('Select All')} <span style="font-weight:normal;color:#6c7680;">(${__('every parameter, all groups')})</span></span>
            </label>
        </div>`;
}


function sc5v2_renderL2Section(cat, cavMap, acceptanceChoicesMap) {
    const params = cat.params;
    const headerExtras = cat.missing
        ? `<span style="background:#ffcdd2;color:#c62828;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:auto;">${__('⚠ QIPG missing')}</span>`
        : `<span style="background:#e0e0e0;color:#525960;font-size:11px;padding:2px 8px;border-radius:10px;margin-left:auto;">${__('{0} params', [params.length])}</span>`;

    const leavesHtml = (params.length === 0 && !cat.missing)
        ? `<div style="padding:8px 0; color:#9e9e9e; font-style:italic;">${__('No parameters in this category yet.')}</div>`
        : params.map(qip => sc5v2_renderLeafRow(qip, cat, cavMap, acceptanceChoicesMap)).join('');

    return `
        <div class="sc5v2-l2-section" data-l2-key="${frappe.utils.escape_html(cat.key)}" style="margin-bottom:8px; border:1px solid #d1d8dd; border-radius:6px; overflow:hidden;">
            <div class="sc5v2-l2-header" style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:#f5f6f8; cursor:pointer; user-select:none;">
                <span class="sc5v2-chevron" style="color:#6c7680; font-size:12px; transition:transform 0.15s;">▶</span>
                <label style="display:inline-flex; align-items:center; cursor:pointer;" onclick="event.stopPropagation()">
                    <input type="checkbox" class="sc5v2-l2-toggle" data-l2-key="${frappe.utils.escape_html(cat.key)}">
                </label>
                <span style="flex:1; font-weight:600;">
                    ${frappe.utils.escape_html(cat.en)}
                    <span style="color:#6c7680; font-weight:normal; font-size:13px;"> / ${frappe.utils.escape_html(cat.es)}</span>
                </span>
                ${headerExtras}
            </div>
            <div class="sc5v2-l2-leaves" style="display:none; padding:6px 14px 12px 36px;">
                ${leavesHtml}
            </div>
        </div>`;
}


function sc5v2_renderLeafRow(qip, cat, cavMap, acceptanceChoicesMap) {
    // Task #33: prefer L4 child rows; fall back to legacy custom_choices Long Text
    const l4Choices = (acceptanceChoicesMap && acceptanceChoicesMap[qip.name]) || [];
    const legacyLines = qip.custom_choices
        ? qip.custom_choices.split('\n').map(s => s.trim()).filter(Boolean)
        : [];
    const choiceCount = l4Choices.length > 0 ? l4Choices.length : legacyLines.length;
    const hasChoices = choiceCount > 0;

    const cavMatches = cavMap[qip.name] || [];
    const needsReview = (qip.l4_migration_status === 'Manual Review')
        || (l4Choices.length === 0 && legacyLines.length === 0 && !qip.custom_is_numeric);

    let badges = '';
    if (cavMatches.length > 0) {
        const tip = cavMatches.length === 1 ? `CAV ${cavMatches[0].name}` : `${cavMatches.length} CAVs`;
        badges += `<span title="${frappe.utils.escape_html(tip)}" style="background:#fff3e0;color:#e65100;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:8px;">🎯 ${__('CAV')}</span>`;
    }
    if (hasChoices) {
        badges += `<span style="background:#c8e6c9;color:#1b5e20;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:8px;">${__('{0} choices', [choiceCount])}</span>`;
    }
    if (needsReview) {
        // Task #33 v3 (2026-05-27): Alicia's lost affordance — clicking the amber tag
        // opens the "Edit Posibles Valores" dialog so she can quickly add choice text.
        badges += `<span class="sc5v2-edit-choices-trigger"
                          data-qip-name="${frappe.utils.escape_html(qip.name)}"
                          style="background:#ffe0b2;color:#e65100;font-size:10px;padding:1px 6px;border-radius:8px;margin-left:8px;cursor:pointer;text-decoration:underline dotted;"
                          title="${frappe.utils.escape_html(__('Click to add Acceptance Choices — current L4 status: {0}', [qip.l4_migration_status || 'Not Migrated']))}">${__('needs review')} ✎</span>`;
    }

    // Build the radio block for L4 choices. Render only when 2+ choices; for 0 or 1
    // it's a single-spec QIP, no radio UI needed (saving the first/only choice is automatic).
    let choicesHtml = '';
    if (l4Choices.length >= 2) {
        const qipSafe = frappe.utils.escape_html(qip.name);
        const radioName = `sc5v2_choice_${qip.name.replace(/[^A-Za-z0-9_-]/g, '_')}`;
        const items = l4Choices.map((c, i) => {
            const isDefault = c.is_default ? true : (i === 0);
            // Numeric bounds — Phase 3 migration stores 0.0 (not null) for Manual-Review
            // rows, so guard against showing a misleading "min=0 max=0" on a row that
            // had no real bounds parsed. Show when either side is > 0 or target is set.
            const hasBounds = (c.min_value != null && c.min_value > 0)
                || (c.max_value != null && c.max_value > 0)
                || (c.target_value != null && c.target_value > 0);
            const subParts = [];
            if (hasBounds) {
                const minTxt = (c.min_value != null && !isNaN(c.min_value)) ? c.min_value : 'N/A';
                const maxTxt = (c.max_value != null && !isNaN(c.max_value)) ? c.max_value : 'N/A';
                subParts.push(__('min: {0}, max: {1}', [minTxt, maxTxt]));
            }
            if (c.target_value != null && c.target_value > 0) subParts.push(`target: ${c.target_value}`);
            if (c.unit) subParts.push(`UOM: ${c.unit}`);
            if (c.sub_spec) subParts.push(c.sub_spec);
            if (c.reconstituted_to_05_solids) subParts.push(__('recon 0.5%'));
            // Tooltip (on the radio input itself, so hovering the radio surfaces it
            // — Comet's B1 finding: the title on the <label> alone didn't reach the radio)
            const tip = subParts.join(' · ');
            // Inline subtitle (the richer UX Hugh recommended) — only when there's content
            const subtitle = subParts.length > 0
                ? `<div style="margin-left:22px; font-size:11px; color:#6c7680; line-height:1.3;">${frappe.utils.escape_html(subParts.join(' · '))}</div>`
                : '';
            const defaultTag = isDefault ? ` <span style="color:#1b5e20; font-size:10px;">${__('(default)')}</span>` : '';
            return `
                <div class="sc5v2-choice-radio-row" style="padding:2px 0;">
                    <label title="${frappe.utils.escape_html(tip)}" style="display:flex; align-items:center; gap:6px; cursor:pointer; font-size:12px;">
                        <input type="radio" name="${radioName}" value="${frappe.utils.escape_html(c.name)}"
                               title="${frappe.utils.escape_html(tip)}"
                               data-qip-name="${qipSafe}"
                               data-text-label="${frappe.utils.escape_html(c.text_label || '')}"
                               data-min-value="${c.min_value != null ? c.min_value : ''}"
                               data-max-value="${c.max_value != null ? c.max_value : ''}"
                               data-target-value="${c.target_value != null ? c.target_value : ''}"
                               data-unit="${frappe.utils.escape_html(c.unit || '')}"
                               data-sub-spec="${frappe.utils.escape_html(c.sub_spec || '')}"
                               ${isDefault ? 'checked' : ''}>
                        <span>${frappe.utils.escape_html(c.text_label || '(empty)')}${defaultTag}</span>
                    </label>
                    ${subtitle}
                </div>`;
        }).join('');
        choicesHtml = `
            <div class="sc5v2-choices-block" data-qip-name="${qipSafe}" style="margin-left:24px; padding:4px 0 6px 0; border-left:2px solid #e0e0e0; padding-left:10px;">
                ${items}
            </div>`;
    }

    // Task #33 v3 (2026-05-27): always-visible ✎ pencil next to the parameter name as a
    // secondary "Edit choices" affordance. Sibling of the (clickable) needs-review tag.
    // Lives OUTSIDE the checkbox <label> so click doesn't toggle the checkbox.
    const editPencil = `<span class="sc5v2-edit-choices-trigger"
                              data-qip-name="${frappe.utils.escape_html(qip.name)}"
                              title="${frappe.utils.escape_html(__('Edit Posibles Valores for this parameter'))}"
                              style="margin-left:4px; cursor:pointer; color:#888; font-size:12px; user-select:none;">✎</span>`;
    return `
        <div class="sc5v2-leaf-row" data-qip-name="${frappe.utils.escape_html(qip.name)}" style="padding:4px 0; font-size:13px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <label style="display:inline-flex; align-items:center; gap:8px; cursor:pointer;">
                    <input type="checkbox" class="sc5v2-qip-cb"
                           data-qip-name="${frappe.utils.escape_html(qip.name)}"
                           data-param-group="${frappe.utils.escape_html(qip.parameter_group || '')}"
                           data-l2-key="${frappe.utils.escape_html(cat.key)}"
                           data-l2-name="${frappe.utils.escape_html(cat.en)}">
                    <span>${frappe.utils.escape_html(qip.parameter || qip.name)}</span>
                </label>
                ${editPencil}
                <span style="flex:1;"></span>
                ${badges}
            </div>
            ${choicesHtml}
        </div>`;
}


// ─── Event handlers ───
function sc5v2_attachHandlers() {
    document.querySelectorAll('.sc5v2-l2-header').forEach(header => {
        header.addEventListener('click', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'LABEL') return;
            const section = this.closest('.sc5v2-l2-section');
            const leaves = section.querySelector('.sc5v2-l2-leaves');
            const chevron = section.querySelector('.sc5v2-chevron');
            const open = leaves.style.display !== 'none';
            leaves.style.display = open ? 'none' : 'block';
            if (chevron) chevron.style.transform = open ? '' : 'rotate(90deg)';
        });
    });

    document.querySelectorAll('.sc5v2-l2-toggle').forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            const section = this.closest('.sc5v2-l2-section');
            section.querySelectorAll('.sc5v2-qip-cb').forEach(leaf => { leaf.checked = this.checked; });
            sc5v2_updateMasterTriState();
            sc5v2_updateSummary();
        });
    });

    document.querySelectorAll('.sc5v2-qip-cb').forEach(cb => {
        cb.addEventListener('change', function() {
            const section = this.closest('.sc5v2-l2-section');
            sc5v2_updateL2TriState(section);
            sc5v2_updateMasterTriState();
            sc5v2_updateSummary();
        });
    });

    // Task #33 v3 (2026-05-27): clickable amber "needs review" tag + ✎ pencil →
    // open Alicia's "Edit Posibles Valores" dialog. e.preventDefault/stopPropagation
    // so the click doesn't bubble to the parent label and toggle the checkbox.
    document.querySelectorAll('.sc5v2-edit-choices-trigger').forEach(el => {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const qipName = this.dataset.qipName;
            if (qipName) sc5v2_openEditChoicesDialog(qipName);
        });
    });

    const master = document.getElementById('sc5v2-master-select-all');
    if (master) {
        master.addEventListener('change', function() {
            document.querySelectorAll('.sc5v2-qip-cb').forEach(cb => { cb.checked = this.checked; });
            document.querySelectorAll('.sc5v2-l2-toggle').forEach(t => { t.checked = this.checked; t.indeterminate = false; });
            sc5v2_updateSummary();
        });
    }

    // Auto-open first section so users see something immediately
    const firstSection = document.querySelector('.sc5v2-l2-section');
    if (firstSection) {
        const leaves = firstSection.querySelector('.sc5v2-l2-leaves');
        const chevron = firstSection.querySelector('.sc5v2-chevron');
        if (leaves) leaves.style.display = 'block';
        if (chevron) chevron.style.transform = 'rotate(90deg)';
    }
}


function sc5v2_updateL2TriState(section) {
    if (!section) return;
    const all = section.querySelectorAll('.sc5v2-qip-cb');
    const checked = section.querySelectorAll('.sc5v2-qip-cb:checked');
    const toggle = section.querySelector('.sc5v2-l2-toggle');
    if (!toggle) return;
    if (checked.length === 0) { toggle.checked = false; toggle.indeterminate = false; }
    else if (checked.length === all.length) { toggle.checked = true; toggle.indeterminate = false; }
    else { toggle.checked = false; toggle.indeterminate = true; }
}


function sc5v2_updateMasterTriState() {
    const all = document.querySelectorAll('.sc5v2-qip-cb');
    const checked = document.querySelectorAll('.sc5v2-qip-cb:checked');
    const master = document.getElementById('sc5v2-master-select-all');
    if (!master) return;
    if (checked.length === 0) { master.checked = false; master.indeterminate = false; }
    else if (checked.length === all.length) { master.checked = true; master.indeterminate = false; }
    else { master.checked = false; master.indeterminate = true; }
}


function sc5v2_updateSummary() {
    const total = document.querySelectorAll('.sc5v2-qip-cb:checked').length;
    const groups = new Set();
    document.querySelectorAll('.sc5v2-qip-cb:checked').forEach(cb => groups.add(cb.dataset.l2Key));
    const summary = document.getElementById('sc5v2-sel-summary');
    if (summary) summary.textContent = __('{0} parameter(s) selected across {1} group(s)', [total, groups.size]);
    const addBtn = document.getElementById('sc5v2-add-btn');
    if (addBtn) addBtn.disabled = total === 0;
}


// ─── Action bar ───
function sc5v2_renderActionBar(frm) {
    const actionEl = document.getElementById('phase-1c-action-bar');
    if (!actionEl) return;
    actionEl.innerHTML = `
        <div style="display:flex; gap:10px; align-items:center; padding:14px 0; border-top:1px solid #d1d8dd; margin-top:10px;">
            <button id="sc5v2-add-btn" class="btn btn-primary btn-sm" disabled>+ ${__('Add Selected Parameters')}</button>
            <button id="sc5v2-clear-btn" class="btn btn-default btn-sm">${__('Clear Selections')}</button>
            <span id="sc5v2-sel-summary" style="color:#6c7680; font-size:13px;">${__('0 parameter(s) selected across 0 group(s)')}</span>
        </div>`;

    const addBtn = document.getElementById('sc5v2-add-btn');
    if (addBtn) addBtn.addEventListener('click', () => sc5v2_addSelected(frm));

    const clearBtn = document.getElementById('sc5v2-clear-btn');
    if (clearBtn) clearBtn.addEventListener('click', () => {
        document.querySelectorAll('#phase-1c-tree-picker input[type=checkbox]').forEach(cb => { cb.checked = false; cb.indeterminate = false; });
        sc5v2_updateSummary();
    });
}


// ─── Edit Posibles Valores dialog — Task #33 v3 (2026-05-27) ───
//
// Restores Alicia's lost UX affordance from the deprecated erp.sysmayal2.cloud bench:
// click the amber "needs review" tag (or the ✎ pencil next to the parameter name) →
// dialog opens → existing Acceptance Choice rows shown read-only → free-text textarea
// for new lines → Save calls the server method and re-renders the picker.
//
// The new lines land in the structured `acceptance_choices` Table (the same backing
// the radio buttons read from) — NOT the legacy `custom_choices` Long Text. The
// l4_migration_status is NOT auto-flipped (text-only choices still need min/max
// before ratification — that happens via the full QIP form).
async function sc5v2_openEditChoicesDialog(qipName) {
    let qipDoc;
    try {
        qipDoc = await frappe.db.get_doc('Quality Inspection Parameter', qipName);
    } catch (e) {
        frappe.msgprint({
            title: __('Could not open dialog'),
            message: __('Failed to load QIP "{0}": {1}', [qipName, String(e.message || e)]),
            indicator: 'red',
        });
        return;
    }

    const existing = qipDoc.acceptance_choices || [];
    const existingHtml = (existing.length === 0)
        ? `<i class="text-muted">${__('No Acceptance Choices yet — add the first one below.')}</i>`
        : `<ul style="margin:4px 0 8px 18px; padding-left:0; max-height:220px; overflow-y:auto; font-size:12px; list-style:disc;">${
            existing.map(c => {
                const defaultTag = c.is_default
                    ? ` <span style="color:#1b5e20; font-size:10px;">(${__('default')})</span>` : '';
                const subSpec = c.sub_spec
                    ? ` <span style="color:#6c7680;">(${frappe.utils.escape_html(c.sub_spec)})</span>` : '';
                const hasBounds = (c.min_value != null && c.min_value > 0)
                    || (c.max_value != null && c.max_value > 0);
                const minMax = hasBounds
                    ? ` <span style="color:#6c7680; font-size:11px;">[${c.min_value || 'N/A'}–${c.max_value || 'N/A'}]</span>`
                    : '';
                return `<li>${frappe.utils.escape_html(c.text_label || '(empty)')}${minMax}${subSpec}${defaultTag}</li>`;
            }).join('')
        }</ul>`;

    const qipFormUrl = `/app/quality-inspection-parameter/${encodeURIComponent(qipName)}`;
    const statusBadge = qipDoc.l4_migration_status
        ? `<span style="background:#eceff1; color:#37474f; padding:1px 6px; border-radius:8px; font-size:10px; margin-left:8px;">${frappe.utils.escape_html(qipDoc.l4_migration_status)}</span>`
        : '';
    const helpHtml = `
        <div style="margin-top:10px; padding:8px 12px; background:#f5f6f8; border-radius:6px; font-size:11px; color:#525960;">
            ℹ ${__('Each non-empty line becomes a new Acceptance Choice row with the typed text as label. Min / Max / UOM can be filled later by editing the QIP directly.')}
            <br><a href="${qipFormUrl}" target="_blank" style="color:#1a73e8; font-size:12px;">→ ${__('Open QIP full form')}</a>
        </div>`;

    const d = new frappe.ui.Dialog({
        title: __('Edit Posibles Valores: {0}', [qipName]),
        size: 'large',
        fields: [
            {
                fieldname: 'existing_section', fieldtype: 'HTML',
                options: `
                    <div style="font-weight:600; font-size:12px; color:#525960; margin-bottom:4px;">
                        ${__('Existing Acceptance Choices')} (${existing.length})${statusBadge}
                    </div>
                    ${existingHtml}`,
            },
            { fieldtype: 'Section Break' },
            {
                fieldname: 'new_lines', fieldtype: 'Long Text',
                label: __('Add new choices (one per line)'),
                description: __('Duplicates of existing labels are skipped silently (case-insensitive).'),
            },
            {
                fieldname: 'help_section', fieldtype: 'HTML',
                options: helpHtml,
            },
        ],
        primary_action_label: __('Save & Add to Picker'),
        primary_action: async function (values) {
            const newLines = (values.new_lines || '').trim();
            if (!newLines) {
                d.hide();
                return;
            }
            d.disable_primary_action();
            try {
                const resp = await frappe.call({
                    method: 'amb_w_tds.api.picker.add_acceptance_choices',
                    args: { qip_name: qipName, lines: newLines },
                });
                const m = (resp && resp.message) || {};
                let toast = __('Added {0} choice(s) to {1}', [m.added || 0, qipName]);
                if (m.skipped_duplicates) toast += ' · ' + __('{0} duplicate(s) skipped', [m.skipped_duplicates]);
                if (m.skipped_empty) toast += ' · ' + __('{0} empty line(s) skipped', [m.skipped_empty]);
                frappe.show_alert({
                    message: toast,
                    indicator: (m.added > 0) ? 'green' : 'orange',
                });
                d.hide();
                // Re-render just the picker (don't reload the whole TDS form).
                // renderParameterPicker re-fetches the acceptance_choices_map, so the
                // newly-added rows appear as radio buttons + the badge count updates.
                if (typeof cur_frm !== 'undefined' && cur_frm && cur_frm.doc
                        && cur_frm.doc.doctype === 'TDS Product Specification') {
                    try { await sc5v2_renderParameterPicker(cur_frm); }
                    catch (e) { console.warn('SC5 v2: picker re-render after dialog save failed', e); }
                }
            } catch (err) {
                console.error('SC5 v2: dialog save failed', err);
                frappe.msgprint({
                    title: __('Save Failed'),
                    message: String((err && err.message) || err),
                    indicator: 'red',
                });
                d.enable_primary_action();
            }
        },
    });
    d.show();
}


// ─── Add selected → IQI child table (wraps each row write in try/catch) ───
async function sc5v2_addSelected(frm) {
    const checked = document.querySelectorAll('.sc5v2-qip-cb:checked');
    if (checked.length === 0) {
        frappe.show_alert({ message: __('Select at least one parameter first.'), indicator: 'orange' });
        return;
    }

    // SC5 v2 fix (2026-05-26) — pre-fetch the Quality Inspection Method catalog to guard
    // against bad-data QIPs that store an Item code in custom_method (saw 1 such case:
    // QIP 'Color Visual' had custom_method='0227 ORGANIC INNOVALOE...'). Saving an IQI
    // row with a non-existent Method record fails Frappe's Link validation. The guard
    // below leaves row.custom_method blank when the source value isn't in the catalog —
    // user can fill it in manually after row insert.
    let validMethodSet = null;
    try {
        const methods = await frappe.db.get_list('Quality Inspection Method', { fields: ['name'], limit: 0 });
        validMethodSet = new Set(methods.map(m => m.name));
    } catch (e) {
        console.warn('SC5 v2: could not pre-fetch Method catalog (skipping guard, all assignments will pass through)', e);
    }

    const existing = (frm.doc.item_quality_inspection_parameter || []);
    const existingSpecs = new Set();
    const existingTitles = new Set();
    existing.forEach(r => {
        if (r.custom_is_title_row === 1 && r.specification) existingTitles.add(r.specification);
        else if (r.specification) existingSpecs.add(r.specification);
    });

    // Group selections by L2 for section-header insertion
    // Task #33: also collect the selected L4 acceptance-choice radio per QIP (if any)
    const selections = [];
    let dupeCount = 0;
    checked.forEach(cb => {
        const qipName = cb.dataset.qipName;
        if (existingSpecs.has(qipName)) { dupeCount++; return; }
        const radio = document.querySelector(`.sc5v2-choices-block[data-qip-name="${qipName.replace(/"/g, '\\"')}"] input[type=radio]:checked`);
        const choice = radio ? {
            name: radio.value,
            text_label: radio.dataset.textLabel || '',
            min_value: radio.dataset.minValue !== '' ? parseFloat(radio.dataset.minValue) : null,
            max_value: radio.dataset.maxValue !== '' ? parseFloat(radio.dataset.maxValue) : null,
            target_value: radio.dataset.targetValue !== '' ? parseFloat(radio.dataset.targetValue) : null,
            unit: radio.dataset.unit || '',
            sub_spec: radio.dataset.subSpec || '',
        } : null;
        selections.push({
            qipName,
            paramGroup: cb.dataset.paramGroup,
            l2Key: cb.dataset.l2Key,
            l2Name: cb.dataset.l2Name,
            choice,
        });
    });

    selections.sort((a, b) => a.l2Key.localeCompare(b.l2Key) || a.qipName.localeCompare(b.qipName));

    // Customer derivation (custom_tds_customers preferred, Item.customer fallback)
    let cavCustomers = (frm.doc.custom_tds_customers || []).map(r => r.customer).filter(Boolean);
    if (cavCustomers.length === 0 && frm.doc.product_item) {
        try {
            const r = await frappe.db.get_value('Item', frm.doc.product_item, ['customer']);
            const c = r && r.message && r.message.customer;
            if (c) cavCustomers = [c];
        } catch (e) { console.warn('SC5 v2: customer fallback failed', e); }
    }

    let added = 0, cavCount = 0, headerCount = 0;
    const wroteHeader = new Set();
    const today = frappe.datetime.get_today();

    for (const sel of selections) {
        // Section header (once per L2)
        if (sel.l2Name && !existingTitles.has(sel.l2Name) && !wroteHeader.has(sel.l2Name)) {
            try {
                const hr = frm.add_child('item_quality_inspection_parameter');
                if (hr) {
                    hr.specification = sel.l2Name;
                    hr.parameter_group = sel.l2Name;
                    hr.custom_is_title_row = 1;
                    wroteHeader.add(sel.l2Name);
                    headerCount++;
                }
            } catch (e) { console.warn('SC5 v2: header insert failed for', sel.l2Name, e); }
        }

        try {
            const row = frm.add_child('item_quality_inspection_parameter');
            if (!row) continue;
            row.specification = sel.qipName;
            if (sel.paramGroup) row.parameter_group = sel.paramGroup;

            // Task #33: if user picked an L4 acceptance-choice radio, set the row's
            // acceptance_choice Link + clone min/max from the choice. This precedes
            // CAV / QIP-default lookups so an explicit L4 selection wins.
            if (sel.choice) {
                row.acceptance_choice = sel.choice.name;
                if (sel.choice.text_label) row.value = sel.choice.text_label;
                if (sel.choice.min_value != null && !isNaN(sel.choice.min_value)) row.min_value = sel.choice.min_value;
                if (sel.choice.max_value != null && !isNaN(sel.choice.max_value)) row.max_value = sel.choice.max_value;
                if (sel.choice.unit) row.custom_uom = sel.choice.unit;
                row.numeric = (sel.choice.min_value != null || sel.choice.max_value != null) ? 1 : 0;
            }

            // QIP defaults (still fetched for method/uom fallback even when L4 picked)
            let qipDoc = null;
            try { qipDoc = await frappe.db.get_doc('Quality Inspection Parameter', sel.qipName); }
            catch (e) { console.warn('SC5 v2: QIP doc fetch failed for', sel.qipName, e); }

            // CAV consultation
            let cav = null;
            if (cavCustomers.length > 0) {
                try {
                    const rows = await frappe.db.get_list('Customer Acceptable Value', {
                        filters: { parameter: sel.qipName, customer: ['in', cavCustomers], status: 'Approved', is_active: 1 },
                        fields: ['name', 'customer', 'value_type', 'value_text', 'value_min', 'value_max',
                                 'method', 'unit_of_measurement', 'effective_from', 'effective_to'],
                        order_by: 'effective_from desc', limit: 5,
                    });
                    cav = rows.find(c => (!c.effective_from || c.effective_from <= today)
                                     && (!c.effective_to || c.effective_to >= today));
                } catch (e) { console.warn('SC5 v2: CAV lookup failed for', sel.qipName, e); }
            }

            if (cav) {
                let v = cav.value_text;
                if (!v && cav.value_min != null) {
                    v = cav.value_max != null ? `${cav.value_min} - ${cav.value_max}` : `${cav.value_min}`;
                }
                if (v) row.value = v;
                if (cav.value_min != null) row.min_value = cav.value_min;
                if (cav.value_max != null) row.max_value = cav.value_max;
                if (cav.method) {
                    if (validMethodSet === null || validMethodSet.has(cav.method)) {
                        row.custom_method = cav.method;
                    } else {
                        console.warn(`SC5 v2: CAV "${cav.name}" has stale Method "${cav.method}" — leaving row.custom_method blank`);
                    }
                }
                if (cav.unit_of_measurement) row.custom_uom = cav.unit_of_measurement;
                else if (qipDoc && qipDoc.custom_unit) row.custom_uom = qipDoc.custom_unit;
                cavCount++;
                added++;
                continue;
            }

            // Standard FoxPro flow — skip value/min/max set when L4 already populated them
            // (sel.choice is the user's explicit picker selection; don't overwrite).
            if (qipDoc) {
                if (!sel.choice) {
                    if (qipDoc.custom_is_numeric) {
                        row.numeric = 1;
                        if (qipDoc.custom_value_min != null) row.min_value = qipDoc.custom_value_min;
                        if (qipDoc.custom_value_max != null) row.max_value = qipDoc.custom_value_max;
                    } else if (qipDoc.custom_value_text) {
                        row.value = qipDoc.custom_value_text;
                        const formula = sc5v2_parseValueFormula(qipDoc.custom_value_text);
                        if (formula) {
                            if (formula.min != null) row.min_value = formula.min;
                            if (formula.max != null) row.max_value = formula.max;
                            if (formula.isNumeric) row.numeric = 1;
                        }
                    } else if (qipDoc.custom_choices) {
                        const first = qipDoc.custom_choices.split('\n').map(s => s.trim()).filter(Boolean)[0];
                        if (first) row.value = first;
                    }
                }
                if (qipDoc.custom_method) {
                    if (validMethodSet === null || validMethodSet.has(qipDoc.custom_method)) {
                        row.custom_method = qipDoc.custom_method;
                    } else {
                        console.warn(`SC5 v2: QIP "${sel.qipName}" has stale Method "${qipDoc.custom_method}" — leaving row.custom_method blank`);
                    }
                }
                if (qipDoc.custom_unit && !row.custom_uom) row.custom_uom = qipDoc.custom_unit;
            }
            added++;
        } catch (e) {
            console.warn('SC5 v2: row add failed for', sel.qipName, e);
        }
    }

    frm.refresh_field('item_quality_inspection_parameter');

    document.querySelectorAll('#phase-1c-tree-picker input[type=checkbox]').forEach(cb => { cb.checked = false; cb.indeterminate = false; });
    sc5v2_updateSummary();

    let msg = __('Added {0} parameter(s)', [added]);
    if (headerCount > 0) msg += __(' · {0} section header(s)', [headerCount]);
    if (dupeCount > 0) msg += __(' · {0} duplicate(s) skipped', [dupeCount]);
    if (cavCount > 0) msg += __(' · {0} from CAV', [cavCount]);
    frappe.show_alert({ message: msg, indicator: added > 0 ? 'green' : 'orange' });
}


// ─── Formula parser (preserved from V14.3.3) ───
function sc5v2_parseValueFormula(valueStr) {
    if (!valueStr) return null;
    const s = String(valueStr).trim();
    const rangeMatch = s.match(/^\s*([\-+]?\d+(?:[\.,]\d+)?)\s*[-–—]\s*([\-+]?\d+(?:[\.,]\d+)?)/);
    if (rangeMatch) {
        const lo = parseFloat(rangeMatch[1].replace(',', '.'));
        const hi = parseFloat(rangeMatch[2].replace(',', '.'));
        if (!isNaN(lo) && !isNaN(hi)) return { min: lo, max: hi, isNumeric: true };
    }
    const stripped = s.replace(/\s*(%|PPM|PPB|CFU\/?[A-Z]+|MG\/[A-Z]+|G\/[A-Z]+|ML)\b.*$/i, '').trim();
    const nmtMatch = stripped.match(/^\s*(?:NMT|LE|<=?|≤)\s*([\-+]?\d+(?:[\.,]\d+)?)/i);
    if (nmtMatch) {
        const v = parseFloat(nmtMatch[1].replace(',', '.'));
        if (!isNaN(v)) return { min: 0, max: v, isNumeric: true };
    }
    const nltMatch = stripped.match(/^\s*(?:NLT|GE|>=?|≥)\s*([\-+]?\d+(?:[\.,]\d+)?)/i);
    if (nltMatch) {
        const v = parseFloat(nltMatch[1].replace(',', '.'));
        if (!isNaN(v)) return { min: v, max: null, isNumeric: true };
    }
    return null;
}
