// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('BOM Version', {
    refresh: function(frm) {
        // Add custom logic here
    },
    
    bom_template: function(frm) {
        // Auto-suggest next version number
        if (frm.doc.bom_template && !frm.doc.version_number) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'BOM Version',
                    filters: { bom_template: frm.doc.bom_template },
                    fields: ['version_number'],
                    order_by: 'version_number desc',
                    limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('version_number', r.message[0].version_number + 1);
                    } else {
                        frm.set_value('version_number', 1.0);
                    }
                }
            });
        }
    },
    
    is_active: function(frm) {
        // Warn user when activating a version
        if (frm.doc.is_active) {
            frappe.msgprint(__('This will deactivate other active versions for the same BOM Template'));
        }
    }
});
