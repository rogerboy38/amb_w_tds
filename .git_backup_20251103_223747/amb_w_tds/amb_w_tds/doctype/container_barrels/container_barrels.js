
// Copyright (c) 2025, SPC Team and contributors
// Container Barrels - Form Enhancement

frappe.ui.form.on('Container Barrels', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            set_status_indicator(frm);
            add_custom_buttons(frm);
            enhance_form_ui(frm);
        }
    },
    
    gross_weight: function(frm) {
        calculate_net_weight(frm);
    },
    
    tara_weight: function(frm) {
        calculate_net_weight(frm);
    },
    
    status: function(frm) {
        set_status_indicator(frm);
    }
});

function set_status_indicator(frm) {
    const status_colors = {
        'New': 'blue',
        'In Use': 'green',
        'Available': 'green',
        'Maintenance': 'orange',
        'Retired': 'red',
        'Damaged': 'red'
    };
    
    const color = status_colors[frm.doc.status] || 'gray';
    frm.dashboard.set_headline_alert(
        `Status: ${frm.doc.status}`,
        color
    );
}

function add_custom_buttons(frm) {
    frm.add_custom_button(__('View Usage History'), function() {
        show_usage_history(frm);
    }, __('Actions'));
    
    frm.add_custom_button(__('Mark for Maintenance'), function() {
        update_barrel_status(frm, 'Maintenance');
    }, __('Actions'));
    
    frm.add_custom_button(__('Retire Barrel'), function() {
        show_retirement_dialog(frm);
    }, __('Actions'));
}

function enhance_form_ui(frm) {
    // Usage progress indicator
    if (frm.doc.usage_count && frm.doc.max_reuse_count) {
        const percentage = (frm.doc.usage_count / frm.doc.max_reuse_count * 100).toFixed(1);
        const color = percentage > 80 ? '#f44336' : percentage > 50 ? '#ff9800' : '#4CAF50';
        
        const html = `
            <div class="barrel-usage-indicator" style="margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span><strong>Usage Progress</strong></span>
                    <span><strong>${percentage}%</strong></span>
                </div>
                <div style="width: 100%; height: 25px; background: #f0f0f0; border-radius: 5px; overflow: hidden;">
                    <div style="width: ${percentage}%; height: 100%; background: ${color}; transition: width 0.3s;"></div>
                </div>
                <div style="margin-top: 5px; font-size: 12px; color: #666;">
                    ${frm.doc.usage_count} / ${frm.doc.max_reuse_count} uses
                </div>
            </div>
        `;
        
        frm.set_df_property('usage_count', 'description', html);
    }
    
    // Lifecycle info
    const created = moment(frm.doc.creation);
    const age_days = moment().diff(created, 'days');
    
    const info_html = `
        <div class="barrel-quick-info" style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
                <div>
                    <div style="font-size: 11px; color: #888;">Barrel Age</div>
                    <div style="font-size: 16px; font-weight: bold;">${age_days} days</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: #888;">Total Cycles</div>
                    <div style="font-size: 16px; font-weight: bold;">${(frm.doc.total_fill_cycles || 0) + (frm.doc.total_empty_cycles || 0)}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: #888;">Last Used</div>
                    <div style="font-size: 16px; font-weight: bold;">${frm.doc.last_used_date ? moment(frm.doc.last_used_date).fromNow() : 'Never'}</div>
                </div>
                <div>
                    <div style="font-size: 11px; color: #888;">Current Location</div>
                    <div style="font-size: 16px; font-weight: bold;">${frm.doc.current_warehouse || 'Not Set'}</div>
                </div>
            </div>
        </div>
    `;
    
    frm.set_df_property('barrel_serial_number', 'description', info_html);
}

function calculate_net_weight(frm) {
    if (frm.doc.gross_weight && frm.doc.tara_weight) {
        const net = frm.doc.gross_weight - frm.doc.tara_weight;
        frm.set_value('net_weight', net);
    }
}

function show_usage_history(frm) {
    frappe.msgprint({
        title: __('Usage History: {0}', [frm.doc.barrel_serial_number]),
        message: `
            <div style="line-height: 2;">
                <strong>Usage Statistics:</strong><br>
                • Total Uses: ${frm.doc.usage_count || 0}<br>
                • Fill Cycles: ${frm.doc.total_fill_cycles || 0}<br>
                • Empty Cycles: ${frm.doc.total_empty_cycles || 0}<br>
                • First Used: ${frm.doc.first_used_date || 'Never'}<br>
                • Last Used: ${frm.doc.last_used_date || 'Never'}<br>
                • Last Cleaned: ${frm.doc.last_cleaned_date || 'Never'}<br>
            </div>
        `,
        indicator: 'blue'
    });
}

function update_barrel_status(frm, new_status) {
    frm.set_value('status', new_status);
    frm.save();
}

function show_retirement_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Retire Barrel'),
        fields: [
            {
                fieldname: 'retirement_reason',
                fieldtype: 'Select',
                label: __('Reason'),
                options: ['End of Life\nDamaged\nQuality Issues\nLost\nOther'],
                reqd: 1
            },
            {
                fieldname: 'notes',
                fieldtype: 'Small Text',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Retire'),
        primary_action: function(values) {
            frm.set_value('status', 'Retired');
            frm.set_value('retirement_reason', values.retirement_reason + (values.notes ? ': ' + values.notes : ''));
            frm.save();
            d.hide();
        }
    });
    d.show();
}
