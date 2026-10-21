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
			get_query: () => {
				const producto = frappe.query_report.get_filter_value("producto");
				return { filters: producto ? { product_item: producto, docstatus: 1 } : { docstatus: 1 } };
			},
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
			const params = new URLSearchParams({
				doctype: "BOM Formula",
				name: first.propuesta,
				format: "Propuestas de Formulación",
				no_letterhead: 1,
			});
			window.open(`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`);
		});
	},
};
