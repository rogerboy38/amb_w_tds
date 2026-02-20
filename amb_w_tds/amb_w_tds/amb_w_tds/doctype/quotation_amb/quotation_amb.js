frappe.ui.form.on("Quotation AMB", {
    refresh(frm) {
        if (frm.is_new()) {
            frm.set_value("status", "Draft");
        }
    },

    customer(frm) {
        if (!frm.doc.transaction_date) {
            frm.set_value("transaction_date", frappe.datetime.get_today());
        }
    },

    custom_folio(frm) {
        if (frm.doc.custom_folio) {
            frm.set_df_property("custom_folio", "read_only", 1);
        }
    }
});
