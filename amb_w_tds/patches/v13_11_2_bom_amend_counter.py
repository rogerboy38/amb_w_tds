"""13.11.2: future BOM amendments use "Amend Counter" (BOM-0307-006 -> BOM-0307-006-1) instead of taking
the next plain number, which ERPNext's BOM picker then skips and re-proposes ("Duplicate Name").

Touches ONLY the BOM row of Document Naming Settings -> Amended Document Naming Settings: creates it
if absent, sets action = Amend Counter if different. The single's default_amend_naming and every other
row are left alone (the Single is not saved; saving it via update_amendment_rule would delete rows not
in its in-memory table). Renames nothing; existing BOMs keep their names. Idempotent."""
import frappe

PARENT = "Document Naming Settings"
ACTION = "Amend Counter"


def execute():
	row = frappe.db.get_value("Amended Document Naming Settings", {"document_type": "BOM"}, ["name", "action"], as_dict=True)
	if row:
		if row.action != ACTION:
			frappe.db.set_value("Amended Document Naming Settings", row.name, "action", ACTION, update_modified=False)
			print(f"v13_11_2_bom_amend_counter: BOM amendment naming {row.action} -> {ACTION}")
		else:
			print("v13_11_2_bom_amend_counter: BOM already uses Amend Counter")
		return
	idx = (frappe.db.sql("select max(idx) from `tabAmended Document Naming Settings` where parent=%s", PARENT)[0][0] or 0) + 1
	frappe.get_doc({"doctype": "Amended Document Naming Settings", "parent": PARENT, "parenttype": PARENT,
		"parentfield": "amend_naming_override", "idx": idx, "document_type": "BOM", "action": ACTION}).db_insert()
	print(f"v13_11_2_bom_amend_counter: added BOM -> {ACTION}")
