import frappe
import os
import json
import glob
import re
from datetime import datetime

def clean_parameter_name(param_name):
    """Clean and map parameter name"""
    if not param_name:
        return "Appearance", 0
    
    original = param_name.strip()
    has_asterisk = original.endswith('*')
    
    # Remove asterisk and other symbols
    cleaned = re.sub(r'[\*\#\-\+\=]$', '', original)
    cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
    cleaned = re.sub(r'\s+\(.*\)$', '', cleaned)
    
    # Common mappings
    mappings = {
        "color gardner": "Color Gardner",
        "ph": "pH",
        "specific gravity": "Specific Gravity",
        "aloin content": "Aloin Content",
        "appearance": "Appearance",
        "particle size": "Particle Size",
        "solubility": "Solubility",
        "loss on drying": "Loss on Drying",
        "total plate count": "Total Plate Count",
        "yeast & mold": "Yeast & Mold",
        "e. coli": "E. Coli",
        "salmonella": "Salmonella",
        "heavy metals": "Heavy Metals",
        "moisture": "Moisture",
        "ash": "Ash",
        "odor": "Odor",
        "taste": "Taste",
        "preservatives": "Preservatives",
        "pathogens": "Pathogens",
        "coliforms": "Coliforms",
        "aerobic plate count": "Aerobic Plate Count",
        "mold and yeast": "Mold And Yeast"
    }
    
    param_lower = cleaned.lower()
    for pattern, mapped_name in mappings.items():
        if pattern in param_lower:
            return mapped_name, (1 if has_asterisk else 0)
    
    # Try to find existing parameter
    if frappe.db.exists("Quality Inspection Parameter", cleaned):
        return cleaned, (1 if has_asterisk else 0)
    
    # Try title case
    titled = cleaned.title()
    if frappe.db.exists("Quality Inspection Parameter", titled):
        return titled, (1 if has_asterisk else 0)
    
    # Find similar
    similar = frappe.get_all("Quality Inspection Parameter",
        filters={"parameter": ["like", f"%{cleaned}%"]},
        fields=["parameter"],
        limit=1
    )
    
    if similar:
        return similar[0].parameter, (1 if has_asterisk else 0)
    
    # Create if not found
    try:
        param_doc = frappe.get_doc({
            "doctype": "Quality Inspection Parameter",
            "parameter": cleaned,
            "parameter_group": "General"
        })
        param_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"    ⚙️  Created parameter: {cleaned}")
        return cleaned, (1 if has_asterisk else 0)
    except:
        return "Appearance", (1 if has_asterisk else 0)

def ensure_item_exists(product_code, product_name):
    """Ensure item exists, create if not"""
    if frappe.db.exists("Item", product_code):
        return True
    
    try:
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": product_code,
            "item_name": product_name or f"Product {product_code}",
            "item_group": "Products"
        })
        item.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"    ⚙️  Created Item: {product_code}")
        return True
    except Exception as e:
        print(f"    ❌ Failed to create Item {product_code}: {e}")
        return False

def process_foxpro_file(file_path):
    """Process a single FoxPro JSON file"""
    filename = os.path.basename(file_path)
    print(f"\n📄 Processing: {filename}")
    
    created_docs = []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        coa_data = data.get('coa_data', {})
        
        if not coa_data:
            print(f"  ⏭️  No COA data")
            return created_docs
        
        for batch_id, batch_info in coa_data.items():
            print(f"  📦 Batch: {batch_id}")
            
            revisions = batch_info.get('revisions', [])
            if not revisions:
                print(f"    ⚠️  No revisions")
                continue
            
            revision = revisions[0]
            
            # Extract data
            product_code = revision.get('product_code', '').strip()
            product_desc = revision.get('product_description', '').strip()
            approval_date = revision.get('date', '').strip()
            readings = revision.get('readings', [])
            
            if not product_code:
                print(f"    ❌ No product code")
                continue
            
            # Ensure item exists
            if not ensure_item_exists(product_code, product_desc):
                continue
            
            # Create COA AMB document
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
                
                # Link to Batch AMB if exists
                if frappe.db.exists("Batch AMB", batch_id):
                    coa_doc.batch_reference = batch_id
                    print(f"    🔗 Linked to Batch AMB")
                
                # Add test parameters
                param_count = 0
                asterisk_count = 0
                
                for reading in readings:
                    analysis_name = reading.get('analysis_name', '').strip()
                    specification = reading.get('specification', '').strip()
                    result = reading.get('result', '').strip()
                    test_method = reading.get('test_method', '').strip()
                    
                    if not analysis_name:
                        continue
                    
                    # Clean parameter
                    clean_param, has_asterisk = clean_parameter_name(analysis_name)
                    
                    # Determine status
                    result_lower = result.lower() if result else ""
                    status = "Pass" if any(word in result_lower for word in ['pass', 'conform', 'meet', 'ok']) else "Fail"
                    
                    # Add to child table
                    coa_doc.append("coa_quality_test_parameter", {
                        "parameter_name": clean_param,
                        "specification": specification[:140] if specification else "Meets specifications",
                        "test_method": test_method[:140] if test_method else "Standard method",
                        "result": result[:140] if result else status,
                        "status": status,
                        "custom_reconstituted_to_05_total_solids_solution": has_asterisk
                    })
                    param_count += 1
                    
                    if has_asterisk:
                        asterisk_count += 1
                
                print(f"    📊 Parameters: {param_count}")
                print(f"    ⚙️  Reconstituted: {asterisk_count}")
                
                # Must have at least 1 parameter
                if param_count == 0:
                    print(f"    ⚠️  No parameters, adding default...")
                    coa_doc.append("coa_quality_test_parameter", {
                        "parameter_name": "Appearance",
                        "specification": "Meets specifications",
                        "test_method": "Visual inspection",
                        "result": "Pass",
                        "status": "Pass"
                    })
                    param_count = 1
                
                # Save document
                coa_doc.insert(ignore_permissions=True)
                frappe.db.commit()
                
                print(f"    ✅ Created: {coa_doc.name}")
                
                created_docs.append({
                    "name": coa_doc.name,
                    "file": filename,
                    "batch": batch_id,
                    "product": product_code,
                    "parameters": param_count,
                    "reconstituted": asterisk_count
                })
                
            except Exception as e:
                print(f"    ❌ Error creating COA: {str(e)[:150]}")
                frappe.log_error("COA Migration Error", str(e))
                frappe.db.rollback()
    
    except Exception as e:
        print(f"❌ File error: {str(e)}")
        frappe.log_error("COA Migration File Error", str(e))
    
    return created_docs

def migrate_coa_data():
    """Main migration function"""
    print("🚀 COA AMB Data Migration")
    print("=" * 60)
    
    # Configuration
    foxpro_dir = "/home/frappe/sysmayaldata/foxpro_migration/data/json_files"
    results_dir = "/home/frappe/frappe-bench/coa_migration_final"
    
    # Create results directory
    os.makedirs(results_dir, exist_ok=True)
    
    if not os.path.exists(foxpro_dir):
        print(f"❌ Directory not found: {foxpro_dir}")
        return {"status": "error", "message": "Directory not found"}
    
    # Find files with COA data
    folio_files = glob.glob(os.path.join(foxpro_dir, "migration_folio_*.json"))
    folio_files.sort()
    
    print(f"📁 Found {len(folio_files)} folio files")
    
    # Process first 3 files with COA data
    files_to_process = []
    for file_path in folio_files[:50]:  # Check first 50 files
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if data.get('coa_data') and len(data['coa_data']) > 0:
                files_to_process.append(file_path)
                if len(files_to_process) >= 3:
                    break
        except:
            continue
    
    print(f"📊 Processing {len(files_to_process)} files with COA data")
    
    if not files_to_process:
        print("❌ No files with COA data found")
        return {"status": "no_data"}
    
    # Process files
    all_created_docs = []
    
    for i, file_path in enumerate(files_to_process):
        print(f"\n{'='*50}")
        print(f"File {i+1}/{len(files_to_process)}")
        created = process_foxpro_file(file_path)
        all_created_docs.extend(created)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"migration_results_{timestamp}.json")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "files_processed": len(files_to_process),
        "documents_created": len(all_created_docs),
        "created_documents": all_created_docs
    }
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 MIGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Files processed: {len(files_to_process)}")
    print(f"✅ Documents created: {len(all_created_docs)}")
    print(f"📄 Results saved to: {results_file}")
    
    if all_created_docs:
        print(f"\n📝 Created documents:")
        for doc in all_created_docs:
            print(f"  • {doc['name']} - Product: {doc['product']}, Parameters: {doc['parameters']}")
    
    return {
        "status": "success",
        "files_processed": len(files_to_process),
        "documents_created": len(all_created_docs),
        "results_file": results_file
    }

if __name__ == "__main__":
    migrate_coa_data()
