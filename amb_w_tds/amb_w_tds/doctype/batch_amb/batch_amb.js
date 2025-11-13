frappe.ui.form.on('Batch AMB', {
    onload: function(frm) {
        // Initialize custom properties
        frm.custom_bom_data = {};
    },

    refresh: function(frm) {
        // Clear existing buttons
        frm.clear_custom_buttons();
        
        // Show buttons based on document status and BOM progress
        if (frm.doc.docstatus === 0) { // Draft
            // Only show MRP BOM button if no BOM exists
            if (!frm.doc.bom_reference && !frm.doc.standard_bom_reference) {
                frm.add_custom_button(__('Generate MRP BOM'), function() {
                    generate_mrp_bom(frm);
                }).addClass('btn-primary');
            }
            
        } else if (frm.doc.docstatus === 1) { // Submitted
            // MRP BOM button
            if (!frm.doc.bom_reference && !frm.doc.standard_bom_reference) {
                frm.add_custom_button(__('Generate MRP BOM'), function() {
                    generate_mrp_bom(frm);
                }).addClass('btn-primary');
            }
            
            // Standard BOM button (only if MRP BOM exists but no Standard BOM)
            if (frm.doc.bom_reference && !frm.doc.standard_bom_reference) {
                frm.add_custom_button(__('Generate Standard BOM'), function() {
                    generate_standard_bom(frm);
                }).addClass('btn-warning');
            }
            
            // Cost Breakdown button (if any BOM exists)
            if (frm.doc.bom_reference || frm.doc.standard_bom_reference) {
                frm.add_custom_button(__('View Cost Breakdown'), function() {
                    view_cost_breakdown(frm);
                }).addClass('btn-info');
                
                frm.add_custom_button(__('Create Work Order'), function() {
                    create_work_order(frm);
                }).addClass('btn-success');
            // Add custom buttons for BOM generation
            if (frm.doc.item_to_manufacture && !frm.doc.bom_reference) {
                frm.add_custom_button(__('Generate BOM'), function() {
                    // Trigger BOM generation wizard
                });

            }
        },
        
        work_order_ref: function(frm) {
          // Auto-populate batch data from work order
        },
        
        item_to_manufacture: function(frm) {
            // Fetch TDS and standard BOM for item
        }
        });
        
        // Always show refresh button

        frm.add_custom_button(__('Refresh Status'), function() {
            frm.reload_doc();
        });
    },

    validate: function(frm) {
        // Client-side validation for BOM generation
        if (frm.doc.batch_items && frm.doc.batch_items.length === 0) {
            frappe.msgprint({
                title: __('Validation Error'),
                message: __('Batch must have at least one item for BOM generation'),
                indicator: 'red'
            });
            frappe.validated = false;
        }
    }
});

// MRP BOM Generation
function generate_mrp_bom(frm) {
    // Validate items before generating BOM
    if (!frm.doc.batch_items || frm.doc.batch_items.length === 0) {
        frappe.msgprint({
            title: __('Validation Error'),
            message: __('Please add items to the batch before generating BOM'),
            indicator: 'red'
        });
        return;
    }
    
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_mrp_bom',
        args: {
            batch_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating MRP BOM...'),
        callback: function(r) {
            if (r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('BOM Generation Failed'),
                    message: r.message.message,
                    indicator: 'red'
                });
            }
        }
    });
}

// Standard BOM Generation
function generate_standard_bom(frm) {
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.generate_standard_bom',
        args: {
            batch_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating Standard BOM...'),
        callback: function(r) {
            if (r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __('Standard BOM Generation Failed'),
                    message: r.message.message,
                    indicator: 'red'
                });
            }
        }
    });
}

// Cost Breakdown
function view_cost_breakdown(frm) {
    const bom_name = frm.doc.standard_bom_reference || frm.doc.bom_reference;
    
    if (!bom_name) {
        frappe.msgprint(__('No BOM reference found for cost breakdown'));
        return;
    }
    
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.get_bom_cost_breakdown',
        args: {
            bom_name: bom_name
        },
        freeze: true,
        freeze_message: __('Calculating cost breakdown...'),
        callback: function(r) {
            if (r.message.success) {
                const cost = r.message.cost_breakdown;
                show_cost_dialog(cost, bom_name);
            } else {
                frappe.msgprint({
                    title: __('Cost Calculation Failed'),
                    message: r.message.message,
                    indicator: 'red'
                });
            }
        }
    });
}

// Work Order Creation
function create_work_order(frm) {
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.create_work_order',
        args: {
            batch_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating Work Order...'),
        callback: function(r) {
            if (r.message.success) {
                frappe.msgprint({
                    title: __('Success'),
                    message: r.message.message,
                    indicator: 'green'
                });
                
                // Optionally open the work order
                if (r.message.work_order_name) {
                    frappe.set_route('Form', 'Work Order', r.message.work_order_name);
                }
            } else {
                frappe.msgprint({
                    title: __('Work Order Creation Failed'),
                    message: r.message.message,
                    indicator: 'red'
                });
            }
        }
    });
}

// Show Cost Breakdown Dialog
function show_cost_dialog(cost, bom_name) {
    const dialog = new frappe.ui.Dialog({
        title: __('BOM Cost Breakdown - {0}', [bom_name]),
        fields: [
            {
                fieldname: 'cost_html',
                fieldtype: 'HTML',
                options: `
                    <div class="cost-breakdown" style="padding: 15px;">
                        <div class="row">
                            <div class="col-sm-6">
                                <h4 style="color: #2E86AB;">Total Cost: ${format_currency(cost.total_cost)}</h4>
                                <h5 style="color: #A23B72;">Cost per Unit: ${format_currency(cost.cost_per_unit)}</h5>
                            </div>
                            <div class="col-sm-6">
                                <div class="well" style="background: #f8f9fa; padding: 10px;">
                                    <p><strong>Quantity:</strong> ${cost.quantity}</p>
                                    <p><strong>Items:</strong> ${cost.item_count}</p>
                                </div>
                            </div>
                        </div>
                        <hr>
                        <table class="table table-bordered" style="margin-top: 15px;">
                            <thead class="thead-light">
                                <tr>
                                    <th>Cost Component</th>
                                    <th style="text-align: right;">Amount</th>
                                    <th style="text-align: right;">Percentage</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Material Cost</td>
                                    <td style="text-align: right;">${format_currency(cost.total_material_cost)}</td>
                                    <td style="text-align: right;">${calculate_percentage(cost.total_material_cost, cost.total_cost)}%</td>
                                </tr>
                                <tr>
                                    <td>Operation Cost</td>
                                    <td style="text-align: right;">${format_currency(cost.operation_cost)}</td>
                                    <td style="text-align: right;">${calculate_percentage(cost.operation_cost, cost.total_cost)}%</td>
                                </tr>
                                <tr style="background-color: #e9ecef; font-weight: bold;">
                                    <td><strong>Total Cost</strong></td>
                                    <td style="text-align: right;"><strong>${format_currency(cost.total_cost)}</strong></td>
                                    <td style="text-align: right;"><strong>100%</strong></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                `
            }
        ],
        size: 'large',
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });
    
    dialog.show();
}

// Format currency helper
function format_currency(amount) {
    return frappe.format(amount, { fieldtype: 'Currency' });
}

// Calculate percentage helper
function calculate_percentage(part, total) {
    if (!total || total === 0) return 0;
    return ((part / total) * 100).toFixed(2);
}

// Add this to handle batch_items table changes
frappe.ui.form.on('Batch AMB Item', {
    batch_items_add: function(frm, cdt, cdn) {
        update_bom_buttons(frm);
    },
    batch_items_remove: function(frm, cdt, cdn) {
        update_bom_buttons(frm);
    }
});

function update_bom_buttons(frm) {
    // This function can be used to dynamically update button states
    // based on the batch_items table content
    if (frm.doc.batch_items && frm.doc.batch_items.length > 0) {
        // Enable BOM buttons if items exist
        $('.btn-primary').prop('disabled', false);
    } else {
        // Disable BOM buttons if no items
        $('.btn-primary').prop('disabled', true);
    }
}
