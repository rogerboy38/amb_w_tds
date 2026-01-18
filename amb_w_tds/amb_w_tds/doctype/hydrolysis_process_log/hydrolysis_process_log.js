// Copyright (c) 2026, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hydrolysis Process Log', {
	// Refresh event for the child table row
	refresh: function(frm) {
		// This runs when the child table row is loaded
	},
	
	// Auto-calculate yields when penca or juice values change
	penca_total_kg: function(frm, cdt, cdn) {
		calculate_yields(frm, cdt, cdn);
	},
	
	juice_pressed_liters: function(frm, cdt, cdn) {
		calculate_yields(frm, cdt, cdn);
		calculate_pressed_solids(frm, cdt, cdn);
	},
	
	bagazo_kg: function(frm, cdt, cdn) {
		calculate_yields(frm, cdt, cdn);
	},
	
	// Auto-calculate enzyme total
	enzyme_ml_per_kg: function(frm, cdt, cdn) {
		calculate_enzyme_total(frm, cdt, cdn);
	},
	
	// Auto-calculate solids for each stage
	juice_pressed_solids_percent: function(frm, cdt, cdn) {
		calculate_pressed_solids(frm, cdt, cdn);
	},
	
	juice_decolorized_liters: function(frm, cdt, cdn) {
		calculate_decolorized_solids(frm, cdt, cdn);
	},
	
	juice_decolorized_solids_percent: function(frm, cdt, cdn) {
		calculate_decolorized_solids(frm, cdt, cdn);
	},
	
	juice_refiltrated_liters: function(frm, cdt, cdn) {
		calculate_refiltrated_solids(frm, cdt, cdn);
	},
	
	juice_refiltrated_solids_percent: function(frm, cdt, cdn) {
		calculate_refiltrated_solids(frm, cdt, cdn);
	},
	
	// Auto-calculate final output
	kilos_envasado: function(frm, cdt, cdn) {
		calculate_final_solids(frm, cdt, cdn);
		calculate_rendimiento(frm, cdt, cdn);
	},
	
	final_solids_percent: function(frm, cdt, cdn) {
		calculate_final_solids(frm, cdt, cdn);
	}
});

// ==================== CALCULATION FUNCTIONS ====================

function calculate_yields(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var penca = flt(row.penca_total_kg);
	var bagazo = flt(row.bagazo_kg);
	var juice_pressed = flt(row.juice_pressed_liters);
	
	if (penca > 0) {
		// Yield: Penca to Juice (assuming 1 L ≈ 1 kg)
		if (juice_pressed > 0) {
			frappe.model.set_value(cdt, cdn, 'penca_to_juice_percent', 
				(juice_pressed / penca) * 100);
		}
		
		// Yield: Penca to Bagazo
		if (bagazo > 0) {
			frappe.model.set_value(cdt, cdn, 'penca_to_bagazo_percent', 
				(bagazo / penca) * 100);
		}
	}
}

function calculate_enzyme_total(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var enzyme_ml_kg = flt(row.enzyme_ml_per_kg);
	var penca = flt(row.penca_total_kg);
	
	if (enzyme_ml_kg > 0 && penca > 0) {
		frappe.model.set_value(cdt, cdn, 'enzyme_total_ml', 
			enzyme_ml_kg * penca);
	}
}

function calculate_pressed_solids(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var liters = flt(row.juice_pressed_liters);
	var percent = flt(row.juice_pressed_solids_percent);
	
	if (liters > 0 && percent > 0) {
		frappe.model.set_value(cdt, cdn, 'juice_pressed_solids_kg', 
			(liters * percent) / 100);
	}
}

function calculate_decolorized_solids(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var liters = flt(row.juice_decolorized_liters);
	var percent = flt(row.juice_decolorized_solids_percent);
	
	if (liters > 0 && percent > 0) {
		frappe.model.set_value(cdt, cdn, 'juice_decolorized_solids_kg', 
			(liters * percent) / 100);
		
		// Calculate solids loss
		var initial_solids = flt(row.juice_pressed_solids_kg);
		var decolorized_solids = (liters * percent) / 100;
		
		if (initial_solids > 0 && decolorized_solids > 0) {
			frappe.model.set_value(cdt, cdn, 'solids_loss_percent', 
				((initial_solids - decolorized_solids) / initial_solids) * 100);
		}
	}
}

function calculate_refiltrated_solids(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var liters = flt(row.juice_refiltrated_liters);
	var percent = flt(row.juice_refiltrated_solids_percent);
	
	if (liters > 0 && percent > 0) {
		frappe.model.set_value(cdt, cdn, 'juice_refiltrated_solids_kg', 
			(liters * percent) / 100);
	}
}

function calculate_final_solids(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var kilos = flt(row.kilos_envasado);
	var percent = flt(row.final_solids_percent);
	
	if (kilos > 0 && percent > 0) {
		frappe.model.set_value(cdt, cdn, 'final_solids_kg', 
			(kilos * percent) / 100);
	}
}

function calculate_rendimiento(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	var penca = flt(row.penca_total_kg);
	var final_solids = flt(row.final_solids_kg);
	
	if (penca > 0 && final_solids > 0) {
		frappe.model.set_value(cdt, cdn, 'rendimiento_porcentual', 
			(final_solids / penca) * 100);
	}
}
