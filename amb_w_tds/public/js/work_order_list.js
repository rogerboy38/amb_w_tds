// Work Order List Override - Show Draft documents
// Path: amb_w_tds/amb_w_tds/public/js/work_order_list.js

frappe.listview_settings['Work Order'] = frappe.listview_settings['Work Order'] || {};

// Add Status and docstatus to list fields
frappe.listview_settings['Work Order'].add_fields = ['status', 'docstatus', 'production_item', 'qty', 'company'];

// Custom indicator to show Draft status
frappe.listview_settings['Work Order'].get_indicator = function(doc) {
    if (doc.docstatus === 0) {
        return [__('Draft'), 'red', 'docstatus,=,0'];
    } else if (doc.status === 'Not Started') {
        return [__('Not Started'), 'orange', 'status,=,Not Started'];
    } else if (doc.status === 'In Process') {
        return [__('In Process'), 'blue', 'status,=,In Process'];  
    } else if (doc.status === 'Completed') {
        return [__('Completed'), 'green', 'status,=,Completed'];
    } else if (doc.status === 'Stopped') {
        return [__('Stopped'), 'darkgrey', 'status,=,Stopped'];
    }
};

// Override onload to modify filters
frappe.listview_settings['Work Order'].onload = function(listview) {
    // Add button to toggle draft visibility
    listview.page.add_inner_button(__('Show Drafts'), function() {
        frappe.route_options = {
            'docstatus': ['in', [0, 1]]
        };
        frappe.set_route('List', 'Work Order');
    });
    
    // Check if we should show drafts
    if (frappe.route_options && frappe.route_options.docstatus) {
        // Drafts filter is applied
        listview.page.set_indicator(__('Including Drafts'), 'orange');
    }
};

// Override get_args to include drafts when requested
frappe.listview_settings['Work Order'].get_args = function(args) {
    // Check URL for docstatus parameter
    const url_params = new URLSearchParams(window.location.search);
    if (url_params.get('docstatus')) {
        args.docstatus = JSON.parse(decodeURIComponent(url_params.get('docstatus')));
    }
    return args;
};
