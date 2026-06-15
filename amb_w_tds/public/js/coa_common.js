/**
 * coa_common.js — shared COA audit helper for COA AMB (signed certificate)
 *                 and COA AMB2 (inspectors' working notebook).
 * =====================================================================
 * T137 consolidation (2026-06-15). Single source of truth for the
 * "Audit Compliance" report, in APP CODE (loaded via doctype_js for both
 * doctypes) — NOT a DB Client Script. Survives `bench migrate` with or
 * without --skip-fixtures because it is code, not a fixture.
 *
 * The doctype controllers (coa_amb.js / coa_amb2.js) already handle TDS load
 * + validation correctly; this only ADDS the Audit Compliance modal that the
 * legacy Client Scripts provided (the buggy copy is being deleted by patch
 * v14_3_11). Fully additive: Frappe merges frappe.ui.form.on() across files.
 *
 * Correct fields (verified against COA Quality Test Parameter meta):
 *   parameter_name (Link), custom_is_title_row (Check), result, status,
 *   value / specification, numeric, min_value, max_value.
 * Read-only: prefers each row's stored `status` (authoritative — set by the
 * server-side "Validate All Tests"); falls back to a computed decision only
 * for not-yet-validated rows. No writes, no dirtying the doc.
 */
window.amb_coa = window.amb_coa || {};

// Pure decision used only as a fallback for un-validated rows. No writes.
amb_coa.decide_status = function (row) {
    if (row.custom_is_title_row) return 'TITLE';
    if (!row.result && row.result !== 0) return 'Pending';
    if (row.numeric) {
        const v = parseFloat(row.result);
        if (isNaN(v)) return 'Fail';
        const min = parseFloat(row.min_value);
        const max = parseFloat(row.max_value);
        const lo = isNaN(min) ? -Infinity : min;
        const hi = isNaN(max) ? Infinity : max;
        return (v >= lo && v <= hi) ? 'Pass' : 'Fail';
    }
    const res = (row.result || '').toString().toUpperCase().trim();
    const acc = (row.value || row.specification || '').toString().toUpperCase().trim();
    if (['PASS', 'YES', 'OK', 'TRUE', 'NEGATIVE'].indexOf(res) !== -1) return 'Pass';
    if (['FAIL', 'NO', 'NOT OK', 'FALSE'].indexOf(res) !== -1) return 'Fail';
    if (acc) return (res === acc) ? 'Pass' : 'Fail';
    return 'N/A';
};

amb_coa._card = function (bg, n, label) {
    return '<div style="flex:1;background:' + bg + ';border-radius:8px;padding:12px;text-align:center;">' +
           '<div style="font-size:28px;font-weight:bold;">' + n + '</div><div>' + label + '</div></div>';
};

amb_coa.audit_report = function (frm) {
    const rows = frm.doc.coa_quality_test_parameter || [];
    if (!rows.length) { frappe.msgprint(__('No test parameters to audit')); return; }

    const a = { total: 0, passed: 0, failed: 0, pending: 0, na: 0, title: 0, details: [] };
    rows.forEach(function (p, i) {
        const pname = p.parameter_name || p.parameter_group || '';
        if (p.custom_is_title_row) {            // section header — skip (the old false-FAIL bug)
            a.title++;
            a.details.push({ row: i + 1, parameter: pname, status: 'TITLE', message: 'Section header' });
            return;
        }
        a.total++;
        const acceptance = (p.value || p.specification || '').toString();
        // Prefer the authoritative stored status; fall back to a computed decision.
        let st = (p.status || '').toString().trim();
        if (!st || st.toLowerCase() === 'pending') {
            const d = amb_coa.decide_status(p);
            st = (d === 'TITLE') ? 'Pending' : d;
        }
        const norm = st.toUpperCase();
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

    const pct = a.total ? (a.passed / a.total) * 100 : 0;
    const overall = a.failed ? 'FAIL' : (a.pending ? 'PARTIAL' : (a.passed ? 'PASS' : 'PENDING'));

    let m = '<div style="margin:10px 0;"><h3 style="text-align:center;">📋 COA Compliance Audit Report</h3><hr>';
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
        const bg = d.status === 'PASS' ? '#d4edda' : (d.status === 'FAIL' ? '#f8d7da' : (d.status === 'PENDING' ? '#fff3cd' : '#e9ecef'));
        const lbl = d.status === 'PASS' ? '✅ PASS' : (d.status === 'FAIL' ? '❌ FAIL' : (d.status === 'PENDING' ? '⏳ PENDING' : (d.status === 'TITLE' ? '📋 TITLE' : 'N/A')));
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

// Additive button on BOTH doctypes (merges with each controller's own refresh).
['COA AMB', 'COA AMB2'].forEach(function (dt) {
    frappe.ui.form.on(dt, {
        refresh: function (frm) {
            if (frm.is_new()) return;
            frm.add_custom_button(__('Audit Compliance'), function () {
                amb_coa.audit_report(frm);
            }, __('Actions'));
        }
    });
});
