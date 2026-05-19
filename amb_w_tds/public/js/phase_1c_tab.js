// Phase 1C-B — Parameter Selection tab JS for TDS Product Specification
//
// V14.3.0 — promoted post Phase 1C-A prod-green (2026-05-19T02:30Z comet 5/5 GREEN ratified).
// Doctype-driven, 3-level hierarchy (Family → Sub-group → QIP) with singleton + unassigned handling.
//
// Architectural rules (Hugh + Alicia confirmed):
//   1. ZERO hardcoded choice strings. All Posibles Valores come from
//      frappe.db.get_doc('Quality Inspection Parameter', name).custom_choices (split by '\n').
//   2. ZERO hardcoded family/group structure. Families are auto-detected as common
//      prefixes among parameter_group values (>=2 distinct groups share a prefix → family).
//   3. Singleton sub-groups (count=1) render inline at family level (no L3 header per comet).
//   4. NULL/empty parameter_group → "Needs Categorization (N)" section at end.
//
// Composes with existing tds_product_specification.js — registered via doctype_js hook in hooks.py.
//
// References:
//   ADR-001 — Parameter Selection tab
//   ADR-002 — depth-4 data-driven L2 catalog
//   Comet 2026-05-19T01:21Z prod QIP audit (90 QIPs / 41 groups / 13 unassigned / 22 singletons)
//   Cowork-ops 2026-05-19T02:34Z — V14.3.0 promotion authorization
//   Phase 1C-A migration — populates QIP custom_choices, custom_is_numeric, parameter_group


frappe.ui.form.on('TDS Product Specification', {
    refresh: async function(frm) {
        const pickerEl = document.getElementById('phase-1c-tree-picker');
        const actionEl = document.getElementById('phase-1c-action-bar');
        if (!pickerEl || !actionEl) {
            // HTML fields not on this doctype yet (Phase 1C-B deploy directive will add them)
            // — silent no-op. Don't render anything. When deploy schema lands, this becomes active.
            return;
        }

        if (frm.is_new() || !frm.doc.product_item) {
            pickerEl.innerHTML = `<i class="text-muted">${__('Save the document and set a Product Item to enable Parameter Selection.')}</i>`;
            actionEl.innerHTML = '';
            return;
        }

        await renderParameterPicker(frm);
        renderActionBar(frm);
    }
});

// ---------------------------------------------------------------------------
// Family auto-detection (data-driven; no hardcoded family names)
// ---------------------------------------------------------------------------

function detectFamilies(parameterGroupNames) {
    // Generate all prefixes of length 1..N words for each group name.
    // A prefix "qualifies" as a family if it appears as a prefix in >=2 distinct group names.
    // Pick the LONGEST qualifying prefix per group → that's the group's family.
    //
    // Examples on prod data:
    //   "Physicochemical LQD"          → family "Physicochemical LQD"     sub-group ""
    //   "Physicochemical LQD pH"       → family "Physicochemical LQD"     sub-group "pH"
    //   "Other Analysis LQD"           → family "Other Analysis LQD"      sub-group ""
    //   "Other Analysis LQD Preservatives" → family "Other Analysis LQD"  sub-group "Preservatives"

    const prefixOccurrences = {};  // prefix → Set of group names it prefixes
    for (const gname of parameterGroupNames) {
        const parts = gname.split(/\s+/);
        for (let n = 1; n <= parts.length; n++) {
            const prefix = parts.slice(0, n).join(' ');
            if (!prefixOccurrences[prefix]) prefixOccurrences[prefix] = new Set();
            prefixOccurrences[prefix].add(gname);
        }
    }

    // A prefix qualifies as family if it's prefix of >=2 distinct group names.
    const qualifiedFamilies = new Set();
    for (const [prefix, groupSet] of Object.entries(prefixOccurrences)) {
        if (groupSet.size >= 2) qualifiedFamilies.add(prefix);
    }

    // For each group, pick the LONGEST qualifying prefix that prefixes it.
    const groupToFamily = {};
    for (const gname of parameterGroupNames) {
        const parts = gname.split(/\s+/);
        let best = null;  // longest qualifying prefix
        for (let n = parts.length; n >= 1; n--) {
            const candidate = parts.slice(0, n).join(' ');
            if (qualifiedFamilies.has(candidate)) {
                best = candidate;
                break;
            }
        }
        groupToFamily[gname] = best || '__OTHER__';  // unmatched → "Other"
    }
    return groupToFamily;
}

function deriveSubgroup(groupName, familyName) {
    // Sub-group = group name with family prefix removed.
    // If group name == family, sub-group is "" (general bucket within family).
    if (groupName === familyName) return '';
    if (groupName.startsWith(familyName + ' ')) {
        return groupName.slice(familyName.length + 1);
    }
    return groupName;  // unmatched fallback
}

// ---------------------------------------------------------------------------
// Tree picker rendering
// ---------------------------------------------------------------------------

async function renderParameterPicker(frm) {
    // Fetch ALL QIPs (including unassigned per comet audit — they're a curation queue, not orphans).
    const allQips = await frappe.db.get_list('Quality Inspection Parameter', {
        // NOTE: QIP has `custom_specification` (Link → Quality Inspection Method) as its method field.
        // IQI child row has `custom_method` (Link → same Method). The transfer is QIP.custom_specification → IQI.custom_method.
        fields: ['name', 'parameter', 'parameter_group', 'custom_choices', 'custom_is_numeric', 'custom_specification', 'custom_unit'],
        order_by: 'parameter_group asc, parameter asc',
        limit: 0
    });

    // Partition: assigned vs unassigned
    const assigned = [];
    const unassigned = [];
    for (const q of allQips) {
        if (!q.parameter_group || q.parameter_group === '') {
            unassigned.push(q);
        } else {
            assigned.push(q);
        }
    }

    // Group assigned QIPs by parameter_group
    const qipsByGroup = {};
    for (const q of assigned) {
        if (!qipsByGroup[q.parameter_group]) qipsByGroup[q.parameter_group] = [];
        qipsByGroup[q.parameter_group].push(q);
    }
    const allGroupNames = Object.keys(qipsByGroup);

    // Auto-detect families
    const groupToFamily = detectFamilies(allGroupNames);

    // Reorganize: family → { '<subgroup>': [qips], ... }
    // Sub-group '' is the "general" bucket (parameter_group exactly equals family name).
    const familyTree = {};
    for (const gname of allGroupNames) {
        const family = groupToFamily[gname];
        const subgroup = deriveSubgroup(gname, family);
        if (!familyTree[family]) familyTree[family] = {};
        if (!familyTree[family][subgroup]) familyTree[family][subgroup] = { groupName: gname, qips: [] };
        familyTree[family][subgroup].qips = qipsByGroup[gname];
    }

    // Counts for master controls
    const familyCount = Object.keys(familyTree).filter(f => f !== '__OTHER__').length
                       + (familyTree['__OTHER__'] ? 1 : 0)
                       + (unassigned.length > 0 ? 1 : 0);

    let html = renderMasterControls(familyCount, allQips.length, unassigned.length);

    // Render canonical families (sorted), then __OTHER__, then unassigned bucket last
    const sortedFamilies = Object.keys(familyTree)
        .filter(f => f !== '__OTHER__')
        .sort();
    for (const family of sortedFamilies) {
        html += renderFamily(family, familyTree[family]);
    }
    if (familyTree['__OTHER__']) {
        html += renderFamily(__('Other'), familyTree['__OTHER__'], { otherBucket: true });
    }
    if (unassigned.length > 0) {
        html += renderUnassignedBucket(unassigned);
    }

    document.getElementById('phase-1c-tree-picker').innerHTML = html;
    attachEventHandlers(frm);
}

function renderMasterControls(familyCount, qipCount, unassignedCount) {
    const unassignedSpan = unassignedCount > 0
        ? ` · <span class="phase-1c-summary-warn">${unassignedCount} ${__('need categorization')}</span>`
        : '';
    return `
        <div class="phase-1c-master-controls">
            <button class="btn btn-sm btn-default" id="phase-1c-expand-all">${__('Expand All')}</button>
            <button class="btn btn-sm btn-default" id="phase-1c-collapse-all">${__('Collapse All')}</button>
            <span class="phase-1c-summary text-muted">
                ${familyCount} ${__('families')} · ${qipCount} ${__('parameters')}${unassignedSpan}
            </span>
        </div>
    `;
}

function renderFamily(familyName, subgroups, opts) {
    opts = opts || {};
    const subgroupKeys = Object.keys(subgroups);

    // Separate sub-groups: "" (general) | singletons (count=1) | multi (count>=2)
    const general = subgroups[''] || null;
    const singletons = [];
    const multi = [];
    for (const sk of subgroupKeys) {
        if (sk === '') continue;
        const sg = subgroups[sk];
        if (sg.qips.length === 1) singletons.push(sg);
        else multi.push(sg);
    }
    multi.sort((a, b) => a.groupName.localeCompare(b.groupName));
    singletons.sort((a, b) => a.qips[0].parameter.localeCompare(b.qips[0].parameter));

    // Count total QIPs in this family
    let totalQips = 0;
    for (const sk of subgroupKeys) totalQips += subgroups[sk].qips.length;

    let body = '';

    // 1. General bucket (parameter_group == family name exactly)
    if (general) {
        body += general.qips.map(q => renderLeaf(q, general.groupName)).join('');
    }

    // 2. Multi-QIP sub-groups (collapsible L3 sub-sections)
    for (const sg of multi) {
        body += renderSubgroup(sg);
    }

    // 3. Singletons — rendered inline at family level (no L3 header per comet adjustment 2)
    if (singletons.length > 0) {
        const singletonLeaves = singletons.map(sg => renderLeaf(sg.qips[0], sg.groupName, { singleton: true })).join('');
        body += `
            <div class="phase-1c-singletons-block">
                <div class="phase-1c-singletons-label text-muted">${__('Other parameters')} (${singletons.length}):</div>
                ${singletonLeaves}
            </div>
        `;
    }

    const familyClass = opts.otherBucket ? 'phase-1c-family phase-1c-family-other' : 'phase-1c-family';
    return `
        <div class="${familyClass}" data-family="${escapeHtml(familyName)}">
            <div class="phase-1c-family-header">
                <span class="phase-1c-chevron">▶</span>
                <input type="checkbox" class="phase-1c-family-toggle" />
                <span class="phase-1c-family-name">${escapeHtml(familyName)}</span>
                <span class="phase-1c-family-count">${totalQips} ${__('params')}</span>
            </div>
            <div class="phase-1c-family-body" style="display: none;">
                ${body}
            </div>
        </div>
    `;
}

function renderSubgroup(sg) {
    // L3 sub-group section (collapsible) — only for sub-groups with >=2 QIPs.
    const leaves = sg.qips.map(q => renderLeaf(q, sg.groupName)).join('');
    const subgroupLabel = deriveSubgroup(sg.groupName, sg.groupName.split(/\s+/).slice(0, -1).join(' '))
                          || sg.groupName;
    // Use the FULL group name as the visible sub-header for clarity (e.g. "Physicochemical LQD pH")
    return `
        <div class="phase-1c-subgroup" data-subgroup="${escapeHtml(sg.groupName)}">
            <div class="phase-1c-subgroup-header">
                <span class="phase-1c-chevron-sub">▶</span>
                <input type="checkbox" class="phase-1c-subgroup-toggle" />
                <span class="phase-1c-subgroup-name">${escapeHtml(sg.groupName)}</span>
                <span class="phase-1c-subgroup-count">${sg.qips.length}</span>
            </div>
            <div class="phase-1c-subgroup-leaves" style="display: none;">
                ${leaves}
            </div>
        </div>
    `;
}

function renderUnassignedBucket(unassignedQips) {
    // Per comet adjustment 3: explicit "Needs Categorization (N)" section at end.
    // Dashed border + secondary color to signal Alicia attention. Items are pickable
    // (they're still valid QIPs), just visually distinct.
    const leaves = unassignedQips.map(q => renderLeaf(q, '__UNASSIGNED__')).join('');
    return `
        <div class="phase-1c-family phase-1c-family-unassigned" data-family="__UNASSIGNED__">
            <div class="phase-1c-family-header phase-1c-family-header-unassigned">
                <span class="phase-1c-chevron">▶</span>
                <input type="checkbox" class="phase-1c-family-toggle" />
                <span class="phase-1c-family-name">${__('Needs Categorization')}</span>
                <span class="phase-1c-family-count">${unassignedQips.length}</span>
                <span class="phase-1c-needs-attention-badge">${__('Alicia review')}</span>
            </div>
            <div class="phase-1c-family-body" style="display: none;">
                ${leaves}
            </div>
        </div>
    `;
}

function renderLeaf(qip, groupName, opts) {
    opts = opts || {};
    const choiceCount = qip.custom_choices ? qip.custom_choices.split('\n').filter(s => s.trim()).length : 0;
    const badge = choiceCount > 0
        ? `<span class="phase-1c-badge phase-1c-badge-choices">${choiceCount} ${__('choices')}</span>`
        : (qip.custom_is_numeric
            ? `<span class="phase-1c-badge phase-1c-badge-numeric">${__('numeric')}</span>`
            : `<span class="phase-1c-badge phase-1c-badge-text">${__('text')}</span>`);
    const escapedName = escapeHtml(qip.parameter);
    // Show full group name as subscript on singletons + unassigned for context (since no sub-group header)
    const contextTag = (opts.singleton || groupName === '__UNASSIGNED__')
        ? `<span class="phase-1c-leaf-context text-muted">${escapeHtml(groupName === '__UNASSIGNED__' ? __('(no group)') : groupName)}</span>`
        : '';
    return `
        <label class="phase-1c-leaf">
            <input type="checkbox" class="phase-1c-leaf-cb"
                   data-qip-name="${escapeHtml(qip.name)}"
                   data-param-group="${escapeHtml(groupName === '__UNASSIGNED__' ? '' : groupName)}" />
            <span class="phase-1c-leaf-name">${escapedName}</span>
            ${badge}
            ${contextTag}
        </label>
    `;
}

function renderActionBar(frm) {
    document.getElementById('phase-1c-action-bar').innerHTML = `
        <button class="btn btn-primary" id="phase-1c-add-selected">
            ${__('+ Add Selected Parameters')}
        </button>
        <button class="btn btn-default" id="phase-1c-clear-selections">
            ${__('Clear Selections')}
        </button>
        <span class="phase-1c-selection-summary text-muted"></span>
    `;
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

function attachEventHandlers(frm) {
    // Family header expand/collapse
    document.querySelectorAll('.phase-1c-family-header').forEach(header => {
        header.addEventListener('click', function(e) {
            if (e.target.tagName === 'INPUT') return;
            const family = this.closest('.phase-1c-family');
            const body = family.querySelector('.phase-1c-family-body');
            const chevron = family.querySelector('.phase-1c-chevron');
            const isOpen = body.style.display !== 'none';
            body.style.display = isOpen ? 'none' : 'block';
            chevron.textContent = isOpen ? '▶' : '▼';
        });
    });

    // Sub-group header expand/collapse
    document.querySelectorAll('.phase-1c-subgroup-header').forEach(header => {
        header.addEventListener('click', function(e) {
            if (e.target.tagName === 'INPUT') return;
            e.stopPropagation();
            const sg = this.closest('.phase-1c-subgroup');
            const leaves = sg.querySelector('.phase-1c-subgroup-leaves');
            const chevron = sg.querySelector('.phase-1c-chevron-sub');
            const isOpen = leaves.style.display !== 'none';
            leaves.style.display = isOpen ? 'none' : 'block';
            chevron.textContent = isOpen ? '▶' : '▼';
        });
    });

    // Family-level checkbox toggles ALL leaves in the family (including sub-groups + singletons)
    document.querySelectorAll('.phase-1c-family-toggle').forEach(cb => {
        cb.addEventListener('click', function(e) {
            e.stopPropagation();
            const family = this.closest('.phase-1c-family');
            const leafCheckboxes = family.querySelectorAll('.phase-1c-leaf-cb');
            leafCheckboxes.forEach(leaf => leaf.checked = this.checked);
            // Also sync sub-group toggles within
            family.querySelectorAll('.phase-1c-subgroup-toggle').forEach(sgt => sgt.checked = this.checked);
            updateSelectionSummary();
        });
    });

    // Sub-group-level checkbox toggles all leaves in the sub-group
    document.querySelectorAll('.phase-1c-subgroup-toggle').forEach(cb => {
        cb.addEventListener('click', function(e) {
            e.stopPropagation();
            const sg = this.closest('.phase-1c-subgroup');
            const leafCheckboxes = sg.querySelectorAll('.phase-1c-leaf-cb');
            leafCheckboxes.forEach(leaf => leaf.checked = this.checked);
            updateSelectionSummary();
        });
    });

    // Leaf-level checkbox updates selection summary
    document.querySelectorAll('.phase-1c-leaf-cb').forEach(cb => {
        cb.addEventListener('change', updateSelectionSummary);
    });

    // Expand all / Collapse all (operates on both family bodies + sub-group leaves)
    const expandAll = document.getElementById('phase-1c-expand-all');
    if (expandAll) {
        expandAll.addEventListener('click', () => {
            document.querySelectorAll('.phase-1c-family-body, .phase-1c-subgroup-leaves')
                .forEach(el => el.style.display = 'block');
            document.querySelectorAll('.phase-1c-chevron, .phase-1c-chevron-sub')
                .forEach(el => el.textContent = '▼');
        });
    }
    const collapseAll = document.getElementById('phase-1c-collapse-all');
    if (collapseAll) {
        collapseAll.addEventListener('click', () => {
            document.querySelectorAll('.phase-1c-family-body, .phase-1c-subgroup-leaves')
                .forEach(el => el.style.display = 'none');
            document.querySelectorAll('.phase-1c-chevron, .phase-1c-chevron-sub')
                .forEach(el => el.textContent = '▶');
        });
    }

    // Add Selected
    const addBtn = document.getElementById('phase-1c-add-selected');
    if (addBtn) {
        addBtn.addEventListener('click', () => addSelectedParameters(frm));
    }
    // Clear selections
    const clearBtn = document.getElementById('phase-1c-clear-selections');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            document.querySelectorAll('#phase-1c-tree-picker input[type=checkbox]').forEach(cb => cb.checked = false);
            updateSelectionSummary();
        });
    }
}

function updateSelectionSummary() {
    const checked = document.querySelectorAll('.phase-1c-leaf-cb:checked').length;
    const summary = document.querySelector('.phase-1c-selection-summary');
    if (summary) {
        summary.textContent = checked > 0
            ? __(`${checked} parameter(s) selected`)
            : '';
    }
}

// ---------------------------------------------------------------------------
// Add Selected Parameters — bulk-insert with dedupe
// ---------------------------------------------------------------------------

async function addSelectedParameters(frm) {
    const checked = document.querySelectorAll('.phase-1c-leaf-cb:checked');
    if (checked.length === 0) {
        frappe.show_alert({
            message: __('Select at least one parameter first.'),
            indicator: 'orange'
        });
        return;
    }

    // Group selections by parameter_group (the value stored on data-param-group,
    // which is the FULL parameter_group string — empty for unassigned QIPs).
    const selectionsByGroup = {};
    checked.forEach(cb => {
        const groupName = cb.dataset.paramGroup || '';  // '' for unassigned
        const qipName = cb.dataset.qipName;
        if (!selectionsByGroup[groupName]) selectionsByGroup[groupName] = [];
        selectionsByGroup[groupName].push(qipName);
    });

    let added = 0;
    let skipped = 0;
    const sortedGroups = Object.keys(selectionsByGroup).sort();

    for (const groupName of sortedGroups) {
        // Title row insertion — skip for unassigned (empty group name has no title)
        if (groupName !== '') {
            const existingRows = frm.doc.item_quality_inspection_parameter || [];
            const existingTitle = existingRows.find(
                r => r.parameter_group === groupName && r.custom_is_title_row === 1
            );
            if (!existingTitle) {
                const titleRow = frm.add_child('item_quality_inspection_parameter');
                titleRow.parameter_group = groupName;
                titleRow.custom_is_title_row = 1;
                titleRow.value = '';
            }
        }

        for (const qipName of selectionsByGroup[groupName]) {
            // Dedupe per (parameter_group, specification)
            const duplicate = (frm.doc.item_quality_inspection_parameter || []).find(
                r => (r.parameter_group || '') === groupName
                  && r.specification === qipName
                  && r.custom_is_title_row !== 1
            );
            if (duplicate) {
                skipped++;
                continue;
            }

            const row = frm.add_child('item_quality_inspection_parameter');
            row.specification = qipName;
            if (groupName !== '') row.parameter_group = groupName;
            row.custom_is_title_row = 0;

            // Fetch QIP defaults from doctype-driven source (NO hardcoded choices)
            try {
                const qipDoc = await frappe.db.get_doc('Quality Inspection Parameter', qipName);
                if (qipDoc.custom_is_numeric) {
                    row.numeric = 1;
                }
                // QIP's method lives on `custom_specification` (Link → Quality Inspection Method).
                // IQI child row's method field is `custom_method` (also Link → Method) — value transfers as the linked name.
                if (qipDoc.custom_specification) row.custom_method = qipDoc.custom_specification;
                if (qipDoc.custom_unit) row.custom_uom = qipDoc.custom_unit;
            } catch (err) {
                console.warn(`Phase 1C-B: could not fetch QIP defaults for ${qipName}:`, err);
            }

            added++;
        }
    }

    frm.refresh_field('item_quality_inspection_parameter');

    document.querySelectorAll('#phase-1c-tree-picker input[type=checkbox]').forEach(cb => cb.checked = false);
    updateSelectionSummary();

    frappe.show_alert({
        message: __(`Added ${added} parameter(s); ${skipped} duplicate(s) skipped.`),
        indicator: 'green'
    });
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ---------------------------------------------------------------------------
// Print view handling (directive §1.3) — deferred to Print Format customization at deploy.
// ---------------------------------------------------------------------------
