// Sample Request AMB - v10.0.0 Consolidated
console.log("🔧 Sample Request AMB JS loaded");

frappe.ui.form.on("Sample Request AMB", {
	refresh(frm) {
		// BUG 81 – Filter package_type to Sample Packaging Materials
		frm.fields_dict.samples.grid.get_field("package_type").get_query = function (doc, cdt, cdn) {
			return {
				filters: { item_group: "Sample Packaging Materials" }
			};
		};

		// BUG 81 – Filter container_type to FG Packaging Materials
		frm.fields_dict.samples.grid.get_field("container_type").get_query = function (doc, cdt, cdn) {
			return {
				filters: { item_group: "FG Packaging Materials" }
			};
		};
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