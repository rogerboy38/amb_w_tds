/**
 * Distribution Organization List View Script
 * 
 * Custom list view configuration for enhanced user experience
 */

frappe.listview_settings['Distribution Organization'] = {
    add_fields: ["status", "regulatory_status", "country", "organization_type", "agreement_expiry"],
    
    get_indicator: function(doc) {
        var indicator = [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
        
        // Override indicator based on regulatory status
        if (doc.regulatory_status === "Non-Compliant" || doc.regulatory_status === "Expired") {
            indicator = [__(doc.regulatory_status), "red"];
        } else if (doc.regulatory_status === "Pending Review") {
            indicator = [__(doc.regulatory_status), "orange"];
        } else if (doc.regulatory_status === "Compliant") {
            indicator = [__(doc.regulatory_status), "green"];
        }
        
        return indicator;
    },
    
    onload: function(listview) {
        // Add custom filters
        listview.page.add_menu_item(__("Compliance Dashboard"), function() {
            frappe.set_route('query-report', 'Distribution Analytics Report');
        });
        
        listview.page.add_menu_item(__("Export Organizations"), function() {
            export_organizations_data(listview);
        });
        
        listview.page.add_menu_item(__("Bulk Import"), function() {
            frappe.call({
                method: "sysmayal.sysmayal.data_import.bulk_importer.get_import_template",
                args: {"doctype": "Distribution Organization"},
                callback: function(r) {
                    if (r.message) {
                        window.open(r.message.template_url);
                    }
                }
            });
        });
    },
    
    formatters: {
        organization_name: function(value, field, doc) {
            // Add country flag icon
            let flag_html = "";
            if (doc.country) {
                flag_html = `<span class="flag-icon flag-icon-${get_country_code(doc.country).toLowerCase()}" style="margin-right: 5px;"></span>`;
            }
            return flag_html + value;
        },
        
        regulatory_status: function(value, field, doc) {
            if (!value) return "";
            
            let color_map = {
                "Compliant": "green",
                "Pending Review": "orange", 
                "Non-Compliant": "red",
                "Expired": "red",
                "Not Applicable": "gray"
            };
            
            let color = color_map[value] || "gray";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        },
        
        agreement_expiry: function(value, field, doc) {
            if (!value) return "";
            
            let today = frappe.datetime.get_today();
            let days_diff = frappe.datetime.get_diff(value, today);
            
            if (days_diff < 0) {
                return `<span style="color: red; font-weight: bold;">${value} (Expired)</span>`;
            } else if (days_diff <= 30) {
                return `<span style="color: orange; font-weight: bold;">${value} (${days_diff} days)</span>`;
            } else {
                return value;
            }
        }
    },
    
    primary_action: function() {
        // Custom primary action
        frappe.new_doc("Distribution Organization");
    }
};

function get_country_code(country) {
    // Simple country code mapping - in production, use a comprehensive mapping
    const country_codes = {
        "United States": "US",
        "Canada": "CA", 
        "Germany": "DE",
        "France": "FR",
        "Australia": "AU",
        "Japan": "JP",
        "United Kingdom": "GB",
        "Brazil": "BR",
        "India": "IN",
        "China": "CN"
    };
    
    return country_codes[country] || "UN";
}

function export_organizations_data(listview) {
    // Get filtered data from current list view
    let filters = listview.get_filters_for_args();
    
    frappe.call({
        method: "sysmayal.sysmayal.data_import.bulk_importer.export_organizations",
        args: {
            "filters": filters
        },
        callback: function(r) {
            if (r.message) {
                // Download the exported file
                window.open(r.message.file_url);
                frappe.msgprint(__("Organizations data exported successfully"));
            }
        }
    });
}
