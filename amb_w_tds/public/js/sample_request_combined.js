// =============================================================================
// Sample Request Combined Module
// Contains both utilities and button logic in one file for reliable loading
// Version: 2026-03-19 - Simplified for Docker production
// =============================================================================

console.log("🚀 Sample Request module loading...");

// =============================================================================
// PART 1: SampleRequestUtils (Utilities)
// =============================================================================
window.SampleRequestUtils = window.SampleRequestUtils || {
    /**
     * Check if user has permission to create sample requests
     */
    hasPermission: function() {
        var allowed_roles = ["System Manager", "RND Manager", "Manufacturing Manager"];
        var user_roles = frappe.user_roles || [];
        return allowed_roles.some(function(role) {
            return user_roles.indexOf(role) !== -1;
        });
    },

    /**
     * Create a sample request from any doctype
     */
    createSampleRequest: function(doctype, docname) {
        var self = this;
        
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

    /**
     * Add the Sample Request button to a form
     */
    addButtonToForm: function(frm, doctype) {
        // Don't add button to new documents
        if (frm.is_new()) return;
        
        // Check permission
        if (!this.hasPermission()) return;

        // Check if button already exists to avoid duplicates
        var button_exists = false;
        if (frm.custom_buttons && frm.custom_buttons["Sample Request"]) {
            button_exists = true;
        }

        if (!button_exists) {
            frm.add_custom_button(
                __("Sample Request"),
                function() {
                    window.SampleRequestUtils.createSampleRequest(doctype, frm.doc.name);
                },
                __("Create")
            );
            console.log("✅ Sample Request button added to", doctype);
        }
    }
};

console.log("✅ SampleRequestUtils loaded");

// =============================================================================
// PART 2: Button Registration
// =============================================================================
var TARGET_DOCTYPES = [
    "Lead",
    "Prospect", 
    "Opportunity",
    "Quotation",
    "Sales Order"
];

// Function to register buttons for a doctype
function registerSampleRequestButtons(doctype) {
    frappe.ui.form.on(doctype, {
        refresh: function(frm) {
            window.SampleRequestUtils.addButtonToForm(frm, doctype);
        }
    });
    console.log("📋 Registered buttons for", doctype);
}

// Register all target doctypes
TARGET_DOCTYPES.forEach(function(doctype) {
    registerSampleRequestButtons(doctype);
});

console.log("✅ Sample Request buttons registered for:", TARGET_DOCTYPES);
