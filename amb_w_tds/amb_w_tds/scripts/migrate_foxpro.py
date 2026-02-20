import frappe
import pandas as pd
import os
import json
from frappe.utils import now_datetime

def migrate_foxpro(auto_confirm=True):
    """
    Migrate suppliers, addresses, and contacts from FoxPro data
    Supports both English and Spanish column names
    
    Args:
        auto_confirm (bool): If True, skip confirmation prompts
    """
    print("=" * 70)
    print("🔄 MIGRATING FROM FOXPRO TO ERPNext")
    print("=" * 70)
    
    # Define the path to your FoxPro data
    data_dir = "/home/frappe/sysmayaldata/working12/"
    
    # Look for data files
    data_files = []
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.lower().endswith(('.xlsx', '.xls', '.csv', '.dbf')):
                data_files.append(os.path.join(data_dir, f))
    
    if not data_files:
        print(f"❌ No data files found in {data_dir}")
        print("\nPlease export your FoxPro data to:")
        print("1. Excel (.xlsx or .xls)")
        print("2. CSV (.csv)")
        print("3. DBF (.dbf)")
        print(f"\nAnd place it in: {data_dir}")
        
        # Check if directory exists
        if not os.path.exists(data_dir):
            print(f"\n📁 Directory {data_dir} does not exist. Creating it...")
            os.makedirs(data_dir, exist_ok=True)
        
        # List what's in the directory
        print(f"\n📁 Contents of {data_dir}:")
        try:
            for item in os.listdir(data_dir):
                print(f"  • {item}")
        except:
            print("  (empty)")
        
        return
    
    print(f"\n📁 Found data files:")
    for i, f in enumerate(data_files, 1):
        print(f"   {i}. {os.path.basename(f)}")
    
    # For now, use the first file
    data_file = data_files[0]
    print(f"\n📊 Using file: {os.path.basename(data_file)}")
    
    try:
        # Load data based on file type
        if data_file.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(data_file)
        elif data_file.lower().endswith('.csv'):
            # Try different encodings
            try:
                df = pd.read_csv(data_file, encoding='utf-8')
            except:
                df = pd.read_csv(data_file, encoding='latin-1')
        elif data_file.lower().endswith('.dbf'):
            # Install dbfread first: pip install dbfread
            try:
                from dbfread import DBF
                table = DBF(data_file)
                df = pd.DataFrame(iter(table))
            except ImportError:
                print("❌ Please install dbfread: pip install dbfread")
                return
        
        print(f"✅ Loaded {len(df)} records")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Show sample data
        print("\n📄 Sample data (first 3 rows):")
        print(df.head(3).to_string())
        
        # Auto-confirm if specified
        if not auto_confirm:
            print("\n⚠️  This will create/update suppliers, addresses, and contacts.")
            response = input("Continue? (y/n): ").strip().lower()
            if response != 'y':
                print("Migration cancelled.")
                return
        else:
            print("\n⚠️  Auto-confirmation enabled. Starting migration...")
        
        success_count = 0
        error_count = 0
        
        # Column mapping - Spanish to English
        column_mapping = {
            # Spanish column names (common in Mexican FoxPro systems)
            'CODIGO': 'CODE',
            'NOMBRE': 'COMPANY',
            'RAZON_SOCIAL': 'COMPANY',
            'NOMBRE_COMERCIAL': 'COMPANY',
            'DIRECCION': 'ADDRESS',
            'DIRECCION1': 'ADDRESS',
            'DIRECCION2': 'ADDRESS2',
            'COLONIA': 'NEIGHBORHOOD',
            'CIUDAD': 'CITY',
            'MUNICIPIO': 'CITY',
            'ESTADO': 'STATE',
            'CP': 'ZIP',
            'CODIGO_POSTAL': 'ZIP',
            'TELEFONO': 'PHONE',
            'TEL': 'PHONE',
            'TELEFONO1': 'PHONE',
            'TELEFONO2': 'PHONE2',
            'CELULAR': 'MOBILE',
            'EMAIL': 'EMAIL',
            'CORREO': 'EMAIL',
            'CONTACTO': 'CONTACT',
            'CONTACTO1': 'CONTACT',
            'RFC': 'TAX_ID',
            'GIRO': 'BUSINESS',
            'ACTIVIDAD': 'BUSINESS',
            'PAIS': 'COUNTRY',
            
            # English column names
            'COMPANY': 'COMPANY',
            'NAME': 'COMPANY',
            'ADDRESS': 'ADDRESS',
            'ADDRESS1': 'ADDRESS',
            'ADDRESS2': 'ADDRESS2',
            'CITY': 'CITY',
            'STATE': 'STATE',
            'ZIP': 'ZIP',
            'PINCODE': 'ZIP',
            'POSTAL_CODE': 'ZIP',
            'PHONE': 'PHONE',
            'PHONE1': 'PHONE',
            'PHONE2': 'PHONE2',
            'MOBILE': 'MOBILE',
            'EMAIL': 'EMAIL',
            'CONTACT': 'CONTACT',
            'TAX_ID': 'TAX_ID',
            'VAT': 'TAX_ID',
            'COUNTRY': 'COUNTRY',
        }
        
        print("\n🚀 Starting migration...")
        
        for idx, row in df.iterrows():
            row_num = idx + 1
            if row_num % 10 == 0:
                print(f"[{row_num}/{len(df)}] Processing...")
            
            try:
                row_dict = row.to_dict()
                
                # Map columns
                mapped_data = {}
                for col, value in row_dict.items():
                    col_str = str(col).strip().upper()
                    if col_str in column_mapping:
                        mapped_key = column_mapping[col_str]
                        mapped_data[mapped_key] = str(value).strip() if pd.notna(value) else ''
                    else:
                        # Keep original if not in mapping
                        mapped_data[col_str] = str(value).strip() if pd.notna(value) else ''
                
                # Supplier name (most important field)
                supplier_name = (
                    mapped_data.get('COMPANY') or 
                    mapped_data.get('NAME') or 
                    f'Supplier-{row_num}'
                )
                
                if not supplier_name or supplier_name.lower() == 'nan':
                    supplier_name = f'Supplier-{row_num}'
                
                # Clean up supplier name
                supplier_name = supplier_name.strip()
                
                # Check if supplier exists
                existing_supplier = frappe.db.exists('Supplier', {'supplier_name': supplier_name})
                
                if existing_supplier:
                    print(f"   ⚠️ Supplier already exists: {supplier_name}")
                    # Use existing supplier name
                    supplier_name = existing_supplier
                else:
                    # Create new supplier
                    supplier_data = {
                        'doctype': 'Supplier',
                        'supplier_name': supplier_name,
                        'supplier_group': 'All Supplier Groups',
                        'supplier_type': 'Company',
                        'country': mapped_data.get('COUNTRY', 'Mexico'),
                    }
                    
                    # Add optional fields if available
                    tax_id = mapped_data.get('TAX_ID') or mapped_data.get('RFC')
                    if tax_id and tax_id.lower() != 'nan':
                        supplier_data['tax_id'] = tax_id
                    
                    email = mapped_data.get('EMAIL')
                    if email and email.lower() != 'nan' and '@' in email:
                        supplier_data['email_id'] = email
                    else:
                        supplier_data['email_id'] = 'no-email@example.com'
                    
                    phone = mapped_data.get('PHONE') or mapped_data.get('TELEFONO')
                    if phone and phone.lower() != 'nan':
                        supplier_data['mobile_no'] = phone
                    
                    supplier = frappe.get_doc(supplier_data)
                    supplier.insert(ignore_permissions=True)
                    print(f"   ✅ Created supplier: {supplier_name}")
                
                # Create address
                address_title = f"{supplier_name} - Billing"
                existing_address = frappe.db.exists('Address', {'address_title': address_title})
                
                if not existing_address:
                    # Get address data
                    address_line1 = mapped_data.get('ADDRESS') or 'Not specified'
                    if address_line1.lower() == 'nan':
                        address_line1 = 'Not specified'
                    
                    city = mapped_data.get('CITY') or 'Not specified'
                    if city.lower() == 'nan':
                        city = 'Not specified'
                    
                    state = mapped_data.get('STATE') or ''
                    if state.lower() == 'nan':
                        state = ''
                    
                    zip_code = mapped_data.get('ZIP') or mapped_data.get('CODIGO_POSTAL') or '000000'
                    if str(zip_code).lower() == 'nan':
                        zip_code = '000000'
                    
                    country = mapped_data.get('COUNTRY') or 'Mexico'
                    
                    address_data = {
                        'doctype': 'Address',
                        'address_title': address_title,
                        'address_type': 'Billing',
                        'address_line1': address_line1[:140],
                        'city': city[:50],
                        'state': state[:50],
                        'country': country,
                        'pincode': str(zip_code)[:10],
                    }
                    
                    # Add email to address
                    email = mapped_data.get('EMAIL')
                    if email and email.lower() != 'nan' and '@' in email:
                        address_data['email_id'] = email
                    else:
                        address_data['email_id'] = 'no-email@example.com'
                    
                    # Add optional fields
                    phone = mapped_data.get('PHONE') or mapped_data.get('TELEFONO')
                    if phone and phone.lower() != 'nan':
                        address_data['phone'] = phone[:20]
                    
                    address_line2 = mapped_data.get('ADDRESS2') or mapped_data.get('COLONIA')
                    if address_line2 and address_line2.lower() != 'nan':
                        address_data['address_line2'] = address_line2[:140]
                    
                    address = frappe.get_doc(address_data)
                    address.insert(ignore_permissions=True)
                    
                    # Link address to supplier
                    address.append('links', {
                        'link_doctype': 'Supplier',
                        'link_name': supplier_name
                    })
                    address.save(ignore_permissions=True)
                    print(f"   ✅ Created address for {supplier_name}")
                
                # Create contact if contact information exists
                contact_name = mapped_data.get('CONTACT') or mapped_data.get('CONTACTO')
                if contact_name and contact_name.lower() != 'nan':
                    # Try to split into first and last name
                    name_parts = str(contact_name).split(' ', 1)
                    first_name = name_parts[0][:50]
                    last_name = name_parts[1][:50] if len(name_parts) > 1 else ''
                    
                    # Check if contact exists
                    existing_contact = frappe.db.get_value('Contact', {
                        'first_name': first_name,
                        'last_name': last_name,
                        'company_name': supplier_name
                    })
                    
                    if not existing_contact:
                        contact_data = {
                            'doctype': 'Contact',
                            'first_name': first_name,
                            'last_name': last_name,
                            'company_name': supplier_name,
                            'is_primary_contact': True,
                        }
                        
                        email = mapped_data.get('EMAIL')
                        if email and email.lower() != 'nan' and '@' in email:
                            contact_data['email_id'] = email
                        
                        phone = mapped_data.get('PHONE') or mapped_data.get('TELEFONO')
                        if phone and phone.lower() != 'nan':
                            contact_data['mobile_no'] = phone[:20]
                        
                        contact = frappe.get_doc(contact_data)
                        contact.insert(ignore_permissions=True)
                        
                        # Link contact to supplier
                        contact.append('links', {
                            'link_doctype': 'Supplier',
                            'link_name': supplier_name
                        })
                        contact.save(ignore_permissions=True)
                        print(f"   ✅ Created contact: {contact_name}")
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ Error processing row {row_num}: {str(e)[:100]}")
                # Continue with next record
                continue
        
        frappe.db.commit()
        
        print("\n" + "=" * 70)
        print(f"✅ MIGRATION COMPLETE!")
        print(f"   Successfully processed: {success_count}/{len(df)} records")
        print(f"   Errors: {error_count}")
        print("=" * 70)
        
        # Save migration report
        report = {
            'source_file': data_file,
            'total_records': len(df),
            'successful': success_count,
            'errors': error_count,
            'timestamp': str(now_datetime()),
            'columns_found': list(df.columns),
            'columns_mapped': list(column_mapping.keys())
        }
        
        report_file = os.path.join(data_dir, f'migration_report_{now_datetime().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📝 Migration report saved to: {report_file}")
        
        # Show summary
        if success_count > 0:
            print(f"\n📊 Summary of imported data:")
            print(f"   • Suppliers created/updated: {success_count}")
            print(f"   • Addresses created: {success_count}")
            print(f"   • Contacts created: {success_count}")
            print(f"\nYou can view the suppliers in:")
            print(f"   ERPNext → Buying → Suppliers")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_foxpro(auto_confirm=True)
