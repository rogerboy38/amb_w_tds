import frappe
import pandas as pd
import os
import json

def migrate_foxpro():
    """Migrate data from FoxPro to ERPNext"""
    print("=" * 70)
    print("🔄 MIGRATING FROM FOXPRO TO ERPNext")
    print("=" * 70)
    
    # Your data file path - CHANGE THIS
    data_file = "/home/frappe/sysmayaldata/working12/foxpro_data.xlsx"
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("\nPlease create an Excel file with your FoxPro data.")
        print("Expected columns: COMPANY, ADDRESS, CITY, STATE, PINCODE, PHONE, EMAIL")
        return
    
    try:
        # Read data
        df = pd.read_excel(data_file)
        print(f"✅ Loaded {len(df)} records")
        print(f"Columns: {list(df.columns)}")
        
        success_count = 0
        total_count = len(df)
        
        for idx, row in df.iterrows():
            print(f"\n[{idx+1}/{total_count}] Processing...")
            
            # Get supplier name
            supplier_name = str(row.get('COMPANY', f'Supplier-{idx+1}')).strip()
            
            # Check if supplier exists
            if frappe.db.exists('Supplier', {'supplier_name': supplier_name}):
                print(f"   ⚠️ Supplier already exists: {supplier_name}")
                continue
            
            # Create supplier
            try:
                supplier = frappe.get_doc({
                    'doctype': 'Supplier',
                    'supplier_name': supplier_name,
                    'supplier_group': str(row.get('GROUP', 'All Supplier Groups')).strip(),
                    'supplier_type': 'Company',
                    'country': str(row.get('COUNTRY', 'India')).strip(),
                })
                supplier.insert(ignore_permissions=True)
                print(f"   ✅ Created supplier: {supplier_name}")
                
                # Create address
                address_title = f"{supplier_name} - Billing"
                if not frappe.db.exists('Address', {'address_title': address_title}):
                    address = frappe.get_doc({
                        'doctype': 'Address',
                        'address_title': address_title,
                        'address_type': 'Billing',
                        'address_line1': str(row.get('ADDRESS', 'Not specified')).strip(),
                        'city': str(row.get('CITY', 'Not specified')).strip(),
                        'state': str(row.get('STATE', '')).strip(),
                        'country': str(row.get('COUNTRY', 'India')).strip(),
                        'pincode': str(row.get('PINCODE', '000000')).strip(),
                        'email_id': str(row.get('EMAIL', 'no-email@example.com')).strip(),
                        'phone': str(row.get('PHONE', '')).strip(),
                    })
                    address.insert(ignore_permissions=True)
                    
                    # Link address to supplier
                    address.append('links', {
                        'link_doctype': 'Supplier',
                        'link_name': supplier.name
                    })
                    address.save(ignore_permissions=True)
                    print(f"   ✅ Created address for {supplier_name}")
                
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error processing {supplier_name}: {str(e)}")
                continue
        
        print("\n" + "=" * 70)
        print(f"✅ MIGRATION COMPLETE!")
        print(f"   Successfully imported: {success_count}/{total_count} suppliers")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

