// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('BOM Template Item', {
    qty: function(frm, cdt, cdn) {
        // Recalculate amount when quantity changes
        var row = locals[cdt][cdn];
        if (row.qty && row.rate) {
            row.amount = row.qty * row.rate;
            refresh_field('amount', cdn, 'items');
        }
    },
    
    rate: function(frm, cdt, cdn) {
        // Recalculate amount when rate changes
        var row = locals[cdt][cdn];
        if (row.qty && row.rate) {
            row.amount = row.qty * row.rate;
            refresh_field('amount', cdn, 'items');
        }
    }
});
