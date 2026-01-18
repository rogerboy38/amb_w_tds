// Copyright (c) 2025, AMB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Batch Processing History', {
	// This event fires when a new row is added to the child table
	setup: function(frm) {
		// Setup logic for child table
	},
	
	// Event when a specific row is selected/loaded
	onload: function(frm, cdt, cdn) {
		// Logic when row loads
	}
});

// Field-level events for child table fields
frappe.ui.form.on('Batch Processing History', {
	// Auto-set timestamp when event type changes
	event_type: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.event_type && !row.timestamp) {
			frappe.model.set_value(cdt, cdn, 'timestamp', frappe.datetime.now_datetime());
		}
	},
	
	// Validate from/to plant consistency
	from_plant: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.from_plant && row.to_plant && row.from_plant === row.to_plant) {
			frappe.msgprint(__('From Plant and To Plant cannot be the same'));
			frappe.model.set_value(cdt, cdn, 'to_plant', '');
		}
	},
	
	to_plant: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.from_plant && row.to_plant && row.from_plant === row.to_plant) {
			frappe.msgprint(__('From Plant and To Plant cannot be the same'));
			frappe.model.set_value(cdt, cdn, 'to_plant', '');
		}
	},
	
	// Auto-set user when notes are added
	notes: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.notes && !row.user) {
			frappe.model.set_value(cdt, cdn, 'user', frappe.session.user);
		}
	}
});
