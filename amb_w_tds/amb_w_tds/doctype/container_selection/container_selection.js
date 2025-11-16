// Enhanced Container Selection JavaScript
// Mobile scanner integration and real-time weight calculations

frappe.ui.form.on('Container Selection', {
    refresh: function(frm) {
        // Add custom buttons
        add_custom_buttons(frm);
        
        // Setup real-time fields
        setup_realtime_fields(frm);
        
        // Add mobile scanner button
        if (frappe.is_mobile()) {
            frm.add_custom_button(__('Mobile Scanner'), function() {
                open_mobile_scanner(frm);
            }, __('Actions'));
        }
    },
    
    gross_weight: function(frm) {
        // Auto-calculate net weight when gross weight changes
        calculate_weights(frm);
    },
    
    container_type: function(frm) {
        // Fetch tara weight from Item master
        if (frm.doc.container_type) {
            fetch_tara_weight(frm);
        }
    },
    
    batch_amb_link: function(frm) {
        // Trigger sync when batch is assigned
        if (frm.doc.batch_amb_link && frm.doc.name) {
            trigger_manual_sync(frm);
        }
    }
});

function add_custom_buttons(frm) {
    if (frm.doc.name) {
        // Add barcode scan button
        frm.add_custom_button(__('Scan Barcode'), function() {
            scan_barcode_dialog(frm);
        }, __('Actions'));
        
        // Add weight calculator
        frm.add_custom_button(__('Calculate Weights'), function() {
            weight_calculator_dialog(frm);
        }, __('Actions'));
        
        // Add sync log viewer
        frm.add_custom_button(__('View Sync Log'), function() {
            view_sync_log(frm);
        }, __('Actions'));
        
        // Add batch assignment button
        if (!frm.doc.batch_amb_link) {
            frm.add_custom_button(__('Assign to Batch'), function() {
                assign_to_batch_dialog(frm);
            }, __('Actions'));
        }
    }
}

function setup_realtime_fields(frm) {
    // Make weight fields prominent
    frm.set_df_property('gross_weight', 'bold', 1);
    frm.set_df_property('net_weight', 'bold', 1);
    frm.set_df_property('weight_variance_percentage', 'bold', 1);
    
    // Color code tolerance field
    if (frm.doc.is_within_tolerance) {
        frm.set_df_property('is_within_tolerance', 'description', 
            '<span style="color: green;">✓ Within 1% tolerance</span>');
    } else if (frm.doc.weight_variance_percentage > 1) {
        frm.set_df_property('is_within_tolerance', 'description', 
            '<span style="color: red;">⚠ Outside tolerance limit</span>');
    }
    
    // Update sync status indicator
    update_sync_status_indicator(frm);
}

function calculate_weights(frm) {
    if (frm.doc.gross_weight && frm.doc.tara_weight) {
        let net_weight = frm.doc.gross_weight - frm.doc.tara_weight;
        frm.set_value('net_weight', net_weight);
        
        // Calculate variance if expected weight exists
        if (frm.doc.expected_weight) {
            let variance = Math.abs(net_weight - frm.doc.expected_weight) / frm.doc.expected_weight;
            let variance_percent = variance * 100;
            frm.set_value('weight_variance_percentage', variance_percent);
            frm.set_value('is_within_tolerance', variance <= 0.01 ? 1 : 0);
            
            // Show variance dialog if outside tolerance
            if (variance > 0.01) {
                show_variance_warning(frm, variance_percent);
            }
        }
    }
}

function fetch_tara_weight(frm) {
    frappe.db.get_value('Item', frm.doc.container_type, 'weight_per_unit', function(r) {
        if (r && r.weight_per_unit) {
            frm.set_value('tara_weight', r.weight_per_unit);
            calculate_weights(frm);
        }
    });
}

function scan_barcode_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Barcode Scanner'),
        fields: [
            {
                label: __('Barcode'),
                fieldname: 'barcode',
                fieldtype: 'Data',
                reqd: 1,
                description: __('Scan or enter container barcode')
            }
        ],
        primary_action_label: __('Process Scan'),
        primary_action: function() {
            process_barcode_scan(frm, d.get_value('barcode'));
            d.hide();
        }
    });
    
    d.show();
    
    // Auto-focus barcode field for scanner
    setTimeout(() => {
        d.get_field('barcode').$input.focus();
    }, 500);
}

function process_barcode_scan(frm, barcode) {
    frappe.call({
        method: 'amb_w_tds.doctype.container_selection.container_selection.scan_barcode',
        args: {
            barcode: barcode,
            plant: frm.doc.plant
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                // Update scan fields
                frm.set_value('barcode_scanned_at', frappe.datetime.now_datetime());
                frm.set_value('scanned_by', frappe.session.user);
                frm.save();
                
                frappe.show_alert({
                    message: __('Barcode scan recorded successfully'),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Scan Error'),
                    message: r.message ? r.message.message : __('Barcode scan failed'),
                    indicator: 'red'
                });
            }
        }
    });
}

function weight_calculator_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Weight Calculator'),
        fields: [
            {
                label: __('Gross Weight (Kg)'),
                fieldname: 'gross_weight',
                fieldtype: 'Float',
                precision: 3,
                default: frm.doc.gross_weight
            },
            {
                label: __('Tara Weight (Kg)'),
                fieldname: 'tara_weight',
                fieldtype: 'Float',
                precision: 3,
                default: frm.doc.tara_weight,
                read_only: 1
            },
            {
                label: __('Calculated Net Weight (Kg)'),
                fieldname: 'calculated_net',
                fieldtype: 'Float',
                precision: 3,
                read_only: 1
            },
            {
                label: __('Expected Weight (Kg)'),
                fieldname: 'expected_weight',
                fieldtype: 'Float',
                precision: 3,
                default: frm.doc.expected_weight
            },
            {
                label: __('Variance %'),
                fieldname: 'variance_percent',
                fieldtype: 'Float',
                precision: 2,
                read_only: 1
            }
        ],
        primary_action_label: __('Update Weights'),
        primary_action: function() {
            let values = d.get_values();
            frm.set_value('gross_weight', values.gross_weight);
            frm.set_value('expected_weight', values.expected_weight);
            calculate_weights(frm);
            frm.save();
            d.hide();
        }
    });
    
    // Auto-calculate when gross weight changes
    d.get_field('gross_weight').$input.on('input', function() {
        let gross = parseFloat(d.get_value('gross_weight')) || 0;
        let tara = parseFloat(d.get_value('tara_weight')) || 0;
        let expected = parseFloat(d.get_value('expected_weight')) || 0;
        
        let net = gross - tara;
        d.set_value('calculated_net', net);
        
        if (expected > 0) {
            let variance = Math.abs(net - expected) / expected * 100;
            d.set_value('variance_percent', variance);
        }
    });
    
    d.show();
}

function assign_to_batch_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Assign to Batch AMB'),
        fields: [
            {
                label: __('Batch AMB'),
                fieldname: 'batch_amb',
                fieldtype: 'Link',
                options: 'Batch AMB',
                reqd: 1,
                get_query: function() {
                    return {
                        filters: {
                            'status': ['!=', 'Completed']
                        }
                    };
                }
            }
        ],
        primary_action_label: __('Assign'),
        primary_action: function() {
            assign_to_batch(frm, d.get_value('batch_amb'));
            d.hide();
        }
    });
    
    d.show();
}

function assign_to_batch(frm, batch_name) {
    frappe.call({
        method: 'amb_w_tds.doctype.container_selection.container_selection.assign_to_batch',
        args: {
            container_name: frm.doc.name,
            batch_amb_name: batch_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.reload_doc();
                frappe.show_alert({
                    message: __('Container assigned to batch successfully'),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Assignment Error'),
                    message: r.message ? r.message.error : __('Assignment failed'),
                    indicator: 'red'
                });
            }
        }
    });
}

function view_sync_log(frm) {
    frappe.route_options = {
        'container_selection': frm.doc.name
    };
    frappe.set_route('List', 'Container Sync Log');
}

function trigger_manual_sync(frm) {
    frappe.call({
        method: 'amb_w_tds.api.container_api.manual_sync',
        args: {
            container_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.reload_doc();
                frappe.show_alert({
                    message: __('Sync completed successfully'),
                    indicator: 'green'
                });
            }
        }
    });
}

function update_sync_status_indicator(frm) {
    let sync_status = frm.doc.sync_status;
    let indicator_html = '';
    
    switch(sync_status) {
        case 'Synced':
            indicator_html = '<span style="color: green;">● Synced</span>';
            break;
        case 'Pending':
            indicator_html = '<span style="color: orange;">● Pending</span>';
            break;
        case 'Error':
            indicator_html = '<span style="color: red;">● Error</span>';
            break;
        default:
            indicator_html = '<span style="color: gray;">● Not Synced</span>';
    }
    
    frm.set_df_property('sync_status', 'description', indicator_html);
}

function show_variance_warning(frm, variance_percent) {
    frappe.msgprint({
        title: __('Weight Variance Warning'),
        message: __('Weight variance of {0}% exceeds 1% tolerance. Please verify measurements.', 
                   [variance_percent.toFixed(2)]),
        indicator: 'orange'
    });
}

function open_mobile_scanner(frm) {
    // Redirect to mobile scanner page
    window.open('/desk#mobile-scanner', '_blank');
}

// Lifecycle status change handler
frappe.ui.form.on('Container Selection', {
    lifecycle_status: function(frm) {
        // Set date fields based on status
        if (frm.doc.lifecycle_status === 'Reserved' && !frm.doc.reserved_date) {
            frm.set_value('reserved_date', frappe.datetime.now_datetime());
        }
        
        if (frm.doc.lifecycle_status === 'Completed' && !frm.doc.completed_date) {
            frm.set_value('completed_date', frappe.datetime.now_datetime());
        }
        
        // Update sync status
        if (frm.doc.batch_amb_link) {
            frm.set_value('sync_status', 'Pending');
        }
    }
});

// Auto-refresh every 30 seconds if sync is pending
setInterval(function() {
    if (cur_frm && cur_frm.doc && cur_frm.doc.sync_status === 'Pending') {
        cur_frm.reload_doc();
    }
}, 30000);