// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('COA AMB', {
    refresh: function(frm) {
        setup_coa_buttons(frm);
        apply_coa_filters(frm);
        show_coa_indicators(frm);
        
        // ============================================================
        // 117A FIX: Ensure save button is always visible and enabled
        // ============================================================
        // Force show primary save button for draft documents
        if (frm.doc.docstatus === 0) {
            frm.page.set_primary_action(__('Save'), () => {
                frm.save();
            }, null, __('Save'));
        }
    },
    
    linked_tds: function(frm) {
        if (frm.doc.linked_tds) {
            // Check if draft TDS is selected (show warning)
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TDS Product Specification',
                    name: frm.doc.linked_tds,
                    fields: ['docstatus', 'name']
                },
                callback: function(r) {
                    if (r.message && r.message.docstatus === 0) {
                        frappe.msgprint({
                            title: __('⚠️ Warning: Draft TDS'),
                            message: __('TDS "{0}" is in DRAFT status. Only SUBMITTED TDS should be used for final COA certification. Please review and submit the TDS before proceeding.', [frm.doc.linked_tds]),
                            indicator: 'orange'
                        });
                    }
                }
            });
            
            // Fetch TDS details and populate COA
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TDS Product Specification',
                    name: frm.doc.linked_tds
                },
                callback: function(r) {
                    if (r.message) {
                        // Set product details
                        frm.set_value('product_item', r.message.product_item);
                        frm.set_value('item_name', r.message.item_name);
                        frm.set_value('item_code', r.message.item_code);
                        
                        // Copy specifications to quality parameters
                        if (!frm.doc.coa_quality_test_parameter || 
                            frm.doc.coa_quality_test_parameter.length === 0) {
                            copy_tds_specifications(frm, r.message);
                        }
                        
                        frappe.show_alert({
                            message: __('TDS specifications loaded'),
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    },
    
    product_item: function(frm) {
        if (frm.doc.product_item) {
            frappe.db.get_value('Item', frm.doc.product_item, 
                ['item_name', 'item_code'], 
                function(r) {
                    if (r) {
                        frm.set_value('item_name', r.item_name);
                        frm.set_value('item_code', r.item_code);
                    }
                }
            );
            // Refresh TDS filter when product changes
            frm.refresh_field('linked_tds');
        }
    },
    
    batch_reference: function(frm) {
        if (frm.doc.batch_reference) {
            // Get batch details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Batch AMB',
                    name: frm.doc.batch_reference
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('product_item', r.message.item_to_manufacture);
                        frm.set_value('production_date', r.message.production_end_date);
                        frm.set_value('batch_quantity', r.message.produced_qty);
                    }
                }
            });
        }
    },
    
    approval_date: function(frm) {
        if (frm.doc.approval_date) {
            // Auto-set approved by
            if (!frm.doc.approved_by) {
                frm.set_value('approved_by', frappe.session.user);
            }
        }
    },
    
    // ============================================================
    // 117K FIX: Dynamic TDS filter based on show_draft_tds checkbox
    // ============================================================
    show_draft_tds: function(frm) {
        // Refresh the TDS link field when checkbox changes
        frm.refresh_field('linked_tds');
        // Also show info message
        if (frm.doc.show_draft_tds) {
            frappe.show_alert({
                message: __('Showing both Draft and Submitted TDS. Draft TDS will have a warning if selected.'),
                indicator: 'blue'
            });
        } else {
            frappe.show_alert({
                message: __('Showing only Submitted TDS. Check "Include Draft TDS" to also see draft versions.'),
                indicator: 'blue'
            });
        }
    },
    
    // ============================================================
    // 117A FIX: Before save - allow partial saves with empty rows
    // ============================================================
    before_save: function(frm) {
        // Allow save even if some rows are empty (no validation on save)
        // The server will skip empty rows in validate_test_parameters()
        return true;
    }
});

// Child table events
frappe.ui.form.on('COA Quality Test Parameter', {
    result: function(frm, cdt, cdn) {
        // Validate result against specification
        let row = locals[cdt][cdn];
        validate_test_result(frm, row);
    },
    
    custom_is_title_row: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.custom_is_title_row) {
            // Clear validation fields for title rows
            frappe.model.set_value(cdt, cdn, 'status', 'N/A');
            frappe.model.set_value(cdt, cdn, 'result', '');
        }
    }
});

function setup_coa_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Create from TDS button
        if (!frm.doc.linked_tds) {
            frm.add_custom_button(__('Link TDS'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Select TDS'),
                    fields: [{
                        fieldname: 'tds',
                        fieldtype: 'Link',
                        label: __('TDS Product Specification'),
                        options: 'TDS Product Specification',
                        reqd: 1,
                        get_query: function() {
                            let show_draft = frm.doc.show_draft_tds || 0;
                            return {
                                filters: show_draft ? 
                                    { 'docstatus': ['in', [0, 1]] } : 
                                    { 'docstatus': 1 }
                            };
                        }
                    }],
                    primary_action_label: __('Link'),
                    primary_action: function(values) {
                        frm.set_value('linked_tds', values.tds);
                        d.hide();
                    }
                });
                d.show();
            }, __('Actions'));
        }
        
        // Generate PDF button
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Generate PDF'), function() {
                frappe.call({
                    method: 'amb_w_tds.amb_w_tds.doctype.coa_amb.coa_amb.generate_coa_pdf',
                    args: { coa_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            window.open(r.message);
                        }
                    }
                });
            }, __('Actions'));
        }
        
        // View Batch button
        if (frm.doc.batch_reference) {
            frm.add_custom_button(__('View Batch'), function() {
                frappe.set_route('Form', 'Batch AMB', frm.doc.batch_reference);
            }, __('View'));
        }
        
        // Validate All Tests button
        if (frm.doc.coa_quality_test_parameter && frm.doc.coa_quality_test_parameter.length > 0) {
            frm.add_custom_button(__('Validate All Tests'), function() {
                frappe.call({
                    method: 'amb_w_tds.amb_w_tds.doctype.coa_amb.coa_amb.validate_all_tests',
                    args: { coa_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(r.message.message);
                            frm.refresh();
                        }
                    }
                });
            }, __('Actions'));
        }
    }
}

// ============================================================
// 117K FIX: Dynamic query for TDS link field
// ============================================================
function apply_coa_filters(frm) {
    // Dynamic TDS filter based on show_draft_tds checkbox
    frm.set_query('linked_tds', function() {
        let show_draft = frm.doc.show_draft_tds || 0;
        let filters = {};
        
        // Docstatus filter
        if (show_draft) {
            filters['docstatus'] = ['in', [0, 1]];  // Show both draft and submitted
        } else {
            filters['docstatus'] = 1;  // Show only submitted
        }
        
        // Product filter (optional - only if product_item has a value)
        if (frm.doc.product_item && frm.doc.product_item !== "") {
            filters['product_item'] = frm.doc.product_item;
        }
        
        return { filters: filters };
    });
    
    // Filter batches
    frm.set_query('batch_reference', function() {
        let filters = { 'docstatus': 1 };
        if (frm.doc.product_item && frm.doc.product_item !== "") {
            filters['item_to_manufacture'] = frm.doc.product_item;
        }
        return { filters: filters };
    });
}

function show_coa_indicators(frm) {
    if (frm.doc.overall_result) {
        let color = frm.doc.overall_result === 'Pass' ? 'green' : 
                    frm.doc.overall_result === 'Fail' ? 'red' : 'orange';
        let icon = frm.doc.overall_result === 'Pass' ? '✅' : 
                   frm.doc.overall_result === 'Fail' ? '❌' : '⚠️';
        frm.dashboard.set_headline_alert(
            __('{0} Quality: {1}', [icon, frm.doc.overall_result]),
            color
        );
    }
}

function copy_tds_specifications(frm, tds) {
    // Use the correct field: item_quality_inspection_parameter
    let specifications = tds.item_quality_inspection_parameter || tds.specifications || [];
    
    if (specifications.length === 0) {
        frappe.msgprint({
            title: __('No Specifications'),
            message: __('No quality test parameters found in the selected TDS.'),
            indicator: 'orange'
        });
        return;
    }
    
    frm.clear_table('coa_quality_test_parameter');
    
    specifications.forEach(function(spec) {
        let row = frm.add_child('coa_quality_test_parameter');
        
        // Check if this is a title row
        let is_title = spec.is_title || spec.custom_is_title_row || 0;
        
        if (is_title) {
            row.custom_is_title_row = 1;
            row.parameter_name = null;
            row.specification = spec.title_text || spec.specification || 'Section Header';
            row.status = 'N/A';
        } else {
            row.custom_is_title_row = 0;
            row.parameter_name = spec.parameter_name || spec.parameter || spec.specification;
            row.specification = spec.value || spec.specification || '';
            row.test_method = spec.test_method || '';
            row.min_value = spec.min_value;
            row.max_value = spec.max_value;
            row.numeric = spec.numeric || 0;
            row.formula_based_criteria = spec.formula_based_criteria || 0;
            row.acceptance_formula = spec.acceptance_formula || '';
            row.parameter_group = spec.parameter_group;
            row.status = 'Pending';
        }
    });
    
    frm.refresh_field('coa_quality_test_parameter');
    
    frappe.show_alert({
        message: __('Copied {0} parameters from TDS', [specifications.length]),
        indicator: 'green'
    });
}

function validate_test_result(frm, row) {
    if (!row.result || !row.specification || row.custom_is_title_row) return;
    
    // Simple validation - can be enhanced with complex logic
    let result = parseFloat(row.result);
    if (!isNaN(result)) {
        // Extract min/max from specification if formatted like "10-20"
        let match = row.specification.match(/(\d+\.?\d*)\s*-\s*(\d+\.?\d*)/);
        if (match) {
            let min = parseFloat(match[1]);
            let max = parseFloat(match[2]);
            
            if (result < min || result > max) {
                frappe.msgprint({
                    title: __('Result Out of Specification'),
                    message: __('{0}: Result {1} is outside specification {2}', 
                        [row.parameter_name, result, row.specification]),
                    indicator: 'orange'
                });
            }
        }
    }
}
