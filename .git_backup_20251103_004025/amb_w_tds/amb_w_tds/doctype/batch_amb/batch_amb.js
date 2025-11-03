// Copyright (c) 2024, Roger Mori and contributors
// For license information, please see license.txt


frappe.ui.form.on("Batch AMB", {

    refresh(frm) {

        // Add custom buttons

        if (!frm.is_new()) {

            // Split Batch button

            frm.add_custom_button(__('Split Batch'), function() {

                split_batch(frm);

            });


            // Create Items button

            frm.add_custom_button(__('Create Items'), function() {

                create_items(frm);

            });


            // Create BOMs button

            frm.add_custom_button(__('Create BOMs'), function() {

                create_boms(frm);

            });

        }


        // Refresh fields

        frm.refresh_field('batch_details');

        frm.refresh_field('container_details');

    },


    onload(frm) {

        // Set queries for link fields

        frm.set_query('item', function() {

            return {

                filters: {

                    'has_batch_no': 1

                }

            };

        });


        frm.set_query('warehouse', function() {

            return {

                filters: {

                    'is_group': 0

                }

            };

        });

    },


    // Calculate total volume when container details change

    validate(frm) {

        calculate_total_volume(frm);

        calculate_concentrations(frm);

    },


    // Field change handlers

    item(frm) {

        if (frm.doc.item) {

            // Fetch item details

            frappe.call({

                method: 'frappe.client.get',

                args: {

                    doctype: 'Item',

                    name: frm.doc.item

                },

                callback: function(r) {

                    if (r.message) {

                        frm.set_value('item_name', r.message.item_name);

                        frm.set_value('stock_uom', r.message.stock_uom);

                    }

                }

            });

        }

    },


    manufacturing_date(frm) {

        if (frm.doc.manufacturing_date && frm.doc.expiry_period_in_days) {

            calculate_expiry_date(frm);

        }

    },


    expiry_period_in_days(frm) {

        if (frm.doc.manufacturing_date && frm.doc.expiry_period_in_days) {

            calculate_expiry_date(frm);

        }

    },


    total_volume_liters(frm) {

        calculate_concentrations(frm);

    }

});


// Container Details child table

frappe.ui.form.on("Batch Container Detail", {

    container_details_add(frm, cdt, cdn) {

        // Auto-increment container number

        let row = locals[cdt][cdn];

        let max_container = 0;
        

        if (frm.doc.container_details) {

            frm.doc.container_details.forEach(function(d) {

                if (d.container_number && d.container_number > max_container) {

                    max_container = d.container_number;

                }

            });

        }

        

        frappe.model.set_value(cdt, cdn, 'container_number', max_container + 1);

    },


    volume_liters(frm, cdt, cdn) {

        calculate_total_volume(frm);

    },


    container_details_remove(frm, cdt, cdn) {

        calculate_total_volume(frm);

    }

});


// Helper Functions


function calculate_total_volume(frm) {

    let total = 0;

    if (frm.doc.container_details) {

        frm.doc.container_details.forEach(function(row) {

            if (row.volume_liters) {

                total += flt(row.volume_liters);

            }

        });

    }

    frm.set_value('total_volume_liters', total);

}


function calculate_concentrations(frm) {

    if (!frm.doc.total_volume_liters || frm.doc.total_volume_liters === 0) {

        return;

    }


    let total_volume = flt(frm.doc.total_volume_liters);


    // Calculate CBD concentration

    if (frm.doc.total_cbd_mg) {

        let cbd_concentration = (flt(frm.doc.total_cbd_mg) / total_volume);

        frm.set_value('cbd_concentration_mg_ml', cbd_concentration);

    }


    // Calculate THC concentration

    if (frm.doc.total_thc_mg) {

        let thc_concentration = (flt(frm.doc.total_thc_mg) / total_volume);

        frm.set_value('thc_concentration_mg_ml', thc_concentration);

    }


    // Calculate CBG concentration

    if (frm.doc.total_cbg_mg) {

        let cbg_concentration = (flt(frm.doc.total_cbg_mg) / total_volume);

        frm.set_value('cbg_concentration_mg_ml', cbg_concentration);

    }


    // Calculate CBN concentration

    if (frm.doc.total_cbn_mg) {

        let cbn_concentration = (flt(frm.doc.total_cbn_mg) / total_volume);

        frm.set_value('cbn_concentration_mg_ml', cbn_concentration);

    }

}


function calculate_expiry_date(frm) {

    if (frm.doc.manufacturing_date && frm.doc.expiry_period_in_days) {

        let mfg_date = frappe.datetime.str_to_obj(frm.doc.manufacturing_date);

        let expiry_date = frappe.datetime.add_days(mfg_date, frm.doc.expiry_period_in_days);

        frm.set_value('expiry_date', frappe.datetime.obj_to_str(expiry_date));

    }

}


function split_batch(frm) {

    if (!frm.doc.container_details || frm.doc.container_details.length === 0) {

        frappe.msgprint(__('No containers to split'));

        return;

    }


    let d = new frappe.ui.Dialog({

        title: __('Split Batch into Sub-Batches'),

        fields: [

            {

                label: __('Number of Sub-Batches'),

                fieldname: 'num_sub_batches',

                fieldtype: 'Int',

                reqd: 1,

                default: frm.doc.container_details.length

            },

            {

                label: __('Naming Pattern'),

                fieldname: 'naming_pattern',

                fieldtype: 'Data',

                reqd: 1,

                default: frm.doc.name + '-'

            }

        ],

        primary_action_label: __('Split'),

        primary_action(values) {

            frappe.call({

                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.split_batch',

                args: {

                    batch_id: frm.doc.name,

                    num_sub_batches: values.num_sub_batches,

                    naming_pattern: values.naming_pattern

                },

                callback: function(r) {

                    if (r.message) {

                        frappe.msgprint(__('Batch split successfully into {0} sub-batches', [values.num_sub_batches]));

                        frm.reload_doc();

                    }

                }

            });

            d.hide();

        }

    });


    d.show();

}


function create_items(frm) {

    if (!frm.doc.container_details || frm.doc.container_details.length === 0) {

        frappe.msgprint(__('No containers available to create items'));

        return;

    }


    frappe.confirm(

        __('This will create Items for each container. Continue?'),

        function() {

            frappe.call({

                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.create_container_items',

                args: {

                    batch_id: frm.doc.name

                },

                callback: function(r) {

                    if (r.message) {

                        frappe.msgprint({

                            title: __('Items Created'),

                            message: __('Created {0} items successfully', [r.message.length]),

                            indicator: 'green'

                        });

                        frm.reload_doc();

                    }

                }

            });

        }

    );

}


function create_boms(frm) {

    if (!frm.doc.container_details || frm.doc.container_details.length === 0) {

        frappe.msgprint(__('No containers available to create BOMs'));

        return;

    }


    // Check if items exist for containers

    let containers_without_items = frm.doc.container_details.filter(function(row) {

        return !row.item_code;

    });


    if (containers_without_items.length > 0) {

        frappe.msgprint(__('Please create items first using "Create Items" button'));

        return;

    }


    frappe.confirm(

        __('This will create BOMs for each container item. Continue?'),

        function() {

            frappe.call({

                method: 'amb_w_tds.amb_w_tds.doctype.batch_amb.batch_amb.create_container_boms',

                args: {

                    batch_id: frm.doc.name

                },

                callback: function(r) {

                    if (r.message) {

                        frappe.msgprint({

                            title: __('BOMs Created'),

                            message: __('Created {0} BOMs successfully', [r.message.length]),

                            indicator: 'green'

                        });

                        frm.reload_doc();

                    }

                }

            });

        }

    );

}
