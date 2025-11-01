// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt
frappe.ui.form.on('Batch AMB', {
// ==================== FORM EVENTS ====================
refresh: function(frm) {
    // Set custom buttons and actions
    setup_custom_buttons(frm);
    
    // Apply field filters
    apply_field_filters(frm);
    
    // Set field dependencies
    setup_field_dependencies(frm);
    
    // Show indicators
    show_status_indicators(frm);
},

onload: function(frm) {
    // Set default values
    set_default_values(frm);
    
    // Load saved preferences
    load_user_preferences(frm);
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

// ==================== BEFORE SAVE ====================
before_save: function(frm) {
    // Calculate totals before saving
    calculate_container_totals(frm);
}
});

// ==================== CHILD TABLE: Container Barrels ====================
frappe.ui.form.on('Container Barrels', {
quantity: function(frm, cdt, cdn) {
    // Recalculate totals when container quantity changes
    calculate_container_totals(frm);
},

// NEW: Individual serial generation for a row
barrel_serial_number: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (!row.barrel_serial_number) {
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_single_container_serial',
            args: { batch_name: frm.doc.name },
            callback: function(r) {
                if (r.message && r.message.serial) {
                    // Update the specific row
                    frm.doc.container_barrels.forEach(function(c_row, index) {
                        if (c_row.name === cdn || c_row.idx === index) {
                            frm.doc.container_barrels[index].barrel_serial_number = r.message.serial;
                        }
                    });
                    frm.refresh_field('container_barrels');
                    
                    frappe.show_alert({
                        message: __('Generated serial: {0}', [r.message.serial]),
                        indicator: 'green'
                    });
                }
            }
        });
    }
},

container_barrels_add: function(frm, cdt, cdn) {
    // Set default values for new container row
    let row = locals[cdt][cdn];
    row.status = 'Available'; // Updated from 'Active' to 'Available'
    
    // Auto-generate serial for new containers
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_single_container_serial',
        args: { batch_name: frm.doc.name },
        callback: function(r) {
            if (r.message && r.message.serial) {
                // Update the specific row
                frm.doc.container_barrels.forEach(function(c_row, index) {
                    if (c_row.name === cdn || c_row.idx === index) {
                        frm.doc.container_barrels[index].barrel_serial_number = r.message.serial;
                    }
                });
                frm.refresh_field('container_barrels');
                
                frappe.show_alert({
                    message: __('Auto-generated serial for new container: {0}', [r.message.serial]),
                    indicator: 'green'
                });
            }
        }
    });
    
    frm.refresh_field('container_barrels');
},

container_barrels_remove: function(frm) {
    // Recalculate totals when container is removed
    calculate_container_totals(frm);
}
});

// ==================== HELPER FUNCTIONS ====================
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

    // ==================== NEW SERIAL GENERATION BUTTONS ====================
    // Generate Container Serials button - for containers without serials
    if (frm.doc.container_barrels) {
        let containers_without_serials = frm.doc.container_barrels.filter(row => !row.barrel_serial_number);
        if (containers_without_serials.length > 0) {
            frm.add_custom_button(__(`Generate Serials (${containers_without_serials.length})`), function() {
                generate_container_serials_for_missing(frm);
            }, __('Container Actions'));
        }
    }
    
    // Auto Generate All Serials button - for all containers
    if (frm.doc.container_barrels && frm.doc.container_barrels.length > 0) {
        frm.add_custom_button(__('Generate All Serials'), function() {
            auto_generate_all_serials(frm);
        }, __('Container Actions'));
    }
    
    // Manual Serial Entry button
    frm.add_custom_button(__('Manual Serial Entry'), function() {
        manual_serial_entry(frm);
    }, __('Container Actions'));
    
    // Validate All Serials button
    if (frm.doc.container_barrels && frm.doc.container_barrels.length > 0) {
        frm.add_custom_button(__('Validate Serials'), function() {
            validate_all_serials(frm);
        }, __('Container Actions'));
    }
    // ==================== END NEW SERIAL GENERATION BUTTONS ====================

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

function calculate_container_totals(frm) {
if (!frm.doc.container_barrels) return;
let total_qty = 0;
let total_containers = 0;

frm.doc.container_barrels.forEach(function(row) {
    if (row.quantity) {
        total_qty += flt(row.quantity);
    }
    total_containers++;
});

frm.set_value('total_container_qty', total_qty);
frm.set_value('total_containers', total_containers);
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

// ==================== NEW SERIAL GENERATION FUNCTIONS ====================

function generate_container_serials_for_missing(frm) {
// Generate serials only for containers that don't have serials
let containers_needing_serials = frm.doc.container_barrels.filter(row => !row.barrel_serial_number);

if (containers_needing_serials.length === 0) {
    frappe.show_alert({
        message: __('All containers already have serial numbers'),
        indicator: 'orange'
    });
    return;
}

frappe.call({
    method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_container_serials',
    args: { 
        batch_name: frm.doc.name,
        container_count: containers_needing_serials.length
    },
    callback: function(r) {
        if (r.message && r.message.serials) {
            let serial_index = 0;
            frm.doc.container_barrels.forEach(function(row, index) {
                if (!row.barrel_serial_number && r.message.serials[serial_index]) {
                    frm.doc.container_barrels[index].barrel_serial_number = r.message.serials[serial_index];
                    serial_index++;
                }
            });
            frm.refresh_field('container_barrels');
            
            frappe.show_alert({
                message: __('Generated {0} container serials', [containers_needing_serials.length]),
                indicator: 'green'
            });
        }
    }
});
}

function auto_generate_all_serials(frm) {
// Automatically generate serials for ALL containers
if (!frm.doc.container_barrels || frm.doc.container_barrels.length === 0) {
    frappe.msgprint({
        title: __('No Containers'),
        message: __('Add containers first before generating serials'),
        indicator: 'orange'
    });
    return;
}

frappe.call({
    method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_container_serials',
    args: { 
        batch_name: frm.doc.name,
        container_count: frm.doc.container_barrels.length
    },
    callback: function(r) {
        if (r.message && r.message.serials) {
            let serial_index = 0;
            frm.doc.container_barrels.forEach(function(row, index) {
                if (r.message.serials[serial_index]) {
                    frm.doc.container_barrels[index].barrel_serial_number = r.message.serials[serial_index];
                    serial_index++;
                }
            });
            frm.refresh_field('container_barrels');
            
            frappe.show_alert({
                message: __('Generated serial numbers for all {0} containers', [frm.doc.container_barrels.length]),
                indicator: 'green'
            });
        }
    }
});
}

function manual_serial_entry(frm) {
let containers_without_serials = frm.doc.container_barrels.filter(row => !row.barrel_serial_number);

if (containers_without_serials.length === 0) {
    frappe.msgprint({
        title: __('All Containers Have Serials'),
        message: __('All containers already have serial numbers assigned'),
        indicator: 'orange'
    });
    return;
}

let d = new frappe.ui.Dialog({
    title: __('Manual Serial Entry'),
    fields: [
        {
            fieldtype: 'HTML',
            fieldname: 'info',
            options: `<div class="alert alert-info">
                       <p><strong>Manual Serial Entry</strong></p>
                       <p>Enter serial numbers for the ${containers_without_serials.length} containers without serials.</p>
                       <p>Format: Enter serials separated by commas or one per line.</p>
                      </div>`
        },
        {
            fieldtype: 'Data',
            fieldname: 'serial_numbers',
            label: 'Serial Numbers',
            reqd: 1,
            description: 'Enter serial numbers separated by commas or new lines'
        }
    ],
    primary_action: function() {
        let data = d.get_values();
        if (data.serial_numbers) {
            let serials = data.serial_numbers.split(/[,|\n]/).map(s => s.trim()).filter(s => s);
            let serial_index = 0;
            
            frm.doc.container_barrels.forEach(function(row, index) {
                if (!row.barrel_serial_number && serials[serial_index]) {
                    frm.doc.container_barrels[index].barrel_serial_number = serials[serial_index];
                    serial_index++;
                }
            });
            frm.refresh_field('container_barrels');
            
            frappe.show_alert({
                message: __('Applied {0} manual serial numbers', [serials.length]),
                indicator: 'green'
            });
            d.hide();
        }
    },
    primary_action_label: __('Apply Serials')
});

d.show();
}

function validate_all_serials(frm) {
if (!frm.doc.container_barrels || frm.doc.container_barrels.length === 0) {
    frappe.msgprint({
        title: __('No Containers'),
        message: __('No containers to validate'),
        indicator: 'orange'
    });
    return;
}

let serials = frm.doc.container_barrels.map(row => row.barrel_serial_number).filter(s => s);
let missing_serials = frm.doc.container_barrels.filter(row => !row.barrel_serial_number);
let duplicate_serials = [];

// Check for duplicates
let serial_counts = {};
serials.forEach(serial => {
    serial_counts[serial] = (serial_counts[serial] || 0) + 1;
});

for (let serial in serial_counts) {
    if (serial_counts[serial] > 1) {
        duplicate_serials.push(serial);
    }
}

let message = '';
let indicator = 'green';

if (missing_serials.length > 0) {
    message += `Missing serials: ${missing_serials.length} containers<br>`;
    indicator = 'orange';
}

if (duplicate_serials.length > 0) {
    message += `Duplicate serials: ${duplicate_serials.join(', ')}<br>`;
    indicator = 'red';
}

if (missing_serials.length === 0 && duplicate_serials.length === 0) {
    message = 'All serial numbers are valid and unique!';
}

frappe.msgprint({
    title: __('Serial Validation Results'),
    message: message,
    indicator: indicator
});
}
🔧 File 2: Enhanced batch_amb.py (Add these methods to your existing file)
Add these methods to your existing Python file at the end of the BatchAMB class:

python
def generate_container_serial(self, batch_name=None):
    """Generate a unique container serial number"""
    if not batch_name:
        batch_name = self.name
        
    if not batch_name:
        frappe.throw(_("Batch name is required to generate serial numbers"))
    
    # Get existing serials for this batch to avoid duplicates
    existing_serials = frappe.get_all(
        "Container Barrels",
        filters={"parent": batch_name, "barrel_serial_number": ["!=", ""]},
        fields=["barrel_serial_number"],
        as_list=True
    )
    
    existing_serial_set = {serial[0] for serial in existing_serials}
    
    # Generate new serial number
    serial_number = self._create_unique_serial(batch_name, existing_serial_set)
    
    return serial_number

def _create_unique_serial(self, batch_name, existing_serials):
    """Create a unique serial number"""
    import random
    import string
    
    batch_prefix = batch_name.replace("BATCH-", "").replace("-", "")
    
    # Generate random component
    while True:
        random_component = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        check_digit = self._calculate_check_digit(batch_prefix + random_component)
        
        serial = f"AMB-{batch_prefix}-{random_component}{check_digit}"
        
        # Check if this serial already exists in system
        if serial not in existing_serials:
            # Also check other batches to ensure global uniqueness
            duplicate = frappe.get_all(
                "Container Barrels",
                filters={"barrel_serial_number": serial},
                limit=1
            )
            if not duplicate:
                return serial

def _calculate_check_digit(self, base_number):
    """Calculate check digit for serial validation"""
    total = 0
    for i, char in enumerate(base_number):
        if char.isdigit():
            total += int(char) * (i + 1)
        else:
            total += ord(char) * (i + 1)
    return str(total % 10)  # Return last digit as check digit

def generate_multiple_serials(self, count):
    """Generate multiple unique serial numbers"""
    serials = []
    batch_name = self.name
    
    if not batch_name:
        frappe.throw(_("Batch name is required to generate serial numbers"))
    
    for i in range(count):
        serial = self.generate_container_serial(batch_name)
        serials.append(serial)
    
    return serials
Add these whitelisted functions at the END of the Python file:

python
@frappe.whitelist()
def generate_container_serials(batch_name, container_count):
    """Generate serial numbers for containers"""
    batch = frappe.get_doc("Batch AMB", batch_name)
    serials = batch.generate_multiple_serials(cint(container_count))
    
    return {
        "serials": serials,
        "count": len(serials)
    }

@frappe.whitelist()
def generate_single_container_serial(batch_name):
    """Generate a single container serial number"""
    batch = frappe.get_doc("Batch AMB", batch_name)
    serial = batch.generate_container_serial(batch_name)
    
    return {
        "serial": serial
    }
