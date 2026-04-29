// Copyright (c) 2024, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('COA AMB', {
    refresh: function(frm) {
        setup_coa_buttons(frm);
        apply_coa_filters(frm);
        show_coa_indicators(frm);
    },
    
    linked_tds: function(frm) {
        if (frm.doc.linked_tds) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'TDS Product Specification',
                    name: frm.doc.linked_tds
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('product_item', r.message.product_item);
                        frm.set_value('item_name', r.message.item_name);
                        frm.set_value('item_code', r.message.item_code);
                        
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
        }
    },
    
    batch_reference: function(frm) {
        if (frm.doc.batch_reference) {
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
            if (!frm.doc.approved_by) {
                frm.set_value('approved_by', frappe.session.user);
            }
        }
    },
    
    // 117K FIX: Dynamic TDS filter based on show_draft_tds checkbox
    show_draft_tds: function(frm) {
        frm.refresh_field('linked_tds');
        if (frm.doc.show_draft_tds) {
            frappe.show_alert({
                message: __('Showing both Draft and Submitted TDS.'),
                indicator: 'blue'
            });
        } else {
            frappe.show_alert({
                message: __('Showing only Submitted TDS.'),
                indicator: 'blue'
            });
        }
    }
});

// Child table events
frappe.ui.form.on('COA Quality Test Parameter', {
    result: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        validate_test_result(frm, row);
    },

    custom_is_title_row: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.custom_is_title_row) {
            frappe.model.set_value(cdt, cdn, 'status', 'N/A');
            frappe.model.set_value(cdt, cdn, 'result', '');
        }
    }
});

function setup_coa_buttons(frm) {
    if (!frm.doc.__islocal) {
        if (!frm.doc.linked_tds) {
            frm.add_custom_button(__('Link TDS'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Select TDS'),
                    fields: [{
                        fieldname: 'tds',
                        fieldtype: 'Link',
                        label: __('TDS Product Specification'),
                        options: 'TDS Product Specification',
                        reqd: 1
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
        
        if (frm.doc.batch_reference) {
            frm.add_custom_button(__('View Batch'), function() {
                frappe.set_route('Form', 'Batch AMB', frm.doc.batch_reference);
            }, __('View'));
        }
    }
}

function apply_coa_filters(frm) {
    // Dynamic TDS filter based on show_draft_tds checkbox
    frm.set_query('linked_tds', function() {
        let show_draft = frm.doc.show_draft_tds || 0;
        let filters = {};
        
        if (show_draft) {
            filters['docstatus'] = ['in', [0, 1]];
        } else {
            filters['docstatus'] = 1;
        }
        
        if (frm.doc.product_item && frm.doc.product_item !== "") {
            filters['item_code'] =  ['like', `%${frm.doc.product_item}%`];
        }
        
        return { filters: filters };
    });
    
    // Filter batches
    frm.set_query('batch_reference', function() {
        let filters = { 'docstatus': 1 };
        if (frm.doc.product_item && frm.doc.product_item !== "") {
            filters['current_item_code'] = frm.doc.product_item;
        }
        return { filters: filters };
    });
}

function show_coa_indicators(frm) {
    // Get all quality test parameters that are not title rows
    let test_rows = (frm.doc.coa_quality_test_parameter || []).filter(row => !row.custom_is_title_row);
    
    let total = test_rows.length;
    let pending = test_rows.filter(row => row.status === 'Pending').length;
    let passed = test_rows.filter(row => row.status === 'Pass').length;
    let failed = test_rows.filter(row => row.status === 'Fail').length;
    
    // Get COA number
    let coa_number = frm.doc.coa_number || frm.doc.name || 'New COA';
    
    // Build consolidated message
    let message = '';
    let color = 'orange';
    
    if (failed > 0) {
        message = `❌ Quality: Fail (${failed}/${total} tests failed) - ${coa_number}`;
        color = 'red';
    } else if (pending > 0 && pending === total) {
        message = `⏳ Quality: Pending (${pending}/${total} tests pending) - ${coa_number}`;
        color = 'orange';
    } else if (pending > 0) {
        message = `🟡 Quality: Partial (${passed} passed, ${pending} pending, ${failed} failed) - ${coa_number}`;
        color = 'yellow';
    } else if (passed === total && total > 0) {
        message = `✅ Quality: Pass (${passed}/${total} tests passed) - ${coa_number}`;
        color = 'green';
    } else if (total === 0) {
        message = `📋 Quality: No Tests - ${coa_number}`;
        color = 'blue';
    }
    
    if (message) {
        frm.dashboard.set_headline_alert(message, color);
    }
}

function copy_tds_specifications(frm, tds) {
    if (!tds.specifications) return;
    
    frm.clear_table('coa_quality_test_parameter');
    
    tds.specifications.forEach(function(spec) {
        let row = frm.add_child('coa_quality_test_parameter');
        row.parameter_name = spec.parameter;
        row.specification = spec.specification;
        row.test_method = spec.test_method;
        row.result = '';
    });
    
    frm.refresh_field('coa_quality_test_parameter');
}

function validate_test_result(frm, row) {
    if (!row.result || !row.specification) return;
    
    let result = parseFloat(row.result);
    if (!isNaN(result)) {
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
