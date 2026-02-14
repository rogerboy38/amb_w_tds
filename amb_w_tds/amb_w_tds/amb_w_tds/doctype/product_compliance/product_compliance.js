/**
 * Product Compliance Form Script
 * 
 * Client-side JavaScript for enhanced Product Compliance form
 */

frappe.ui.form.on('Product Compliance', {
    refresh: function(frm) {
        add_custom_buttons(frm);
        set_form_styling(frm);
        update_compliance_indicators(frm);
        setup_auto_calculations(frm);
    },
    
    onload: function(frm) {
        set_field_properties(frm);
        setup_compliance_tracking(frm);
    },
    
    country: function(frm) {
        load_country_regulations(frm);
    },
    
    compliance_status: function(frm) {
        update_compliance_percentage(frm);
        set_review_dates(frm);
    },
    
    approval_date: function(frm) {
        calculate_expiry_date(frm);
    },
    
    testing_status: function(frm) {
        update_compliance_percentage(frm);
    },
    
    approval_status: function(frm) {
        update_compliance_percentage(frm);
    }
});

function add_custom_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Add Workflow Actions
        if (frm.doc.workflow_state && frm.doc.workflow_state !== "Compliant") {
            frm.add_custom_button(__('Process Workflow'), function() {
                show_workflow_actions(frm);
            }, __('Actions'));
        }
        
        // Add Generate Certificate button
        if (frm.doc.compliance_status === "Compliant") {
            frm.add_custom_button(__('Generate Certificate'), function() {
                generate_compliance_certificate(frm);
            }, __('Create'));
        }
        
        // Add Renewal button
        if (frm.doc.compliance_status === "Expired") {
            frm.add_custom_button(__('Renew Compliance'), function() {
                renew_compliance(frm);
            }, __('Actions'));
        }
        
        // Add Testing Request button
        if (frm.doc.testing_status !== "Completed") {
            frm.add_custom_button(__('Request Testing'), function() {
                request_product_testing(frm);
            }, __('Actions'));
        }
        
        // Add Compliance Report button
        frm.add_custom_button(__('Compliance Report'), function() {
            frappe.set_route('query-report', 'Compliance Status Report', {
                'product_name': frm.doc.product_name,
                'country': frm.doc.country
            });
        }, __('View'));
    }
}

function set_form_styling(frm) {
    // Color-code sections based on compliance status
    if (frm.doc.compliance_status) {
        let color_map = {
            "Compliant": "#d4edda",
            "Non-Compliant": "#f8d7da",
            "Pending Review": "#fff3cd",
            "Partially Compliant": "#fff3cd",
            "Expired": "#f8d7da"
        };
        
        let bg_color = color_map[frm.doc.compliance_status];
        if (bg_color) {
            frm.form_wrapper.find('.form-page').css('background-color', bg_color);
        }
    }
}

function update_compliance_indicators(frm) {
    // Clear existing indicators
    frm.dashboard.clear_headline();
    
    // Add compliance percentage indicator
    if (frm.doc.compliance_percentage) {
        let color = "red";
        if (frm.doc.compliance_percentage >= 80) color = "green";
        else if (frm.doc.compliance_percentage >= 60) color = "orange";
        
        frm.dashboard.add_indicator(
            `Compliance: ${frm.doc.compliance_percentage}%`,
            color
        );
    }
    
    // Add risk level indicator
    if (frm.doc.risk_level) {
        let risk_colors = {
            'Low': 'green',
            'Medium': 'orange',
            'High': 'red',
            'Critical': 'red'
        };
        
        frm.dashboard.add_indicator(
            `Risk: ${frm.doc.risk_level}`,
            risk_colors[frm.doc.risk_level] || 'gray'
        );
    }
    
    // Add expiry warning
    if (frm.doc.expiry_date) {
        let today = frappe.datetime.get_today();
        let days_to_expiry = frappe.datetime.get_diff(frm.doc.expiry_date, today);
        
        if (days_to_expiry < 0) {
            frm.dashboard.add_indicator(__('Expired'), 'red');
        } else if (days_to_expiry <= 30) {
            frm.dashboard.add_indicator(`Expires in ${days_to_expiry} days`, 'orange');
        }
    }
}

function setup_auto_calculations(frm) {
    // Auto-calculate compliance percentage based on various factors
    if (frm.doc.approval_status && frm.doc.testing_status) {
        let score = 0;
        
        // Approval status scoring
        if (frm.doc.approval_status === "Approved") score += 50;
        else if (frm.doc.approval_status === "Under Review") score += 25;
        
        // Testing status scoring
        if (frm.doc.testing_status === "Completed") score += 30;
        else if (frm.doc.testing_status === "In Progress") score += 15;
        
        // Additional compliance factors
        if (frm.doc.required_tests) score += 10;
        if (frm.doc.certifications_held) score += 10;
        
        if (score > 0 && (!frm.doc.compliance_percentage || frm.doc.compliance_percentage === 0)) {
            frm.set_value('compliance_percentage', Math.min(score, 100));
        }
    }
}

function set_field_properties(frm) {
    // Set manufacturer filter to only show relevant organizations
    frm.set_query('manufacturer', function() {
        return {
            filters: {
                'organization_type': ['in', ['Manufacturer', 'Supplier']],
                'status': 'Active'
            }
        };
    });
    
    // Set responsible person filter
    frm.set_query('responsible_person', function() {
        return {
            filters: {
                'enabled': 1,
                'user_type': 'System User'
            }
        };
    });
}

function setup_compliance_tracking(frm) {
    // Set up automatic compliance tracking
    if (frm.doc.country && frm.doc.product_name) {
        frappe.call({
            method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.get_compliance_requirements",
            args: {
                country: frm.doc.country,
                product_category: frm.doc.product_category
            },
            callback: function(r) {
                if (r.message) {
                    update_compliance_requirements(frm, r.message);
                }
            }
        });
    }
}

function load_country_regulations(frm) {
    if (frm.doc.country) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Country Regulation",
                filters: {"country_name": frm.doc.country},
                fields: ["*"]
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let regulation = r.message[0];
                    frm.set_value('regulatory_authority', regulation.regulatory_authority);
                    
                    // Show regulatory info in a dialog
                    show_regulatory_info(regulation);
                }
            }
        });
    }
}

function update_compliance_percentage(frm) {
    let percentage = 0;
    
    // Calculate based on status
    if (frm.doc.compliance_status === "Compliant") percentage = 100;
    else if (frm.doc.compliance_status === "Partially Compliant") percentage = 70;
    else if (frm.doc.compliance_status === "Pending Review") percentage = 50;
    else if (frm.doc.compliance_status === "Non-Compliant") percentage = 20;
    else if (frm.doc.compliance_status === "Expired") percentage = 0;
    
    frm.set_value('compliance_percentage', percentage);
}

function set_review_dates(frm) {
    if (frm.doc.compliance_status === "Pending Review" && !frm.doc.next_review_date) {
        // Set next review date to 30 days from now
        let review_date = frappe.datetime.add_days(frappe.datetime.get_today(), 30);
        frm.set_value('next_review_date', review_date);
    }
}

function calculate_expiry_date(frm) {
    if (frm.doc.approval_date && !frm.doc.expiry_date) {
        // Default expiry to 2 years from approval date
        let expiry_date = frappe.datetime.add_months(frm.doc.approval_date, 24);
        frm.set_value('expiry_date', expiry_date);
    }
}

function show_workflow_actions(frm) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Workflow Action",
            filters: {
                "reference_doctype": "Product Compliance",
                "reference_name": frm.doc.name,
                "status": "Open"
            },
            fields: ["*"]
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_workflow_dialog(frm, r.message);
            } else {
                frappe.msgprint(__("No pending workflow actions"));
            }
        }
    });
}

function generate_compliance_certificate(frm) {
    frappe.call({
        method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.generate_compliance_certificate",
        args: {
            "compliance_name": frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.msgprint(__("Compliance certificate generated successfully"));
                // Open the certificate document
                frappe.set_route("Form", "Certification Document", r.message);
            }
        }
    });
}

function renew_compliance(frm) {
    frappe.confirm(
        __("Are you sure you want to renew this compliance record?"),
        function() {
            frappe.call({
                method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.renew_compliance",
                args: {
                    "compliance_name": frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.msgprint(__("Compliance renewed successfully"));
                    }
                }
            });
        }
    );
}

function request_product_testing(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __("Request Product Testing"),
        fields: [
            {
                fieldname: "test_type",
                label: __("Test Type"),
                fieldtype: "Select",
                options: "Microbiological Testing\\nHeavy Metals Analysis\\nPesticide Residue Testing\\nAloesin Content Analysis\\nStability Testing\\nOther",
                reqd: 1
            },
            {
                fieldname: "testing_lab",
                label: __("Testing Laboratory"),
                fieldtype: "Data"
            },
            {
                fieldname: "expected_completion",
                label: __("Expected Completion"),
                fieldtype: "Date"
            },
            {
                fieldname: "notes",
                label: __("Notes"),
                fieldtype: "Text"
            }
        ],
        primary_action_label: __("Request Testing"),
        primary_action: function(values) {
            frappe.call({
                method: "sysmayal.sysmayal.doctype.product_compliance.product_compliance.request_testing",
                args: {
                    "compliance_name": frm.doc.name,
                    "test_details": values
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.msgprint(__("Testing request submitted successfully"));
                        dialog.hide();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function update_compliance_requirements(frm, requirements) {
    if (requirements.required_tests && !frm.doc.required_tests) {
        frm.set_value('required_tests', requirements.required_tests);
    }
    
    if (requirements.compliance_requirements && !frm.doc.compliance_notes) {
        frm.set_value('compliance_notes', requirements.compliance_requirements);
    }
}

function show_regulatory_info(regulation) {
    let dialog = new frappe.ui.Dialog({
        title: __("Regulatory Information"),
        fields: [
            {
                fieldname: "regulatory_info",
                fieldtype: "HTML",
                options: `
                    <div class="regulatory-info">
                        <h5>${regulation.country_name} - Regulatory Requirements</h5>
                        <p><strong>Authority:</strong> ${regulation.regulatory_authority || 'Not specified'}</p>
                        <p><strong>Product Classification:</strong> ${regulation.product_classification || 'Not specified'}</p>
                        <p><strong>Key Requirements:</strong></p>
                        <div>${regulation.key_requirements || 'No specific requirements listed'}</div>
                    </div>
                `
            }
        ]
    });
    
    dialog.show();
}

function show_workflow_dialog(frm, actions) {
    let action_options = actions.map(action => action.action).join("\\n");
    
    let dialog = new frappe.ui.Dialog({
        title: __("Workflow Actions"),
        fields: [
            {
                fieldname: "action",
                label: __("Select Action"),
                fieldtype: "Select",
                options: action_options,
                reqd: 1
            },
            {
                fieldname: "comment",
                label: __("Comment"),
                fieldtype: "Text"
            }
        ],
        primary_action_label: __("Execute Action"),
        primary_action: function(values) {
            frappe.call({
                method: "frappe.client.set_value",
                args: {
                    doctype: "Product Compliance",
                    name: frm.doc.name,
                    fieldname: "workflow_state",
                    value: values.action
                },
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                        dialog.hide();
                    }
                }
            });
        }
    });
    
    dialog.show();
}
