// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('TDS Product Specification', {
    refresh: function(frm) {
        setup_tds_buttons(frm);
        apply_tds_filters(frm);
        show_version_info(frm);
    },
    
    product_item: function(frm) {
        if (frm.doc.product_item) {
            // Get item details
            frappe.db.get_value('Item', frm.doc.product_item, 
                ['item_name', 'item_code', 'description'], 
                function(r) {
                    if (r) {
                        frm.set_value('item_name', r.item_name);
                        frm.set_value('item_code', r.item_code);
                    }
                }
            );
            
            // Get latest version
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.tds_product_specification.tds_product_specification.get_latest_tds_version',
                args: { product_item: frm.doc.product_item },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Latest Version'),
                            message: __('Latest TDS version for this product is: {0}', 
                                [r.message.version || 'N/A']),
                            indicator: 'blue'
                        });
                    }
                }
            });
        }
    }
});

function setup_tds_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Create COA button
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create COA'), function() {
                frappe.call({
                    method: 'amb_w_tds.amb_w_tds.doctype.coa_amb.coa_amb.create_coa_from_tds',
                    args: { tds_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            frappe.set_route('Form', 'COA AMB', r.message);
                        }
                    }
                });
            }, __('Create'));
        }
        
        // Copy from previous version
        frm.add_custom_button(__('Copy from Previous Version'), function() {
            show_version_selector(frm);
        }, __('Actions'));
    }
}

function apply_tds_filters(frm) {
    frm.set_query('product_item', function() {
        return {
            filters: {
                'is_stock_item': 1,
                'disabled': 0
            }
        };
    });
}

function show_version_info(frm) {
    if (frm.doc.version) {
        frm.dashboard.add_indicator(
            __('Version {0}', [frm.doc.version]),
            'blue'
        );
    }
}

function show_version_selector(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Select Previous Version'),
        fields: [{
            fieldname: 'source_tds',
            fieldtype: 'Link',
            label: __('Source TDS'),
            options: 'TDS Product Specification',
            get_query: function() {
                return {
                    filters: {
                        'product_item': frm.doc.product_item,
                        'name': ['!=', frm.doc.name],
                        'docstatus': 1
                    }
                };
            },
            reqd: 1
        }],
        primary_action_label: __('Copy'),
        primary_action: function(values) {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.tds_product_specification.tds_product_specification.copy_specifications_from_previous',
                args: {
                    source_tds: values.source_tds,
                    target_tds: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        d.hide();
                    }
                }
            });
        }
    });
    d.show();
}
