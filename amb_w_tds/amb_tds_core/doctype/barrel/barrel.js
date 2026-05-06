// Copyright (c) 2025, SPC Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Barrel', {
    refresh: function(frm) {
        set_status_indicator(frm);
        add_custom_buttons(frm);
        setup_realtime_updates(frm);
        enhance_form_ui(frm);
        add_quick_info_section(frm);
    },
    
    onload: function(frm) {
        setup_field_dependencies(frm);
        if (!frm.is_new()) {
            load_barrel_analytics(frm);
        }
    },
    
    barrel_volume_gallons: function(frm) {
        calculate_available_volume(frm);
    },
    
    current_fill_level_gallons: function(frm) {
        calculate_available_volume(frm);
        update_fill_percentage(frm);
    },
    
    barrel_type: function(frm) {
        set_default_volumes(frm);
    },
    
    current_status: function(frm) {
        set_status_indicator(frm);
    },
    
    current_location: function(frm) {
        if (frm.doc.current_location) {
            fetch_location_info(frm);
        }
    }
});

function set_status_indicator(frm) {
    const status_colors = {
        'Active': 'green',
        'In Use': 'blue',
        'Available': 'green',
        'Maintenance': 'orange',
        'Retired': 'red',
        'Reserved': 'purple',
        'In Transit': 'yellow'
    };
    
    const color = status_colors[frm.doc.current_status] || 'gray';
    frm.page.set_indicator(frm.doc.current_status, color);
}

function add_custom_buttons(frm) {
    if (!frm.is_new()) {
        frm.add_custom_button(__('Fill Barrel'), function() {
            show_fill_dialog(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Transfer'), function() {
            show_transfer_dialog(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Mark for Maintenance'), function() {
            show_maintenance_dialog(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('View History'), function() {
            show_barrel_history(frm);
        }, __('View'));
        
        frm.add_custom_button(__('View Analytics'), function() {
            show_barrel_analytics(frm);
        }, __('View'));
    }
}

function setup_realtime_updates(frm) {
    frappe.realtime.on('barrel_updated_' + frm.doc.name, function(data) {
        frappe.show_alert({
            message: __('Barrel updated: {0}', [data.message]),
            indicator: 'blue'
        });
        frm.reload_doc();
    });
}

function enhance_form_ui(frm) {
    if (frm.doc.current_fill_level_gallons && frm.doc.barrel_volume_gallons) {
        const percentage = (frm.doc.current_fill_level_gallons / frm.doc.barrel_volume_gallons * 100).toFixed(1);
        
        const html = `
            <div class="barrel-fill-indicator" style="margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span><strong>Fill Level</strong></span>
                    <span><strong>${percentage}%</strong></span>
                </div>
                <div style="width: 100%; height: 30px; background: #f0f0f0; border-radius: 5px; overflow: hidden;">
                    <div style="width: ${percentage}%; height: 100%; background: linear-gradient(90deg, #4CAF50, #45a049);"></div>
                </div>
                <div style="margin-top: 5px; font-size: 12px; color: #666;">
                    ${frm.doc.current_fill_level_gallons} / ${frm.doc.barrel_volume_gallons} gallons
                </div>
            </div>
        `;
        
        frm.set_df_property('current_fill_level_gallons', 'description', html);
    }
}

function add_quick_info_section(frm) {
    if (!frm.is_new()) {
        const created = moment(frm.doc.creation);
        const age_days = moment().diff(created, 'days');
        
        const info_html = `
            <div class="barrel-quick-info" style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div>
                        <div style="font-size: 11px; color: #888;">Barrel Age</div>
                        <div style="font-size: 16px; font-weight: bold;">${age_days} days</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #888;">Available Capacity</div>
                        <div style="font-size: 16px; font-weight: bold;">${frm.doc.available_volume_gallons || 0} gal</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #888;">Last Activity</div>
                        <div style="font-size: 16px; font-weight: bold;">${moment(frm.doc.modified).fromNow()}</div>
                    </div>
                </div>
            </div>
        `;
        
        frm.set_df_property('barrel_code', 'description', info_html);
    }
}

function calculate_available_volume(frm) {
    if (frm.doc.barrel_volume_gallons && frm.doc.current_fill_level_gallons) {
        const available = frm.doc.barrel_volume_gallons - frm.doc.current_fill_level_gallons;
        frm.set_value('available_volume_gallons', available);
    }
}

function update_fill_percentage(frm) {
    if (frm.doc.barrel_volume_gallons && frm.doc.current_fill_level_gallons) {
        const percentage = (frm.doc.current_fill_level_gallons / frm.doc.barrel_volume_gallons * 100).toFixed(2);
        frm.set_value('fill_percentage', percentage);
    }
}

function set_default_volumes(frm) {
    const default_volumes = {
        'Wine': 60,
        'Whiskey': 53,
        'Bourbon': 53,
        'Rum': 55,
        'Tequila': 55,
        'Other': 50
    };
    
    if (frm.doc.barrel_type && !frm.doc.barrel_volume_gallons) {
        frm.set_value('barrel_volume_gallons', default_volumes[frm.doc.barrel_type] || 50);
    }
}

function fetch_location_info(frm) {
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Location',
            name: frm.doc.current_location
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: __('Location: {0}', [r.message.location_name || r.message.name]),
                    indicator: 'blue'
                });
            }
        }
    });
}

function show_fill_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Fill Barrel'),
        fields: [
            {
                fieldname: 'product',
                fieldtype: 'Link',
                label: __('Product'),
                options: 'Item',
                reqd: 1
            },
            {
                fieldname: 'fill_amount',
                fieldtype: 'Float',
                label: __('Fill Amount (gallons)'),
                reqd: 1,
                default: frm.doc.available_volume_gallons
            },
            {
                fieldname: 'fill_date',
                fieldtype: 'Date',
                label: __('Fill Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                fieldname: 'notes',
                fieldtype: 'Small Text',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Fill Barrel'),
        primary_action: function(values) {
            frappe.call({
                method: 'spc_barrels.spc_barrels.api.barrel_operations.fill_barrel',
                args: {
                    barrel_name: frm.doc.name,
                    product: values.product,
                    fill_amount: values.fill_amount,
                    fill_date: values.fill_date,
                    notes: values.notes
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Barrel filled successfully'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                        d.hide();
                    }
                }
            });
        }
    });
    
    d.show();
}

function show_transfer_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Transfer Barrel'),
        fields: [
            {
                fieldname: 'from_location',
                fieldtype: 'Link',
                label: __('From Location'),
                options: 'Location',
                default: frm.doc.current_location,
                read_only: 1
            },
            {
                fieldname: 'to_location',
                fieldtype: 'Link',
                label: __('To Location'),
                options: 'Location',
                reqd: 1
            },
            {
                fieldname: 'transfer_date',
                fieldtype: 'Date',
                label: __('Transfer Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                fieldname: 'reason',
                fieldtype: 'Small Text',
                label: __('Reason for Transfer')
            }
        ],
        primary_action_label: __('Transfer'),
        primary_action: function(values) {
            frappe.call({
                method: 'spc_barrels.spc_barrels.api.barrel_operations.transfer_barrel',
                args: {
                    barrel_name: frm.doc.name,
                    from_location: values.from_location,
                    to_location: values.to_location,
                    transfer_date: values.transfer_date,
                    reason: values.reason
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Barrel transferred successfully'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                        d.hide();
                    }
                }
            });
        }
    });
    
    d.show();
}

function show_maintenance_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Schedule Maintenance'),
        fields: [
            {
                fieldname: 'maintenance_type',
                fieldtype: 'Select',
                label: __('Maintenance Type'),
                options: ['Cleaning', 'Repair', 'Inspection', 'Replacement', 'Other'],
                reqd: 1
            },
            {
                fieldname: 'scheduled_date',
                fieldtype: 'Date',
                label: __('Scheduled Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            },
            {
                fieldname: 'notes',
                fieldtype: 'Small Text',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Schedule'),
        primary_action: function(values) {
            frappe.call({
                method: 'spc_barrels.spc_barrels.api.barrel_operations.schedule_maintenance',
                args: {
                    barrel_name: frm.doc.name,
                    maintenance_type: values.maintenance_type,
                    scheduled_date: values.scheduled_date,
                    notes: values.notes
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Maintenance scheduled successfully'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                        d.hide();
                    }
                }
            });
        }
    });
    
    d.show();
}

function show_barrel_history(frm) {
    frappe.route_options = {
        'barrel': frm.doc.name
    };
    frappe.set_route('List', 'Barrel Activity Log');
}

function show_barrel_analytics(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Barrel Analytics: {0}', [frm.doc.barrel_code]),
        size: 'large'
    });
    
    frappe.call({
        method: 'spc_barrels.spc_barrels.api.barrel_analytics.get_barrel_analytics',
        args: {
            barrel_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                const data = r.message;
                const html = `
                    <div class="barrel-analytics">
                        <h4>Usage Statistics</h4>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
                            <div class="stat-card">
                                <div class="stat-label">Total Uses</div>
                                <div class="stat-value">${data.total_uses || 0}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Total Volume Processed</div>
                                <div class="stat-value">${data.total_volume || 0} gal</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Average Fill Level</div>
                                <div class="stat-value">${data.avg_fill_level || 0}%</div>
                            </div>
                        </div>
                    </div>
                `;
                d.$wrapper.find('.modal-body').html(html);
            }
        }
    });
    
    d.show();
}

function setup_field_dependencies(frm) {
    frm.set_query('current_location', function() {
        return {
            filters: {
                'is_group': 0
            }
        };
    });
}

function load_barrel_analytics(frm) {
    frappe.call({
        method: 'spc_barrels.spc_barrels.api.barrel_analytics.get_barrel_summary',
        args: {
            barrel_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.barrel_analytics = r.message;
            }
        }
    });
}
