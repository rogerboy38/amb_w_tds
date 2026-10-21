"""G-0b-2a leg A — give every existing Mix Input line an explicit COA doctype.

`source_coa_amb2` becomes a Dynamic Link on the new `source_coa_doctype`, so
every row that already carries a value needs that companion set or the link
dangles. Rows that carry nothing are left NULL rather than defaulted, because a
doctype on an empty link would be a claim the data does not make.

`Formulation Settings.default_coa_source` is set explicitly to `COA AMB` (rule
z): the option already existed, only the stored value changes. COA AMB is the
populated doctype -- COA AMB2 has 0 rows on every tier.
"""
import frappe


def execute():
    before = frappe.db.count("BOM Formula Mix Input",
                             {"source_coa_amb2": ["is", "set"]})

    # Both directions, per the card's STOP condition: no value may be lost, and
    # none may be invented. A bare UPDATE would satisfy neither on its own.
    frappe.db.sql("""
        update `tabBOM Formula Mix Input`
           set source_coa_doctype = 'COA AMB2'
         where source_coa_amb2 is not null and source_coa_amb2 != ''
    """)
    frappe.db.sql("""
        update `tabBOM Formula Mix Input`
           set source_coa_doctype = null
         where source_coa_amb2 is null or source_coa_amb2 = ''
    """)

    after = frappe.db.count("BOM Formula Mix Input",
                            {"source_coa_amb2": ["is", "set"]})
    tagged = frappe.db.count("BOM Formula Mix Input",
                             {"source_coa_doctype": ["is", "set"]})
    if before != after:
        frappe.throw(f"g0b2a: source_coa_amb2 count changed {before} -> {after}")
    if tagged != after:
        frappe.throw(f"g0b2a: {after} linked rows but {tagged} tagged with a doctype")

    if frappe.db.exists("Formulation Settings", "Formulation Settings"):
        frappe.db.set_value("Formulation Settings", "Formulation Settings",
                            "default_coa_source", "COA AMB")

    print(f"g0b2a_source_coa_doctype: {after} linked rows tagged COA AMB2; "
          f"default_coa_source = COA AMB")
