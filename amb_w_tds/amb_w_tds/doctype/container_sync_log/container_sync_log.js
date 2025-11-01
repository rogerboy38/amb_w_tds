// Container Sync Log JavaScript

frappe.ui.form.on('Container Sync Log', {
    refresh: function(frm) {
        // Add custom buttons and formatting
        setup_sync_log_display(frm);
        
        // Add action buttons
        if (frm.doc.sync_status === 'Error') {
            frm.add_custom_button(__('Retry Sync'), function() {
                retry_failed_sync(frm);
            }, __('Actions'));
        }
        
        if (frm.doc.synced_fields) {
            frm.add_custom_button(__('View Details'), function() {
                show_sync_details(frm);
            }, __('Actions'));
        }
    }
});

function setup_sync_log_display(frm) {
    // Color-code status field
    let status_colors = {
        'Success': 'green',
        'Error': 'red',
        'Partial': 'orange',
        'Retrying': 'blue'
    };
    
    let color = status_colors[frm.doc.sync_status] || 'gray';
    frm.set_df_property('sync_status', 'description', 
        `<span style="color: ${color};">● ${frm.doc.sync_status}</span>`);
    
    // Format direction indicator
    let direction_icons = {
        'CS_to_Batch': '→ To Batch AMB',
        'Batch_to_CS': '← From Batch AMB',
        'Bidirectional': '↔ Bidirectional',
        'Internal': '⚙ Internal',
        'Conflict_Resolution': '⚖ Conflict Resolution'
    };
    
    let direction_text = direction_icons[frm.doc.sync_direction] || frm.doc.sync_direction;
    frm.set_df_property('sync_direction', 'description', direction_text);
}

function show_sync_details(frm) {
    let synced_fields = {};
    let sync_result = {};
    
    try {
        synced_fields = JSON.parse(frm.doc.synced_fields || '{}');
        sync_result = JSON.parse(frm.doc.sync_result || '{}');
    } catch (e) {
        console.error('Error parsing sync data:', e);
    }
    
    let html = '<div class="sync-details">';
    html += '<h4>Synced Fields:</h4>';
    html += '<table class="table table-bordered">';
    
    for (let field in synced_fields) {
        html += `<tr><td><strong>${field}</strong></td><td>${synced_fields[field]}</td></tr>`;
    }
    
    html += '</table>';
    
    if (Object.keys(sync_result).length > 0) {
        html += '<h4>Sync Result:</h4>';
        html += '<pre>' + JSON.stringify(sync_result, null, 2) + '</pre>';
    }
    
    html += '</div>';
    
    frappe.msgprint({
        title: __('Sync Details'),
        message: html,
        wide: true
    });
}

function retry_failed_sync(frm) {
    frappe.confirm(
        __('Retry the failed synchronization for this container?'),
        function() {
            frappe.call({
                method: 'amb_w_tds.api.container_api.retry_failed_sync',
                args: {
                    sync_log_name: frm.doc.name,
                    container_name: frm.doc.container_selection
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Sync retry initiated successfully'),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Retry Failed'),
                            message: r.message ? r.message.error : __('Retry operation failed'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// List view customization
frappe.listview_settings['Container Sync Log'] = {
    add_fields: ['sync_status', 'sync_direction', 'container_selection'],
    get_indicator: function(doc) {
        let status_colors = {
            'Success': 'green',
            'Error': 'red',
            'Partial': 'orange',
            'Retrying': 'blue'
        };
        
        return [doc.sync_status, status_colors[doc.sync_status] || 'gray', 'sync_status,=,' + doc.sync_status];
    },
    
    formatters: {
        sync_direction: function(value) {
            let icons = {
                'CS_to_Batch': '→',
                'Batch_to_CS': '←',
                'Bidirectional': '↔',
                'Internal': '⚙',
                'Conflict_Resolution': '⚖'
            };
            return icons[value] + ' ' + value;
        }
    }
};