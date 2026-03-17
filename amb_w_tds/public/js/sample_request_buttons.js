// =============================================================================
// Sample Request Buttons
// Adds Sample Request button to Lead, Prospect, Opportunity, Quotation, Sales Order
// Version: 2026-03-17
// =============================================================================

// Target doctypes for Sample Request button
var TARGET_DOCTYPES = [
    "Lead",
    "Prospect", 
    "Opportunity",
    "Quotation",
    "Sales Order"
];

// Wait for Frappe to be ready
frappe.router.on("change", function() {
    // This ensures the app is loaded
});

$(document).on('app_ready', function() {
    console.log("🚀 Initializing Sample Request buttons for", TARGET_DOCTYPES);
    
    // Apply to each doctype
    TARGET_DOCTYPES.forEach(function(doctype) {
        frappe.ui.form.on(doctype, {
            refresh: function(frm) {
                // Add the button using our utility
                window.SampleRequestUtils.addButtonToForm(frm, doctype);
                
                // Doctype-specific logic if needed
                if (doctype === "Quotation") {
                    console.log("Quotation form - Sample Request button added");
                }
            }
        });
    });
});

console.log("✅ Sample Request Buttons script loaded for:", TARGET_DOCTYPES);
