/**
 * Distribution Organization Form Script
 * 
 * Client-side JavaScript for the Distribution Organization form,
 * handling user interactions, validations, and dynamic behavior.
 */

frappe.ui.form.on('Distribution Organization', {
    refresh: function(frm) {
        // Add custom buttons and actions
        add_custom_buttons(frm);
        
        // Set form styling
        set_form_styling(frm);
        
        // Update status indicators
        update_status_indicators(frm);
    },
    
    onload: function(frm) {
        // Set field properties and filters
        set_field_properties(frm);
        
        // Load country-specific data if country is set
        if (frm.doc.country) {
            load_country_regulations(frm);
        }
    },
    
    country: function(frm) {
        // When country changes, update related fields
        if (frm.doc.country) {
            load_country_regulations(frm);
            set_default_currency(frm);
            clear_territory(frm);
        }
    },
    
    organization_name: function(frm) {
        // Check for duplicate organization names in the same country
        if (frm.doc.organization_name && frm.doc.country) {
            check_duplicate_organization(frm);
        }
    },
    
    organization_type: function(frm) {
        // Set default values based on organization type
        set_organization_type_defaults(frm);
    },
    
    agreement_expiry: function(frm) {
        // Validate agreement expiry date
        validate_agreement_expiry(frm);
    },
    
    email_id: function(frm) {
        // Validate email format
        if (frm.doc.email_id) {
            validate_email_format(frm);
        }
    },
    
    before_save: function(frm) {
        // Final validations before saving
        perform_pre_save_validations(frm);
    }
});

function add_custom_buttons(frm) {
    if (!frm.doc.__islocal) {
        // Add "View Hierarchy" button
        frm.add_custom_button(__('View Hierarchy'), function() {
            show_organization_hierarchy(frm);
        }, __('Actions'));
        
        // Add "Compliance Checklist" button
        frm.add_custom_button(__('Compliance Checklist'), function() {
            show_compliance_checklist(frm);
        }, __('Actions'));
        
        // Add "Create Customer" button if not exists
        if (frm.doc.organization_type in ['Distributor', 'Retailer', 'Wholesaler']) {
            frm.add_custom_button(__('Create Customer'), function() {
                create_customer_record(frm);
            }, __('Create'));
        }
        
        // Add "Create Supplier" button if not exists
        if (frm.doc.organization_type in ['Supplier', 'Manufacturer']) {
            frm.add_custom_button(__('Create Supplier'), function() {
                create_supplier_record(frm);
            }, __('Create'));
        }
        
        // Add "Export Data" button
        frm.add_custom_button(__('Export Data'), function() {
            export_organization_data(frm);
        }, __('Actions'));
        
        // Add "Market Research" button
        frm.add_custom_button(__('Market Research'), function() {
            create_market_research(frm);
        }, __('Create'));
        
        // Add "Analytics Dashboard" button
        frm.add_custom_button(__('Analytics Dashboard'), function() {
            frappe.set_route('query-report', 'Distribution Analytics Report', {
                'organization_type': frm.doc.organization_type,
                'country': frm.doc.country
            });
        }, __('View'));
    }
}

function set_form_styling(frm) {
    // Add status-specific styling
    if (frm.doc.status) {
        const status_colors = {
            'Active': 'green',
            'Inactive': 'red',
            'Pending': 'orange',
            'Suspended': 'red',
            'Terminated': 'dark'
        };
        
        if (status_colors[frm.doc.status]) {
            frm.dashboard.set_headline_alert(
                `Organization Status: ${frm.doc.status}`,
                status_colors[frm.doc.status]
            );
        }
    }
    
    // Add regulatory status indicator
    if (frm.doc.regulatory_status) {
        const reg_colors = {
            'Compliant': 'green',
            'Pending Review': 'orange',
            'Non-Compliant': 'red',
            'Expired': 'red',
            'Not Applicable': 'blue'
        };
        
        if (reg_colors[frm.doc.regulatory_status]) {
            frm.dashboard.add_indicator(
                `Regulatory: ${frm.doc.regulatory_status}`,
                reg_colors[frm.doc.regulatory_status]
            );
        }
    }
}

function update_status_indicators(frm) {
    // Check agreement expiry
    if (frm.doc.agreement_expiry) {
        const today = frappe.datetime.get_today();
        const expiry_date = frm.doc.agreement_expiry;
        const days_to_expiry = frappe.datetime.get_diff(expiry_date, today);
        
        if (days_to_expiry < 0) {
            frm.dashboard.add_indicator(__('Agreement Expired'), 'red');
        } else if (days_to_expiry <= 30) {
            frm.dashboard.add_indicator(__('Agreement Expiring Soon'), 'orange');
        }
    }
    
    // Check audit due date
    if (frm.doc.next_audit_due) {
        const today = frappe.datetime.get_today();
        const audit_due = frm.doc.next_audit_due;
        const days_to_audit = frappe.datetime.get_diff(audit_due, today);
        
        if (days_to_audit < 0) {
            frm.dashboard.add_indicator(__('Audit Overdue'), 'red');
        } else if (days_to_audit <= 30) {
            frm.dashboard.add_indicator(__('Audit Due Soon'), 'orange');
        }
    }
}

function set_field_properties(frm) {
    // Set territory filter based on country
    frm.set_query('territory', function() {
        return {
            filters: {
                'is_group': 0
            }
        };
    });
    
    // Set parent organization filter (exclude self)
    frm.set_query('parent_organization', function() {
        return {
            filters: {
                'name': ['!=', frm.doc.name || '']
            }
        };
    });
    
    // Set currency filter to show active currencies
    frm.set_query('currency', function() {
        return {
            filters: {
                'enabled': 1
            }
        };
    });
}

function load_country_regulations(frm) {
    if (frm.doc.country) {
        frappe.call({
            method: 'get_country_regulations',
            doc: frm.doc,
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    const regulations = r.message[0];
                    
                    // Show regulatory information in a message
                    const msg = `
                        <strong>Regulatory Authority:</strong> ${regulations.regulatory_authority || 'Not specified'}<br>
                        <strong>Website:</strong> ${regulations.authority_website ? 
                            `<a href="${regulations.authority_website}" target="_blank">${regulations.authority_website}</a>` : 
                            'Not specified'}
                    `;
                    
                    frm.dashboard.add_comment(msg, 'blue', true);
                }
            }
        });
    }
}

function set_default_currency(frm) {
    if (frm.doc.country && !frm.doc.currency) {
        frappe.db.get_value('Country', frm.doc.country, 'default_currency')
            .then(r => {
                if (r.message && r.message.default_currency) {
                    frm.set_value('currency', r.message.default_currency);
                }
            });
    }
}

function clear_territory(frm) {
    // Clear territory when country changes to avoid invalid combinations
    if (frm.doc.territory) {
        frm.set_value('territory', '');
        frappe.msgprint(__('Territory cleared. Please select appropriate territory for the new country.'));
    }
}

function check_duplicate_organization(frm) {
    frappe.call({
        method: 'sysmayal.sysmayal.doctype.distribution_organization.distribution_organization.check_duplicate_organization',
        args: {
            organization_name: frm.doc.organization_name,
            country: frm.doc.country
        },
        callback: function(r) {
            if (r.message && r.message.exists && r.message.name !== frm.doc.name) {
                frappe.msgprint({
                    title: __('Duplicate Organization'),
                    message: __('An organization with this name already exists in {0}. Please check: {1}', 
                        [frm.doc.country, r.message.name]),
                    indicator: 'orange'
                });
            }
        }
    });
}

function set_organization_type_defaults(frm) {
    // Set default regulatory status based on organization type
    if (!frm.doc.regulatory_status) {
        const regulatory_defaults = {
            'Distributor': 'Pending Review',
            'Retailer': 'Pending Review',
            'Supplier': 'Pending Review',
            'Manufacturer': 'Pending Review',
            'Regulatory Body': 'Not Applicable',
            'Consultant': 'Not Applicable'
        };
        
        if (regulatory_defaults[frm.doc.organization_type]) {
            frm.set_value('regulatory_status', regulatory_defaults[frm.doc.organization_type]);
        }
    }
}

function validate_agreement_expiry(frm) {
    if (frm.doc.agreement_expiry) {
        const today = frappe.datetime.get_today();
        if (frm.doc.agreement_expiry < today) {
            frappe.msgprint({
                title: __('Agreement Expired'),
                message: __('The distribution agreement expiry date is in the past.'),
                indicator: 'orange'
            });
        }
    }
}

function validate_email_format(frm) {
    const email_regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email_regex.test(frm.doc.email_id)) {
        frappe.msgprint(__('Please enter a valid email address'));
        frm.set_value('email_id', '');
    }
}

function perform_pre_save_validations(frm) {
    // Validate required field combinations
    if (frm.doc.organization_type === 'Distributor' && !frm.doc.territory) {
        frappe.validated = false;
        frappe.msgprint(__('Territory is required for Distributor organizations'));
        return;
    }
    
    // Validate business information for commercial organizations
    const commercial_types = ['Distributor', 'Retailer', 'Supplier', 'Manufacturer', 'Wholesaler'];
    if (commercial_types.includes(frm.doc.organization_type)) {
        if (!frm.doc.contact_person || !frm.doc.email_id) {
            frappe.msgprint(__('Contact person and email are required for commercial organizations'));
        }
    }
}

function show_organization_hierarchy(frm) {
    frappe.call({
        method: 'sysmayal.sysmayal.doctype.distribution_organization.distribution_organization.get_organization_hierarchy',
        args: {
            organization_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                const hierarchy_html = build_hierarchy_html(r.message);
                
                frappe.msgprint({
                    title: __('Organization Hierarchy'),
                    message: hierarchy_html,
                    wide: true
                });
            }
        }
    });
}

function build_hierarchy_html(hierarchy, level = 0) {
    const indent = '&nbsp;'.repeat(level * 4);
    let html = `${indent}<strong>${hierarchy.organization_name}</strong> (${hierarchy.organization_type}) - ${hierarchy.status}<br>`;
    
    if (hierarchy.children && hierarchy.children.length > 0) {
        hierarchy.children.forEach(child => {
            html += build_hierarchy_html(child, level + 1);
        });
    }
    
    return html;
}

function show_compliance_checklist(frm) {
    frappe.call({
        method: 'get_compliance_checklist',
        doc: frm.doc,
        callback: function(r) {
            if (r.message) {
                const checklist_html = build_checklist_html(r.message);
                
                frappe.msgprint({
                    title: __('Compliance Checklist'),
                    message: checklist_html,
                    wide: true
                });
            }
        }
    });
}

function build_checklist_html(checklist) {
    let html = '<table class="table table-bordered"><thead><tr><th>Item</th><th>Status</th><th>Details</th></tr></thead><tbody>';
    
    checklist.forEach(item => {
        const status_color = {
            'Complete': 'success',
            'Compliant': 'success',
            'Valid': 'success',
            'Incomplete': 'warning',
            'Pending Review': 'warning',
            'Expiring Soon': 'warning',
            'Expired': 'danger',
            'Non-Compliant': 'danger',
            'Not Set': 'secondary'
        };
        
        const color = status_color[item.status] || 'secondary';
        
        html += `
            <tr>
                <td>${item.item}</td>
                <td><span class="badge badge-${color}">${item.status}</span></td>
                <td>${item.details}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    return html;
}

function create_customer_record(frm) {
    frappe.new_doc('Customer', {
        customer_name: frm.doc.organization_name,
        customer_type: 'Company',
        territory: frm.doc.territory,
        custom_distribution_organization: frm.doc.name
    });
}

function create_supplier_record(frm) {
    frappe.new_doc('Supplier', {
        supplier_name: frm.doc.organization_name,
        supplier_type: 'Company',
        custom_distribution_organization: frm.doc.name
    });
}

function export_organization_data(frm) {
    const export_data = {
        organization: frm.doc,
        export_date: frappe.datetime.get_today(),
        export_time: frappe.datetime.get_time()
    };
    
    const dataStr = JSON.stringify(export_data, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `${frm.doc.organization_name}_${frappe.datetime.get_today()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

function create_market_research(frm) {
    // Create new Market Research document with pre-filled data from organization
    frappe.new_doc('Market Research', {
        research_title: `Market Analysis - ${frm.doc.organization_name}`,
        research_type: 'Market Analysis',
        country: frm.doc.country,
        region: frm.doc.territory,
        research_lead: frappe.session.user,
        research_date: frappe.datetime.get_today(),
        priority: 'Medium',
        target_demographics: `Target market for ${frm.doc.organization_type} in ${frm.doc.country}`,
        additional_notes: `Research initiated from Distribution Organization: ${frm.doc.name}`
    });
}
