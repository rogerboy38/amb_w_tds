// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('BOM Enhancement', {
    refresh: function(frm) {
        // Add custom buttons or logic here
    },
    
    bom_template: function(frm) {
        // Trigger when BOM Template changes
        if (frm.doc.bom_template) {
            frm.set_value('enhancement_name', `Enhancement for ${frm.doc.bom_template}`);
        }
    }
});
