// G-1a: tab visibility follows formula_type. Buttons for the candidate-lot
// query ship hidden — they are wired in G-1b.
frappe.ui.form.on("BOM Formula", {
	refresh(frm) {
		frm.trigger("g1a_tab_visibility");
	},
	formula_type(frm) {
		frm.trigger("g1a_tab_visibility");
	},
	g1a_tab_visibility(frm) {
		const t = frm.doc.formula_type;
		const is_mix = t === "Mix";
		const is_base = t === "Base";
		const is_juice = !!t && !is_mix && !is_base;
		frm.toggle_display("base_tab", is_base || is_mix);
		frm.toggle_display("seleccion_tab", is_mix || is_base);
		frm.toggle_display("mix_tab", is_mix);
		frm.toggle_display("prediccion_tab", is_mix || is_base);
		frm.toggle_display("juice_tab", is_juice);
		["btn_ver_existencias", "btn_seleccionar", "btn_calcular", "btn_eval"].forEach((b) =>
			frm.toggle_display(b, false)
		);
	},
});
