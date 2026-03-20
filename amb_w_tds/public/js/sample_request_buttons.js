// =============================================================================
// Sample Request Buttons - Combined Module
// Contains both utilities and button logic
// Works with doctype_js - no bundling required
// =============================================================================

// =============================================================================
// PART 1: SampleRequestUtils (Utilities) - Embedded directly
// =============================================================================
window.SampleRequestUtils = {
    hasPermission: function() {
        var allowed_roles = ["System Manager", "RND Manager", "Manufacturing Manager"];
        var user_roles = frappe.user_roles || [];
        return allowed_roles.some(function(role) {
            return user_roles.indexOf(role) !== -1;
        });
    },

    createSampleRequest: function(doctype, docname) {
        if (!this.hasPermission()) {
            frappe.msgprint({
                title: __("Permission Denied"),
                message: __("You don't have permission to create sample requests."),
                indicator: "red"
            });
            return;
        }

        frappe.call({
            method: "amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.make_sample_request_from_source",
            args: {
                source_doctype: doctype,
                source_name: docname
            },
            freeze: true,
            freeze_message: __("Creating Sample Request..."),
            callback: function(r) {
                if (!r.exc && r.message) {
                    frappe.set_route("Form", "Sample Request AMB", r.message);
                    frappe.show_alert({
                        message: __("Sample Request created successfully"),
                        indicator: "green"
                    });
                }
            }
        });
    },

    addButtonToForm: function(frm, doctype) {
        if (frm.is_new()) return;
        if (!this.hasPermission()) return;

        frm.add_custom_button(
            __("Sample Request"),
            function() {
                window.SampleRequestUtils.createSampleRequest(doctype, frm.doc.name);
            },
            __("Create")
        );
    }
};

// =============================================================================
// PART 2: Button Registration
// =============================================================================
// Direct frappe.ui.form.on registration - works with doctype_js loading
// When loaded via doctype_js, the form is already available, so we register directly
frappe.ui.form.on(cur_frm.doctype, {
    refresh: function(frm) {
        window.SampleRequestUtils.addButtonToForm(frm, frm.doctype);
    }
});

console.log("✅ Sample Request buttons registered for", cur_frm.doctype);
