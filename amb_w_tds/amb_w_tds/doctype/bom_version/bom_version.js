frappe.ui.form.on('BOM Version', {
    refresh: function(frm) {
        // Add custom buttons
        frm.add_custom_button(__('Compare with Previous'), function() {
            frm.events.compare_with_previous(frm);
        });
        
        frm.add_custom_button(__('Create New BOM'), function() {
            frm.events.create_new_bom(frm);
        });
        
        frm.add_custom_button(__('Set Active'), function() {
            frm.events.set_active(frm);
        });
        
        frm.add_custom_button(__('View All Versions'), function() {
            frm.events.view_all_versions(frm);
        });
        
        // Set up queries
        frm.set_query('bom_name', function() {
            return {
                filters: {
                    'is_active': 1
                }
            };
        });
        
        frm.set_query('bom_enhancement', function() {
            return {
                filters: {
                    'docstatus': 1
                }
            };
        });
        
        // Show/hide fields based on status
        frm.trigger('update_field_visibility');
    },
    
    bom_name: function(frm) {
        if (frm.doc.bom_name) {
            // Auto-generate version name if not set
            if (!frm.doc.version) {
                frappe.call({
                    method: 'frappe.client.get_value',
                    args: {
                        doctype: 'BOM Version',
                        fieldname: ['version'],
                        filters: {
                            'bom_name': frm.doc.bom_name
                        },
                        order_by: 'creation desc'
                    },
                    callback: function(r) {
                        if (r.message) {
                            let last_version = r.message.version;
                            let new_version = '1.0';
                            
                            if (last_version) {
                                let version_parts = last_version.split('.');
                                let major = parseInt(version_parts[0]) || 1;
                                let minor = parseInt(version_parts[1]) || 0;
                                new_version = major + '.' + (minor + 1);
                            }
                            
                            frm.set_value('version', new_version);
                        }
                    }
                });
            }
            
            // Load BOM details
            frm.trigger('load_bom_details');
        }
    },
    
    effective_date: function(frm) {
        if (frm.doc.effective_date) {
            frm.trigger('update_status_based_on_date');
        }
    },
    
    status: function(frm) {
        frm.trigger('update_field_visibility');
    },
    
    update_field_visibility: function(frm) {
        // Show/hide fields based on status
        if (frm.doc.status === 'Active') {
            frm.toggle_display(['expiration_date', 'deactivation_reason'], true);
        } else {
            frm.toggle_display(['expiration_date', 'deactivation_reason'], false);
        }
        
        if (frm.doc.status === 'Rejected') {
            frm.toggle_display(['rejection_reason'], true);
        } else {
            frm.toggle_display(['rejection_reason'], false);
        }
    },
    
    update_status_based_on_date: function(frm) {
        if (frm.doc.effective_date) {
            let effective_date = new Date(frm.doc.effective_date);
            let today = new Date();
            
            if (effective_date <= today && frm.doc.status === 'Approved') {
                frm.set_value('status', 'Active');
            }
        }
    },
    
    load_bom_details: function(frm) {
        if (frm.doc.bom_name) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'BOM',
                    fieldname: ['item', 'item_name', 'quantity', 'uom', 'with_operations'],
                    filters: {
                        'name': frm.doc.bom_name
                    }
                },
                callback: function(r) {
                    if (r.message) {
                        frm.dashboard.add_indicator(__('Item: {0}', [r.message.item_name]), 'blue');
                        frm.dashboard.add_indicator(__('Quantity: {0} {1}', [r.message.quantity, r.message.uom]), 'green');
                        
                        if (r.message.with_operations) {
                            frm.dashboard.add_indicator(__('With Operations: Yes'), 'orange');
                        }
                    }
                }
            });
        }
    },
    
    compare_with_previous: function(frm) {
        if (!frm.doc.bom_name) {
            frappe.msgprint(__('Please select a BOM first'));
            return;
        }
        
        frappe.call({
            method: 'compare_with_previous_version',
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    if (r.message.has_previous) {
                        let cost_diff = r.message.cost_difference;
                        let cost_color = cost_diff < 0 ? 'green' : (cost_diff > 0 ? 'red' : 'blue');
                        let cost_icon = cost_diff < 0 ? '↓' : (cost_diff > 0 ? '↑' : '→');
                        
                        let msg = __(`
                            <h4>Comparison with Previous Version</h4>
                            <table class="table table-bordered">
                                <tr>
                                    <th>Metric</th>
                                    <th>Previous (${r.message.previous_version})</th>
                                    <th>Current (${frm.doc.version})</th>
                                    <th>Difference</th>
                                </tr>
                                <tr>
                                    <td>Total Cost</td>
                                    <td>${format_currency(r.message.previous_cost)}</td>
                                    <td>${format_currency(r.message.current_cost)}</td>
                                    <td><span style="color: ${cost_color}">${cost_icon} ${format_currency(Math.abs(cost_diff))}</span></td>
                                </tr>
                                <tr>
                                    <td>Item Count</td>
                                    <td>${r.message.previous_items || 0}</td>
                                    <td>${frm.doc.total_items || 0}</td>
                                    <td>${r.message.item_count_difference > 0 ? '+' : ''}${r.message.item_count_difference}</td>
                                </tr>
                            </table>
                        `);
                        
                        frappe.msgprint({
                            title: __('Version Comparison'),
                            message: msg,
                            wide: true
                        });
                    } else {
                        frappe.msgprint({
                            title: __('No Previous Version'),
                            message: __('No previous active version found for comparison'),
                            indicator: 'orange'
                        });
                    }
                }
            }
        });
    },
    
    create_new_bom: function(frm) {
        if (!frm.doc.bom_name) {
            frappe.msgprint(__('Please select a BOM first'));
            return;
        }
        
        frappe.confirm(
            __('Are you sure you want to create a new BOM from this version?'),
            function() {
                frappe.call({
                    method: 'create_new_bom_from_version',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message.bom_created) {
                            frappe.msgprint({
                                title: __('Success'),
                                indicator: 'green',
                                message: r.message.message
                            });
                            
                            frappe.set_route('Form', 'BOM', r.message.new_bom_name);
                        }
                    }
                });
            }
        );
    },
    
    set_active: function(frm) {
        if (frm.doc.docstatus !== 1) {
            frappe.msgprint(__('Please submit the document first'));
            return;
        }
        
        frappe.call({
            method: 'amb_w_tds.amb_w_tds.doctype.bom_version.bom_version.set_version_active',
            args: {
                version_name: frm.doc.name
            },
            callback: function(r) {
                if (r.message.success) {
                    frappe.msgprint({
                        title: __('Success'),
                        indicator: 'green',
                        message: r.message.message
                    });
                    frm.reload_doc();
                }
            }
        });
    },
    
    view_all_versions: function(frm) {
        if (!frm.doc.bom_name) {
            frappe.msgprint(__('Please select a BOM first'));
            return;
        }
        
        frappe.set_route('List', 'BOM Version', {
            bom_name: frm.doc.bom_name
        });
    }
});

// List view settings
frappe.views.ListView.on('BOM Version', {
    refresh: function(listview) {
        // Add custom button to list view
        listview.page.add_menu_item(__('Compare Selected Versions'), function() {
            let selected = listview.get_checked_items();
            if (selected.length !== 2) {
                frappe.msgprint(__('Please select exactly two versions to compare'));
                return;
            }
            
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.doctype.bom_version.bom_version.get_version_comparison',
                args: {
                    version1: selected[0].name,
                    version2: selected[1].name
                },
                callback: function(r) {
                    if (r.message) {
                        let comp = r.message;
                        let msg = __(`
                            <h4>Version Comparison</h4>
                            <table class="table table-bordered">
                                <tr>
                                    <th>Metric</th>
                                    <th>${comp.version1.version}</th>
                                    <th>${comp.version2.version}</th>
                                    <th>Difference</th>
                                </tr>
                                <tr>
                                    <td>Total Cost</td>
                                    <td>${format_currency(comp.version1.total_cost)}</td>
                                    <td>${format_currency(comp.version2.total_cost)}</td>
                                    <td>${format_currency(comp.differences.cost_difference)}</td>
                                </tr>
                                <tr>
                                    <td>Item Count</td>
                                    <td>${comp.version1.total_items || 0}</td>
                                    <td>${comp.version2.total_items || 0}</td>
                                    <td>${comp.differences.item_difference}</td>
                                </tr>
                                <tr>
                                    <td>Status</td>
                                    <td>${comp.version1.status}</td>
                                    <td>${comp.version2.status}</td>
                                    <td>-</td>
                                </tr>
                            </table>
                        `);
                        
                        frappe.msgprint({
                            title: __('Version Comparison'),
                            message: msg,
                            wide: true
                        });
                    }
                }
            });
        });
    }
});
