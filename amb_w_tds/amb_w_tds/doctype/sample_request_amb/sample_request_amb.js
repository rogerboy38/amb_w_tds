frappe.ui.form.on("Sample Request AMB", {
    refresh(frm) {
        // Placeholder for future buttons
    },

    setup(frm) {
        // BUG 81: Set query for Package Type and Container Type fields to filter by Item Group
        frm.set_query("package_type", "samples", function() {
            return {
                filters: {
                    item_group: "Sample Packaging Materials"
                }
            };
        });
        
        // Also filter container_type if it exists (BUG 72B)
        frm.set_query("container_type", "samples", function() {
            return {
                filters: {
                    item_group: "Sample Packaging Materials"
                }
            };
        });
    },

    customer(frm) {
        if (frm.doc.customer) {
            frappe.db.get_value("Customer", frm.doc.customer, "customer_name")
                .then(r => {
                    if (r && r.message) {
                        frm.set_value("customer_name", r.message.customer_name);
                    }
                });
        } else {
            frm.set_value("customer_name", "");
        }
    }
});

frappe.ui.form.on("Sample Request AMB Item", {
    samples_count(frm, cdt, cdn) {
        update_total_qty(cdt, cdn);
    },
    qty_per_sample(frm, cdt, cdn) {
        update_total_qty(cdt, cdn);
    }
});

function update_total_qty(cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    const count = flt(row.samples_count) || 0;
    const per_sample = flt(row.qty_per_sample) || 0;
    frappe.model.set_value(cdt, cdn, "total_qty", count * per_sample);
}
