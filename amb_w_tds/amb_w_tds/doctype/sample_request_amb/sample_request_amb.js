// Sample Request AMB - v11.2.0 Logistics, Paqueteria & Weight Model (shipment vs batch)
console.log("🔧 Sample Request AMB JS loaded - v11.2.0 weight model");
frappe.ui.form.on("Sample Request AMB", {
	refresh(frm) {
		frm.fields_dict.samples.grid.get_field("package_type").get_query = function () {
			return { filters: { item_group: "Sample Packaging Materials" } };
		};
		frm.fields_dict.samples.grid.get_field("container_type").get_query = function () {
			return { filters: { item_group: "FG Packaging Materials" } };
		};
		if (frm.doc.batch_reference) {
			const needsFetch = !frm.doc.coa_amb || !frm.doc.item || !frm.doc.batch_quantity || !frm.doc.sales_order_related;
			if (needsFetch) frm.trigger("batch_reference");
		}
		if (frm.doc.shipment_type) update_shipment_checkboxes(frm);
	},
	customer(frm) {
		if (frm.doc.customer) {
			frappe.db.get_value("Customer", frm.doc.customer, ["customer_name", "customer_primary_address", "customer_primary_contact"])
				.then(r => {
					if (r && r.message) {
						frm.set_value("customer_name", r.message.customer_name);
						if (r.message.customer_primary_address) frm.set_value("address", r.message.customer_primary_address);
						if (r.message.customer_primary_contact) frm.set_value("contact_person", r.message.customer_primary_contact);
					}
				});
		} else { frm.set_value("customer_name", ""); }
	},
	batch_reference(frm) {
		if (!frm.doc.batch_reference) {
			["coa_amb","item","batch_quantity","item_name","custom_golden_number","production_plant_name",
			 "sales_order_related","wo_item_name","item_to_manufacture","planned_qty","total_net_weight",
			 "custom_batch_level","title"].forEach(f => frm.set_value(f, ""));
			return;
		}
		frm.dashboard.show_progress(__("Loading batch data..."), 0, 1);
		const fields = ["coa_amb","item_to_manufacture","item_name","planned_qty","batch_quantity",
			"total_net_weight","custom_golden_number","production_plant_name","custom_batch_level",
			"title","sales_order_related","wo_item_name","work_order_ref","company","production_plant","custom_plant_code"];
		frappe.db.get_value("Batch AMB", frm.doc.batch_reference, fields)
			.then(r => {
				frm.dashboard.hide_progress();
				if (r.message) {
					const b = r.message;
					frm.set_value("coa_amb", b.coa_amb || "");
					frm.set_value("item", b.item_to_manufacture || "");
					frm.set_value("item_name", b.item_name || "");
					frm.set_value("batch_quantity", b.planned_qty || b.batch_quantity || b.total_net_weight || 0);
					frm.set_value("sales_order_related", b.sales_order_related || "");
					frm.set_value("wo_item_name", b.wo_item_name || "");
					frm.set_value("item_to_manufacture", b.item_to_manufacture || "");
					frm.set_value("planned_qty", b.planned_qty || 0);
					frm.set_value("total_net_weight", b.total_net_weight || 0);  // BATCH net (reference)
					if (frm.fields_dict.custom_golden_number) frm.set_value("custom_golden_number", b.custom_golden_number || "");
					if (frm.fields_dict.production_plant_name) frm.set_value("production_plant_name", b.production_plant_name || "");
					if (frm.fields_dict.custom_batch_level) frm.set_value("custom_batch_level", b.custom_batch_level || "");
					if (frm.fields_dict.work_order_ref) frm.set_value("work_order_ref", b.work_order_ref || "");
					frappe.show_alert({ message: __("Batch data loaded: {0} | Item: {1} | Qty: {2}", [b.title || b.name, b.item_to_manufacture || "N/A", b.planned_qty || 0]), indicator: "green" }, 5);
				}
			})
			.catch(err => { frm.dashboard.hide_progress(); console.error(err); frappe.msgprint({ title: __("Error"), message: __("Failed to fetch batch data."), indicator: "red" }); });
	},
	item(frm) {
		if (frm.doc.item) {
			frappe.db.get_value("Item", frm.doc.item, ["custom_product_key_tds", "item_name", "description", "stock_uom"])
				.then(r => {
					if (r.message) {
						if (r.message.custom_product_key_tds) frm.set_value("custom_product_key_tds", r.message.custom_product_key_tds);
						if (r.message.item_name && !frm.doc.item_name) frm.set_value("item_name", r.message.item_name);
					}
				});
		}
	},
	shipment_nature(frm) { if (frm.doc.shipment_nature) update_shipment_checkboxes(frm); },
	internal_export_type(frm) { if (frm.doc.internal_export_type) update_shipment_checkboxes(frm); },
	special_export_type(frm) { if (frm.doc.special_export_type) update_shipment_checkboxes(frm); },
	cb_muestra(frm) { if (frm.doc.cb_muestra) { frm.set_value("shipment_type", "Muestra"); frm.set_value("cb_venta_paqueteria", 0); frm.set_value("cb_forwarder", 0); } },
	cb_venta_paqueteria(frm) { if (frm.doc.cb_venta_paqueteria) { frm.set_value("shipment_type", "Venta; Paqueteria"); frm.set_value("cb_muestra", 0); frm.set_value("cb_forwarder", 0); } },
	cb_forwarder(frm) { if (frm.doc.cb_forwarder) { frm.set_value("shipment_type", "Forwarder"); frm.set_value("cb_muestra", 0); frm.set_value("cb_venta_paqueteria", 0); } },
	gross_weight_kg(frm) { if (frm.doc.gross_weight_kg < 0) frm.set_value("gross_weight_kg", 0); },
	number_of_packages(frm) { if (frm.doc.number_of_packages < 1) frm.set_value("number_of_packages", 1); },
	commercial_value_usd(frm) { if (frm.doc.commercial_value_usd < 0) frm.set_value("commercial_value_usd", 0); }
});
frappe.ui.form.on("Sample Request AMB Item", {
	samples_count(frm, cdt, cdn) { update_total_qty(cdt, cdn); amb_row_wt(frm, cdt, cdn); },
	qty_per_sample(frm, cdt, cdn) { update_total_qty(cdt, cdn); amb_row_wt(frm, cdt, cdn); },
	number_of_boxes(frm, cdt, cdn) { amb_row_wt(frm, cdt, cdn); },
	package_type(frm, cdt, cdn) { amb_fetch_w(frm, cdt, cdn, "package_type", "bag_weight"); },
	container_type(frm, cdt, cdn) { amb_fetch_w(frm, cdt, cdn, "container_type", "box_weight"); },
	samples_remove(frm) { amb_wt_rollup(frm); },
	item(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.item) {
			frappe.db.get_value("Item", row.item, ["description", "item_name"]).then(r => {
				if (r.message) {
					if (r.message.description) frappe.model.set_value(cdt, cdn, "description", r.message.description);
					if (r.message.item_name) frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
				}
			});
		}
	}
});
function update_total_qty(cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	frappe.model.set_value(cdt, cdn, "total_qty", (flt(row.samples_count) || 0) * (flt(row.qty_per_sample) || 0));
}
function amb_fetch_w(frm, cdt, cdn, src, target) {
	const row = frappe.get_doc(cdt, cdn);
	if (!row[src]) { amb_row_wt(frm, cdt, cdn); return; }
	frappe.db.get_value("Item", row[src], "weight_per_unit").then(r => {
		frappe.model.set_value(cdt, cdn, target, (r.message && r.message.weight_per_unit) || 0);
		amb_row_wt(frm, cdt, cdn);
	});
}
function amb_row_wt(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	const net = flt(row.samples_count) * flt(row.qty_per_sample);
	const tara = flt(row.samples_count) * flt(row.bag_weight) + (flt(row.number_of_boxes) || 1) * flt(row.box_weight);
	frappe.model.set_value(cdt, cdn, "row_net_weight", net);
	frappe.model.set_value(cdt, cdn, "row_tara_weight", tara);
	frappe.model.set_value(cdt, cdn, "row_gross_weight", net + tara);
	amb_wt_rollup(frm);
}
function amb_wt_rollup(frm) {
	let n = 0, t = 0, g = 0;
	(frm.doc.samples || []).forEach(r => { n += flt(r.row_net_weight); t += flt(r.row_tara_weight); g += flt(r.row_gross_weight); });
	frm.set_value("shipment_net_weight", n);
	frm.set_value("shipment_tara_weight", t);
	frm.set_value("computed_gross_kg", g);
	if (!flt(frm.doc.gross_weight_kg)) frm.set_value("gross_weight_kg", g);
}
function update_shipment_checkboxes(frm) {
	console.log("Shipment purpose:", { shipment_nature: frm.doc.shipment_nature, internal_export_type: frm.doc.internal_export_type, special_export_type: frm.doc.special_export_type });
}
