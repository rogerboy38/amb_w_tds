frappe.ui.form.on('BOM Enhancement', {
    refresh: function(frm) {
        // Add custom buttons
        frm.add_custom_button(__('Get BOM Details'), function() {
            frm.events.get_bom_details(frm);
        });
        
        frm.add_custom_button(__('Create Enhanced BOM'), function() {
            frm.events.create_enhanced_bom(frm);
        });
        
        frm.add_custom_button(__('Create Version'), function() {
            frm.events.create_version(frm);
        });
        
        // Toggle fields based on enhancement type
        frm.toggle_display(['bom_reference', 'version'], true);
        
        // Set up triggers
        frm.set_query('bom_reference', function() {
            return {
                filters: {
                    'is_active': 1
                }
            };
        });
    },
    
    bom_reference: function(frm) {
        if (frm.doc.bom_reference) {
            frm.events.get_bom_details(frm);
        }
    },
    
    enhancement_type: function(frm) {
        // Show/hide fields based on enhancement type
        if (frm.doc.enhancement_type === 'Cost Optimization') {
            frm.toggle_display(['cost_savings_target', 'optimization_notes'], true);
        } else {
            frm.toggle_display(['cost_savings_target', 'optimization_notes'], false);
        }
        
        if (frm.doc.enhancement_type === 'Quality Improvement') {
            frm.toggle_display(['quality_standards', 'compliance_notes'], true);
        } else {
            frm.toggle_display(['quality_standards', 'compliance_notes'], false);
        }
    },
    
    get_bom_details: function(frm) {
        if (!frm.doc.bom_reference) {
            frappe.msgprint(__('Please select a BOM Reference first'));
            return;
        }
        
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.bom_enhancement.bom_enhancement.get_bom_details',
            args: {
                name: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    frappe.msgprint({
                        title: __('BOM Details'),
                        message: __(`
                            Item: ${r.message.item_name}<br>
                            Quantity: ${r.message.quantity} ${r.message.uom}<br>
                            Reference: ${frm.doc.bom_reference}
                        `)
                    });
                }
            }
        });
    },
    
    create_enhanced_bom: function(frm) {
        if (!frm.doc.bom_reference) {
            frappe.msgprint(__('Please select a BOM Reference first'));
            return;
        }
        
        frappe.confirm(
            __('Are you sure you want to create an enhanced BOM from this enhancement?'),
            function() {
                frappe.call({
                    method: 'create_enhanced_bom',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message.bom_created) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                            
                            // Refresh the form
                            frm.reload_doc();
                        }
                    }
                });
            }
        );
    },
    
    create_version: function(frm) {
        if (!frm.doc.bom_reference) {
            frappe.msgprint(__('Please select a BOM Reference first'));
            return;
        }
        
        frappe.prompt([
            {
                fieldname: 'version',
                fieldtype: 'Data',
                label: __('Version'),
                default: frm.doc.version || '1.0',
                reqd: 1
            },
            {
                fieldname: 'effective_date',
                fieldtype: 'Date',
                label: __('Effective Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            }
        ], function(values) {
            frappe.call({
                method: 'frappe.client.insert',
                args: {
                    doc: {
                        doctype: 'BOM Version',
                        bom_name: frm.doc.bom_reference,
                        version: values.version,
                        bom_enhancement: frm.doc.name,
                        effective_date: values.effective_date,
                        status: 'Draft'
                    }
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: __('BOM Version {0} created successfully').format(r.message.name)
                        });
                        
                        frappe.set_route('Form', 'BOM Version', r.message.name);
                    }
                }
            });
        }, __('Create BOM Version'), __('Create'));
    },
    
    validate: function(frm) {
        // Client-side validation
        if (frm.doc.valid_from && frm.doc.valid_to) {
            let valid_from = new Date(frm.doc.valid_from);
            let valid_to = new Date(frm.doc.valid_to);
            
            if (valid_from > valid_to) {
                frappe.msgprint({
                    title: __('Validation Error'),
                    indicator: 'red',
                    message: __('Valid From date cannot be after Valid To date')
                });
                frappe.validated = false;
            }
        }
    }
});

// Custom functions for BOM Enhancement
frappe.bom_enhancement = {
    calculate_efficiency: function(bom_name) {
        // Calculate efficiency metrics for BOM
        return frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.bom_enhancement.bom_enhancement.calculate_efficiency',
            args: {
                bom_name: bom_name
            }
        });
    },
    
    get_enhancement_history: function(bom_name) {
        // Get enhancement history for a BOM
        return frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.bom_enhancement.bom_enhancement.get_enhancement_history',
            args: {
                bom_name: bom_name
            }
        });
    }
};
