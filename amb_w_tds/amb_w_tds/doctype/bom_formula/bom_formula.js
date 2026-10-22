// G-1a: tab visibility follows formula_type. Buttons for the candidate-lot
// query ship hidden — they are wired in G-1b.
frappe.ui.form.on("BOM Formula", {
	refresh(frm) {
		frm.trigger("g1a_tab_visibility");
		frm.trigger("workflow_hint");
		frm.trigger("propuesta_actions");
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
	// 13.11.1: say where the approval stands and what this user can do next. Built from the
	// same transitions Frappe puts in the "Acciones" menu, filtered by the user's roles exactly
	// as Frappe filters them; it adds no action of its own.
	workflow_hint(frm) {
		const field = frappe.workflow.get_state_fieldname(frm.doctype);
		const state = field && frm.doc[field];
		if (frm.is_new() || !state) return;
		frappe.workflow.get_transitions(frm.doc).then((transitions) => {
			const mine = (transitions || [])
				.filter((t) => frappe.user_roles.includes(t.allowed))
				.map((t) => __(t.action));
			const next = mine.length
				? __("Siguiente acción: {0} (menú Acciones)", [mine.join(", ")])
				: __("Sin acción disponible para su rol");
			frm.set_intro(__("Estado: {0} · {1}", [__(state), next]), mine.length ? "blue" : "gray");
		});
	},
	// 13.10.0: "Propuesta" actions. Offered only to users who can run the Propuestas de
	// Formulación report (the server decides; the methods re-check on every call).
	propuesta_actions(frm) {
		if (frm.is_new()) return;
		const M = "amb_w_tds.formulation.propuesta_actions.";
		const group = __("Propuesta");
		frappe.call({ method: M + "propuesta_access", args: { bom_formula: frm.doc.name } }).then((r) => {
			const a = r.message || {};
			if (!a.allowed) return;
			frm.add_custom_button(
				__("Generar PDF y Excel"),
				() =>
					frappe
						.call({
							method: M + "generate_propuesta_files",
							args: { bom_formula: frm.doc.name },
							freeze: true,
							freeze_message: __("Generando PDF y Excel…"),
						})
						.then(() => {
							frappe.show_alert({ message: __("PDF y Excel adjuntos a la propuesta"), indicator: "green" });
							frm.reload_doc();
						}),
				group
			);
			if (a.can_share) {
				frm.add_custom_button(__("Compartir"), () => frm.share_doc(), group);
			}
			// supporting action: email the same files to Dirección (recipients = Formulation Settings)
			if (a.recipients_configured) {
				frm.add_custom_button(
					__("Enviar a Dirección"),
					() =>
						frappe.confirm(__("¿Enviar la propuesta a Dirección?"), () =>
							frappe
								.call({
									method: M + "email_propuesta_to_direccion",
									args: { bom_formula: frm.doc.name },
									freeze: true,
									freeze_message: __("Enviando a Dirección…"),
								})
								.then((res) => {
									const n = (res.message || {}).sent_to || 0;
									frappe.show_alert({
										message: __("Propuesta enviada a Dirección ({0} destinatarios)", [n]),
										indicator: "green",
									});
									frm.reload_doc();
								})
						),
					group
				);
			} else {
				frm.add_custom_button(
					__("Enviar a Dirección"),
					() =>
						frappe.msgprint({
							title: __("Sin destinatarios de Dirección"),
							message: __(
								'Configure los destinatarios de Dirección en Formulation Settings ("Destinatarios de Dirección").'
							),
							indicator: "orange",
						}),
					group
				);
			}
		});
	},
});
