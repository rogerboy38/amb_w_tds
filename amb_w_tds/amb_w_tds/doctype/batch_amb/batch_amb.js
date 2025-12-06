// Enhanced Batch AMB Client Script - Complete Integration
// Copyright (c) 2024, AMB and contributors

// Initialize utility function at the top
if (typeof flt === 'undefined') {
    window.flt = frappe.utils.flt || function(val) { 
        return parseFloat(val) || 0; 
    };
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
    },

    // ==================== FIELD EVENTS ====================
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            fetch_work_order_details(frm);
        }
    },

    work_order_ref: function(frm) {
        if (frm.doc.work_order_ref) {
            fetch_work_order_data(frm);
        }
    },

    custom_batch_level: function(frm) {
        if (!frm.is_new() && frm.doc.custom_batch_level !== frm.doc.__original_level) {
            frappe.msgprint(__('Cannot change batch level of existing documents. Create a new document for different levels.'));
            frm.set_value('custom_batch_level', frm.doc.__original_level || '1');
            return;
        }
        
        if (!frm.doc.__original_level) {
            frm.doc.__original_level = frm.doc.custom_batch_level;
        }
        
        configure_level_settings(frm);
        
        if (should_auto_generate(frm)) {
            generate_batch_code(frm);
        }
    },

    parent_batch_amb: function(frm) {
        if (frm.doc.parent_batch_amb === frm.doc.name) {
            frappe.msgprint(__('A batch cannot be its own parent'));
            frm.set_value('parent_batch_amb', '');
            return;
        }
        
        if (frm.doc.parent_batch_amb && should_auto_generate(frm)) {
            generate_batch_code(frm);
        }
    },

    quick_barcode_scan: function(frm) {
        if (frm.doc.quick_barcode_scan && frm.doc.custom_batch_level == '3') {
            process_quick_barcode_scan(frm);
        }
    },

    default_packaging_type: function(frm) {
        if (frm.doc.default_packaging_type) {
            fetch_default_tara_weight(frm);
        }
    },

    calculate_cost: function(frm) {
        if (frm.doc.calculate_cost) {
            calculate_costs(frm);
        }
    },

    processing_status: function(frm) {
        // Show/hide fields based on status
        if (frm.doc.processing_status === "Scheduled") {
            frm.toggle_display(['scheduled_start_date', 'scheduled_start_time'], true);
        } else {
            frm.toggle_display(['scheduled_start_date', 'scheduled_start_time'], false);
        }
        
        if (frm.doc.processing_status === "Completed") {
            frm.toggle_display(['actual_start', 'actual_completion', 'processed_quantity', 'yield_percentage'], true);
        }
    },

    processed_quantity: function(frm) {
        // Recalculate yield when processed quantity changes
        if (frm.doc.planned_qty && frm.doc.processed_quantity) {
            const yield_percentage = (flt(frm.doc.processed_quantity) / flt(frm.doc.planned_qty)) * 100;
            frm.set_value('yield_percentage', yield_percentage);
        }
    },

    planned_qty: function(frm) {
        if (frm.doc.planned_qty && flt(frm.doc.planned_qty) <= 0) {
            frappe.msgprint(__('Planned Quantity must be greater than 0'));
            frm.set_value('planned_qty', '');
        }
    },

    before_save: function(frm) {
        // Validate parent-child relationship
        if (frm.doc.parent_batch_amb === frm.doc.name) {
            frappe.throw(__('A batch cannot be its own parent'));
            return false;
        }
        
        // Validate parent is required for levels > 1
        if (parseInt(frm.doc.custom_batch_level || '0', 10) > 1 && !frm.doc.parent_batch_amb) {
            frappe.throw(__('Parent Batch AMB is required for level {0}', [frm.doc.custom_batch_level]));
            return false;
        }
        
        // Store original level
        if (!frm.doc.__original_level) {
            frm.doc.__original_level = frm.doc.custom_batch_level;
        }
        
        // Validate barrel data for level 3
        if (frm.doc.custom_batch_level == '3') {
            if (!validate_barrel_data(frm)) {
                return false;
            }
        }
        
        // Calculate container totals
        calculate_container_totals(frm);
        
        return true;
    },

    after_save: function(frm) {
        // Refresh to get latest values
        frm.refresh();
    }
});

// ==================== CHILD TABLE: Container Barrels ====================

frappe.ui.form.on('Container Barrels', {
    quantity: function(frm, cdt, cdn) {
        calculate_container_totals(frm);
    },
    
    container_barrels_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.status = 'Active';
        
        if (frm.doc.default_packaging_type) {
            frappe.model.set_value(cdt, cdn, 'packaging_type', frm.doc.default_packaging_type);
        }
        
        generate_barrel_serial_number(frm, row);
        frm.refresh_field('container_barrels');
    },
    
    container_barrels_remove: function(frm) {
        calculate_container_totals(frm);
    },

    barcode_scan_input: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.barcode_scan_input) {
            process_barcode_scan(frm, cdt, cdn, row.barcode_scan_input);
        }
    },

    gross_weight: function(frm, cdt, cdn) {
        calculate_net_weight(frm, cdt, cdn);
        update_weight_totals(frm);
    },

    tara_weight: function(frm, cdt, cdn) {
        calculate_net_weight(frm, cdt, cdn);
        update_weight_totals(frm);
    },

    packaging_type: function(frm, cdt, cdn) {
        fetch_tara_weight_for_row(frm, cdt, cdn);
    }
});

// ==================== HELPER FUNCTIONS ====================

function setup_custom_buttons(frm) {
    console.log('🔧 Setting up custom buttons for', frm.doc.name);
    
    // Clear existing manufacturing buttons to avoid duplicates
    if (frm.custom_buttons && frm.custom_buttons['🏭 MANUFACTURING ACTIONS']) {
        delete frm.custom_buttons['🏭 MANUFACTURING ACTIONS'];
    }
    
    // Only add manufacturing buttons if document is saved
    if (!frm.doc.__islocal) {
        // Create BOM Button
        frm.add_custom_button(__('🏭 Create BOM'), function() {
            frappe.msgprint({
                title: __('Create BOM'),
                message: __('Creating BOM for batch {0}...', [frm.doc.name]),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.create_bom_with_wizard',
                args: { 
                    batch_name: frm.doc.name,
                    options: {
                        include_packaging: true,
                        include_utilities: true, 
                        include_labor: true
                    }
                },
                callback: function(r) {
                    console.log('BOM Creation Response:', r);
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('BOM Created'),
                            message: __('BOM {0} created successfully!', [r.message.bom_name]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Failed to create BOM: {0}', [r.message?.message || 'Unknown error']),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, __('🏭 MANUFACTURING ACTIONS'));

        // Generate MRP Button
        frm.add_custom_button(__('📊 Generate MRP'), function() {
            frappe.msgprint({
                title: __('Generate MRP'),
                message: __('Generating material requirements for batch {0}...', [frm.doc.name]),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.calculate_material_requirements',
                args: { batch_name: frm.doc.name },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('MRP Generated'),
                            message: __('Material requirements calculated for {0} units', [r.message.batch_quantity]),
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Error generating MRP: {0}', [r.message.message || 'Unknown error']),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, __('🏭 MANUFACTURING ACTIONS'));

        // Assign Golden Number Button
        frm.add_custom_button(__('⭐ Assign Golden Number'), function() {
            frappe.msgprint({
                title: __('Assign Golden Number'),
                message: __('Assigning Golden Number to batch {0}...', [frm.doc.name]),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.assign_golden_number_to_batch',
                args: { batch_name: frm.doc.name },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Golden Number Assigned'),
                            message: __('Golden Number {0} assigned successfully!', [r.message.golden_number]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Error assigning Golden Number: {0}', [r.message.message || 'Unknown error']),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, __('🏭 MANUFACTURING ACTIONS'));

        // Update Planned Qty Button
        frm.add_custom_button(__('📈 Update Planned Qty'), function() {
            frappe.msgprint({
                title: __('Update Planned Qty'),
                message: __('Updating planned quantity for batch {0}...', [frm.doc.name]),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.update_planned_qty_from_work_order',
                args: { batch_name: frm.doc.name },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Planned Qty Updated'),
                            message: __('Planned quantity updated to {0}', [r.message.planned_qty]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Error updating planned quantity: {0}', [r.message.message || 'Unknown error']),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, __('🏭 MANUFACTURING ACTIONS'));
        
        console.log('✅ Manufacturing buttons added');
    }
}

function apply_field_filters(frm) {
    // Filter work orders
    frm.set_query('work_order', function() {
        return {
            filters: {
                'status': ['not in', ['Completed', 'Stopped', 'Cancelled']],
                'docstatus': 1
            }
        };
    });
    
    // Filter items to manufacture
    frm.set_query('item_to_manufacture', function() {
        return {
            filters: {
                'is_stock_item': 1,
                'disabled': 0
            }
        };
    });
    
    // Filter warehouses
    frm.set_query('source_warehouse', function() {
        return {
            filters: {
                'is_group': 0,
                'disabled': 0,
                'company': frm.doc.company
            }
        };
    });
    
    frm.set_query('target_warehouse', function() {
        return {
            filters: {
                'is_group': 0,
                'disabled': 0,
                'company': frm.doc.company
            }
        };
    });
}

function setup_field_dependencies(frm) {
    // Show/hide fields based on conditions
    frm.toggle_display('labor_cost', frm.doc.calculate_cost);
    frm.toggle_display('overhead_cost', frm.doc.calculate_cost);
    frm.toggle_display('total_batch_cost', frm.doc.calculate_cost);
    frm.toggle_display('cost_per_unit', frm.doc.calculate_cost);
    
    frm.toggle_display('container_barrels', frm.doc.use_containers);
    frm.toggle_display('total_containers', frm.doc.use_containers);
    frm.toggle_display('total_container_qty', frm.doc.use_containers);
}

function show_status_indicators(frm) {
    if (frm.doc.batch_status) {
        let color = {
            'Draft': 'gray',
            'In Progress': 'orange',
            'Completed': 'green',
            'On Hold': 'yellow',
            'Cancelled': 'red'
        }[frm.doc.batch_status] || 'gray';
        
        frm.dashboard.set_headline_alert(
            __('Status: {0}', [frm.doc.batch_status]),
            color
        );
    }
    
    if (frm.doc.quality_status) {
        let indicator = {
            'Passed': 'green',
            'Failed': 'red',
            'Pending': 'orange',
            'In Testing': 'blue'
        }[frm.doc.quality_status] || 'gray';
        
        frm.add_custom_button(
            __(frm.doc.quality_status),
            function() {},
            null,
            indicator
        );
    }
}

function set_default_values(frm) {
    if (frm.doc.__islocal) {
        if (!frm.doc.company) {
            frm.set_value('company', frappe.defaults.get_default('company'));
        }
        
        if (!frm.doc.production_start_date) {
            frm.set_value('production_start_date', frappe.datetime.get_today());
        }
        
        if (!frm.doc.batch_status) {
            frm.set_value('batch_status', 'Draft');
        }
    }
}

function load_user_preferences(frm) {
    frappe.db.get_value('User', frappe.session.user, 'default_warehouse', function(r) {
        if (r && r.default_warehouse && !frm.doc.target_warehouse) {
            frm.set_value('target_warehouse', r.default_warehouse);
        }
    });
}

function calculate_container_totals(frm) {
    if (!frm.doc.container_barrels || frm.doc.container_barrels.length === 0) return;
    
    let total_qty = 0;
    let total_containers = 0;
    let total_gross = 0, total_tara = 0, total_net = 0, barrel_count = 0;
    
    frm.doc.container_barrels.forEach(function(row) {
        if (row.quantity) {
            total_qty += flt(row.quantity);
        }
        total_containers++;
        
        if (row.gross_weight) total_gross += flt(row.gross_weight);
        if (row.tara_weight) total_tara += flt(row.tara_weight);
        if (row.net_weight) total_net += flt(row.net_weight);
        if (row.barrel_serial_number) barrel_count += 1;
    });
    
    frm.set_value('total_container_qty', total_qty);
    frm.set_value('total_containers', total_containers);
    
    frm.set_value('total_gross_weight', total_gross);
    frm.set_value('total_tara_weight', total_tara);
    frm.set_value('total_net_weight', total_net);
    frm.set_value('barrel_count', barrel_count);
}

function calculate_costs(frm) {
    if (!frm.doc.calculate_cost) return;
    
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.calculate_batch_cost',
        args: { batch_name: frm.doc.name },
        callback: function(r) {
            if (r.message) {
                frm.set_value('total_batch_cost', r.message.total_batch_cost);
                frm.set_value('cost_per_unit', r.message.cost_per_unit);
            }
        }
    });
}

// ==================== BATCHL2 ENHANCED FUNCTIONS ====================

function fetch_work_order_details(frm) {
    if (frm.doc.work_order) {
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.get_work_order_details',
            args: { work_order: frm.doc.work_order },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('item_to_manufacture', r.message.item_to_manufacture);
                    frm.set_value('planned_qty', r.message.planned_qty);
                    frm.set_value('company', r.message.company);
                    
                    frappe.show_alert({
                        message: __('Work Order details loaded'),
                        indicator: 'green'
                    });
                }
            }
        });
    }
}

function fetch_work_order_data(frm) {
    if (frm.doc.work_order_ref) {
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.get_work_order_data',
            args: { work_order: frm.doc.work_order_ref },
            callback: function(r) {
                if (r.message) {
                    // Try multiple possible quantity fields
                    let quantity = null;
                    
                    if (r.message.qty) {
                        quantity = r.message.qty;
                    } else if (r.message.production_qty) {
                        quantity = r.message.production_qty;
                    } else if (r.message.qty_to_manufacture) {
                        quantity = r.message.qty_to_manufacture;
                    }
                    
                    if (quantity && flt(quantity) > 0) {
                        frm.set_value('planned_qty', flt(quantity));
                        frappe.show_alert({
                            message: __('Planned quantity updated to {0}', [quantity]),
                            indicator: 'green'
                        });
                    } else {
                        frappe.show_alert({
                            message: __('No valid quantity found in Work Order'),
                            indicator: 'orange'
                        });
                    }
                }
            }
        });
    }
}

function initialize_barrel_management(frm) {
    if (!frm.doc.container_barrels) {
        frm.doc.container_barrels = [];
    }
}

function add_level_specific_buttons(frm) {
    if (frm.doc.custom_batch_level == '3') {
        frm.add_custom_button(__('Barrel Scanner'), function() {
            frm.set_value('quick_barcode_scan', '');
        });
        
        frm.add_custom_button(__('Validate Barrels'), function() {
            validate_all_barrels(frm);
        });
        
        frm.add_custom_button(__('Calculate Totals'), function() {
            update_weight_totals(frm);
        });
    }
}

function should_auto_generate(frm) {
    return frm.is_new() && (
        (frm.doc.custom_batch_level == '1' && !frm.doc.title) ||
        (frm.doc.custom_batch_level == '2' && frm.doc.parent_batch_amb) ||
        (frm.doc.custom_batch_level == '3' && frm.doc.parent_batch_amb && !frm.doc.custom_generated_batch_name)
    );
}

function generate_batch_code(frm) {
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_batch_code',
        args: {
            parent_batch: frm.doc.parent_batch_amb,
            batch_level: frm.doc.custom_batch_level,
            work_order: frm.doc.work_order_ref
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('custom_generated_batch_name', r.message.code);
                if (!frm.doc.title) {
                    frm.set_value('title', r.message.code);
                }
            }
        }
    });
}

function configure_level_settings(frm) {
    const level = parseInt(frm.doc.custom_batch_level || '1', 10);
    
    switch(level) {
        case 1:
            frm.set_df_property('parent_batch_amb', 'hidden', 1);
            frm.set_df_property('container_barrels_section', 'hidden', 1);
            break;
        case 2:
            frm.set_df_property('parent_batch_amb', 'hidden', 0);
            frm.set_df_property('container_barrels_section', 'hidden', 1);
            break;
        case 3:
            frm.set_df_property('parent_batch_amb', 'hidden', 0);
            frm.set_df_property('container_barrels_section', 'hidden', 0);
            break;
    }
}

function process_quick_barcode_scan(frm) {
    const barcode = frm.doc.quick_barcode_scan;
    if (!barcode) return;
    
    if (!validate_code39_format(barcode)) {
        frappe.msgprint(__('Invalid CODE-39 barcode format'));
        frm.set_value('quick_barcode_scan', '');
        return;
    }
    
    const row = frm.add_child('container_barrels');
    row.barrel_serial_number = barcode;
    row.packaging_type = frm.doc.default_packaging_type;
    row.scan_timestamp = frappe.datetime.now_datetime();
    
    if (row.packaging_type) {
        fetch_tara_weight_for_row(frm, row.doctype, row.name);
    }
    
    frm.refresh_field('container_barrels');
    frm.set_value('quick_barcode_scan', '');
    
    setTimeout(function() { 
        frm.scroll_to_field('container_barrels'); 
    }, 300);
}

function process_barcode_scan(frm, cdt, cdn, barcode) {
    const row = locals[cdt][cdn];
    if (!validate_code39_format(barcode)) {
        frappe.msgprint(__('Invalid CODE-39 barcode format'));
        frappe.model.set_value(cdt, cdn, 'barcode_scan_input', '');
        return;
    }
    frappe.model.set_value(cdt, cdn, 'barrel_serial_number', barcode);
    frappe.model.set_value(cdt, cdn, 'scan_timestamp', frappe.datetime.now_datetime());
    frappe.model.set_value(cdt, cdn, 'barcode_scan_input', '');
    
    if (row.packaging_type) {
        fetch_tara_weight_for_row(frm, cdt, cdn);
    }
}

function generate_barrel_serial_number(frm, row) {
    const container_code = frm.doc.title || frm.doc.custom_generated_batch_name;
    if (!container_code) return;

    let max_seq = 0;
    (frm.doc.container_barrels || []).forEach(barrel => {
        if (barrel.barrel_serial_number && barrel.barrel_serial_number.startsWith(container_code)) {
            const match = barrel.barrel_serial_number.match(/-([0-9]+)$/);
            if (match) {
                max_seq = Math.max(max_seq, parseInt(match[1], 10));
            }
        }
    });

    const next_seq = (max_seq + 1).toString().padStart(3, '0');
    row.barrel_serial_number = `${container_code}-${next_seq}`;
}

function fetch_tara_weight_for_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.packaging_type) return;

    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Item',
            name: row.packaging_type
        },
        callback: function(r) {
            if (r.message && r.message.weight_per_unit) {
                frappe.model.set_value(cdt, cdn, 'tara_weight', r.message.weight_per_unit);
                calculate_net_weight(frm, cdt, cdn);
            }
        }
    });
}

function fetch_default_tara_weight(frm) {
    if (!frm.doc.default_packaging_type) return;

    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Item',
            name: frm.doc.default_packaging_type
        },
        callback: function(r) {
            if (r.message && r.message.weight_per_unit) {
                (frm.doc.container_barrels || []).forEach(row => {
                    if (!row.tara_weight) {
                        frappe.model.set_value(row.doctype, row.name, 'tara_weight', r.message.weight_per_unit);
                        calculate_net_weight(frm, row.doctype, row.name);
                    }
                });
            }
        }
    });
}

function calculate_net_weight(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.gross_weight && row.tara_weight) {
        const net_weight = flt(row.gross_weight) - flt(row.tara_weight);
        frappe.model.set_value(cdt, cdn, 'net_weight', net_weight);
        frappe.model.set_value(cdt, cdn, 'weight_validated', net_weight > 0 && net_weight < flt(row.gross_weight) ? 1 : 0);
    }
}

function update_weight_totals(frm) {
    if (frm.doc.custom_batch_level != '3' || !frm.doc.container_barrels) return;

    let total_gross = 0, total_tara = 0, total_net = 0, barrel_count = 0;
    
    frm.doc.container_barrels.forEach(row => {
        if (row.gross_weight) total_gross += flt(row.gross_weight);
        if (row.tara_weight) total_tara += flt(row.tara_weight);
        if (row.net_weight) total_net += flt(row.net_weight);
        if (row.barrel_serial_number) barrel_count += 1;
    });
    
    frm.set_value('total_gross_weight', total_gross);
    frm.set_value('total_tara_weight', total_tara);
    frm.set_value('total_net_weight', total_net);
    frm.set_value('barrel_count', barrel_count);
}

function validate_barrel_data(frm) {
    if (!frm.doc.container_barrels || frm.doc.container_barrels.length === 0) {
        frappe.msgprint(__('Container barrels are required for Level 3 batches'));
        return false;
    }

    const serials = [];
    const duplicates = [];
    
    frm.doc.container_barrels.forEach(row => {
        if (row.barrel_serial_number) {
            if (serials.includes(row.barrel_serial_number)) {
                duplicates.push(row.barrel_serial_number);
            } else {
                serials.push(row.barrel_serial_number);
            }
        }
    });

    if (duplicates.length > 0) {
        frappe.throw(__('Duplicate barrel serial numbers found: {0}', [duplicates.join(', ')]));
        return false;
    }

    return true;
}

function validate_all_barrels(frm) {
    let valid = 0;
    let invalid = 0;
    const issues = [];

    (frm.doc.container_barrels || []).forEach((row, index) => {
        if (!row.barrel_serial_number) {
            invalid++;
            issues.push(__('Row {0}: Missing serial number', [index + 1]));
        } else if (!validate_code39_format(row.barrel_serial_number)) {
            invalid++;
            issues.push(__('Row {0}: Invalid format ({1})', [index + 1, row.barrel_serial_number]));
        } else {
            valid++;
        }
    });

    if (issues.length > 0) {
        frappe.msgprint(__('Validation Issues:') + '<br>' + issues.join('<br>'), __('Invalid'));
    } else {
        frappe.msgprint(__('All barrels validated successfully! Valid: {0}, Total: {1}', [valid, valid + invalid]), __('Valid'));
    }
}

function validate_code39_format(barcode) {
    const s = String(barcode || '').toUpperCase();
    return /^[A-Z0-9\-\.\s$\/+%*]+$/.test(s);
}

function add_processing_buttons(frm) {
    // Clear existing processing buttons
    const processingGroup = __('PROCESSING ACTIONS');
    if (frm.custom_buttons && frm.custom_buttons[processingGroup]) {
        delete frm.custom_buttons[processingGroup];
    }
    
    if (frm.doc.processing_status === "Draft" || frm.doc.processing_status === "Scheduled") {
        frm.add_custom_button(__('Start Processing'), function() {
            frm.call({
                method: 'start_processing',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('PROCESSING ACTIONS'));
    }
    
    if (frm.doc.processing_status === "In Progress") {
        frm.add_custom_button(__('Complete Processing'), function() {
            frm.call({
                method: 'complete_processing',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('PROCESSING ACTIONS'));
        
        frm.add_custom_button(__('Pause Processing'), function() {
            frm.call({
                method: 'pause_processing',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('PROCESSING ACTIONS'));
    }
    
    if (frm.doc.processing_status === "On Hold") {
        frm.add_custom_button(__('Resume Processing'), function() {
            frm.call({
                method: 'resume_processing',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('PROCESSING ACTIONS'));
    }
    
    if (frm.doc.processing_status === "Quality Check") {
        frm.add_custom_button(__('Approve Quality'), function() {
            frm.call({
                method: 'approve_quality',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('PROCESSING ACTIONS'));
        
        frm.add_custom_button(__('Reject Quality'), function() {
            frm.call({
                method: 'reject_quality',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('PROCESSING ACTIONS'));
    }
}

// Add schedule processing button separately
frappe.ui.form.on('Batch AMB', {
    refresh: function(frm) {
        // Add schedule button for draft status
        if (frm.doc.processing_status === "Draft") {
            frm.add_custom_button(__('Schedule Processing'), function() {
                show_schedule_dialog(frm);
            }, __('PROCESSING ACTIONS'));
        }
    }
});

function show_schedule_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Schedule Processing'),
        fields: [
            {
                label: __('Start Date'),
                fieldname: 'start_date',
                fieldtype: 'Date',
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                label: __('Start Time'),
                fieldname: 'start_time',
                fieldtype: 'Time',
                default: '08:00:00'
            }
        ],
        primary_action_label: __('Schedule'),
        primary_action(values) {
            frm.call({
                method: 'schedule_processing',
                doc: frm.doc,
                args: {
                    start_date: values.start_date,
                    start_time: values.start_time
                },
                callback: function(r) {
                    if (r.message) {
                        d.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    
    d.show();
}
