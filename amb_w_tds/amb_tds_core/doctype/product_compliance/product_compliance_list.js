/**
 * Product Compliance List View Script
 * 
 * Custom list view configuration for Product Compliance
 */

frappe.listview_settings['Product Compliance'] = {
    add_fields: ["compliance_status", "risk_level", "country", "compliance_percentage", "expiry_date", "workflow_state"],
    
    get_indicator: function(doc) {
        let indicator = [__(doc.compliance_status), "gray"];
        
        if (doc.compliance_status === "Compliant") {
            indicator = [__("Compliant"), "green"];
        } else if (doc.compliance_status === "Non-Compliant") {
            indicator = [__("Non-Compliant"), "red"];
        } else if (doc.compliance_status === "Expired") {
            indicator = [__("Expired"), "red"];
        } else if (doc.compliance_status === "Pending Review") {
            indicator = [__("Pending Review"), "orange"];
        } else if (doc.compliance_status === "Partially Compliant") {
            indicator = [__("Partially Compliant"), "yellow"];
        }
        
        // Override with risk level if critical
        if (doc.risk_level === "Critical") {
            indicator = [__("Critical Risk"), "red"];
        }
        
        return indicator;
    },
    
    onload: function(listview) {
        // Add custom menu items
        listview.page.add_menu_item(__("Compliance Dashboard"), function() {
            frappe.set_route('query-report', 'Compliance Status Report');
        });
        
        listview.page.add_menu_item(__("Bulk Update Status"), function() {
            bulk_update_compliance_status(listview);
        });
        
        listview.page.add_menu_item(__("Export Compliance Data"), function() {
            export_compliance_data(listview);
        });
        
        listview.page.add_menu_item(__("Expiry Alerts"), function() {
            show_expiry_alerts(listview);
        });
        
        // Add quick filters
        listview.page.add_field({
            fieldname: "compliance_status_filter",
            label: __("Status Filter"),
            fieldtype: "Select",
            options: "\\nCompliant\\nPending Review\\nNon-Compliant\\nPartially Compliant\\nExpired\\nNot Applicable",
            change: function() {
                let status = this.get_value();
                if (status) {
                    listview.filter_area.add_filter('Product Compliance', 'compliance_status', '=', status);
                } else {
                    listview.filter_area.remove_filter('Product Compliance', 'compliance_status');
                }
                listview.refresh();
            }
        });
        
        listview.page.add_field({
            fieldname: "risk_level_filter", 
            label: __("Risk Filter"),
            fieldtype: "Select",
            options: "\\nLow\\nMedium\\nHigh\\nCritical",
            change: function() {
                let risk = this.get_value();
                if (risk) {
                    listview.filter_area.add_filter('Product Compliance', 'risk_level', '=', risk);
                } else {
                    listview.filter_area.remove_filter('Product Compliance', 'risk_level');
                }
                listview.refresh();
            }
        });
    },
    
    formatters: {
        compliance_status: function(value, field, doc) {
            if (!value) return "";
            
            let color_map = {
                "Compliant": "green",
                "Non-Compliant": "red",
                "Expired": "red", 
                "Pending Review": "orange",
                "Partially Compliant": "orange",
                "Not Applicable": "gray"
            };
            
            let color = color_map[value] || "gray";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        },
        
        risk_level: function(value, field, doc) {
            if (!value) return "";
            
            let color_map = {
                "Low": "green",
                "Medium": "orange",
                "High": "red", 
                "Critical": "red"
            };
            
            let color = color_map[value] || "gray";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        },
        
        compliance_percentage: function(value, field, doc) {
            if (!value) return "";
            
            let color = "red";
            if (value >= 80) color = "green";
            else if (value >= 60) color = "orange";
            else if (value >= 40) color = "yellow";
            
            return `<span style="color: ${color}; font-weight: bold;">${value}%</span>`;
        },
        
        expiry_date: function(value, field, doc) {
            if (!value) return "";
            
            let today = frappe.datetime.get_today();
            let days_diff = frappe.datetime.get_diff(value, today);
            
            if (days_diff < 0) {
                return `<span style="color: red; font-weight: bold;">${value} (Expired)</span>`;
            } else if (days_diff <= 30) {
                return `<span style="color: orange; font-weight: bold;">${value} (${days_diff} days)</span>`;
            } else if (days_diff <= 90) {
                return `<span style="color: #f39c12;">${value} (${days_diff} days)</span>`;
            } else {
                return value;
            }
        },
        
        workflow_state: function(value, field, doc) {
            if (!value) return "";
            
            let state_colors = {
                "Draft": "gray",
                "Under Review": "orange",
                "Testing Required": "blue",
                "Regulatory Submission": "orange",
                "Compliant": "green",
                "Non-Compliant": "red",
                "Expired": "red"
            };
            
            let color = state_colors[value] || "gray";
            return `<span style="color: ${color}; font-size: 11px;">${value}</span>`;
        }
    },
    
    primary_action: function() {
        frappe.new_doc("Product Compliance");
    },
    
    // Bulk actions
    button: {
        show: function(doc) {
            return doc.compliance_status !== "Compliant";
        },
        get_label: function() {
            return __("Bulk Actions");
        },
        get_description: function(doc) {
            return __("Bulk update compliance status");
        },
        action: function(selection) {
            bulk_update_selected_compliance(selection);
        }
    }
};

function bulk_update_compliance_status(listview) {
    let dialog = new frappe.ui.Dialog({
        title: __("Bulk Update Compliance Status"),
        fields: [
            {
                fieldname: "filters",
                label: __("Apply to"),
                fieldtype: "Select",
                options: "All Records\\nFiltered Records\\nSelected Records",
                default: "Filtered Records",
                reqd: 1
            },
            {
                fieldname: "new_status",
                label: __("New Status"),
                fieldtype: "Select",
                options: "Compliant\\nPending Review\\nNon-Compliant\\nPartially Compliant\\nExpired\\nNot Applicable",
                reqd: 1
            },
            {
                fieldname: "notes",
                label: __("Notes"),
                fieldtype: "Text",
                description: __("Optional notes about the status change")
            }
        ],
        primary_action_label: __("Update"),
        primary_action: function(values) {
            let filters = {};
            if (values.filters === "Filtered Records") {
                filters = listview.get_filters_for_args();
            }
            
            frappe.call({
                method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.bulk_update_compliance_status",
                args: {
                    filters: filters,
                    new_status: values.new_status,
                    notes: values.notes
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        listview.refresh();
                        dialog.hide();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function export_compliance_data(listview) {
    let filters = listview.get_filters_for_args();
    
    frappe.call({
        method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.export_compliance_data",
        args: {
            filters: filters
        },
        callback: function(r) {
            if (r.message) {
                window.open(r.message.file_url);
                frappe.msgprint(__("Compliance data exported successfully"));
            }
        }
    });
}

function show_expiry_alerts(listview) {
    frappe.call({
        method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.get_expiry_alerts",
        callback: function(r) {
            if (r.message) {
                show_expiry_alerts_dialog(r.message);
            }
        }
    });
}

function show_expiry_alerts_dialog(alerts) {
    let html = "<div class='expiry-alerts'>";
    
    if (alerts.expired && alerts.expired.length > 0) {
        html += "<h5 style='color: red;'>Expired Products</h5>";
        html += "<ul>";
        alerts.expired.forEach(function(item) {
            html += `<li><strong>${item.product_name}</strong> (${item.country}) - Expired on ${item.expiry_date}</li>`;
        });
        html += "</ul>";
    }
    
    if (alerts.expiring_soon && alerts.expiring_soon.length > 0) {
        html += "<h5 style='color: orange;'>Expiring Soon (30 days)</h5>";
        html += "<ul>";
        alerts.expiring_soon.forEach(function(item) {
            html += `<li><strong>${item.product_name}</strong> (${item.country}) - Expires on ${item.expiry_date}</li>`;
        });
        html += "</ul>";
    }
    
    if (alerts.reviews_due && alerts.reviews_due.length > 0) {
        html += "<h5 style='color: blue;'>Reviews Due</h5>";
        html += "<ul>";
        alerts.reviews_due.forEach(function(item) {
            html += `<li><strong>${item.product_name}</strong> (${item.country}) - Review due on ${item.next_review_date}</li>`;
        });
        html += "</ul>";
    }
    
    html += "</div>";
    
    if (alerts.expired.length === 0 && alerts.expiring_soon.length === 0 && alerts.reviews_due.length === 0) {
        html = "<p>No immediate compliance alerts.</p>";
    }
    
    frappe.msgprint({
        title: __("Compliance Alerts"),
        message: html,
        wide: true
    });
}

function bulk_update_selected_compliance(selection) {
    if (selection.length === 0) {
        frappe.msgprint(__("Please select records to update"));
        return;
    }
    
    let dialog = new frappe.ui.Dialog({
        title: __("Update Selected Records"),
        fields: [
            {
                fieldname: "new_status",
                label: __("New Status"),
                fieldtype: "Select", 
                options: "Compliant\\nPending Review\\nNon-Compliant\\nPartially Compliant\\nExpired\\nNot Applicable",
                reqd: 1
            },
            {
                fieldname: "notes",
                label: __("Notes"),
                fieldtype: "Text"
            }
        ],
        primary_action_label: __("Update"),
        primary_action: function(values) {
            let names = selection.map(item => item.name);
            
            frappe.call({
                method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.bulk_update_compliance_status",
                args: {
                    product_names: names,
                    new_status: values.new_status,
                    notes: values.notes
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        dialog.hide();
                        window.location.reload();
                    }
                }
            });
        }
    });
    
    dialog.show();
}
