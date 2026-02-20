// Copyright (c) 2025, SPC Team and contributors
// Barrel List View Customization

frappe.listview_settings['Barrel'] = {
    get_indicator: function(doc) {
        const status_colors = {
            'Active': ['Active', 'green', 'current_status,=,Active'],
            'In Use': ['In Use', 'blue', 'current_status,=,In Use'],
            'Available': ['Available', 'green', 'current_status,=,Available'],
            'Maintenance': ['Maintenance', 'orange', 'current_status,=,Maintenance'],
            'Retired': ['Retired', 'red', 'current_status,=,Retired'],
            'Reserved': ['Reserved', 'purple', 'current_status,=,Reserved'],
            'In Transit': ['In Transit', 'yellow', 'current_status,=,In Transit']
        };
        
        return status_colors[doc.current_status] || ['Unknown', 'gray'];
    },
    
    onload: function(listview) {
        listview.page.add_inner_button(__('Bulk Transfer'), function() {
            show_bulk_transfer_dialog(listview);
        }, __('Bulk Actions'));
        
        listview.page.add_inner_button(__('Bulk Status Update'), function() {
            show_bulk_status_dialog(listview);
        }, __('Bulk Actions'));
        
        listview.page.add_inner_button(__('Export Selected'), function() {
            export_selected_barrels(listview);
        }, __('Bulk Actions'));
        
        listview.page.add_inner_button(__('Available Barrels'), function() {
            listview.filter_area.add([[listview.doctype, 'current_status', '=', 'Available']]);
        }, __('Quick Filters'));
        
        listview.page.add_inner_button(__('In Use'), function() {
            listview.filter_area.add([[listview.doctype, 'current_status', '=', 'In Use']]);
        }, __('Quick Filters'));
        
        listview.page.add_inner_button(__('Need Maintenance'), function() {
            listview.filter_area.add([[listview.doctype, 'current_status', '=', 'Maintenance']]);
        }, __('Quick Filters'));
        
        listview.page.add_inner_button(__('Open Dashboard'), function() {
            frappe.set_route('barrel-dashboard');
        }).css({'background': '#4CAF50', 'color': 'white', 'font-weight': 'bold'});
        
        add_custom_list_styles();
    },
    
    formatters: {
        barrel_code: function(value, df, doc) {
            return `<strong>${value}</strong>`;
        },
        current_fill_level_gallons: function(value, df, doc) {
            if (value && doc.barrel_volume_gallons) {
                const percentage = (value / doc.barrel_volume_gallons * 100).toFixed(0);
                const color = percentage > 80 ? '#f44336' : percentage > 50 ? '#ff9800' : '#4CAF50';
                return `<span style="color: ${color}; font-weight: bold;">${value} gal (${percentage}%)</span>`;
            }
            return value;
        },
        available_volume_gallons: function(value) {
            return value ? `<span style="color: #4CAF50;">${value} gal</span>` : '0 gal';
        }
    },
    
    add_fields: [
        'barrel_code',
        'barrel_type',
        'current_status',
        'current_location',
        'barrel_volume_gallons',
        'current_fill_level_gallons',
        'available_volume_gallons',
        'owner'
    ],
    
    primary_action: function() {
        frappe.new_doc('Barrel');
    }
};

function show_bulk_transfer_dialog(listview) {
    const selected = listview.get_checked_items();
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select barrels to transfer'));
        return;
    }
    
    const d = new frappe.ui.Dialog({
        title: __('Bulk Transfer {0} Barrels', [selected.length]),
        fields: [
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
                label: __('Reason')
            }
        ],
        primary_action_label: __('Transfer All'),
        primary_action: function(values) {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.api.barrel_bulk_operations.bulk_transfer_barrels',
                args: {
                    barrel_names: selected.map(item => item.name),
                    to_location: values.to_location,
                    transfer_date: values.transfer_date,
                    reason: values.reason
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Barrels transferred successfully'),
                            indicator: 'green'
                        });
                        listview.refresh();
                        d.hide();
                    }
                }
            });
        }
    });
    
    d.show();
}

function show_bulk_status_dialog(listview) {
    const selected = listview.get_checked_items();
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select barrels to update'));
        return;
    }
    
    const d = new frappe.ui.Dialog({
        title: __('Update Status for {0} Barrels', [selected.length]),
        fields: [
            {
                fieldname: 'new_status',
                fieldtype: 'Select',
                label: __('New Status'),
                options: ['Active', 'Available', 'In Use', 'Maintenance', 'Reserved', 'In Transit', 'Retired'],
                reqd: 1
            },
            {
                fieldname: 'reason',
                fieldtype: 'Small Text',
                label: __('Reason')
            }
        ],
        primary_action_label: __('Update All'),
        primary_action: function(values) {
            frappe.call({
                method: 'amb_w_tds.amb_w_tds.api.barrel_bulk_operations.bulk_update_status',
                args: {
                    barrel_names: selected.map(item => item.name),
                    new_status: values.new_status,
                    reason: values.reason
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Status updated successfully'),
                            indicator: 'green'
                        });
                        listview.refresh();
                        d.hide();
                    }
                }
            });
        }
    });
    
    d.show();
}

function export_selected_barrels(listview) {
    const selected = listview.get_checked_items();
    
    if (selected.length === 0) {
        frappe.msgprint(__('Please select barrels to export'));
        return;
    }
    
    frappe.call({
        method: 'amb_w_tds.amb_w_tds.api.barrel_bulk_operations.export_barrels',
        args: {
            barrel_names: selected.map(item => item.name)
        },
        callback: function(r) {
            if (r.message) {
                const csv_data = r.message;
                const blob = new Blob([csv_data], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `barrels_export_${frappe.datetime.now_datetime()}.csv`;
                a.click();
            }
        }
    });
}

function add_custom_list_styles() {
    const style = `
        <style>
            .list-row-container[data-doctype="Barrel"]:hover {
                transform: translateX(5px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        </style>
    `;
    
    if (!$('#barrel-list-custom-styles').length) {
        $('head').append(style);
    }
}
