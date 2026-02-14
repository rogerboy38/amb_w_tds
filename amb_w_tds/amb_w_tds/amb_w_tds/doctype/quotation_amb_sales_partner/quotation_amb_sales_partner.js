// Copyright (c) 2025
// For license information, please see license.txt

frappe.ui.form.on("Quotation AMB Sales Partner", {

    // runs when row is loaded in the child table grid
    form_render: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Auto compute commission amount if rate & base exists
        if (row.commission_rate && frm.doc.base_total) {
            row.commission_amount =
                (frm.doc.base_total * row.commission_rate) / 100;
            frm.refresh_field("commission_lines");
        }
    },

    commission_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (frm.doc.base_total) {
            row.commission_amount =
                (frm.doc.base_total * row.commission_rate) / 100;

            frm.refresh_field("commission_lines");
        }
    }

});

