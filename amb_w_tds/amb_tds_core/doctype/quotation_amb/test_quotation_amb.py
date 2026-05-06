import frappe


def run():
    """
    Manual test runner for Quotation AMB.
    Run from bench console:
        >>> from amb_w_tds.api.tests.test_quotation_amb import run
        >>> run()
    """

    frappe.db.rollback()  # safety for repeated runs

    CUSTOMER = "ALBAFLOR"
    COMPANY = "AMB-Wellness"
    FOLIO = "TEST-FOLIO-955"

    print("▶ Creating / fetching Quotation AMB")

    existing = frappe.db.get_value(
        "Quotation AMB",
        {"custom_folio": FOLIO},
        "name"
    )

    if existing:
        print(f"✔ Existing quotation found: {existing}")
        doc = frappe.get_doc("Quotation AMB", existing)
    else:
        doc = frappe.get_doc({
            "doctype": "Quotation AMB",
            "customer": CUSTOMER,
            "company": COMPANY,
            "custom_folio": FOLIO,
            "status": "Draft"
        })
        doc.insert(ignore_permissions=True)
        print(f"✔ Created quotation: {doc.name}")

    # Assertions
    assert doc.customer == CUSTOMER
    assert doc.company == COMPANY
    assert doc.custom_folio == FOLIO
    assert doc.status == "Draft"

    print("✔ Field validation passed")

    # Reload test
    reloaded = frappe.get_doc("Quotation AMB", doc.name)
    assert reloaded.name == doc.name

    print("✔ Reload validation passed")

    frappe.db.commit()

    print("✅ Quotation AMB test PASSED")
    return doc.name
