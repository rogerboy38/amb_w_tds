// Enhanced Batch AMB Client Script - Complete Integration
// Copyright (c) 2024, AMB and contributors

// Initialize utility function at the top
if (typeof flt === 'undefined') {
    window.flt = frappe.utils.flt || function(val) { 
        return parseFloat(val) || 0; 
    };
}

// ==================== SERIAL TRACKING INTEGRATION ====================

function integrateSerialTracking(frm) {
    frappe.confirm(
        'Connect this batch to Serial Tracking?',
        function() {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.integrate_serial_tracking',
                args: {batch_name: frm.doc.name},
                freeze: true,
                freeze_message: 'Integrating with Serial Tracking...',
                callback: function(r) {
                    if (r.message.status === 'success') {
                        frappe.show_alert({message: 'Serial Tracking integrated!', indicator: 'green'});
                        frm.reload_doc();
                    } else {
                        frappe.show_alert({message: 'Integration failed', indicator: 'red'});
                    }
                }
            });
        }
    );
}

function generateSerialNumbers(frm) {
    frappe.prompt({
        fieldname: 'quantity',
        fieldtype: 'Int',
        label: 'Number of serials to generate',
        default: frm.doc.planned_qty || 1,
        reqd: 1
    }, function(values) {
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_serial_numbers',
            args: {batch_name: frm.doc.name, quantity: values.quantity},
            freeze: true,
            freeze_message: 'Generating serial numbers...',
            callback: function(r) {
                if (r.message.status === 'success') {
                    frappe.msgprint({
                        title: 'Serial Numbers Generated',
                        message: 'Generated ' + r.message.count + ' serial numbers'
                    });
                    frm.reload_doc();
                }
            }
        });
    });
}

function displaySerialTrackingStatus(frm) {
    if (frm.doc.custom_serial_tracking_integrated) {
        var serials = frm.doc.custom_serial_numbers ? frm.doc.custom_serial_numbers.split('\\n').length : 0;
        var html = '<div style="padding: 10px; background: #e8f5e9; border-radius: 5px; margin: 10px 0;">' +
                   '<h5 style="margin: 0 0 5px 0;">Serial Tracking Active</h5>' +
                   '<div style="font-size: 12px;">' +
                   'Serial Numbers: ' + serials + '<br>' +
                   'Last Sync: ' + (frm.doc.custom_last_api_sync || 'Never') +
                   '</div></div>';
        frm.dashboard.add_section(html);
    }
}

function addSerialTrackingButtons(frm) {
    // Add Serial Tracking buttons
    if (!frm.doc.custom_serial_tracking_integrated) {
        frm.add_custom_button('Integrate Serial Tracking', function() {
            integrateSerialTracking(frm);
        }, 'SERIAL TRACKING').addClass('btn-primary');
    }
    
    frm.add_custom_button('Generate Serial Numbers', function() {
        generateSerialNumbers(frm);
    }, 'SERIAL TRACKING');
    
    // Display status
    displaySerialTrackingStatus(frm);
}

frappe.ui.form.on('Batch AMB', {
    // ==================== FORM EVENTS ====================
    
    refresh: function(frm) {
        // Basic setup
        setup_custom_buttons(frm);
        apply_field_filters(frm);
        setup_field_dependencies(frm);
        show_status_indicators(frm);
        
        // Batch level specific
        if (should_auto_generate(frm)) {
            generate_batch_code(frm);
        }
        add_level_specific_buttons(frm);
        
        // Update weight totals for level 3
        if (frm.doc.custom_batch_level == '3') {
            update_weight_totals(frm);
        }
        
        // Add processing buttons
        add_processing_buttons(frm);
        
        // Add serial tracking integration
        addSerialTrackingButtons(frm);
    },
    
    onload: function(frm) {
        // Set defaults
        set_default_values(frm);
        load_user_preferences(frm);
        
        // Initialize batch level
        if (frm.is_new()) {
            frm.set_value('custom_batch_level', '1');
            frm.set_value('is_group', 1);
        }
        
        // Initialize barrel management for level 3
        if (frm.doc.custom_batch_level == '3') {
            initialize_barrel_management(frm);
        }
    }
});

// ==================== UTILITY FUNCTIONS ====================

function setup_custom_buttons(frm) {
    // Your existing setup_custom_buttons function
}

function apply_field_filters(frm) {
    // Your existing apply_field_filters function
}

function setup_field_dependencies(frm) {
    // Your existing setup_field_dependencies function
}

function show_status_indicators(frm) {
    // Your existing show_status_indicators function
}

function should_auto_generate(frm) {
    // Your existing should_auto_generate function
}

function generate_batch_code(frm) {
    // Your existing generate_batch_code function
}

function add_level_specific_buttons(frm) {
    // Your existing add_level_specific_buttons function
}

function update_weight_totals(frm) {
    // Your existing update_weight_totals function
}

function add_processing_buttons(frm) {
    // Your existing add_processing_buttons function
}

function set_default_values(frm) {
    // Your existing set_default_values function
}

function load_user_preferences(frm) {
    // Your existing load_user_preferences function
}

function initialize_barrel_management(frm) {
    // Your existing initialize_barrel_management function
}
