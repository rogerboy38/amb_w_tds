"""
Bench Console Script - Debug Billing Address Validation
Run with: bench console
Then: exec(open('debug_address.py').read())
"""

import frappe

# Test Sales Order
so_name = "SO-02125-Barentz Italia Specchiasol"

print(f"\n=== DEBUG: {so_name} ===\n")

# 1. Get the Sales Order
so = frappe.get_doc("Sales Order", so_name)
print(f"Customer: {so.customer}")

# 2. Check all addresses linked to this customer
print("\n=== Addresses with Dynamic Link to Customer ===")
links = frappe.db.sql("""
    SELECT dl.parent, a.address_type, a.address_line1, a.city, a.country
    FROM `tabDynamic Link` dl
    JOIN `tabAddress` a ON dl.parent = a.name
    WHERE dl.link_doctype = 'Customer' 
    AND dl.link_name = %s
    AND dl.parenttype = 'Address'
""", (so.customer,), as_dict=True)

print(f"Found {len(links)} addresses:")
for l in links:
    print(f"  - {l.parent} (Type: {l.address_type}, City: {l.city})")

# 3. Check if the auto-created address exists
addr_name = f"{so.customer}-Auto"
print(f"\n=== Check Auto-Created Address: {addr_name} ===")
if frappe.db.exists("Address", addr_name):
    addr = frappe.get_doc("Address", addr_name)
    print(f"Address exists: {addr.name}")
    print(f"  address_type: {addr.address_type}")
    print(f"  address_line1: {addr.address_line1}")
    print(f"  city: {addr.city}")
    
    # Check Dynamic Links
    print("\n  Dynamic Links:")
    for dl in addr.links:
        print(f"    - {dl.link_doctype}: {dl.link_name}")
else:
    print("Auto-created address does NOT exist")

# 4. Try to understand what ERPNext validates
print("\n=== Test Address Validation Logic ===")

# Check the Customer doc
customer = frappe.get_doc("Customer", so.customer)
print(f"Customer default_address: {customer.default_address}")
print(f"Customer primary_address: {customer.primary_address}")

# 5. Try to see what make_sales_invoice returns
print("\n=== Test make_sales_invoice output ===")
from erpnext.controllers.accounts_controller import get_from_doctype
si = frappe.get_doc({
    "doctype": "Sales Invoice",
    "company": so.company,
    "customer": so.customer,
    "posting_date": frappe.utils.today(),
})
si.set_missing_values()
si.calculate_taxes_and_totals()

# Check what addresses are set
print(f"SI customer_address: {getattr(si, 'customer_address', None)}")
print(f"SI billing_address: {getattr(si, 'billing_address', None)}")
print(f"SI shipping_address_name: {getattr(si, 'shipping_address_name', None)}")

# 6. Most important - test if an address passes validation
print("\n=== Test Address Belongs to Customer ===")

# Get first available address
test_addr = links[0].parent if links else None
if not test_addr:
    # Use auto-created
    test_addr = addr_name if frappe.db.exists("Address", addr_name) else None

if test_addr:
    print(f"Testing address: {test_addr}")
    
    # This is what ERPNext validates - check if address links to customer
    is_linked = frappe.db.exists("Dynamic Link", {
        "parent": test_addr,
        "parenttype": "Address",
        "link_doctype": "Customer",
        "link_name": so.customer
    })
    print(f"Has Dynamic Link to customer: {bool(is_linked)}")
    
    # Check Address doctype's validate method
    # ERPNext typically validates in before_save
    addr_doc = frappe.get_doc("Address", test_addr)
    print(f"Address is_primary: {getattr(addr_doc, 'is_primary_address', None)}")
    print(f"Address is_shipping: {getattr(addr_doc, 'is_shipping_address', None)}")
else:
    print("No address found to test")

print("\n=== END DEBUG ===")
