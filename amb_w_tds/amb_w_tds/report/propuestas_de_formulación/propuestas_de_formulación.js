// Script Report "Propuestas de Formulación" — read-only comparison of draft Mix proposals.
// Excel/CSV: the report's own Export. PDF: the "PDF para Dirección" button renders the
// Print Format "Propuestas de Formulación" (server-side Jinja) for the same product/order.

frappe.query_reports["Propuestas de Formulación"] = {
	filters: [
		{ fieldname: "producto", label: __("Producto"), fieldtype: "Link", options: "Item", reqd: 1 },
		{ fieldname: "sales_order", label: __("Pedido"), fieldtype: "Link", options: "Sales Order" },
		{
			fieldname: "tds",
			label: __("TDS (opcional)"),
			fieldtype: "Link",
			options: "TDS Product Specification",
			// any approved or draft TDS: prod TDS name a longer Item than the proposal's SKU,
			// so filtering the list by product_item would hide the right one; cancelled never judges
			get_query: () => ({ filters: { docstatus: ["<", 2] } }),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = `<b>${value}</b>`;
		}
		return value;
	},

	onload(report) {
		report.page.add_inner_button(__("PDF para Dirección"), () => {
			const first = (report.data || []).find((r) => r.propuesta);
			if (!first) {
				frappe.msgprint(__("No hay propuestas para este filtro."));
				return;
			}
			// Pass the report's own filters so the PDF judges and scopes exactly as the screen:
			// an empty pedido means "all orders" (not the first proposal's own order), an empty
			// tds means "each proposal's target_tds".
			const params = new URLSearchParams({
				doctype: "BOM Formula",
				name: first.propuesta,
				format: "Propuestas de Formulación",
				no_letterhead: 1,
				pedido: frappe.query_report.get_filter_value("sales_order") || "",
				tds: frappe.query_report.get_filter_value("tds") || "",
			});
			window.open(`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`);
		});
	},
};
