import frappe
import os
import json

def migrate_foxpro_coa(foxpro_dir, max_files=10):
    """
    Migrate FoxPro COA data to COA AMB
    foxpro_dir: Path to FoxPro JSON files
    max_files: Maximum number of files to process
    """
    
    # Get all folio files
    import glob
    folio_files = glob.glob(os.path.join(foxpro_dir, "migration_folio_*.json"))
    folio_files.sort()
    
    print(f"📁 Found {len(folio_files)} files")
    
    created_docs = []
    
    for file_path in folio_files[:max_files]:
        filename = os.path.basename(file_path)
        print(f"\n📄 Processing: {filename}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            coa_data = data.get('coa_data', {})
            
            if not coa_data:
                print("  ⏭️ No COA data")
                continue
            
            for batch_id, batch_info in coa_data.items():
                print(f"  📦 Batch: {batch_id}")
                
                revisions = batch_info.get('revisions', [])
                if not revisions:
                    print("    ⚠️ No revisions")
                    continue
                
                revision = revisions[0]
                
                # Extract data
                product_code = revision.get('product_code', '').strip()
                product_desc = revision.get('product_description', '').strip()
                approval_date = revision.get('date', '').strip()
                readings = revision.get('readings', [])
                
                if not product_code:
                    print("    ❌ No product code")
                    continue
                
                # Ensure Item exists
                if not frappe.db.exists("Item", product_code):
                    try:
                        item = frappe.get_doc({
                            "doctype": "Item",
                            "item_code": product_code,
                            "item_name": product_desc or f"Product {product_code}",
                            "item_group": "Products"
                        })
                        item.insert(ignore_permissions=True)
                        frappe.db.commit()
                    except:
                        continue
                
                # Create COA AMB
                try:
                    coa_doc = frappe.get_doc({
                        "doctype": "COA AMB",
                        "naming_series": "COA-.YY.-.####",
                        "product_item": product_code,
                        "item_name": product_desc,
                        "item_code": product_code,
                        "approval_date": approval_date if approval_date else None,
                        "coa_quality_test_parameter": []
                    })
                    
                    # Add test parameters
                    for reading in readings:
                        analysis_name = reading.get('analysis_name', '').strip()
                        specification = reading.get('specification', '').strip()
                        result = reading.get('result', '').strip()
                        test_method = reading.get('test_method', '').strip()
                        
                        if not analysis_name:
                            continue
                        
                        # Clean parameter
                        clean_param = analysis_name.rstrip('*').strip()
                        has_asterisk = analysis_name.endswith('*')
                        clean_param = clean_param.title()
                        
                        # Add to child table
                        coa_doc.append("coa_quality_test_parameter", {
                            "parameter_name": clean_param,
                            "specification": specification[:140] if specification else "",
                            "value": result[:140] if result else specification[:140],
                            "test_method": test_method[:140] if test_method else "",
                            "result": result[:140] if result else "",
                            "status": "Pass",
                            "custom_reconstituted_to_05_total_solids_solution": 1 if has_asterisk else 0
                        })
                    
                    # Save document
                    coa_doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                    
                    print(f"    ✅ Created: {coa_doc.name}")
                    created_docs.append(coa_doc.name)
                    
                except Exception as e:
                    print(f"    ❌ Error: {str(e)[:100]}")
                    frappe.db.rollback()
        
        except Exception as e:
            print(f"  ❌ File error: {str(e)[:100]}")
    
    print(f"\n✅ Migration complete! Created {len(created_docs)} documents:")
    for doc_name in created_docs:
        print(f"  • {doc_name}")
    
    return created_docs

# Usage
migrate_foxpro_coa("/home/frappe/sysmayaldata/foxpro_migration/data/json_files", max_files=50)
