frappe.ui.form.on('Batch AMB Item', {
    item_code: function(frm, cdt, cdn) {
        // When item code changes, fetch item details
        var row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    'doctype': 'Item',
                    'filters': {'name': row.item_code},
                    'fieldname': [
                        'item_name', 
                        'item_group', 
                        'stock_uom',
                        'description',
                        'valuation_rate',
                        'standard_rate',
                        'weight_per_unit',
                        'volume_per_unit',
                        'shelf_life_in_days',
                        'has_bom'
                    ]
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, {
                            'item_name': r.message.item_name,
                            'item_group': r.message.item_group,
                            'uom': r.message.stock_uom,
                            'description': r.message.description,
                            'valuation_rate': r.message.valuation_rate,
                            'standard_rate': r.message.standard_rate,
                            'weight_per_unit': r.message.weight_per_unit,
                            'volume_per_unit': r.message.volume_per_unit,
                            'shelf_life_days': r.message.shelf_life_in_days,
                            'has_bom': r.message.has_bom
                        });
                        
                        // Set rate to valuation rate if not set
                        if (!row.rate && r.message.valuation_rate) {
                            frappe.model.set_value(cdt, cdn, 'rate', r.message.valuation_rate);
                        }
                        
                        // Calculate totals
                        calculate_row_totals(frm, cdt, cdn);
                    }
                }
            });
        }
    },

    quantity: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    },

    rate: function(frm, cdt, cdn) {
        calculate_row_totals(frm, cdt, cdn);
    },

    weight_per_unit: function(frm, cdt, cdn) {
        calculate_weight_volume(frm, cdt, cdn);
    },

    volume_per_unit: function(frm, cdt, cdn) {
        calculate_weight_volume(frm, cdt, cdn);
    }
});

function calculate_row_totals(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    
    // Calculate amount
    var amount = flt(row.quantity) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
    
    // Calculate weight and volume
    calculate_weight_volume(frm, cdt, cdn);
}

function calculate_weight_volume(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    
    // Calculate total weight
    var total_weight = flt(row.quantity) * flt(row.weight_per_unit);
    frappe.model.set_value(cdt, cdn, 'total_weight', total_weight);
    
    // Calculate total volume
    var total_volume = flt(row.quantity) * flt(row.volume_per_unit);
    frappe.model.set_value(cdt, cdn, 'total_volume', total_volume);
}

// Add custom button to fetch BOM if item has BOM
frappe.ui.form.on('Batch AMB', {
    refresh: function(frm) {
        // Add button to fetch BOM details for items
        if (frm.doc.batch_items && frm.doc.batch_items.length > 0) {
            frm.add_custom_button(__('Fetch BOM Details'), function() {
                fetch_bom_details_for_items(frm);
            }).addClass('btn-default');
        }
    }
});

function fetch_bom_details_for_items(frm) {
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.fetch_bom_details_for_items',
        args: {
            batch_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Fetching BOM details...'),
        callback: function(r) {
            if (r.message.success) {
                frappe.show_alert({
                    message: __('BOM details fetched successfully'),
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message.message,
                    indicator: 'red'
                });
            }
        }
    });
}
