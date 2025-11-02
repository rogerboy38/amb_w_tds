// Enhanced Batch AMB Client Script - Baseline + Container & Barrel Management
// Combines original working functionality with enhanced container management
// Supports Level 3 containers, Level 4 scanning, and P-INV/P-VTA Work Orders

frappe.ui.form.on('Batch AMB', {
    // ==================== FORM EVENTS ====================
    
    refresh: function(frm) {
        // Set baseline custom buttons and actions
        setup_custom_buttons(frm);
        
        // Add level-specific buttons (ENHANCED FEATURE)
        add_level_specific_buttons(frm);
        
        // Apply field filters
        apply_field_filters(frm);
        
        // Set field dependencies
        setup_field_dependencies(frm);
        
        // Show indicators
        show_status_indicators(frm);
        
        // Update weight totals for level 3 containers
        if (frm.doc.custom_batch_level == '3') {
            update_weight_totals(frm);
        }
    },
    
    onload: function(frm) {
        // Set default values
        set_default_values(frm);
        
        // Load saved preferences
        load_user_preferences(frm);
        
        // Initialize barrel management for level 3
        if (frm.doc.custom_batch_level == '3') {
            initialize_barrel_management(frm);
        }
    },
    
    after_save: function(frm) {
        // Refresh the form to get the latest values from the server
        frm.refresh();
    },
    
    // ==================== FIELD EVENTS ====================
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            // Fetch work order details
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.get_work_order_details',
                args: { work_order: frm.doc.work_order },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('item_to_manufacture', r.message.item_to_manufacture);
                        frm.set_value('item_name', r.message.item_name);
                        frm.set_value('planned_qty', r.message.planned_qty);
                        frm.set_value('company', r.message.company);
                        frm.set_value('bom_no', r.message.bom_no);
                        frm.set_value('source_warehouse', r.message.source_warehouse);
                        frm.set_value('target_warehouse', r.message.target_warehouse);
                        frm.set_value('uom', r.message.uom);
                        
                        frappe.show_alert({
                            message: __('Work Order details loaded'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    },
    
    // Enhanced: Work order ref for container management
    work_order_ref: function(frm) {
        if (frm.doc.work_order_ref) {
            fetch_work_order_data(frm);
        }
    },
    
    item_to_manufacture: function(frm) {
        if (frm.doc.item_to_manufacture) {
            // Get item details
            frappe.db.get_value('Item', frm.doc.item_to_manufacture, 
                ['item_name', 'stock_uom', 'description'], 
                function(r) {
                    if (r) {
                        frm.set_value('item_name', r.item_name);
                        if (!frm.doc.uom) {
                            frm.set_value('uom', r.stock_uom);
                        }
                    }
                }
            );
        }
    },
    
    produced_qty: function(frm) {
        // Recalculate costs when quantity changes
        calculate_costs(frm);
        
        // Validate against container totals
        validate_container_quantities(frm);
    },
    
    production_start_date: function(frm) {
        validate_production_dates(frm);
    },
    
    production_end_date: function(frm) {
        validate_production_dates(frm);
        
        // Calculate production duration
        if (frm.doc.production_start_date && frm.doc.production_end_date) {
            let start = frappe.datetime.str_to_obj(frm.doc.production_start_date);
            let end = frappe.datetime.str_to_obj(frm.doc.production_end_date);
            let duration = frappe.datetime.get_day_diff(end, start);
            
            frm.set_value('production_duration_days', duration);
        }
    },
    
    calculate_cost: function(frm) {
        if (frm.doc.calculate_cost) {
            calculate_costs(frm);
        }
    },
    
    // Enhanced: Custom batch level for container management
    custom_batch_level: function(frm) {
        if (!frm.is_new()) {
            frappe.msgprint('Cannot change batch level of existing documents. Create a new document for different levels.');
            frm.set_value('custom_batch_level', frm.doc.__original_level || '1');
            return;
        }
        configure_level_settings(frm);
        if (should_auto_generate(frm)) {
            generate_batch_code(frm);
        }
    },
    
    parent_batch_amb: function(frm) {
        if (frm.doc.parent_batch_amb === frm.doc.name) {
            frappe.msgprint('A batch cannot be its own parent');
            frm.set_value('parent_batch_amb', '');
            return;
        }
        if (frm.doc.parent_batch_amb && should_auto_generate(frm)) {
            generate_batch_code(frm);
        }
    },
    
    // Enhanced: Barcode scanning
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
    
    // ==================== BEFORE SAVE ====================
    
    before_save: function(frm) {
        // Validate hierarchical relationships
        if (frm.doc.parent_batch_amb === frm.doc.name) {
            frappe.throw('A batch cannot be its own parent');
            return false;
        }
        
        // Validate parent requirements
        if (parseInt(frm.doc.custom_batch_level || '0', 10) > 1 && !frm.doc.parent_batch_amb) {
            frappe.throw('Parent Batch AMB is required for level ' + frm.doc.custom_batch_level);
            return false;
        }
        
        if (!frm.doc.__original_level) {
            frm.doc.__original_level = frm.doc.custom_batch_level;
        }
        
        // Validate barrel data for level 3
        if (frm.doc.custom_batch_level == '3') {
            validate_barrel_data(frm);
        }
        
        // Calculate totals before saving (baseline)
        calculate_container_totals(frm);
        return true;
    }
});

// ==================== CHILD TABLE: Container Barrels ====================

frappe.ui.form.on('Container Barrels', {
    quantity: function(frm, cdt, cdn) {
        // Recalculate totals when container quantity changes (baseline)
        calculate_container_totals(frm);
    },
    
    // Enhanced: Barrel management events
    container_barrels_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        
        // Set default status (baseline)
        row.status = 'Active';
        
        // Enhanced: Set default packaging type
        if (frm.doc.default_packaging_type) {
            frappe.model.set_value(cdt, cdn, 'packaging_type', frm.doc.default_packaging_type);
        }
        
        // Enhanced: Generate barrel serial number
        generate_barrel_serial_number(frm, row);
        
        frm.refresh_field('container_barrels');
    },
    
    // Enhanced: Barcode scanning input
    barcode_scan_input: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.barcode_scan_input) {
            process_barcode_scan(frm, cdt, cdn, row.barcode_scan_input);
        }
    },
    
    packaging_type: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.packaging_type) {
            fetch_tara_weight_for_row(frm, cdt, cdn);
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
    
    container_barrels_remove: function(frm) {
        // Enhanced: Update weight totals
        update_weight_totals(frm);
        
        // Also run baseline calculation
        calculate_container_totals(frm);
    }
});

// ==================== BASELINE CUSTOM BUTTONS ====================

function setup_custom_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Calculate Cost button
        frm.add_custom_button(__('Calculate Cost'), function() {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.calculate_batch_cost',
                args: { batch_name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('total_batch_cost', r.message.total_batch_cost);
                        frm.set_value('cost_per_unit', r.message.cost_per_unit);
                        frappe.show_alert({
                            message: __('Costs calculated'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }, __('Actions'));
        
        // Duplicate Batch button
        frm.add_custom_button(__('Duplicate Batch'), function() {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.duplicate_batch',
                args: { source_name: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        frappe.set_route('Form', 'Batch AMB', r.message);
                    }
                }
            });
        }, __('Actions'));
        
        // Create Stock Entry button (if not submitted)
        if (frm.doc.docstatus === 1 && !frm.doc.stock_entry_reference) {
            frm.add_custom_button(__('Create Stock Entry'), function() {
                frappe.confirm(
                    __('Create Stock Entry for this batch?'),
                    function() {
                        frm.set_value('auto_create_stock_entry', 1);
                        frm.save();
                    }
                );
            }, __('Create'));
        }
        
        // View Stock Entry button
        if (frm.doc.stock_entry_reference) {
            frm.add_custom_button(__('View Stock Entry'), function() {
                frappe.set_route('Form', 'Stock Entry', frm.doc.stock_entry_reference);
            }, __('View'));
        }
        
        // View Lote AMB button
        if (frm.doc.lote_amb_reference) {
            frm.add_custom_button(__('View Lote AMB'), function() {
                frappe.set_route('Form', 'Lote AMB', frm.doc.lote_amb_reference);
            }, __('View'));
        }
    }
}

// ==================== ENHANCED: LEVEL-SPECIFIC BUTTONS ====================

function add_level_specific_buttons(frm) {
    if (frm.is_new()) return;
    
    switch(frm.doc.custom_batch_level) {
        case '1':
            frm.add_custom_button(__('Create Sublot'), function() {
                create_sublot_batch(frm);
            });
            break;
        case '2':
            frm.add_custom_button(__('Create Container'), function() {
                create_container_batch(frm);
            });
            break;
        case '3':
            frm.add_custom_button(__('Scan Multiple Barcodes'), function() {
                open_bulk_scan_dialog(frm);
            });
            frm.add_custom_button(__('Generate Barrel Serials'), function() {
                generate_bulk_barrel_serials(frm);
            });
            frm.add_custom_button(__('Validate All Weights'), function() {
                validate_all_barrel_weights(frm);
            });
            break;
    }
}

// ==================== HELPER FUNCTIONS ====================

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
    
    // Cost calculation fields
    frm.toggle_display('labor_cost', frm.doc.calculate_cost);
    frm.toggle_display('overhead_cost', frm.doc.calculate_cost);
    frm.toggle_display('total_batch_cost', frm.doc.calculate_cost);
    frm.toggle_display('cost_per_unit', frm.doc.calculate_cost);
    
    // Container section
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
    
    // Quality status indicator
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
        // Set default batch level and company
        if (!frm.doc.custom_batch_level) {
            frm.set_value('custom_batch_level', '1');
        }
        
        // Set default company
        if (!frm.doc.company) {
            frm.set_value('company', frappe.defaults.get_default('company'));
        }
        
        // Set default production start date
        if (!frm.doc.production_start_date) {
            frm.set_value('production_start_date', frappe.datetime.get_today());
        }
        
        // Set default status
        if (!frm.doc.batch_status) {
            frm.set_value('batch_status', 'Draft');
        }
    }
}

function load_user_preferences(frm) {
    // Load user's preferred warehouses, etc.
    frappe.db.get_value('User', frappe.session.user, 'default_warehouse', function(r) {
        if (r && r.default_warehouse && !frm.doc.target_warehouse) {
            frm.set_value('target_warehouse', r.default_warehouse);
        }
    });
}

// ==================== ENHANCED: LEVEL SETTINGS AND UI ====================

function configure_level_settings(frm) {
    const level = frm.doc.custom_batch_level;
    switch(level) {
        case '1':
            frm.set_value('parent_batch_amb', '');
            frm.set_value('is_group', 1);
            break;
        case '2':
            frm.set_value('is_group', 1);
            break;
        case '3':
            frm.set_value('is_group', 1);
            initialize_barrel_management(frm);
            break;
        case '4':
            frm.set_value('is_group', 0);
            break;
        default:
            frm.set_value('is_group', 0);
    }
}

// ==================== ENHANCED: BARREL MANAGEMENT ====================

function initialize_barrel_management(frm) {
    setTimeout(function() {
        update_weight_totals(frm);
    }, 500);
}

function process_quick_barcode_scan(frm) {
    const barcode = frm.doc.quick_barcode_scan;
    if (!validate_code39_format(barcode)) {
        frappe.msgprint('Invalid CODE-39 barcode format');
        frm.set_value('quick_barcode_scan', '');
        return;
    }
    
    if (frm.doc.custom_batch_level == '3') {
        calculate_container_totals(frm);
    }
    
    if (check_duplicate_serial(frm, barcode)) {
        frappe.msgprint('Barrel serial number already exists: ' + barcode);
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
    setTimeout(function() { frm.scroll_to_field('container_barrels'); }, 300);
}

function process_barcode_scan(frm, cdt, cdn, barcode) {
    const row = locals[cdt][cdn];
    if (!validate_code39_format(barcode)) {
        frappe.msgprint('Invalid CODE-39 barcode format');
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

function calculate_net_weight(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.gross_weight && row.tara_weight) {
        const net_weight = row.gross_weight - row.tara_weight;
        frappe.model.set_value(cdt, cdn, 'net_weight', net_weight);
        frappe.model.set_value(cdt, cdn, 'weight_validated', net_weight > 0 && net_weight < row.gross_weight ? 1 : 0);
    }
}

function update_weight_totals(frm) {
    if (frm.doc.custom_batch_level != '3' || !frm.doc.container_barrels) return;
    
    let total_gross = 0, total_tara = 0, total_net = 0, barrel_count = 0;
    
    frm.doc.container_barrels.forEach(row => {
        if (row.gross_weight) total_gross += row.gross_weight;
        if (row.tara_weight) total_tara += row.tara_weight;
        if (row.net_weight) total_net += row.net_weight;
        if (row.barrel_serial_number) barrel_count += 1;
    });
    
    frm.set_value('total_gross_weight', total_gross);
    frm.set_value('total_tara_weight', total_tara);
    frm.set_value('total_net_weight', total_net);
    frm.set_value('barrel_count', barrel_count);
}

// ==================== ENHANCED: VALIDATION HELPERS ====================

function validate_code39_format(barcode) {
    const s = String(barcode || '').toUpperCase();
    // Allowed: A-Z 0-9 and - . space $ / + % *
    return /^[A-Z0-9\-.\\s$\\/+%*]+$/.test(s);
}

function check_duplicate_serial(frm, serial) {
    if (!frm.doc.container_barrels) return false;
    return frm.doc.container_barrels.some(row => row.barrel_serial_number === serial);
}

function validate_barrel_data(frm) {
    if (!frm.doc.container_barrels) return true;
    
    let has_errors = false;
    frm.doc.container_barrels.forEach((row, index) => {
        if (row.barrel_serial_number && !row.gross_weight) {
            frappe.msgprint(`Row ${index + 1}: Gross weight is required for barrel ${row.barrel_serial_number}`);
            has_errors = true;
        }
        if (row.gross_weight && row.tara_weight && row.net_weight <= 0) {
            frappe.msgprint(`Row ${index + 1}: Net weight cannot be zero or negative for barrel ${row.barrel_serial_number}`);
            has_errors = true;
        }
    });
    
    if (has_errors) {
        frappe.throw('Please fix barrel weight validation errors before saving.');
    }
    return true;
}

// ==================== ENHANCED: BULK OPERATIONS ====================

function open_bulk_scan_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: 'Bulk Barcode Scanning',
        fields: [
            { fieldtype: 'Small Text', fieldname: 'barcode_list', label: 'Scan Multiple Barcodes (one per line)', description: 'Scan or paste CODE-39 barcodes, one per line' },
            { fieldtype: 'Link', fieldname: 'bulk_packaging_type', label: 'Default Packaging Type', options: 'Item', reqd: 1 }
        ],
        primary_action_label: 'Add Barrels',
        primary_action: function(values) {
            process_bulk_barcodes(frm, values.barcode_list, values.bulk_packaging_type);
            dialog.hide();
        }
    });
    
    if (frm.doc.default_packaging_type) {
        dialog.set_value('bulk_packaging_type', frm.doc.default_packaging_type);
    }
    dialog.show();
}

function process_bulk_barcodes(frm, barcode_text, packaging_type) {
    const barcodes = barcode_text.split('\\n').filter(b => b.trim());
    let added_count = 0;
    
    barcodes.forEach(b => {
        const barcode = b.trim();
        if (!validate_code39_format(barcode)) {
            frappe.msgprint(`Invalid barcode format: ${barcode}`);
            return;
        }
        if (check_duplicate_serial(frm, barcode)) {
            frappe.msgprint(`Duplicate barcode: ${barcode}`);
            return;
        }
        
        const row = frm.add_child('container_barrels');
        row.barrel_serial_number = barcode;
        row.packaging_type = packaging_type;
        row.scan_timestamp = frappe.datetime.now_datetime();
        added_count += 1;
    });
    
    frm.refresh_field('container_barrels');
    if (added_count > 0) {
        frappe.msgprint(`Added ${added_count} barrels successfully`);
        fetch_tara_weights_for_all_rows(frm, packaging_type);
    }
}

function fetch_tara_weights_for_all_rows(frm, packaging_type) {
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Item', name: packaging_type },
        callback: function(r) {
            if (r.message && r.message.weight_per_unit) {
                const tara_weight = r.message.weight_per_unit;
                (frm.doc.container_barrels || []).forEach(row => {
                    if (row.packaging_type === packaging_type && !row.tara_weight) {
                        frappe.model.set_value('Container Barrels', row.name, 'tara_weight', tara_weight);
                    }
                });
                frm.refresh_field('container_barrels');
            }
        }
    });
}

function generate_bulk_barrel_serials(frm) {
    const dialog = new frappe.ui.Dialog({
        title: 'Generate Barrel Serial Numbers',
        fields: [
            { fieldtype: 'Int', fieldname: 'barrel_count', label: 'Number of Barrels', reqd: 1, default: 20 },
            { fieldtype: 'Link', fieldname: 'bulk_packaging_type', label: 'Packaging Type', options: 'Item', reqd: 1 }
        ],
        primary_action_label: 'Generate Serials',
        primary_action: function(values) {
            generate_sequential_serials(frm, values.barrel_count, values.bulk_packaging_type);
            dialog.hide();
        }
    });
    
    if (frm.doc.default_packaging_type) {
        dialog.set_value('bulk_packaging_type', frm.doc.default_packaging_type);
    }
    dialog.show();
}

function generate_sequential_serials(frm, count, packaging_type) {
    const container_code = frm.doc.title || frm.doc.custom_generated_batch_name;
    if (!container_code) {
        frappe.msgprint('Container code not available. Please save the container first.');
        return;
    }
    
    let max_seq = 0;
    (frm.doc.container_barrels || []).forEach(barrel => {
        if (barrel.barrel_serial_number && barrel.barrel_serial_number.startsWith(container_code)) {
            const match = barrel.barrel_serial_number.match(/-([0-9]+)$/);
            if (match) {
                max_seq = Math.max(max_seq, parseInt(match[1], 10));
            }
        }
    });
    
    for (let i = 1; i <= count; i++) {
        const serial_num = (max_seq + i).toString().padStart(3, '0');
        const serial = `${container_code}-${serial_num}`;
        const row = frm.add_child('container_barrels');
        row.barrel_serial_number = serial;
        row.packaging_type = packaging_type;
    }
    
    frm.refresh_field('container_barrels');
    frappe.msgprint(`Generated ${count} barrel serial numbers`);
    fetch_tara_weights_for_all_rows(frm, packaging_type);
}

function validate_all_barrel_weights(frm) {
    if (!frm.doc.container_barrels) {
        frappe.msgprint('No barrels to validate');
        return;
    }
    
    let validated_count = 0, error_count = 0;
    frm.doc.container_barrels.forEach(row => {
        if (row.gross_weight && row.tara_weight && row.net_weight > 0) {
            frappe.model.set_value('Container Barrels', row.name, 'weight_validated', 1);
            validated_count += 1;
        } else {
            error_count += 1;
        }
    });
    
    frm.refresh_field('container_barrels');
    frappe.msgprint(`Validation complete: ${validated_count} valid, ${error_count} with errors`);
}

// ==================== ENHANCED: CREATE CHILDREN BY LEVEL ====================

function create_sublot_batch(parent_frm) {
    frappe.new_doc('Batch AMB', {
        'custom_batch_level': '2',
        'parent_batch_amb': parent_frm.doc.name,
        'work_order_ref': parent_frm.doc.work_order_ref,
        'sales_order_related': parent_frm.doc.sales_order_related,
        'production_plant_name': parent_frm.doc.production_plant_name,
        'custom_batch_year': parent_frm.doc.custom_batch_year,
        'custom_plant_code': parent_frm.doc.custom_plant_code,
        'tds_info': parent_frm.doc.tds_info,
        'wo_item_name': parent_frm.doc.wo_item_name,
        'item_to_manufacture': parent_frm.doc.item_to_manufacture,
        'tds_item_name': parent_frm.doc.tds_item_name,
        'is_group': 1
    });
}

function create_container_batch(parent_frm) {
    frappe.new_doc('Batch AMB', {
        'custom_batch_level': '3',
        'parent_batch_amb': parent_frm.doc.name,
        'work_order_ref': parent_frm.doc.work_order_ref,
        'sales_order_related': parent_frm.doc.sales_order_related,
        'production_plant_name': parent_frm.doc.production_plant_name,
        'custom_batch_year': parent_frm.doc.custom_batch_year,
        'custom_plant_code': parent_frm.doc.custom_plant_code,
        'tds_info': parent_frm.doc.tds_info,
        'wo_item_name': parent_frm.doc.wo_item_name,
        'item_to_manufacture': parent_frm.doc.item_to_manufacture,
        'tds_item_name': parent_frm.doc.tds_item_name,
        'is_group': 1
    });
}

// ==================== ENHANCED: DATA FETCHING AND GENERATION ====================

function fetch_work_order_data(frm) {
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Work Order', name: frm.doc.work_order_ref },
        callback: function(r) {
            if (!r.message) return;
            const wo = r.message;
            frm.set_value('sales_order_related', wo.sales_order);
            frm.set_value('wo_item_name', wo.item_name);
            frm.set_value('item_to_manufacture', wo.production_item);
            fetch_sales_order_data(frm, wo.sales_order);
            fetch_item_data(frm, wo.production_item);
            if (should_auto_generate(frm)) {
                setTimeout(function() { generate_batch_code(frm); }, 300);
            }
        }
    });
}

function fetch_sales_order_data(frm, sales_order) {
    if (!sales_order) return;
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Sales Order', name: sales_order },
        callback: function(r) {}
    });
}

function fetch_item_data(frm, item_code) {
    if (!item_code) return;
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Item', name: item_code },
        callback: function(r) {
            if (!r.message) return;
            const item = r.message;
            frm.set_value('tds_info', item.item_name);
            frm.set_value('tds_item_name', item.item_name);
        }
    });
}

function fetch_default_tara_weight(frm) {
    if (!frm.doc.default_packaging_type) return;
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Item', name: frm.doc.default_packaging_type },
        callback: function(r) {
            if (r.message && r.message.weight_per_unit) {
                frappe.msgprint(`Default tara weight: ${r.message.weight_per_unit} kg`);
            }
        }
    });
}

function should_auto_generate(frm) {
    const has_reference = !!frm.doc.work_order_ref;
    const has_level = !!frm.doc.custom_batch_level;
    const has_plant_code = !!frm.doc.custom_plant_code;
    const has_plant_name = !!frm.doc.production_plant_name;
    const ok = has_reference && has_level && (has_plant_code || has_plant_name);
    if (ok) console.log('Auto-generate conditions met');
    return ok;
}

function generate_batch_code(frm) {
    const level = parseInt(frm.doc.custom_batch_level, 10) || 1;
    if (level === 1) {
        generate_level_1_batch_code(frm);
    } else {
        generate_sublot_batch_code(frm, level);
    }
}

function generate_level_1_batch_code(frm) {
    get_base_components(frm, function(components) {
        const consecutive = components.consecutive.toString().padStart(5, '0');
        const plant_code = String(components.plant_code);
        let final_batch_code;
        if (components.series_type === 'P') {
            // P-INV/P-VTA-00001-
            final_batch_code = `${components.product_code}-${consecutive}-${plant_code}`;
        } else {
            // Standard: PRODUCT(4)+CONSEC(5)+PLANT
            final_batch_code = `${components.product_code}${consecutive}${plant_code}`;
        }
        frm.set_value('title', final_batch_code);
        frm.set_value('custom_generated_batch_name', final_batch_code);
        frm.set_value('custom_consecutive_number', consecutive);
        frm.set_value('custom_plant_code', plant_code);
        frm.refresh_field('title');
        frm.refresh_field('custom_generated_batch_name');
    });
}

function generate_sublot_batch_code(frm, level) {
    if (!frm.doc.parent_batch_amb) return;
    if (frm.doc.parent_batch_amb === frm.doc.name) {
        frappe.msgprint('A batch cannot be its own parent');
        frm.set_value('parent_batch_amb', '');
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Batch AMB', name: frm.doc.parent_batch_amb },
        callback: function(r) {
            if (!r.message) { frappe.msgprint('Could not fetch parent batch information'); return; }
            const parent_batch = r.message;
            const parent_batch_code = parent_batch.title || parent_batch.custom_generated_batch_name;
            if (!parent_batch_code) { frappe.msgprint('Parent batch does not have a valid batch code'); return; }
            get_next_sublot_consecutive(frm, parent_batch_code, function(next_consecutive) {
                let final_batch_code;
                if (level == 3) {
                    final_batch_code = `${parent_batch_code}-C${next_consecutive}`;
                } else {
                    final_batch_code = `${parent_batch_code}-${next_consecutive}`;
                }
                frm.set_value('title', final_batch_code);
                frm.set_value('custom_generated_batch_name', final_batch_code);
                frm.set_value('custom_sublot_consecutive', parseInt(next_consecutive, 10));
                frm.refresh_field('title');
                frm.refresh_field('custom_generated_batch_name');
            });
        }
    });
}

function get_base_components(frm, callback) {
    frappe.call({
        method: 'frappe.client.get',
        args: { doctype: 'Work Order', name: frm.doc.work_order_ref },
        callback: function(r) {
            if (!r.message) {
                return callback({
                    product_code: '0000',
                    consecutive: 1,
                    plant_code: derive_plant_code(frm),
                    source: 'fallback',
                    series_type: 'WO'
                });
            }
            
            const wo = r.message;
            const naming = String(wo.naming_series || wo.name || '').toUpperCase();
            const isPInv = /^P-INV/.test(naming);
            const isPVta = /^P-VTA/.test(naming);
            let series_type = 'WO';
            let product_code = '';
            
            if (isPInv || isPVta) {
                series_type = 'P';
                const m = naming.match(/^(P-(?:INV|VTA))/);
                product_code = m ? m[1] : 'P';
            } else {
                if (wo.production_item) {
                    const m = String(wo.production_item).match(/^(\\d{4})/);
                    product_code = m ? m[1] : '0000';
                } else {
                    product_code = '0000';
                }
            }
            
            let consecutive = 1;
            const wm = String(wo.name || '').match(/(\\d+)$/);
            if (wm) consecutive = parseInt(wm[1], 10);
            
            const plant_code = derive_plant_code(frm);
            callback({ product_code, consecutive, plant_code, source: 'work_order', series_type });
        }
    });
}

function derive_plant_code(frm) {
    const cp = parseInt(frm.doc.custom_plant_code, 10);
    if (!isNaN(cp) && cp > 0) return cp;
    const m = String(frm.doc.production_plant_name || '').match(/^(\\d+)/);
    return m ? parseInt(m[1], 10) : 1;
}

function calculate_container_totals(frm) {
    // Enhanced: Calculate both quantity and weight totals
    let total_qty = 0;
    let total_containers = 0;
    let total_gross = 0;
    let total_tara = 0;
    let total_net = 0;
    let barrel_count = 0;
    
    if (frm.doc.container_barrels) {
        frm.doc.container_barrels.forEach(function(barrel) {
            if (barrel.quantity) {
                total_qty += flt(barrel.quantity);
            }
            if (barrel.gross_weight) {
                total_gross += parseFloat(barrel.gross_weight);
            }
            if (barrel.tara_weight) {
                total_tara += parseFloat(barrel.tara_weight);
            }
            if (barrel.net_weight) {
                total_net += parseFloat(barrel.net_weight);
            }
            if (barrel.barrel_serial_number && barrel.barrel_serial_number.trim()) {
                barrel_count += 1;
            }
            total_containers++;
        });
    }
    
    // Set baseline totals
    frm.set_value('total_container_qty', total_qty);
    frm.set_value('total_containers', total_containers);
    
    // Set enhanced totals
    if (frm.doc.custom_batch_level == '3') {
        frm.set_value('total_gross_weight', total_gross);
        frm.set_value('total_tara_weight', total_tara);
        frm.set_value('total_net_weight', total_net);
        frm.set_value('barrel_count', barrel_count);
    }
}

function get_next_sublot_consecutive(frm, parent_batch_code, callback) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Batch AMB',
            filters: { 'parent_batch_amb': frm.doc.parent_batch_amb, 'name': ['!=', frm.doc.name || ''] },
            fields: ['name', 'title', 'custom_generated_batch_name'],
            limit_page_length: 100
        },
        callback: function(r) {
            let next_consecutive = 1;
            if (r.message && r.message.length > 0) {
                const existing_consecutives = [];
                const parentEsc = parent_batch_code.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
                const patterns = [ new RegExp(`^${parentEsc}-(\\d+)$`), new RegExp(`^${parentEsc}-C(\\d+)$`) ];
                
                r.message.forEach(function(batch) {
                    const batch_name = batch.title || batch.custom_generated_batch_name || '';
                    patterns.forEach(pattern => {
                        const match = batch_name.match(pattern);
                        if (match) existing_consecutives.push(parseInt(match[1], 10));
                    });
                });
                
                if (existing_consecutives.length > 0) next_consecutive = Math.max(...existing_consecutives) + 1;
            }
            callback(next_consecutive);
        }
    });
}

// ==================== BASELINE CALCULATION FUNCTIONS ====================

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

function validate_container_quantities(frm) {
    if (!frm.doc.use_containers || !frm.doc.container_barrels) return;
    
    let container_total = 0;
    frm.doc.container_barrels.forEach(function(row) {
        if (row.quantity) {
            container_total += flt(row.quantity);
        }
    });
    
    let produced = flt(frm.doc.produced_qty);
    let difference = Math.abs(container_total - produced);
    
    if (difference > 0.001) {
        frappe.msgprint({
            title: __('Quantity Mismatch'),
            message: __('Container total ({0}) does not match produced quantity ({1})', 
                [container_total, produced]),
            indicator: 'orange'
        });
    }
}

function validate_production_dates(frm) {
    if (frm.doc.production_start_date && frm.doc.production_end_date) {
        let start = frappe.datetime.str_to_obj(frm.doc.production_start_date);
        let end = frappe.datetime.str_to_obj(frm.doc.production_end_date);
        
        if (end < start) {
            frappe.msgprint({
                title: __('Invalid Dates'),
                message: __('Production end date cannot be before start date'),
                indicator: 'red'
            });
            frm.set_value('production_end_date', '');
        }
    }
}

console.log('Enhanced Batch AMB client script loaded - Baseline + Container Management');
