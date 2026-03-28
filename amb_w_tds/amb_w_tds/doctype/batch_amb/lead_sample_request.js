// =============================================================================
// LEAD - Sample Request Button
// Adds a button to create Sample Request AMB from Lead
// Version: 2026-03-17
// =============================================================================

frappe.ui.form.on('Lead', {
    refresh: function(frm) {
        console.log('🔧 Lead Refresh triggered for:', frm.doc.name);
        
        // Add Sample Request button for existing leads
        if (!frm.is_new()) {
            frm.add_custom_button(__("Sample Request"), function() {
                frappe.call({
                    method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.create_sample_request_from_lead',
                    args: { lead_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Creating Sample Request..."),
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __(r.message.message),
                                indicator: 'green'
                            });
                            frappe.set_route('Form', 'Sample Request AMB', r.message.sample_request);
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message ? r.message.message : __('Failed to create sample request'),
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, __("Create"));
        }
    }
});
