import frappe

# Get all Sales Orders that have linked Quotations (excluding Draft)
print("Fetching all Sales Orders with linked Quotations (non-draft)...")

sos_with_issues = []

# Get all SOs with linked quotations
linked_sos = frappe.db.sql("""
    SELECT DISTINCT parent
    FROM `tabSales Order Item`
    WHERE prevdoc_docname LIKE 'SAL-QTN-%%'
    AND parent LIKE 'SO-%%'
    ORDER BY parent
""", as_list=True)

total_sos = len(linked_sos)
print(f"Found {total_sos} Sales Orders with linked Quotations. Validating TDS fields...\n")

checked = 0
missing_tds = []
missing_address = []

for (so_name,) in linked_sos:
    checked += 1
    if checked % 100 == 0:
        print(f"Progress: {checked}/{total_sos}...")
    
    try:
        so = frappe.get_doc("Sales Order", so_name)
        
        # Skip draft SOs as per user request
        if so.docstatus == 0:
            continue
        
        # Get the first linked quotation
        qt_name = None
        if so.items and so.items[0].prevdoc_docname:
            qt_name = so.items[0].prevdoc_docname
        
        if not qt_name:
            continue
            
        qt = frappe.get_doc("Quotation", qt_name)
        
        # Check TDS fields - need to identify which custom fields contain TDS
        # Common TDS field patterns: tds_*, *_tds_*, tax_deducted_at_source
        tds_missing = False
        
        # Check if SO has any TDS-related custom fields that are empty but filled in QT
        for field in so.meta.fields:
            if 'tds' in field.fieldname.lower():
                so_value = so.get(field.fieldname)
                qt_value = qt.get(field.fieldname) if field.fieldname in [f.fieldname for f in qt.meta.fields] else None
                
                if qt_value and not so_value:
                    tds_missing = True
                    missing_tds.append({
                        'so': so_name,
                        'qt': qt_name,
                        'field': field.fieldname,
                        'qt_value': qt_value,
                        'docstatus': so.docstatus
                    })
        
        # Also check for broken addresses
        if so.customer_address:
            addr_exists = frappe.db.exists("Address", so.customer_address)
            if not addr_exists:
                missing_address.append({'so': so_name, 'address': so.customer_address, 'type': 'customer_address'})
        
        if so.shipping_address_name:
            addr_exists = frappe.db.exists("Address", so.shipping_address_name)
            if not addr_exists:
                missing_address.append({'so': so_name, 'address': so.shipping_address_name, 'type': 'shipping_address'})
                
    except Exception as e:
        print(f"Error checking {so_name}: {str(e)}")

print(f"\n{'='*60}")
print("VALIDATION COMPLETE")
print(f"{'='*60}")
print(f"Total SOs checked: {checked}")
print(f"Non-draft SOs: {len([so for so in linked_sos if frappe.db.get_value('Sales Order', so[0], 'docstatus') != 0])}")
print(f"\nSOs with missing TDS data: {len(set([x['so'] for x in missing_tds]))}")
print(f"SOs with broken addresses: {len(missing_address)}")

if missing_tds:
    print(f"\n{'='*60}")
    print("MISSING TDS DETAILS (first 20):")
    print(f"{'='*60}")
    for item in missing_tds[:20]:
        print(f"SO: {item['so']} (status: {item['docstatus']}) <- QT: {item['qt']}")
        print(f"  Missing field: {item['field']} = {item['qt_value']}")

if missing_address:
    print(f"\n{'='*60}")
    print("BROKEN ADDRESSES (first 20):")
    print(f"{'='*60}")
    for item in missing_address[:20]:
        print(f"SO: {item['so']} -> {item['type']}: {item['address']}")

# Summary by unique SO
unique_sos_with_tds_issues = list(set([x['so'] for x in missing_tds]))
print(f"\n{'='*60}")
print(f"UNIQUE SOs needing TDS fix: {len(unique_sos_with_tds_issues)}")
print(f"{'='*60}")
if unique_sos_with_tds_issues[:30]:
    print("Sample SOs:", unique_sos_with_tds_issues[:30])

