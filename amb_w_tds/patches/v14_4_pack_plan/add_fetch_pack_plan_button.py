"""F-AUD-3 ruling (Hugh 2026-07-06): explicit "Fetch Pack Plan" Desk action on
quotation-mapped Sales Orders — never a silent auto-pull. Idempotent."""

import frappe

SCRIPT_NAME = "SO Fetch Pack Plan Button"

SCRIPT = """
frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        if (frm.doc.docstatus === 0 && !(frm.doc.custom_pack_plan || []).length) {
            frm.add_custom_button(__('Fetch Pack Plan'), () => {
                frappe.call({
                    method: 'amb_w_tds.selling_edge.pack_plan.fetch_pack_plan_from_quotation',
                    args: { sales_order: frm.doc.name },
                    freeze: true,
                    callback: () => frm.reload_doc(),
                });
            }, __('AMB'));
        }
    },
});
"""


def execute():
    if frappe.db.exists("Client Script", SCRIPT_NAME):
        return
    frappe.get_doc({
        "doctype": "Client Script",
        "name": SCRIPT_NAME,
        "dt": "Sales Order",
        "view": "Form",
        "enabled": 1,
        "script": SCRIPT.strip(),
    }).insert(ignore_permissions=True)
