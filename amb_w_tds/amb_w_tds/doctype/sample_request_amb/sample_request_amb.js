// Sample Request AMB - v11.0.0 with Logistics & Paqueteria
console.log("🔧 Sample Request AMB JS loaded - Logistics & Paqueteria");

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

		// If batch_reference is set but fields are empty, trigger fetch
		if (frm.doc.batch_reference) {
			const needsFetch = !frm.doc.coa_amb || 
			                   !frm.doc.item || 
			                   !frm.doc.batch_quantity ||
			                   !frm.doc.sales_order_related;
			if (needsFetch) {
				frm.trigger("batch_reference");
			}
		}

		// Add custom buttons for logistics
		frm.add_custom_button(__("Generate Proforma"), function() {
			frm.print_doc("PROFORMA AMB2");
		}, __("Print"));

		// Update shipment type checkboxes based on selection
		if (frm.doc.shipment_type) {
			update_shipment_checkboxes(frm);
		}
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
	},

	// Enhanced: Fetch ALL fields when batch reference changes
	batch_reference(frm) {
		if (!frm.doc.batch_reference) {
			// Clear all batch-related fields
			frm.set_value("coa_amb", "");
			frm.set_value("item", "");
			frm.set_value("batch_quantity", "");
			frm.set_value("item_name", "");
			frm.set_value("custom_golden_number", "");
			frm.set_value("production_plant_name", "");
			frm.set_value("sales_order_related", "");
			frm.set_value("wo_item_name", "");
			frm.set_value("item_to_manufacture", "");
			frm.set_value("planned_qty", "");
			frm.set_value("total_net_weight", "");
			frm.set_value("custom_batch_level", "");
			frm.set_value("title", "");
			return;
		}

		// Show loading indicator
		frm.dashboard.show_progress(__("Loading batch data..."), 0, 1);

		// Fetch ALL fields from Batch AMB
		const fields = [
			"coa_amb",
			"item_to_manufacture",
			"item_name",
			"planned_qty",
			"batch_quantity",
			"total_net_weight",
			"custom_golden_number",
			"production_plant_name",
			"custom_batch_level",
			"title",
			"sales_order_related",
			"wo_item_name",
			"work_order_ref",
			"company",
			"production_plant",
			"custom_plant_code"
		];

		frappe.db.get_value("Batch AMB", frm.doc.batch_reference, fields)
			.then(r => {
				frm.dashboard.hide_progress();
				
				if (r.message) {
					const batch = r.message;
					
					// Set the fetched values
					frm.set_value("coa_amb", batch.coa_amb || "");
					frm.set_value("item", batch.item_to_manufacture || "");
					frm.set_value("item_name", batch.item_name || "");
					frm.set_value("batch_quantity", batch.planned_qty || batch.batch_quantity || batch.total_net_weight || 0);
					
					// Sales Order and Work Order fields
					frm.set_value("sales_order_related", batch.sales_order_related || "");
					frm.set_value("wo_item_name", batch.wo_item_name || "");
					frm.set_value("item_to_manufacture", batch.item_to_manufacture || "");
					frm.set_value("planned_qty", batch.planned_qty || 0);
					frm.set_value("total_net_weight", batch.total_net_weight || 0);
					
					// Optional fields
					if (frm.fields_dict.custom_golden_number) {
						frm.set_value("custom_golden_number", batch.custom_golden_number || "");
					}
					if (frm.fields_dict.production_plant_name) {
						frm.set_value("production_plant_name", batch.production_plant_name || "");
					}
					if (frm.fields_dict.custom_batch_level) {
						frm.set_value("custom_batch_level", batch.custom_batch_level || "");
					}
					if (frm.fields_dict.work_order_ref) {
						frm.set_value("work_order_ref", batch.work_order_ref || "");
					}
					
					// Show success message
					frappe.show_alert({
						message: __("Batch data loaded: {0} | Item: {1} | Qty: {2}", [
							batch.title || batch.name,
							batch.item_to_manufacture || "N/A",
							batch.planned_qty || 0
						]),
						indicator: "green"
					}, 5);
					
					console.log("✅ Batch data fetched:", {
						batch: frm.doc.batch_reference,
						coa_amb: batch.coa_amb,
						item: batch.item_to_manufacture,
						quantity: batch.planned_qty
					});
				}
			})
			.catch(err => {
				frm.dashboard.hide_progress();
				console.error("Error fetching batch data:", err);
				frappe.msgprint({
					title: __("Error"),
					message: __("Failed to fetch batch data. Please try again."),
					indicator: "red"
				});
			});
	},

	// When item changes, fetch TDS and additional item details
	item(frm) {
		if (frm.doc.item) {
			const fields = ["custom_product_key_tds", "item_name", "description", "stock_uom"];
			frappe.db.get_value("Item", frm.doc.item, fields)
				.then(r => {
					if (r.message) {
						if (r.message.custom_product_key_tds) {
							frm.set_value("custom_product_key_tds", r.message.custom_product_key_tds);
						}
						if (r.message.item_name && !frm.doc.item_name) {
							frm.set_value("item_name", r.message.item_name);
						}
					}
				});
		}
	},

	// ========================================
	// LOGISTICS & PAQUETERIA HANDLERS
	// ========================================
	
	// Update shipment purpose from any of the nature fields
	shipment_nature(frm) {
		if (frm.doc.shipment_nature) {
			update_shipment_checkboxes(frm);
		}
	},

	internal_export_type(frm) {
		if (frm.doc.internal_export_type) {
			update_shipment_checkboxes(frm);
		}
	},

	special_export_type(frm) {
		if (frm.doc.special_export_type) {
			update_shipment_checkboxes(frm);
		}
	},

	// Update shipment type based on checkboxes
	cb_muestra(frm) {
		if (frm.doc.cb_muestra) {
			frm.set_value("shipment_type", "Muestra");
			frm.set_value("cb_venta_paqueteria", 0);
			frm.set_value("cb_forwarder", 0);
		}
	},

	cb_venta_paqueteria(frm) {
		if (frm.doc.cb_venta_paqueteria) {
			frm.set_value("shipment_type", "Venta; Paqueteria");
			frm.set_value("cb_muestra", 0);
			frm.set_value("cb_forwarder", 0);
		}
	},

	cb_forwarder(frm) {
		if (frm.doc.cb_forwarder) {
			frm.set_value("shipment_type", "Forwarder");
			frm.set_value("cb_muestra", 0);
			frm.set_value("cb_venta_paqueteria", 0);
		}
	},

	// Validate weight and packages
	gross_weight_kg(frm) {
		if (frm.doc.gross_weight_kg < 0) {
			frm.set_value("gross_weight_kg", 0);
		}
	},

	number_of_packages(frm) {
		if (frm.doc.number_of_packages < 1) {
			frm.set_value("number_of_packages", 1);
		}
	},

	commercial_value_usd(frm) {
		if (frm.doc.commercial_value_usd < 0) {
			frm.set_value("commercial_value_usd", 0);
		}
	}
});

// ========================================
// CHILD TABLE HANDLERS
// ========================================

frappe.ui.form.on("Sample Request AMB Item", {
	samples_count(frm, cdt, cdn) {
		update_total_qty(cdt, cdn);
	},
	qty_per_sample(frm, cdt, cdn) {
		update_total_qty(cdt, cdn);
	},
	item_code(frm, cdt, cdn) {
		// When item changes in child table, fetch description
		const row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			frappe.db.get_value("Item", row.item_code, ["description", "item_name"])
				.then(r => {
					if (r.message) {
						if (r.message.description) {
							frappe.model.set_value(cdt, cdn, "description", r.message.description);
						}
						if (r.message.item_name) {
							frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
						}
					}
				});
		}
	}
});

// ========================================
// HELPER FUNCTIONS
// ========================================

function update_total_qty(cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	const count = flt(row.samples_count) || 0;
	const per_sample = flt(row.qty_per_sample) || 0;
	frappe.model.set_value(cdt, cdn, "total_qty", count * per_sample);
}

function update_shipment_checkboxes(frm) {
	// This function can be expanded to sync checkbox states
	// based on the selected shipment purpose
	console.log("Shipment purpose updated:", {
		shipment_nature: frm.doc.shipment_nature,
		internal_export_type: frm.doc.internal_export_type,
		special_export_type: frm.doc.special_export_type
	});
}
