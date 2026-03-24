// Sample Request button for Quotation
frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Sample Request'), function() {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.make_sample_request_from_source',
                args: { source_doctype: 'Quotation', source_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Creating Sample Request...'),
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frappe.set_route('Form', 'Sample Request AMB', r.message);
                        frappe.show_alert({ message: __('Sample Request created successfully'), indicator: 'green' });
                    }
                }
            });
        }, __('Create'));
    }
});
