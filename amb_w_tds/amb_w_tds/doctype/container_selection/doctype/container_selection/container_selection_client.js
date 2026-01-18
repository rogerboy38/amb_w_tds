// ================================================
// CONTAINER SELECTION CLIENT SCRIPT
// ================================================

frappe.ui.form.on('Container Selection', {
    // Form event handlers
    onload: function(frm) {
        // Initialize form with available containers
        frm.set_query("current_batch", function() {
            return {
                filters: {
                    "status": "Active"
                }
            };
        });

        // Set up conditional display based on container status
        frm.toggle_display('assignment_section', 
            frm.doc.container_status === 'In Use');

        // Add custom buttons
        frm.add_custom_button(__('Release Assignment'), function() {
            release_container_assignment(frm);
        });

        frm.add_custom_button(__('Get Status Summary'), function() {
            get_status_summary(frm);
        });

        frm.add_custom_button(__('Find Available'), function() {
            find_available_containers(frm);
        });
    },

    // Field change handlers
    container_status: function(frm) {
        // Update form visibility based on status
        frm.toggle_display('assignment_section', 
            frm.doc.container_status === 'In Use');

        // Auto-handle status changes
        if (frm.doc.container_status === 'In Use') {
            if (!frm.doc.current_batch) {
                frappe.msgprint(__('Please assign a batch to this container.'));
            }
        } else if (frm.doc.container_status === 'Maintenance' || 
                   frm.doc.container_status === 'Available') {
            // Clear assignment when moving to maintenance or available
            frm.set_value('current_batch', null);
            frm.set_value('assignment_date', null);
            frm.set_value('assigned_by', null);
        }

        // Update capacity validation display
        update_capacity_validation(frm);
    },

    container_type: function(frm) {
        // Update capacity validation when type changes
        update_capacity_validation(frm);
    },

    capacity_liters: function(frm) {
        // Validate capacity in real-time
        validate_capacity_input(frm);
    },

    current_batch: function(frm) {
        // Auto-fill assignment details when batch is selected
        if (frm.doc.current_batch && frm.doc.container_status === 'In Use') {
            if (!frm.doc.assignment_date) {
                frm.set_value('assignment_date', frappe.datetime.now());
            }
            if (!frm.doc.assigned_by) {
                frm.set_value('assigned_by', frappe.session.user);
            }
        }
    },

    // Validation handlers
    before_save: function(frm) {
        return validate_container_form(frm);
    },

    // Refresh handler
    refresh: function(frm) {
        // Update form styling based on status
        update_form_styling(frm);
        
        // Add status indicator
        add_status_indicator(frm);

        // Set up keyboard shortcuts
        setup_keyboard_shortcuts(frm);
    }
});

// ================================================
// CLIENT FUNCTIONS
// ================================================

function update_capacity_validation(frm) {
    const capacity_limits = {
        "Sample Container": 10,
        "Production Container": 5000,
        "QC Container": 50,
        "Storage Container": 10000
    };

    if (frm.doc.container_type && capacity_limits[frm.doc.container_type]) {
        const max_capacity = capacity_limits[frm.doc.container_type];
        frm.fields_dict.capacity_liters.df.description = 
            `Maximum capacity for ${frm.doc.container_type}: ${max_capacity} liters`;
        frm.refresh_field('capacity_liters');
    }
}

function validate_capacity_input(frm) {
    if (frm.doc.capacity_liters <= 0) {
        frappe.msgprint({
            title: __('Validation Error'),
            message: __('Container capacity must be a positive value.'),
            indicator: 'red'
        });
        return false;
    }
    return true;
}

function update_form_styling(frm) {
    // Remove existing status classes
    frm.wrapper.find('.form-group').removeClass('status-available status-inuse status-maintenance status-retired');
    
    // Add status-specific styling
    const statusClass = 'status-' + (frm.doc.container_status || '').toLowerCase().replace(' ', '');
    frm.wrapper.find('.form-section:contains("Container Information")').addClass(statusClass);
}

function add_status_indicator(frm) {
    // Remove existing indicator
    frm.wrapper.find('.status-indicator').remove();
    
    // Add new indicator
    const statusColors = {
        'Available': 'green',
        'In Use': 'blue',
        'Maintenance': 'orange',
        'Retired': 'red'
    };
    
    const color = statusColors[frm.doc.container_status] || 'gray';
    
    frm.wrapper.find('.form-header h4').after(
        `<div class="status-indicator status-${color.toLowerCase()}">
            <span class="indicator-dot ${color}"></span>
            ${__(frm.doc.container_status)}
        </div>`
    );
}

function setup_keyboard_shortcuts(frm) {
    // Ctrl+S to save and validate
    $(document).on('keydown.container_selection', function(e) {
        if (e.ctrlKey && e.which === 83) {
            e.preventDefault();
            frm.save();
        }
    });
}

function validate_container_form(frm) {
    let is_valid = true;
    let error_messages = [];

    // Validate required fields
    if (!frm.doc.container_id) {
        error_messages.push(__('Container ID is required'));
        is_valid = false;
    }

    if (!frm.doc.container_type) {
        error_messages.push(__('Container type is required'));
        is_valid = false;
    }

    if (!frm.doc.capacity_liters || frm.doc.capacity_liters <= 0) {
        error_messages.push(__('Valid capacity is required'));
        is_valid = false;
    }

    // Validate business rules
    if (frm.doc.container_status === 'In Use' && !frm.doc.current_batch) {
        error_messages.push(__('In Use containers must have a current batch assigned'));
        is_valid = false;
    }

    if (frm.doc.container_status === 'Available' && frm.doc.current_batch) {
        error_messages.push(__('Available containers cannot have current batch assignments'));
        is_valid = false;
    }

    // Show validation errors
    if (!is_valid) {
        frappe.msgprint({
            title: __('Validation Errors'),
            message: error_messages.join('<br>'),
            indicator: 'red'
        });
    }

    return is_valid;
}

// ================================================
// AJAX FUNCTIONS
// ================================================

function release_container_assignment(frm) {
    if (!frm.doc.current_batch) {
        frappe.msgprint(__('This container is not currently assigned to any batch.'));
        return;
    }

    frappe.confirm(
        __('Are you sure you want to release the current batch assignment?'),
        function() {
            frappe.call({
                method: 'frappe.client.run_method',
                args: {
                    dt: 'Container Selection',
                    dn: frm.doc.name,
                    method: 'release_container_assignment',
                    args: { container_name: frm.doc.name }
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(__('Assignment released successfully'));
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}

function get_status_summary(frm) {
    frappe.call({
        method: 'frappe.client.run_method',
        args: {
            dt: 'Container Selection',
            method: 'get_container_status_summary'
        },
        callback: function(r) {
            if (r.message) {
                show_status_summary_dialog(r.message);
            }
        }
    });
}

function find_available_containers(frm) {
    frappe.call({
        method: 'frappe.client.run_method',
        args: {
            dt: 'Container Selection',
            method: 'get_available_containers_by_type'
        },
        callback: function(r) {
            if (r.message) {
                show_available_containers_dialog(r.message);
            }
        }
    });
}

function show_status_summary_dialog(summary_data) {
    let html = '<table class="table table-bordered"><thead><tr>';
    html += '<th>Status</th><th>Count</th><th>Total Capacity (L)</th></tr></thead><tbody>';
    
    summary_data.forEach(function(row) {
        html += `<tr><td>${row.container_status}</td><td>${row.count}</td><td>${row.total_capacity || 0}</td></tr>`;
    });
    
    html += '</tbody></table>';

    const dialog = new frappe.ui.Dialog({
        title: __('Container Status Summary'),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'summary_table',
            options: html
        }]
    });

    dialog.show();
}

function show_available_containers_dialog(containers_data) {
    let html = '<div class="container-list">';
    
    const grouped_by_type = {};
    containers_data.forEach(function(container) {
        if (!grouped_by_type[container.container_type]) {
            grouped_by_type[container.container_type] = [];
        }
        grouped_by_type[container.container_type].push(container);
    });
    
    for (const [type, containers] of Object.entries(grouped_by_type)) {
        html += `<h5>${type}</h5><ul>`;
        containers.forEach(function(container) {
            html += `<li>${container.container_id} - ${container.capacity_liters}L</li>`;
        });
        html += '</ul>';
    }
    
    html += '</div>';

    const dialog = new frappe.ui.Dialog({
        title: __('Available Containers'),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'containers_list',
            options: html
        }]
    });

    dialog.show();
}

// ================================================
// UTILITY FUNCTIONS
// ================================================

// Clean up event listeners when form is destroyed
frappe.ui.form.on('Container Selection', {
    onload_post_render: function(frm) {
        $(document).off('keydown.container_selection');
    }
});

// Global utility functions
frappe.provide('container_selection');

container_selection.utils = {
    format_capacity: function(capacity) {
        return capacity + ' L';
    },

    get_status_color: function(status) {
        const colors = {
            'Available': '#28a745',
            'In Use': '#007bff',
            'Maintenance': '#ffc107',
            'Retired': '#dc3545'
        };
        return colors[status] || '#6c757d';
    },

    validate_container_id: function(container_id) {
        // Validate container ID format
        if (!container_id || container_id.length < 3) {
            frappe.msgprint(__('Container ID must be at least 3 characters long.'));
            return false;
        }
        return true;
    }
};