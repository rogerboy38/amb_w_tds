/**
 * Distribution Contact Form Script
 */

frappe.ui.form.on('Distribution Contact', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Organization Details'), function() {
                show_organization_details(frm);
            }, __('View'));
            
            frm.add_custom_button(__('Communication History'), function() {
                show_communication_history(frm);
            }, __('View'));
            
            frm.add_custom_button(__('Update Last Contacted'), function() {
                update_last_contacted(frm);
            }, __('Actions'));
        }
    },
    
    first_name: function(frm) {
        set_full_name(frm);
    },
    
    last_name: function(frm) {
        set_full_name(frm);
    },
    
    organization: function(frm) {
        if (frm.doc.organization) {
            load_organization_data(frm);
        }
    },
    
    email_id: function(frm) {
        if (frm.doc.email_id && frm.doc.organization) {
            check_duplicate_email(frm);
        }
    }
});

function set_full_name(frm) {
    if (frm.doc.first_name) {
        const full_name = frm.doc.last_name ? 
            `${frm.doc.first_name} ${frm.doc.last_name}` : 
            frm.doc.first_name;
        frm.set_value('full_name', full_name);
    }
}

function load_organization_data(frm) {
    frappe.call({
        method: 'get_organization_details',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                if (!frm.doc.country && r.message.country) {
                    frm.set_value('country', r.message.country);
                }
            }
        }
    });
}

function check_duplicate_email(frm) {
    frappe.db.get_list('Distribution Contact', {
        filters: {
            email_id: frm.doc.email_id,
            organization: frm.doc.organization,
            name: ['!=', frm.doc.name || '']
        },
        limit: 1
    }).then(records => {
        if (records.length > 0) {
            frappe.msgprint(__('A contact with this email already exists in the organization'));
        }
    });
}

function show_organization_details(frm) {
    frappe.call({
        method: 'get_organization_details',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                const details = r.message;
                const html = `
                    <table class="table table-bordered">
                        <tr><th>Organization Name</th><td>${details.organization_name || ''}</td></tr>
                        <tr><th>Type</th><td>${details.organization_type || ''}</td></tr>
                        <tr><th>Country</th><td>${details.country || ''}</td></tr>
                        <tr><th>Territory</th><td>${details.territory || ''}</td></tr>
                        <tr><th>Status</th><td>${details.status || ''}</td></tr>
                        <tr><th>Regulatory Status</th><td>${details.regulatory_status || ''}</td></tr>
                    </table>
                `;
                
                frappe.msgprint({
                    title: __('Organization Details'),
                    message: html,
                    wide: true
                });
            }
        }
    });
}

function show_communication_history(frm) {
    frappe.call({
        method: 'get_communication_history',
        doc: frm.doc,
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                frappe.route_options = {
                    recipients: ['like', `%${frm.doc.email_id}%`]
                };
                frappe.set_route('List', 'Communication');
            } else {
                frappe.msgprint(__('No communication history found'));
            }
        }
    });
}

function update_last_contacted(frm) {
    frappe.call({
        method: 'update_last_contacted',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                frappe.msgprint(r.message);
                frm.reload_doc();
            }
        }
    });
}
