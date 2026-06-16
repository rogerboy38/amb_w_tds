/**
 * coa_common.js — shared COA form logic for COA AMB (signed certificate)
 *                 and COA AMB2 (inspectors' working notebook).
 * =====================================================================
 * T137: read-only "Audit Compliance" report, in APP CODE (loaded via
 *       doctype_js for both doctypes), not a DB Client Script.
 * T140: RESTORED live per-row validation + whole-row painting, recovered
 *       verbatim-in-logic from the decommissioned `load_tds_parameters_1`
 *       Client Script (incl. the T95 NEGATIVE/NONE precedence fix and the
 *       grid_row.$row null-check). Also adds the untagged section-divider
 *       sentinel so "Specification" header rows never score as tests.
 *
 * Single source of truth. Survives `bench migrate` with/without
 * --skip-fixtures because it is code, not a fixture.
 *
 * Correct fields (COA Quality Test Parameter meta):
 *   parameter_name (Link), custom_is_title_row (Check), result, status,
 *   value / specification, numeric, min_value, max_value, test_method.
 *
 * The doctype controllers (coa_amb.js / coa_amb2.js) keep their TDS load +
 * buttons; their child `result` / `custom_is_title_row` handlers DELEGATE
 * here via amb_coa.validate_and_paint (so the logic lives in one place).
 */
window.amb_coa = window.amb_coa || {};

/* ---- header detection: explicit flag OR untagged section divider -------- *
 * Untagged dividers (e.g. "Physicochemical") store acceptance == "Specification"
 * (the placeholder). They must never be scored as tests. Mirrors the server
 * sentinel added in the COA controllers.                                     */
amb_coa.is_header = function (row) {
    if (row.custom_is_title_row) return true;
    var acc = (row.value || row.specification || '').toString().trim().toLowerCase();
    return acc === 'specification';
};

/* ---- canonical per-row status -----------------------------------------
 * Restored from load_tds_parameters_1 (T95). Order matters:
 *   header -> Pending(no result) -> NEGATIVE/NONE match -> explicit PASS ->
 *   NEGATIVE/NONE criteria -> numeric range -> exact text match -> default Pass. */
amb_coa.compute_status = function (row) {
    if (amb_coa.is_header(row)) return 'Title';
    if (!row.result && row.result !== 0) return 'Pending';

    var acc = (row.value || row.specification || '').toString();
    var accU = acc.toUpperCase();
    var res = row.result.toString().toUpperCase().trim();

    // T95: NEGATIVE/NONE criteria with a matching result ALWAYS Pass — placed
    // before the numeric branch, which mis-fires when min/max=0 are inherited
    // defaults on what are really text-only criteria rows.
    var neg = accU.indexOf('NEGATIVE') !== -1 &&
        ['NEGATIVE', 'NEG', 'NONE', '0', 'N/A'].indexOf(res) !== -1;
    var none = accU.indexOf('NONE') !== -1 && accU.indexOf('NEGATIVE') === -1 &&
        ['NONE', '0', 'N/A'].indexOf(res) !== -1;
    if (neg || none) return 'Pass';

    if (res === 'PASS') return 'Pass';
    if (accU.indexOf('NEGATIVE') !== -1)
        return ['NEGATIVE', 'NEG', 'NONE', '0'].indexOf(res) !== -1 ? 'Pass' : 'Fail';
    if (accU.indexOf('NONE') !== -1)
        return ['NONE', '0'].indexOf(res) !== -1 ? 'Pass' : 'Fail';

    var hasMin = row.min_value !== null && row.min_value !== undefined && row.min_value !== '';
    var hasMax = row.max_value !== null && row.max_value !== undefined && row.max_value !== '';
    if (row.numeric || hasMin || hasMax) {
        var v = parseFloat(res);
        if (isNaN(v)) return 'Fail';
        var lo = hasMin ? parseFloat(row.min_value) : -Infinity;
        var hi = hasMax ? parseFloat(row.max_value) : Infinity;
        return (v >= lo && v <= hi) ? 'Pass' : 'Fail';
    }
    if (acc.trim() !== '') return (res === accU.trim()) ? 'Pass' : 'Fail';
    return 'Pass';
};

// Back-compat alias (older callers used decide_status; returns TITLE upper-case).
amb_coa.decide_status = function (row) {
    var s = amb_coa.compute_status(row);
    return s === 'Title' ? 'TITLE' : s;
};

/* ---- whole-row painting (restored .result-pass / .result-fail / .result-na) */
amb_coa.paint_row = function (frm, row) {
    try {
        var fld = frm.fields_dict.coa_quality_test_parameter;
        var grid = fld && fld.grid;
        if (!grid || !grid.grid_rows_by_docname) return;
        var gr = grid.grid_rows_by_docname[row.name];
        if (!gr || !gr.$row) return;           // null-check (the old TypeError fix)

        var s = (row.status || '').toString().toUpperCase();
        var color = s === 'FAIL' ? '#ffe6e6'
                  : s === 'PASS' ? '#e6f7e6'
                  : s === 'TITLE' ? '#eef2f7'
                  : (s === 'N/A' || s === 'NA') ? '#f5f5f5'
                  : '';                          // Pending -> clear
        gr.$row.css('background-color', color);
        gr.$row.find('.grid-static-col, .field-area, .grid-row-col, .editable-row')
               .css('background-color', color);
    } catch (e) {
        console.error('COA paint_row error:', e);
    }
};

amb_coa.paint_all = function (frm) {
    (frm.doc.coa_quality_test_parameter || []).forEach(function (row) {
        amb_coa.paint_row(frm, row);
    });
};

/* ---- live per-row validation (called by each controller's child handler) -- */
amb_coa.validate_and_paint = function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var st = amb_coa.compute_status(row);
    if (row.status !== st) {
        frappe.model.set_value(cdt, cdn, 'status', st).then(function () {
            amb_coa.paint_row(frm, row);
        });
    } else {
        amb_coa.paint_row(frm, row);
    }
};

/* ---- read-only Audit Compliance report (T137) — now header-aware --------- */
amb_coa._card = function (bg, n, label) {
    return '<div style="flex:1;background:' + bg + ';border-radius:8px;padding:12px;text-align:center;">' +
           '<div style="font-size:28px;font-weight:bold;">' + n + '</div><div>' + label + '</div></div>';
};

amb_coa.audit_report = function (frm) {
    var rows = frm.doc.coa_quality_test_parameter || [];
    if (!rows.length) { frappe.msgprint(__('No test parameters to audit')); return; }

    var a = { total: 0, passed: 0, failed: 0, pending: 0, na: 0, title: 0, details: [] };
    rows.forEach(function (p, i) {
        var pname = p.parameter_name || p.parameter_group || '';
        if (amb_coa.is_header(p)) {                       // section header — skip
            a.title++;
            a.details.push({ row: i + 1, parameter: pname, status: 'TITLE', message: 'Section header' });
            return;
        }
        a.total++;
        var acceptance = (p.value || p.specification || '').toString();
        // Prefer the authoritative stored status; fall back to a computed decision.
        var st = (p.status || '').toString().trim();
        if (!st || st.toLowerCase() === 'pending') {
            var d = amb_coa.compute_status(p);
            st = (d === 'Title') ? 'Pending' : d;
        }
        var norm = st.toUpperCase();
        if (norm === 'PASS') {
            a.passed++;
            a.details.push({ row: i + 1, parameter: pname, result: p.result, acceptance, status: 'PASS', message: '✅ Matches criteria' });
        } else if (norm === 'FAIL') {
            a.failed++;
            a.details.push({ row: i + 1, parameter: pname, result: p.result, acceptance, status: 'FAIL', message: '❌ Expected: "' + acceptance + '", Got: "' + (p.result || '') + '"' });
        } else if (norm === 'N/A' || norm === 'NA') {
            a.na++;
            a.details.push({ row: i + 1, parameter: pname, result: p.result, acceptance, status: 'N/A', message: 'N/A' });
        } else {
            a.pending++;
            a.details.push({ row: i + 1, parameter: pname, result: p.result || '', acceptance, status: 'PENDING', message: 'No result entered' });
        }
    });

    var pct = a.total ? (a.passed / a.total) * 100 : 0;
    var overall = a.failed ? 'FAIL' : (a.pending ? 'PARTIAL' : (a.passed ? 'PASS' : 'PENDING'));

    var m = '<div style="margin:10px 0;"><h3 style="text-align:center;">📋 COA Compliance Audit Report</h3><hr>';
    m += '<div style="display:flex; gap:15px; margin-bottom:16px;">';
    m += amb_coa._card('#d4edda', a.passed, '✅ PASS') + amb_coa._card('#f8d7da', a.failed, '❌ FAIL') + amb_coa._card('#fff3cd', a.pending, '⏳ PENDING');
    m += '</div>';
    m += '<div style="background:#e9ecef;border-radius:8px;padding:10px;margin-bottom:16px;text-align:center;">' +
         '<strong>📊 Pass:</strong> <span style="font-size:20px;color:#28a745;">' + pct.toFixed(2) + '%</span> &nbsp;|&nbsp; ' +
         'Title rows: ' + a.title + ' &nbsp;|&nbsp; N/A: ' + a.na + '</div>';
    m += '<div style="max-height:400px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;"><table style="width:100%;border-collapse:collapse;font-size:11px;">';
    m += '<thead><tr style="background:#2c3e50;color:#fff;position:sticky;top:0;">' +
         '<th style="padding:8px;">#</th><th style="padding:8px;">Parameter</th><th style="padding:8px;">Result</th>' +
         '<th style="padding:8px;">Acceptance</th><th style="padding:8px;">Status</th><th style="padding:8px;">Message</th></tr></thead><tbody>';
    a.details.forEach(function (d) {
        var bg = d.status === 'PASS' ? '#d4edda' : (d.status === 'FAIL' ? '#f8d7da' : (d.status === 'PENDING' ? '#fff3cd' : '#e9ecef'));
        var lbl = d.status === 'PASS' ? '✅ PASS' : (d.status === 'FAIL' ? '❌ FAIL' : (d.status === 'PENDING' ? '⏳ PENDING' : (d.status === 'TITLE' ? '📋 TITLE' : 'N/A')));
        m += '<tr style="background:' + bg + ';"><td style="padding:6px;text-align:center;">' + d.row + '</td>' +
             '<td style="padding:6px;">' + (d.parameter || '—') + '</td>' +
             '<td style="padding:6px;">' + (d.result || '—') + '</td>' +
             '<td style="padding:6px;">' + (d.acceptance || '—') + '</td>' +
             '<td style="padding:6px;text-align:center;font-weight:bold;">' + lbl + '</td>' +
             '<td style="padding:6px;">' + (d.message || '—') + '</td></tr>';
    });
    m += '</tbody></table></div></div>';

    frappe.msgprint({
        title: __('COA Compliance Audit'),
        message: m,
        indicator: overall === 'PASS' ? 'green' : (overall === 'PARTIAL' ? 'orange' : 'red'),
        wide: true
    });
};

/* ---- parent hooks on BOTH doctypes (additive; Frappe merges form.on) ----- */
['COA AMB', 'COA AMB2'].forEach(function (dt) {
    frappe.ui.form.on(dt, {
        refresh: function (frm) {
            amb_coa.paint_all(frm);
            if (frm.is_new()) return;
            frm.add_custom_button(__('Audit Compliance'), function () {
                amb_coa.audit_report(frm);
            }, __('Actions'));
        },
        coa_quality_test_parameter_on_form_rendered: function (frm) {
            amb_coa.paint_all(frm);
        }
    });
});
