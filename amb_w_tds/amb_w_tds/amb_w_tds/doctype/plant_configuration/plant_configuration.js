// Plant Configuration JavaScript

frappe.ui.form.on('Plant Configuration', {
    refresh: function(frm) {
        // Add custom buttons
        add_plant_config_buttons(frm);
        
        // Setup field formatting
        setup_field_formatting(frm);
        
        // Validate JSON fields
        validate_json_fields(frm);
    },
    
    min_fill_threshold: function(frm) {
        validate_thresholds(frm);
    },
    
    max_fill_threshold: function(frm) {
        validate_thresholds(frm);
    },
    
    default_tara_weights: function(frm) {
        validate_tara_weights_json(frm);
    }
});

function add_plant_config_buttons(frm) {
    if (frm.doc.name) {
        // Test container calculation
        frm.add_custom_button(__('Test Container Calculation'), function() {
            test_container_calculation_dialog(frm);
        }, __('Tools'));
        
        // View related containers
        frm.add_custom_button(__('View Containers'), function() {
            frappe.route_options = {'plant': frm.doc.plant_name};
            frappe.set_route('List', 'Container Selection');
        }, __('Tools'));
        
        // Import/Export configuration
        frm.add_custom_button(__('Export Config'), function() {
            export_plant_config(frm);
        }, __('Tools'));
    }
}

function setup_field_formatting(frm) {
    // Format thresholds as percentages
    frm.set_df_property('min_fill_threshold', 'description', 'Containers below this threshold will be rejected');
    frm.set_df_property('max_fill_threshold', 'description', 'Containers above this threshold are considered complete');
    frm.set_df_property('weight_tolerance_percentage', 'description', 'Weight variance tolerance for quality control');
    
    // Format sync settings
    if (frm.doc.auto_sync_enabled) {
        frm.set_df_property('auto_sync_enabled', 'description', 
            `<span style="color: green;">✓ Auto-sync every ${frm.doc.sync_interval_minutes} minutes</span>`);
    } else {
        frm.set_df_property('auto_sync_enabled', 'description', 
            '<span style="color: orange;">⚠ Manual sync only</span>');
    }
}

function validate_thresholds(frm) {
    if (frm.doc.min_fill_threshold && frm.doc.max_fill_threshold) {
        if (frm.doc.min_fill_threshold >= frm.doc.max_fill_threshold) {
            frappe.msgprint({
                title: __('Invalid Thresholds'),
                message: __('Minimum fill threshold must be less than maximum fill threshold'),
                indicator: 'red'
            });
            frm.set_value('min_fill_threshold', 10.0);
            frm.set_value('max_fill_threshold', 95.0);
        }
    }
}

function validate_tara_weights_json(frm) {
    if (frm.doc.default_tara_weights) {
        try {
            let weights = JSON.parse(frm.doc.default_tara_weights);
            
            // Validate format
            if (typeof weights !== 'object' || Array.isArray(weights)) {
                throw new Error('Must be a JSON object');
            }
            
            // Format and display validation
            frm.set_df_property('default_tara_weights', 'description', 
                '<span style="color: green;">✓ Valid JSON format</span>');
                
        } catch (e) {
            frm.set_df_property('default_tara_weights', 'description', 
                `<span style="color: red;">✗ Invalid JSON: ${e.message}</span>`);
        }
    }
}

function validate_json_fields(frm) {
    // Auto-validate JSON fields on form load
    if (frm.doc.default_tara_weights) {
        validate_tara_weights_json(frm);
    }
}

function test_container_calculation_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Test Container Calculation'),
        fields: [
            {
                label: __('Batch Size (L)'),
                fieldname: 'batch_size',
                fieldtype: 'Float',
                reqd: 1,
                default: 1000
            },
            {
                label: __('Brix Level'),
                fieldname: 'brix_level',
                fieldtype: 'Float',
                reqd: 1,
                default: 65.0
            },
            {
                label: __('Target Concentration'),
                fieldname: 'target_concentration',
                fieldtype: 'Select',
                options: '1X\n30X',
                default: '30X',
                reqd: 1
            }
        ],
        primary_action_label: __('Calculate'),
        primary_action: function() {
            let values = d.get_values();
            calculate_containers(frm, values);
            d.hide();
        }
    });
    
    d.show();
}

function calculate_containers(frm, values) {
    frappe.call({
        method: 'amb_w_tds.doctype.plant_configuration.plant_configuration.calculate_juice_containers',
        args: {
            plant_name: frm.doc.plant_name,
            batch_size: values.batch_size,
            brix_level: values.brix_level,
            target_concentration: values.target_concentration
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                show_calculation_results(r.message);
            } else {
                frappe.msgprint({
                    title: __('Calculation Error'),
                    message: r.message ? r.message.error : __('Calculation failed'),
                    indicator: 'red'
                });
            }
        }
    });
}

function show_calculation_results(result) {
    let html = `
        <div class="calculation-results">
            <h4>Container Calculation Results</h4>
            <table class="table table-bordered">
                <tr><td><strong>Batch Size</strong></td><td>${result.batch_size} L</td></tr>
                <tr><td><strong>Final Volume</strong></td><td>${result.final_volume.toFixed(2)} L</td></tr>
                <tr><td><strong>Conversion Factor</strong></td><td>${result.conversion_factor}x</td></tr>
                <tr><td><strong>Barrels Needed</strong></td><td>${Math.ceil(result.barrels_needed)} barrels</td></tr>
                <tr><td><strong>Truck Loads</strong></td><td>${result.truck_loads.toFixed(2)} trucks</td></tr>
                <tr><td><strong>Barrel Capacity</strong></td><td>${result.barrel_capacity} L each</td></tr>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __('Calculation Results'),
        message: html,
        wide: true
    });
}

function export_plant_config(frm) {
    frappe.call({
        method: 'amb_w_tds.api.plant_management.export_plant_config',
        args: {
            plant_name: frm.doc.plant_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                // Download configuration as JSON
                let data = JSON.stringify(r.message.config, null, 2);
                let blob = new Blob([data], {type: 'application/json'});
                let url = URL.createObjectURL(blob);
                let a = document.createElement('a');
                a.href = url;
                a.download = `${frm.doc.plant_name}_config.json`;
                a.click();
                URL.revokeObjectURL(url);
                
                frappe.show_alert({
                    message: __('Configuration exported successfully'),
                    indicator: 'green'
                });
            }
        }
    });
}

// Child table events for Container Rules
frappe.ui.form.on('Container Type Rule', {
    container_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Auto-fetch item details
        if (row.container_type) {
            frappe.db.get_value('Item', row.container_type, ['weight_per_unit', 'description'], function(r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, 'tara_weight', r.weight_per_unit || 0);
                }
            });
        }
    },
    
    capacity: function(frm, cdt, cdn) {
        // Validate capacity is positive
        let row = locals[cdt][cdn];
        if (row.capacity <= 0) {
            frappe.msgprint(__('Capacity must be greater than 0'));
            frappe.model.set_value(cdt, cdn, 'capacity', 1);
        }
    }
});

// Child table events for Juice Conversion Rules
frappe.ui.form.on('Juice Conversion Config', {
    min_brix: function(frm, cdt, cdn) {
        validate_brix_range(frm, cdt, cdn);
    },
    
    max_brix: function(frm, cdt, cdn) {
        validate_brix_range(frm, cdt, cdn);
    }
});

function validate_brix_range(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.min_brix && row.max_brix && row.min_brix >= row.max_brix) {
        frappe.msgprint(__('Minimum Brix must be less than Maximum Brix'));
        frappe.model.set_value(cdt, cdn, 'max_brix', row.min_brix + 10);
    }
}