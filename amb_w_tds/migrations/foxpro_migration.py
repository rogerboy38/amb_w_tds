#!/usr/bin/env python3
"""
FoxPro to ERPNext Migration - COA and Sales Flow
Maps FoxPro ENHANCED JSON to ERPNext documents
"""

import frappe
from frappe.utils import nowdate, nowtime, add_days, getdate
import json
import os

@frappe.whitelist()
def inspect_folio_json(folio_num, base_path=None):
    """Inspect the JSON structure without creating anything"""
    if base_path is None:
        base_path = "/home/frappe/data/migracion01/migracion01_foxpro_erpnext"
    
    filename = "migration_folio_{:04d}_ENHANCED.json".format(int(folio_num))
    filepath = os.path.join(base_path, filename)
    
    if not os.path.exists(filepath):
        return {'error': 'File not found: {}'.format(filename)}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

@frappe.whitelist()
def create_batches_from_folio(folio_num, base_path=None):
    """
    Create Batch records from folio data
    Must be run BEFORE migrate_folio_to_quality_inspection
    
    Usage:
        import amb_w_tds.migrations.foxpro_migration as fm
        result = fm.create_batches_from_folio(1)
    """
    if base_path is None:
        base_path = "/home/frappe/data/migracion01/migracion01_foxpro_erpnext"
    
    filename = "migration_folio_{:04d}_ENHANCED.json".format(int(folio_num))
    filepath = os.path.join(base_path, filename)
    
    if not os.path.exists(filepath):
        return {'success': False, 'error': 'File not found: {}'.format(filename)}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        batches = data.get('batches', [])
        invoice_lines = data.get('invoice_lines', [])
        
        created_batches = []
        skipped_batches = []
        errors = []
        
        for batch_info in batches:
            lote = batch_info.get('lote')
            batch_data = batch_info.get('batch_data', {})
            
            if frappe.db.exists('Batch', lote):
                skipped_batches.append(lote)
                print("Batch {} already exists - skipped".format(lote))
                continue
            
            # Find item code from invoice lines
            item_code = None
            for line in invoice_lines:
                if line.get('lote_real') == lote:
                    item_code = line.get('product_code', lote)
                    break
            
            if not item_code:
                item_code = batch_data.get('CODIGO', lote)
            
            # Check if item exists
            if not frappe.db.exists('Item', item_code):
                # Create a simple item placeholder
                try:
                    item = frappe.get_doc({
                        'doctype': 'Item',
                        'item_code': item_code,
                        'item_name': batch_data.get('DESCRIP', item_code)[:140],
                        'item_group': 'Products',
                        'stock_uom': 'Kg',
                        'is_stock_item': 1,
                        'has_batch_no': 1,
                        'create_new_batch': 0,
                        'description': 'Migrated from FoxPro'
                    })
                    item.insert(ignore_permissions=True)
                    print("Created item: {}".format(item_code))
                except Exception as e:
                    error_msg = 'Item creation failed: {}'.format(str(e))
                    errors.append({'lote': lote, 'error': error_msg})
                    print(error_msg)
                    continue
            
            # Create batch
            batch_doc = {
                'doctype': 'Batch',
                'batch_id': lote,
                'item': item_code,
                'description': batch_data.get('DESCRIP', '')[:140] if batch_data.get('DESCRIP') else ''
            }
            
            # Add manufacturing date if available
            if batch_data.get('FECHA_MFD'):
                try:
                    batch_doc['manufacturing_date'] = getdate(batch_data.get('FECHA_MFD'))
                except:
                    pass
            
            try:
                batch = frappe.get_doc(batch_doc)
                batch.insert(ignore_permissions=True)
                created_batches.append(lote)
                print("Created batch: {}".format(lote))
            except Exception as e:
                error_msg = str(e)
                errors.append({'lote': lote, 'error': error_msg})
                print("Error creating batch {}: {}".format(lote, error_msg))
        
        frappe.db.commit()
        
        result = {
            'success': True,
            'folio': folio_num,
            'created': len(created_batches),
            'skipped': len(skipped_batches),
            'errors': len(errors),
            'created_batches': created_batches,
            'skipped_batches': skipped_batches,
            'error_details': errors
        }
        return result
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("Batch Creation Error - Folio {}".format(folio_num), str(e))
        result = {
            'success': False,
            'folio': folio_num,
            'error': str(e)
        }
        return result

@frappe.whitelist()
def migrate_folio_to_quality_inspection(folio_num, base_path=None):
    """
    Migrate a single folio to Quality Inspection
    
    Usage:
        import amb_w_tds.migrations.foxpro_migration as fm
        result = fm.migrate_folio_to_quality_inspection(1)
    """
    if base_path is None:
        base_path = "/home/frappe/data/migracion01/migracion01_foxpro_erpnext"
    
    filename = "migration_folio_{:04d}_ENHANCED.json".format(int(folio_num))
    filepath = os.path.join(base_path, filename)
    
    if not os.path.exists(filepath):
        return {'success': False, 'error': 'File not found: {}'.format(filename)}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        invoice_header = data.get('invoice_header', {})
        invoice_lines = data.get('invoice_lines', [])
        batches = data.get('batches', [])
        boms = data.get('boms', [])
        
        created_qis = []
        
        for idx, line in enumerate(invoice_lines):
            lote_real = line.get('lote_real')
            
            batch_data = None
            for batch in batches:
                if batch.get('lote') == lote_real:
                    batch_data = batch.get('batch_data', {})
                    break
            
            coa_ref = None
            for bom in boms:
                if bom.get('producto_finished') == lote_real:
                    coa_refs = bom.get('coa_references', [])
                    if coa_refs:
                        coa_ref = int(coa_refs[0])
                    break
            
            desc_lines = [
                "FoxPro Migration Data:",
                "Cliente: " + str(invoice_header.get('cliente', '')),
                "Factura: " + str(invoice_header.get('factura_number', '')),
                "Fecha: " + str(invoice_header.get('fecha', '')),
                "Lote: " + str(lote_real),
                "Producto: " + str(line.get('descripcion', '')),
                "Cantidad: " + str(line.get('cantidad', '')) + " " + str(line.get('unidad', '')),
                "Moneda: " + str(invoice_header.get('moneda', '')),
                "Precio: " + str(line.get('precio', '')),
                "COA Folio: " + str(coa_ref)
            ]
            description = "\n".join(desc_lines)
            
            qi_dict = {
                'doctype': 'Quality Inspection',
                'naming_series': 'MAT-QA-.YYYY.-',
                'inspection_type': 'Outgoing',
                'report_date': getdate(invoice_header.get('fecha', nowdate())),
                'status': 'Accepted',
                'inspected_by': 'Administrator',
                'item_code': line.get('product_code', lote_real),
                'item_name': line.get('descripcion', '')[:140],
                'sample_size': line.get('cantidad', 1),
                'reference_type': 'Customer',
                'reference_name': invoice_header.get('cliente', 'Default Customer')[:140],
                'batch_no': lote_real,
                'description': description
            }
            
            if batch_data:
                remarks_data = {
                    'foxpro_batch_data': batch_data,
                    'foxpro_line_data': line,
                    'migration_timestamp': data.get('timestamp')
                }
                qi_dict['remarks'] = json.dumps(remarks_data, indent=2)
            
            qi = frappe.get_doc(qi_dict)
            qi.insert(ignore_permissions=True)
            
            created_qis.append({
                'qi_name': qi.name,
                'lote': lote_real,
                'item': line.get('descripcion')
            })
            
            frappe.msgprint("Created QI: {} for batch {}".format(qi.name, lote_real))
        
        frappe.db.commit()
        
        result = {
            'success': True,
            'folio': folio_num,
            'created_qis': created_qis,
            'count': len(created_qis)
        }
        return result
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("Migration Error - Folio {}".format(folio_num), str(e))
        result = {
            'success': False,
            'folio': folio_num,
            'error': str(e)
        }
        return result

@frappe.whitelist()
def create_batches_range(start, end, base_path=None):
    """Create batches for a range of folios"""
    results = []
    total_created = 0
    total_skipped = 0
    total_errors = 0
    
    print("\n" + "="*70)
    print("BATCH CREATION - Folios {} to {}".format(start, end))
    print("="*70 + "\n")
    
    for folio_num in range(int(start), int(end) + 1):
        result = create_batches_from_folio(folio_num, base_path)
        results.append(result)
        
        if result.get('success'):
            total_created += result['created']
            total_skipped += result['skipped']
            total_errors += result['errors']
            print("[{:04d}] Created: {}, Skipped: {}, Errors: {}".format(
                folio_num, result['created'], result['skipped'], result['errors']))
        else:
            print("[{:04d}] Error: {}".format(folio_num, result.get('error', 'Unknown')))
    
    print("\n" + "="*70)
    print("BATCH CREATION SUMMARY:")
    print("  Total Batches Created: {}".format(total_created))
    print("  Total Skipped: {}".format(total_skipped))
    print("  Total Errors: {}".format(total_errors))
    print("="*70 + "\n")
    
    return {
        'total_created': total_created,
        'total_skipped': total_skipped,
        'total_errors': total_errors,
        'details': results
    }

@frappe.whitelist()
def migrate_range(start, end, base_path=None):
    """Migrate a range of folios to Quality Inspections"""
    results = []
    success_count = 0
    error_count = 0
    total_qis = 0
    
    print("\n" + "="*70)
    print("FOXPRO MIGRATION - Folios {} to {}".format(start, end))
    print("="*70 + "\n")
    
    for folio_num in range(int(start), int(end) + 1):
        result = migrate_folio_to_quality_inspection(folio_num, base_path)
        results.append(result)
        
        if result.get('success'):
            success_count += 1
            total_qis += result['count']
            print("[{:04d}] Success - Created {} Quality Inspections".format(
                folio_num, result['count']))
        else:
            error_count += 1
            print("[{:04d}] Error: {}".format(folio_num, result.get('error', 'Unknown')))
    
    print("\n" + "="*70)
    print("SUMMARY:")
    print("  Total Folios: {}".format(end - start + 1))
    print("  Success: {}".format(success_count))
    print("  Errors: {}".format(error_count))
    print("  Quality Inspections Created: {}".format(total_qis))
    print("="*70 + "\n")
    
    return {
        'total_folios': end - start + 1,
        'success': success_count,
        'errors': error_count,
        'total_qis': total_qis,
        'details': results
    }

@frappe.whitelist()
def get_migration_summary():
    """Get summary of migrated Quality Inspections"""
    total = frappe.db.count('Quality Inspection', {'batch_no': ['!=', '']})
    
    by_status = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabQuality Inspection`
        WHERE batch_no IS NOT NULL AND batch_no != ''
        GROUP BY status
    """, as_dict=True)
    
    return {
        'total_migrated': total,
        'by_status': by_status
    }
