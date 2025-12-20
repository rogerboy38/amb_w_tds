# V5.7 FoxPro Migration Agent - COMPLETE MERGED VERSION
"""AGENT v5.7 - FOXPRO MIGRATION & SUPPLIER MANAGEMENT MERGED"""
import frappe
from frappe.utils import today
from datetime import datetime
import json
import csv
from io import StringIO
# amb_w_tds/api/agent.py

import frappe
from frappe.utils import nowdate


class AmbAgent:
    """
    Class-based migration agent, safe for:
    - Frappe Cloud REST
    - frappe.call
    - bench / adapter
    """

    def _resolve_payload(self, payload=None, **kwargs) -> dict:
        """
        Unified resolver:
        1) explicit payload kwarg (adapter / bench)
        2) frappe.form_dict (REST / frappe.call)
        3) flat kwargs (direct Python)
        """
        # 1) adapter or direct Python providing payload
        if isinstance(payload, dict) and payload:
            return payload

        # 2) REST / frappe.call / Frappe Cloud
        if frappe.form_dict:
            fd = dict(frappe.form_dict)

            # support both {"payload": {...}} and flat JSON
            if isinstance(fd.get("payload"), dict):
                return fd["payload"]
            return fd

        # 3) fallback: flat kwargs
        if kwargs:
            return kwargs

        return {}

    # -------------------------------------------------
    # QUOTATION
    # -------------------------------------------------

    def create_or_get_quotation(self, payload=None, **kwargs):
        data = self._resolve_payload(payload=payload, **kwargs)

        customer = data.get("customer")
        custom_folio = data.get("custom_folio")
        company = data.get("company") or frappe.defaults.get_user_default("Company")

        if not customer or not custom_folio:
            frappe.throw("customer and custom_folio are required")

        existing = frappe.db.get_value(
            "Quotation",
            {"custom_folio": custom_folio, "docstatus": 0},
            "name",
        )
        if existing:
            return existing

        doc = frappe.get_doc({
            "doctype": "Quotation",
            "quotation_to": "Customer",
            "customer": customer,
            "company": company,
            "custom_folio": custom_folio,
            "transaction_date": nowdate(),
            "items": [{"item_code": "DUMMY", "qty": 1}],
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    
    # =============================================
    # SUPPLEMENTARY FUNCTIONS
    # =============================================
    #
    def get_request_data(kwargs=None):
        # 1?? Adapter / internal calls (explicit payload)
        if kwargs and isinstance(kwargs, dict):
            if isinstance(kwargs.get("payload"), dict):
                return kwargs["payload"]
    
        # 2?? HTTP / frappe.call / REST
        if frappe.form_dict:
            return dict(frappe.form_dict)
    
        # 3?? Fallback
        return {}

# amb_w_tds/api/agent.py (same file)

@frappe.whitelist()
def create_or_get_quotation(**kwargs):
    """
    REST / frappe.call entrypoint.
    Delegates to AmbAgent.create_or_get_quotation.
    """
    agent = AmbAgent()
    # Pass kwargs as-is; resolver will handle payload/form_dict/flat.
    return agent.create_or_get_quotation(**kwargs)


# =============================================
# SHARED HELPER FUNCTIONS
# =============================================
def get_mexico_tax_template():
    """Get or create Mexico tax template for e-invoicing"""
    try:
        # Check if Mexico tax template exists
        tax_templates = frappe.get_all('Sales Taxes and Charges Template', 
                                      filters={'title': 'Mexico E-Invoice Template'},
                                      fields=['name'])
        
        if tax_templates:
            return tax_templates[0]['name']
        
        # Create Mexico tax template if it doesn't exist
        company = frappe.defaults.get_user_default('Company') or frappe.db.get_single_value('Global Defaults', 'default_company')
        
        tax_template = {
            'doctype': 'Sales Taxes and Charges Template',
            'title': 'Mexico E-Invoice Template',
            'company': company,
            'is_default': 1,
            'taxes': [
                {
                    'charge_type': 'On Net Total',
                    'account_head': get_tax_account('VAT', company),
                    'description': 'IVA 16%',
                    'rate': 16.0,
                    'included_in_print_rate': 1
                }
            ]
        }
        
        template_doc = frappe.get_doc(tax_template)
        template_doc.insert()
        
        return template_doc.name
        
    except Exception as e:
        frappe.log_error(title="Tax Template Error", message=str(e))
        return None

def get_tax_account(tax_type, company):
    """Get tax account for Mexico"""
    try:
        if tax_type == 'VAT':
            accounts = frappe.get_all('Account',
                                    filters={
                                        'account_type': 'Tax',
                                        'account_name': ['like', '%IVA%'],
                                        'company': company
                                    },
                                    fields=['name'])
            if accounts:
                return accounts[0]['name']
        
        # Default tax account
        return 'VAT - 16% - S'
    except:
        return 'VAT - 16% - S'

def check_item_for_sales(item_code):
    """Check if item exists and is enabled for sales"""
    try:
        item = frappe.get_doc('Item', item_code)
        return {
            'exists': True,
            'enabled': item.is_sales_item,
            'status': item.disabled
        }
    except:
        return {'exists': False, 'enabled': False, 'status': True}

def enable_item_for_sales(item_code):
    """Enable item for sales if it exists"""
    try:
        item = frappe.get_doc('Item', item_code)
        item.is_sales_item = 1
        item.disabled = 0
        item.save()
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(title="Enable Item Error", message=f"Item: {item_code}, Error: {str(e)}")
        return False

def get_einvoice_status(invoice_name):
    """Check e-invoice generation status"""
    try:
        # Check if e-invoice was generated
        einvoice = frappe.get_all('E Invoice', 
                                 filters={'reference_name': invoice_name},
                                 fields=['name', 'status'])
        
        if einvoice:
            return einvoice[0]['status']
        return "Not Required"
    except:
        return "Status Check Failed"

# =============================================
# TEST ENDPOINT
# =============================================
@frappe.whitelist(allow_guest=False)
def test():
    """Test endpoint to verify agent version"""
    return {
        "status": "success",
        "message": "✅ Agent v5.7 - Complete FoxPro Migration & Supplier Management",
        "version": "v5.7-complete",
        "timestamp": datetime.now().isoformat()
    }

# =============================================
# BATCH ENDPOINTS (KEEP ALL ORIGINAL)
# =============================================
@frappe.whitelist(allow_guest=False)
def process(**kwargs):
    """CREATE PRODUCTION BATCH WITH CONTAINER_BARRELS SUPPORT - FOXPRO MIGRATION FIXED"""
    try:
        # Get data from all sources
        data = get_request_data(kwargs)
        
        # Handle empty payload
        if not data:
            return {
                "status": "error",
                "message": "Validation failed",
                "errors": ["Empty payload provided"],
                "guidance": {
                    "required_parameters": ["quantity", "(batch_id OR title)"],
                    "example_request": {
                        "quantity": 10,
                        "batch_id": "TEST-001",
                        "title": "Test Batch"
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
        
        # Validate required parameters
        errors = []
        
        # 1. Quantity validation
        quantity = data.get('quantity')
        if quantity is None:
            errors.append("'quantity' parameter is required")
        else:
            try:
                quantity = float(quantity)  # Changed to float for FoxPro compatibility
                if quantity <= 0:
                    errors.append("'quantity' must be > 0")
            except:
                errors.append("'quantity' must be a valid number")
        
        # 2. Batch ID or Title validation
        batch_id = data.get('batch_id', '').strip()
        title = data.get('title', '').strip()
        if not batch_id and not title:
            errors.append("Either 'batch_id' or 'title' is required")
        
        if errors:
            return {
                "status": "error",
                "message": "Validation failed",
                "errors": errors,
                "guidance": {
                    "required_parameters": ["quantity", "(batch_id OR title)"],
                    "example_request": {
                        "quantity": 10,
                        "batch_id": "TEST-001",
                        "title": "Test Batch"
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
        
        # Generate batch ID if not provided
        if not batch_id:
            batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not title:
            title = batch_id
        
        # Ensure title length is appropriate (Batch AMB field limit is 20 chars)
        if len(title) > 20:
            title = title[:20]
        
        # Create batch data with CORRECT FIELD NAMES
        batch_data = {
            'doctype': 'Batch AMB',
            'title': title,
            'custom_golden_number': batch_id,
            'processed_quantity': float(quantity),
            'processing_status': 'Draft',
            'work_order_ref': data.get('work_order', ''),
            'custom_batch_level': data.get('custom_batch_level', '1'),
            'custom_plant_code': data.get('plant_code', '25'),
            'production_plant': data.get('production_plant', '1 (Mix)'),
            'item_code': data.get('item_code', '0334009251')
        }
        
        # Add optional fields
        if data.get('golden_number'):
            batch_data['custom_golden_number'] = data['golden_number']
        if data.get('parent_batch'):
            batch_data['parent_batch_amb'] = data['parent_batch']
        
        # Create document
        doc = frappe.get_doc(batch_data)
        doc.insert()
        
        # 🔥 CRITICAL FIX: Add container_barrels data if provided
        # Check for different possible field names in the request
        containers_data = None
        
        # Try different possible field names
        possible_field_names = [
            'container_barrels',
            'containers_barrels', 
            'barrels_container',
            'barrels_containers',
            'containers',
            'barrels'
        ]
        
        for field_name in possible_field_names:
            if field_name in data:
                containers_data = data.get(field_name)
                break
        
        # If containers data is provided as a dictionary, convert to list
        if containers_data and isinstance(containers_data, dict):
            containers_data = [containers_data]
        
        # ⚠️ IMPORTANT FIELD MAPPING FIX:
        # The database has 'barrel_serial_number' but agent expects 'container_code'
        # We need to map the fields correctly
        
        # Add container_barrels child table rows
        if containers_data and isinstance(containers_data, list):
            container_count = 0
            for container in containers_data:
                # Check for container_code or barrel_serial_number
                container_code = container.get('container_code') or container.get('barrel_serial_number')
                if not container_code:
                    frappe.log_error(
                        title="Container Missing Code",
                        message=f"Container missing container_code/barrel_serial_number: {container}"
                    )
                    continue
                
                # ⚠️ FIX: Map fields to database structure
                # Agent expects: container_code, container_type, quantity, status, location, notes
                # Database has: barrel_serial_number, packaging_type, net_weight, status, etc.
                
                # Use net_weight if quantity not provided
                container_quantity = container.get('quantity')
                if not container_quantity and 'net_weight' in container:
                    container_quantity = container.get('net_weight')
                
                # Use packaging_type if container_type not provided
                container_type = container.get('container_type')
                if not container_type and 'packaging_type' in container:
                    container_type = container.get('packaging_type', 'Barrel')
                
                # Add child table row with CORRECT FIELD NAME: container_barrels
                doc.append('container_barrels', {
                    'barrel_serial_number': container_code,  # Database field name
                    'packaging_type': container_type,  # Database field name
                    'net_weight': float(container_quantity) if container_quantity else 0.0,  # Database field name
                    'status': container.get('status', 'Full'),
                    'full_serial': container.get('full_serial', ''),
                    'golden_number': data.get('golden_number', batch_id),
                    'item_code': data.get('item_code', ''),
                    'work_order': data.get('work_order', '')
                })
                container_count += 1
            
            # Save the document with child table data
            if container_count > 0:
                doc.save()
                frappe.logger().info(f"Added {container_count} containers to batch {doc.name}")
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"✅ Batch created successfully with {container_count if containers_data else 0} containers!",
            "data": {
                "name": doc.name,
                "batch_id": batch_id,
                "title": title,
                "containers_count": container_count if containers_data else 0,
                "containers_added": True if containers_data and container_count > 0 else False
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Agent Process Error", message=str(e))
        return {
            "status": "error",
            "message": f"Internal error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def add_containers_to_existing_batch(**kwargs):
    """ADD CONTAINER_BARRELS TO EXISTING BATCH AMB DOCUMENT"""
    try:
        data = get_request_data(kwargs)
        
        # Validate required parameters
        batch_name = data.get('batch_name')
        batch_id = data.get('batch_id')
        
        if not batch_name and not batch_id:
            return {
                "status": "error",
                "message": "Either batch_name or batch_id is required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Find the batch
        if batch_name:
            batch = frappe.get_doc('Batch AMB', batch_name)
        else:
            # Search by batch_id (custom_golden_number)
            batches = frappe.get_all('Batch AMB',
                                   filters={'custom_golden_number': batch_id},
                                   fields=['name'])
            if not batches:
                return {
                    "status": "error",
                    "message": f"Batch with ID {batch_id} not found",
                    "timestamp": datetime.now().isoformat()
                }
            batch = frappe.get_doc('Batch AMB', batches[0]['name'])
        
        # Get containers data
        containers_data = data.get('container_barrels', data.get('containers', []))
        if not containers_data:
            return {
                "status": "error",
                "message": "No containers data provided",
                "timestamp": datetime.now().isoformat()
            }
        
        # Convert to list if it's a dictionary
        if isinstance(containers_data, dict):
            containers_data = [containers_data]
        
        # ⚠️ FIELD MAPPING FIX for existing batches too
        # Add containers to existing batch
        container_count = 0
        for container in containers_data:
            # Check for container_code or barrel_serial_number
            container_code = container.get('container_code') or container.get('barrel_serial_number')
            if not container_code:
                continue
            
            # Map fields to database structure
            container_quantity = container.get('quantity')
            if not container_quantity and 'net_weight' in container:
                container_quantity = container.get('net_weight')
            
            container_type = container.get('container_type')
            if not container_type and 'packaging_type' in container:
                container_type = container.get('packaging_type', 'Barrel')
                
            batch.append('container_barrels', {
                'barrel_serial_number': container_code,  # Database field
                'packaging_type': container_type,  # Database field
                'net_weight': float(container_quantity) if container_quantity else 0.0,  # Database field
                'status': container.get('status', 'Full'),
                'full_serial': container.get('full_serial', ''),
                'golden_number': batch.custom_golden_number or batch_id,
                'item_code': container.get('item_code', ''),
                'work_order': container.get('work_order', '')
            })
            container_count += 1
        
        if container_count > 0:
            batch.save()
            frappe.db.commit()
            
            return {
                "status": "success",
                "message": f"✅ Added {container_count} containers to batch {batch.name}",
                "data": {
                    "batch_name": batch.name,
                    "batch_id": batch.custom_golden_number,
                    "containers_added": container_count,
                    "total_containers": len(batch.container_barrels) if hasattr(batch, 'container_barrels') else 0
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "No valid containers were added",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Add Containers Error", message=str(e))
        return {
            "status": "error",
            "message": f"Error adding containers: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def migrate_foxpro_invoice(**kwargs):
    """SPECIAL ENDPOINT FOR FOXPRO INVOICE MIGRATION WITH MEXICO TAXES"""
    try:
        data = get_request_data(kwargs)
        
        # Extract invoice data from FoxPro format
        invoice_header = data.get('invoice_header', {})
        invoice_lines = data.get('invoice_lines', [])
        
        # Validate required fields
        if not invoice_header or not invoice_lines:
            return {
                "status": "error",
                "message": "Missing invoice data",
                "errors": ["invoice_header and invoice_lines are required"],
                "timestamp": datetime.now().isoformat()
            }
        
        # Create Sales Invoice with Mexico tax settings
        invoice_data = {
            'doctype': 'Sales Invoice',
            'customer': invoice_header.get('cliente', ''),
            'posting_date': invoice_header.get('fecha', datetime.now().date().isoformat()),
            'due_date': invoice_header.get('fecha', datetime.now().date().isoformat()),
            'currency': invoice_header.get('moneda', 'MXN'),
            'taxes_and_charges': get_mexico_tax_template(),
            'items': [],
            'custom_folio': invoice_header.get('folio'),
            'custom_factura': invoice_header.get('factura')
        }
        
        # Process invoice lines
        for line in invoice_lines:
            item_code = line.get('item_code')
            batch_no = line.get('lote_real')
            
            # Check if item exists and is enabled for sales
            item_status = check_item_for_sales(item_code)
            if not item_status['enabled']:
                # Try to enable the item
                enable_item_for_sales(item_code)
            
            # Create invoice item
            item_data = {
                'item_code': item_code,
                'qty': line.get('cantidad', 1.0),
                'rate': line.get('precio', 0.0),
                'amount': line.get('importe', 0.0),
                'uom': line.get('unidad', 'Kg'),
                'description': line.get('descripcion', '')
            }
            
            # Add batch reference if available
            if batch_no:
                item_data['batch_no'] = batch_no
            
            invoice_data['items'].append(item_data)
        
        # Create the sales invoice
        invoice_doc = frappe.get_doc(invoice_data)
        invoice_doc.insert()
        
        # 🔥 CRITICAL: Submit the invoice to trigger Mexico e-invoice generation
        invoice_doc.submit()
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": "✅ FoxPro invoice migrated successfully with Mexico tax compliance!",
            "data": {
                "invoice_name": invoice_doc.name,
                "customer": invoice_doc.customer,
                "total": invoice_doc.grand_total,
                "items_count": len(invoice_lines),
                "e_invoice_status": get_einvoice_status(invoice_doc.name)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="FoxPro Invoice Migration Error", message=str(e))
        return {
            "status": "error",
            "message": f"Invoice migration error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def batch_with_containers_example():
    """Example API call for creating batch with container_barrels"""
    return {
        "status": "success",
        "example_request": {
            "quantity": 1000,
            "batch_id": "0219071201",
            "title": "FoxPro Migration Batch",
            "item_code": "0219",
            "golden_number": "0219071201",
            "container_barrels": [
                {
                    "container_code": "C001",
                    "container_type": "Barrel",
                    "quantity": 200,
                    "status": "Full",
                    "location": "Warehouse A",
                    "notes": "Primary container"
                },
                {
                    "container_code": "C002", 
                    "container_type": "Barrel",
                    "quantity": 200,
                    "status": "Full",
                    "location": "Warehouse A",
                    "notes": "Secondary container"
                }
            ]
        },
        "example_invoice_request": {
            "invoice_header": {
                "folio": 1,
                "cliente": "BRENNTAG MEXICO SA DE CV (SAN MARTÍN OBISPO)",
                "factura": "F1454",
                "fecha": "2021-08-06",
                "moneda": "USD"
            },
            "invoice_lines": [
                {
                    "lote_real": "0219071201",
                    "item_code": "ITEM_0219071201",
                    "descripcion": "INNOVALOE ALOE VERA GEL SPRAY DRIED POWDER 200:1",
                    "cantidad": 1.0,
                    "precio": 122.0,
                    "importe": 122.0,
                    "unidad": "Kg."
                }
            ]
        },
        "timestamp": datetime.now().isoformat()
    }

@frappe.whitelist(allow_guest=False)
def get_batch_containers(batch_name=None, batch_id=None):
    """Get container_barrels for a specific batch"""
    try:
        if not batch_name and not batch_id:
            return {
                "status": "error",
                "message": "Either batch_name or batch_id is required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Find the batch
        if batch_name:
            batch = frappe.get_doc('Batch AMB', batch_name)
        else:
            # Search by batch_id (custom_golden_number)
            batches = frappe.get_all('Batch AMB',
                                   filters={'custom_golden_number': batch_id},
                                   fields=['name'])
            if not batches:
                return {
                    "status": "error",
                    "message": f"Batch with ID {batch_id} not found",
                    "timestamp": datetime.now().isoformat()
                }
            batch = frappe.get_doc('Batch AMB', batches[0]['name'])
        
        # Get container_barrels data - ⚠️ RETURN DATABASE FIELD NAMES
        containers = []
        if hasattr(batch, 'container_barrels') and batch.container_barrels:
            for container in batch.container_barrels:
                containers.append({
                    'barrel_serial_number': container.barrel_serial_number,
                    'packaging_type': container.packaging_type,
                    'net_weight': container.net_weight,
                    'status': container.status,
                    'full_serial': container.full_serial,
                    'golden_number': container.golden_number,
                    'item_code': container.item_code,
                    'work_order': container.work_order
                })
        
        return {
            "status": "success",
            "batch_name": batch.name,
            "batch_id": batch.custom_golden_number,
            "containers": containers,
            "containers_count": len(containers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(title="Get Containers Error", message=str(e))
        return {
            "status": "error",
            "message": f"Error getting containers: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# =============================================
# KEEP OTHER EXISTING ENDPOINTS
# =============================================
@frappe.whitelist(allow_guest=False)
def migrate_foxpro_batch(**kwargs):
    """Special endpoint for FoxPro migration data"""
    try:
        data = get_request_data(kwargs)
        
        # Handle container_barrels data
        # Try different possible field names
        possible_field_names = [
            'container_barrels',
            'containers_barrels', 
            'barrels_container',
            'barrels_containers',
            'containers',
            'barrels'
        ]
        
        for field_name in possible_field_names:
            if field_name in data and field_name != 'container_barrels':
                # Rename to correct field name
                data['container_barrels'] = data[field_name]
                break
        
        # Call the main process function
        return process(**data)
        
    except Exception as e:
        frappe.log_error(title="Migration Agent Error", message=str(e))
        return {
            "status": "error",
            "message": f"Migration error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def batch_validate_golden(**kwargs):
    """Validate batch ID against golden number pattern"""
    try:
        data = get_request_data(kwargs)
        batch_id = data.get('batch_id', '').strip()
        
        if not batch_id:
            return {
                "status": "error",
                "message": "batch_id parameter required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Validation logic (simplified)
        is_valid = False
        message = ""
        
        if batch_id.isdigit() and len(batch_id) == 10:
            is_valid = True
            message = "Valid golden number format"
        elif '-' in batch_id:
            parts = batch_id.split('-')
            if len(parts[0]) == 10 and parts[0].isdigit():
                is_valid = True
                message = f"Valid hierarchy - Level {len(parts)}"
        
        return {
            "status": "success" if is_valid else "error",
            "is_valid": is_valid,
            "message": message,
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def validate_parameters(**kwargs):
    """Validate parameters without creating batch"""
    try:
        data = get_request_data(kwargs)
        
        validation = {
            "parameters_received": list(data.keys()),
            "validation_results": {}
        }
        
        # Check quantity
        if 'quantity' in data:
            try:
                qty = float(data['quantity'])
                validation["validation_results"]['quantity'] = {
                    "status": "valid" if qty > 0 else "invalid",
                    "message": "valid" if qty > 0 else "must be > 0"
                }
            except:
                validation["validation_results"]['quantity'] = {
                    "status": "invalid",
                    "message": "must be a valid number"
                }
        else:
            validation["validation_results"]['quantity'] = {
                "status": "missing",
                "message": "required parameter"
            }
        
        # Check identifier
        has_batch_id = bool(data.get('batch_id', '').strip())
        has_title = bool(data.get('title', '').strip())
        
        validation["validation_results"]['identifier'] = {
            "status": "valid" if (has_batch_id or has_title) else "missing",
            "message": "valid" if (has_batch_id or has_title) else "either batch_id or title required"
        }
        
        return {
            "status": "success",
            "validation": validation,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def create_demo_batches():
    return {
        "status": "success",
        "message": "Demo batches endpoint",
        "timestamp": datetime.now().isoformat()
    }

@frappe.whitelist(allow_guest=False)
def get_recent_batches_with_details(limit=5):
    try:
        # UPDATED: Query correct fields for Batch AMB
        batches = frappe.get_all('Batch AMB', 
                               fields=['name', 'custom_golden_number', 'title', 'creation', 'processed_quantity'],
                               limit=int(limit) if str(limit).isdigit() else 5,
                               order_by='creation desc')
        return {
            "status": "success",
            "batches": batches,
            "count": len(batches),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fetching batches: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def verify_ui_columns():
    return {
        "status": "success",
        "message": "UI columns verification endpoint",
        "timestamp": datetime.now().isoformat()
    }

@frappe.whitelist(allow_guest=False)
def fix_batch_ids():
    return {
        "status": "success",
        "message": "Batch ID fix endpoint",
        "timestamp": datetime.now().isoformat()
    }

@frappe.whitelist(allow_guest=False)
def fix_all_items_for_sales():
    """Enable all FoxPro migration items for sales"""
    try:
        # Find all items that might be from FoxPro migration
        items = frappe.get_all('Item', 
                             filters={'item_code': ['like', '0%']},
                             fields=['name', 'item_code', 'is_sales_item', 'disabled'])
        
        fixed_count = 0
        for item in items:
            if not item.is_sales_item or item.disabled:
                try:
                    doc = frappe.get_doc('Item', item.name)
                    doc.is_sales_item = 1
                    doc.disabled = 0
                    doc.save()
                    fixed_count += 1
                except Exception as e:
                    frappe.log_error(title="Fix Item Error", message=f"Item: {item.item_code}, Error: {str(e)}")
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"✅ Enabled {fixed_count} items for sales",
            "total_items": len(items),
            "fixed_items": fixed_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fixing items: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# =============================================
# NEW SUPPLIER MANAGEMENT ENDPOINTS
# =============================================

@frappe.whitelist(allow_guest=False)
def create_supplier(**kwargs):
    """CREATE OR UPDATE SUPPLIER WITH COMPLETE DATA"""
    try:
        data = get_request_data(kwargs)
        
        # Validate required fields
        if not data.get('supplier_name'):
            return {
                "status": "error",
                "message": "supplier_name is required",
                "timestamp": datetime.now().isoformat()
            }
        
        supplier_name = data['supplier_name'].strip()
        
        # Check if supplier already exists
        existing = frappe.get_all('Supplier',
                                filters={'supplier_name': supplier_name},
                                fields=['name'])
        
        if existing:
            # Update existing supplier
            doc = frappe.get_doc('Supplier', existing[0]['name'])
            update_mode = True
        else:
            # Create new supplier
            doc = frappe.new_doc('Supplier')
            update_mode = False
        
        # Map data to supplier fields
        field_mapping = {
            'supplier_name': 'supplier_name',
            'supplier_type': 'supplier_type',
            'tax_id': 'tax_id',
            'supplier_group': 'supplier_group',
            'default_currency': 'default_currency',
            'payment_terms': 'payment_terms',
            'custom_rfc': 'custom_rfc',
            'custom_curp': 'custom_curp',
            'custom_phone': 'custom_phone',
            'custom_email': 'custom_email',
            'website': 'website',
            'is_internal_supplier': 'is_internal_supplier',
            'disabled': 'disabled',
            'language': 'language',
            'country': 'country'
        }
        
        for source_field, target_field in field_mapping.items():
            if source_field in data and data[source_field] is not None:
                doc.set(target_field, data[source_field])
        
        # Handle addresses if provided
        if 'addresses' in data and isinstance(data['addresses'], list):
            addresses = data['addresses']
        elif 'address' in data:
            addresses = [data['address']]
        else:
            addresses = []
        
        # Handle contacts if provided
        if 'contacts' in data and isinstance(data['contacts'], list):
            contacts = data['contacts']
        elif 'contact' in data:
            contacts = [data['contact']]
        else:
            contacts = []
        
        # Save supplier first
        if update_mode:
            doc.save()
            message = "✅ Supplier updated"
        else:
            doc.insert()
            message = "✅ Supplier created"
        
        supplier_id = doc.name
        
        # Process addresses
        address_results = []
        for address_data in addresses:
            addr_result = create_or_link_address(address_data, supplier_id)
            address_results.append(addr_result)
        
        # Process contacts
        contact_results = []
        for contact_data in contacts:
            contact_result = create_or_link_contact(contact_data, supplier_id)
            contact_results.append(contact_result)
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"{message} with {len(address_results)} addresses and {len(contact_results)} contacts",
            "data": {
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "addresses_processed": len(address_results),
                "contacts_processed": len(contact_results),
                "is_update": update_mode
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Create Supplier Error", message=str(e))
        return {
            "status": "error",
            "message": f"Supplier creation error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

def create_or_link_address(address_data, supplier_id):
    """Create or link address to supplier"""
    try:
        # Check if address already exists (by address_title or address_line1)
        address_title = address_data.get('address_title', f"{supplier_id} Address")
        existing_addresses = frappe.get_all('Address',
                                          filters={'address_title': address_title},
                                          fields=['name'])
        
        if existing_addresses:
            # Update existing address
            addr = frappe.get_doc('Address', existing_addresses[0]['name'])
        else:
            # Create new address
            addr = frappe.new_doc('Address')
            addr.address_title = address_title
        
        # Map address fields
        address_fields = ['address_type', 'address_line1', 'address_line2', 
                         'city', 'state', 'country', 'pincode', 'email_id', 
                         'phone', 'is_primary_address', 'is_shipping_address']
        
        for field in address_fields:
            if field in address_data:
                addr.set(field, address_data[field])
        
        # Add link to supplier
        link_exists = False
        for link in addr.links or []:
            if link.link_doctype == 'Supplier' and link.link_name == supplier_id:
                link_exists = True
                break
        
        if not link_exists:
            addr.append('links', {
                'link_doctype': 'Supplier',
                'link_name': supplier_id
            })
        
        if existing_addresses:
            addr.save()
        else:
            addr.insert()
        
        return {'status': 'success', 'address_id': addr.name}
        
    except Exception as e:
        frappe.log_error(title="Address Creation Error", 
                        message=f"Supplier: {supplier_id}, Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}

def create_or_link_contact(contact_data, supplier_id):
    """Create or link contact to supplier"""
    try:
        # Generate contact name
        first_name = contact_data.get('first_name', '')
        last_name = contact_data.get('last_name', '')
        email = contact_data.get('email_id', '')
        
        contact_name = f"{first_name} {last_name}".strip()
        if not contact_name and email:
            contact_name = email
        
        # Check if contact exists by email
        existing_contacts = []
        if email:
            existing_contacts = frappe.get_all('Contact',
                                             filters={'email_id': email},
                                             fields=['name'])
        
        if existing_contacts:
            # Update existing contact
            contact = frappe.get_doc('Contact', existing_contacts[0]['name'])
        else:
            # Create new contact
            contact = frappe.new_doc('Contact')
            if contact_name:
                contact.first_name = first_name
                contact.last_name = last_name
            elif email:
                contact.first_name = email
        
        # Map contact fields
        contact_fields = ['designation', 'email_id', 'phone', 'mobile_no',
                         'is_primary_contact', 'department', 'company_name']
        
        for field in contact_fields:
            if field in contact_data:
                contact.set(field, contact_data[field])
        
        # Add link to supplier
        link_exists = False
        for link in contact.links or []:
            if link.link_doctype == 'Supplier' and link.link_name == supplier_id:
                link_exists = True
                break
        
        if not link_exists:
            contact.append('links', {
                'link_doctype': 'Supplier',
                'link_name': supplier_id
            })
        
        if existing_contacts:
            contact.save()
        else:
            contact.insert()
        
        return {'status': 'success', 'contact_id': contact.name}
        
    except Exception as e:
        frappe.log_error(title="Contact Creation Error", 
                        message=f"Supplier: {supplier_id}, Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}

@frappe.whitelist(allow_guest=False)
def get_supplier(supplier_name=None, supplier_id=None):
    """GET SUPPLIER DETAILS WITH ADDRESSES AND CONTACTS"""
    try:
        if not supplier_name and not supplier_id:
            return {
                "status": "error",
                "message": "Either supplier_name or supplier_id is required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Find supplier
        if supplier_id:
            supplier = frappe.get_doc('Supplier', supplier_id)
        else:
            suppliers = frappe.get_all('Supplier',
                                     filters={'supplier_name': supplier_name},
                                     fields=['name'])
            if not suppliers:
                return {
                    "status": "error",
                    "message": f"Supplier '{supplier_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
            supplier = frappe.get_doc('Supplier', suppliers[0]['name'])
        
        # Get linked addresses
        addresses = frappe.get_all('Dynamic Link',
                                 filters=[
                                     ['link_doctype', '=', 'Supplier'],
                                     ['link_name', '=', supplier.name],
                                     ['parenttype', '=', 'Address']
                                 ],
                                 fields=['parent'])
        
        address_details = []
        for addr in addresses:
            address_doc = frappe.get_doc('Address', addr.parent)
            address_details.append({
                'name': address_doc.name,
                'address_title': address_doc.address_title,
                'address_type': address_doc.address_type,
                'address_line1': address_doc.address_line1,
                'address_line2': address_doc.address_line2,
                'city': address_doc.city,
                'state': address_doc.state,
                'country': address_doc.country,
                'pincode': address_doc.pincode,
                'email_id': address_doc.email_id,
                'phone': address_doc.phone,
                'is_primary_address': address_doc.is_primary_address,
                'is_shipping_address': address_doc.is_shipping_address
            })
        
        # Get linked contacts
        contacts = frappe.get_all('Dynamic Link',
                                filters=[
                                    ['link_doctype', '=', 'Supplier'],
                                    ['link_name', '=', supplier.name],
                                    ['parenttype', '=', 'Contact']
                                ],
                                fields=['parent'])
        
        contact_details = []
        for cont in contacts:
            contact_doc = frappe.get_doc('Contact', cont.parent)
            contact_details.append({
                'name': contact_doc.name,
                'first_name': contact_doc.first_name,
                'last_name': contact_doc.last_name,
                'full_name': contact_doc.full_name,
                'designation': contact_doc.designation,
                'email_id': contact_doc.email_id,
                'phone': contact_doc.phone,
                'mobile_no': contact_doc.mobile_no,
                'is_primary_contact': contact_doc.is_primary_contact,
                'department': contact_doc.department,
                'company_name': contact_doc.company_name
            })
        
        return {
            "status": "success",
            "data": {
                "supplier": {
                    "name": supplier.name,
                    "supplier_name": supplier.supplier_name,
                    "supplier_type": supplier.supplier_type,
                    "tax_id": supplier.tax_id,
                    "supplier_group": supplier.supplier_group,
                    "default_currency": supplier.default_currency,
                    "payment_terms": supplier.payment_terms,
                    "custom_rfc": supplier.custom_rfc,
                    "custom_curp": supplier.custom_curp,
                    "custom_phone": supplier.custom_phone,
                    "custom_email": supplier.custom_email,
                    "website": supplier.website,
                    "is_internal_supplier": supplier.is_internal_supplier,
                    "disabled": supplier.disabled,
                    "language": supplier.language,
                    "country": supplier.country,
                    "creation": supplier.creation,
                    "modified": supplier.modified
                },
                "addresses": address_details,
                "contacts": contact_details,
                "counts": {
                    "addresses": len(address_details),
                    "contacts": len(contact_details)
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(title="Get Supplier Error", message=str(e))
        return {
            "status": "error",
            "message": f"Error getting supplier: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def get_all_suppliers(limit=100, offset=0, with_details=False):
    """GET ALL SUPPLIERS WITH OPTIONAL DETAILS"""
    try:
        limit = int(limit) if str(limit).isdigit() else 100
        offset = int(offset) if str(offset).isdigit() else 0
        
        # Get suppliers
        suppliers = frappe.get_all('Supplier',
                                 fields=['name', 'supplier_name', 'supplier_type', 
                                         'tax_id', 'supplier_group', 'default_currency',
                                         'custom_rfc', 'custom_phone', 'custom_email',
                                         'disabled', 'creation'],
                                 limit=limit,
                                 start=offset,
                                 order_by='supplier_name')
        
        total_suppliers = frappe.db.count('Supplier')
        
        result = {
            "status": "success",
            "data": {
                "suppliers": suppliers,
                "count": len(suppliers),
                "total": total_suppliers,
                "limit": limit,
                "offset": offset
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add details if requested
        if with_details and with_details.lower() in ['true', '1', 'yes']:
            detailed_suppliers = []
            for supplier in suppliers:
                details = get_supplier(supplier_id=supplier['name'])
                if details.get('status') == 'success':
                    detailed_suppliers.append(details['data'])
                else:
                    detailed_suppliers.append({
                        "supplier": supplier,
                        "addresses": [],
                        "contacts": []
                    })
            
            result["data"]["detailed_suppliers"] = detailed_suppliers
        
        return result
        
    except Exception as e:
        frappe.log_error(title="Get All Suppliers Error", message=str(e))
        return {
            "status": "error",
            "message": f"Error getting suppliers: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def search_suppliers(search_term, limit=20):
    """SEARCH SUPPLIERS BY NAME, TAX ID, OR RFC"""
    try:
        search_term = f"%{search_term}%"
        
        suppliers = frappe.get_all('Supplier',
                                 filters=[
                                     ['supplier_name', 'like', search_term],
                                     ['tax_id', 'like', search_term],
                                     ['custom_rfc', 'like', search_term]
                                 ],
                                 fields=['name', 'supplier_name', 'tax_id', 
                                         'custom_rfc', 'supplier_type', 'supplier_group'],
                                 or_filters=True,
                                 limit=int(limit) if str(limit).isdigit() else 20)
        
        return {
            "status": "success",
            "data": {
                "suppliers": suppliers,
                "count": len(suppliers),
                "search_term": search_term.replace('%', '')
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(title="Search Suppliers Error", message=str(e))
        return {
            "status": "error",
            "message": f"Search error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def update_supplier(**kwargs):
    """UPDATE EXISTING SUPPLIER"""
    try:
        data = get_request_data(kwargs)
        
        supplier_id = data.get('supplier_id')
        supplier_name = data.get('supplier_name')
        
        if not supplier_id and not supplier_name:
            return {
                "status": "error",
                "message": "Either supplier_id or supplier_name is required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Find supplier
        if supplier_id:
            supplier = frappe.get_doc('Supplier', supplier_id)
        else:
            suppliers = frappe.get_all('Supplier',
                                     filters={'supplier_name': supplier_name},
                                     fields=['name'])
            if not suppliers:
                return {
                    "status": "error",
                    "message": f"Supplier '{supplier_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
            supplier = frappe.get_doc('Supplier', suppliers[0]['name'])
        
        # Update fields
        update_fields = ['supplier_type', 'tax_id', 'supplier_group', 
                        'default_currency', 'payment_terms', 'custom_rfc',
                        'custom_curp', 'custom_phone', 'custom_email',
                        'website', 'is_internal_supplier', 'disabled',
                        'language', 'country']
        
        updated_fields = []
        for field in update_fields:
            if field in data and data[field] is not None:
                old_value = getattr(supplier, field, None)
                new_value = data[field]
                
                if old_value != new_value:
                    setattr(supplier, field, new_value)
                    updated_fields.append(field)
        
        if updated_fields:
            supplier.save()
            frappe.db.commit()
            
            return {
                "status": "success",
                "message": f"✅ Supplier updated - {len(updated_fields)} fields changed",
                "data": {
                    "supplier_id": supplier.name,
                    "supplier_name": supplier.supplier_name,
                    "updated_fields": updated_fields
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "success",
                "message": "ℹ️ No changes detected",
                "data": {
                    "supplier_id": supplier.name,
                    "supplier_name": supplier.supplier_name
                },
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Update Supplier Error", message=str(e))
        return {
            "status": "error",
            "message": f"Update error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def delete_supplier(supplier_id=None, supplier_name=None, force=False):
    """DELETE SUPPLIER (OPTIONALLY WITH FORCE)"""
    try:
        if not supplier_id and not supplier_name:
            return {
                "status": "error",
                "message": "Either supplier_id or supplier_name is required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Find supplier
        if supplier_id:
            supplier = frappe.get_doc('Supplier', supplier_id)
        else:
            suppliers = frappe.get_all('Supplier',
                                     filters={'supplier_name': supplier_name},
                                     fields=['name'])
            if not suppliers:
                return {
                    "status": "error",
                    "message": f"Supplier '{supplier_name}' not found",
                    "timestamp": datetime.now().isoformat()
                }
            supplier = frappe.get_doc('Supplier', suppliers[0]['name'])
        
        # Check for dependencies
        dependencies = []
        
        # Check for Purchase Orders
        po_count = frappe.db.count('Purchase Order', {'supplier': supplier.name})
        if po_count > 0:
            dependencies.append(f"{po_count} Purchase Orders")
        
        # Check for Purchase Invoices
        pi_count = frappe.db.count('Purchase Invoice', {'supplier': supplier.name})
        if pi_count > 0:
            dependencies.append(f"{pi_count} Purchase Invoices")
        
        # Check for Purchase Receipts
        pr_count = frappe.db.count('Purchase Receipt', {'supplier': supplier.name})
        if pr_count > 0:
            dependencies.append(f"{pr_count} Purchase Receipts")
        
        if dependencies and not force:
            return {
                "status": "error",
                "message": "Cannot delete supplier with dependencies",
                "dependencies": dependencies,
                "guidance": "Use force=true to delete anyway",
                "timestamp": datetime.now().isoformat()
            }
        
        # Delete supplier
        supplier_name_for_msg = supplier.supplier_name
        frappe.delete_doc('Supplier', supplier.name, force=bool(force))
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"✅ Supplier '{supplier_name_for_msg}' deleted",
            "data": {
                "supplier_name": supplier_name_for_msg,
                "force_deleted": bool(force),
                "dependencies_ignored": dependencies if force else []
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Delete Supplier Error", message=str(e))
        return {
            "status": "error",
            "message": f"Delete error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def migrate_suppliers_batch(**kwargs):
    """MIGRATE MULTIPLE SUPPLIERS IN BATCH"""
    try:
        data = get_request_data(kwargs)
        
        suppliers_data = data.get('suppliers', [])
        
        if not suppliers_data or not isinstance(suppliers_data, list):
            return {
                "status": "error",
                "message": "Suppliers data must be a list",
                "timestamp": datetime.now().isoformat()
            }
        
        results = {
            "total": len(suppliers_data),
            "success": 0,
            "failed": 0,
            "updated": 0,
            "details": []
        }
        
        for idx, supplier_data in enumerate(suppliers_data):
            try:
                # Check if supplier exists
                supplier_name = supplier_data.get('supplier_name')
                if not supplier_name:
                    results['details'].append({
                        "index": idx,
                        "status": "failed",
                        "message": "Missing supplier_name"
                    })
                    results['failed'] += 1
                    continue
                
                existing = frappe.get_all('Supplier',
                                        filters={'supplier_name': supplier_name},
                                        fields=['name'])
                
                if existing:
                    # Update existing
                    supplier_data['supplier_id'] = existing[0]['name']
                    update_result = update_supplier(**supplier_data)
                    
                    if update_result.get('status') == 'success':
                        results['updated'] += 1
                        results['details'].append({
                            "index": idx,
                            "status": "updated",
                            "supplier_name": supplier_name,
                            "message": "Supplier updated"
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            "index": idx,
                            "status": "failed",
                            "supplier_name": supplier_name,
                            "message": update_result.get('message', 'Update failed')
                        })
                else:
                    # Create new
                    create_result = create_supplier(**supplier_data)
                    
                    if create_result.get('status') == 'success':
                        results['success'] += 1
                        results['details'].append({
                            "index": idx,
                            "status": "created",
                            "supplier_name": supplier_name,
                            "message": "Supplier created"
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            "index": idx,
                            "status": "failed",
                            "supplier_name": supplier_name,
                            "message": create_result.get('message', 'Creation failed')
                        })
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    "index": idx,
                    "status": "error",
                    "message": f"Error: {str(e)[:100]}"
                })
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"✅ Batch migration completed: {results['success']} created, {results['updated']} updated, {results['failed']} failed",
            "data": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Batch Migration Error", message=str(e))
        return {
            "status": "error",
            "message": f"Batch migration error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def get_supplier_stats():
    """GET SUPPLIER STATISTICS"""
    try:
        # Total suppliers
        total_suppliers = frappe.db.count('Supplier')
        
        # Suppliers by type
        suppliers_by_type = frappe.db.sql("""
            SELECT supplier_type, COUNT(*) as count
            FROM `tabSupplier`
            GROUP BY supplier_type
            ORDER BY count DESC
        """, as_dict=True)
        
        # Suppliers by group
        suppliers_by_group = frappe.db.sql("""
            SELECT supplier_group, COUNT(*) as count
            FROM `tabSupplier`
            GROUP BY supplier_group
            ORDER BY count DESC
        """, as_dict=True)
        
        # Suppliers with addresses
        suppliers_with_addresses = frappe.db.sql("""
            SELECT COUNT(DISTINCT dl.link_name) as count
            FROM `tabDynamic Link` dl
            WHERE dl.link_doctype = 'Supplier'
            AND dl.parenttype = 'Address'
        """, as_dict=True)[0]['count']
        
        # Suppliers with contacts
        suppliers_with_contacts = frappe.db.sql("""
            SELECT COUNT(DISTINCT dl.link_name) as count
            FROM `tabDynamic Link` dl
            WHERE dl.link_doctype = 'Supplier'
            AND dl.parenttype = 'Contact'
        """, as_dict=True)[0]['count']
        
        # Recently created suppliers (last 7 days)
        recent_suppliers = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabSupplier`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, as_dict=True)[0]['count']
        
        return {
            "status": "success",
            "data": {
                "total_suppliers": total_suppliers,
                "suppliers_by_type": suppliers_by_type,
                "suppliers_by_group": suppliers_by_group,
                "suppliers_with_addresses": suppliers_with_addresses,
                "suppliers_with_contacts": suppliers_with_contacts,
                "recent_suppliers": recent_suppliers,
                "coverage": {
                    "address_coverage": f"{(suppliers_with_addresses/total_suppliers*100):.1f}%" if total_suppliers > 0 else "0%",
                    "contact_coverage": f"{(suppliers_with_contacts/total_suppliers*100):.1f}%" if total_suppliers > 0 else "0%"
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(title="Supplier Stats Error", message=str(e))
        return {
            "status": "error",
            "message": f"Stats error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def export_suppliers(format='json', include_details=False):
    """EXPORT SUPPLIERS TO VARIOUS FORMATS"""
    try:
        # Get all suppliers
        suppliers = frappe.get_all('Supplier',
                                 fields=['*'],
                                 limit=1000)  # Limit for safety
        
        if format.lower() == 'csv':
            # Simple CSV format
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = ['supplier_name', 'supplier_type', 'tax_id', 'supplier_group',
                     'default_currency', 'payment_terms', 'custom_rfc', 'custom_curp',
                     'custom_phone', 'custom_email']
            writer.writerow(header)
            
            # Write data
            for supplier in suppliers:
                row = [
                    supplier.get('supplier_name', ''),
                    supplier.get('supplier_type', ''),
                    supplier.get('tax_id', ''),
                    supplier.get('supplier_group', ''),
                    supplier.get('default_currency', ''),
                    supplier.get('payment_terms', ''),
                    supplier.get('custom_rfc', ''),
                    supplier.get('custom_curp', ''),
                    supplier.get('custom_phone', ''),
                    supplier.get('custom_email', '')
                ]
                writer.writerow(row)
            
            csv_data = output.getvalue()
            output.close()
            
            return {
                "status": "success",
                "format": "csv",
                "data": csv_data,
                "count": len(suppliers),
                "timestamp": datetime.now().isoformat()
            }
        
        else:  # JSON format (default)
            if include_details and include_details.lower() in ['true', '1', 'yes']:
                detailed_suppliers = []
                for supplier in suppliers:
                    details = get_supplier(supplier_id=supplier['name'])
                    if details.get('status') == 'success':
                        detailed_suppliers.append(details['data'])
                
                export_data = {
                    "metadata": {
                        "export_date": datetime.now().isoformat(),
                        "count": len(detailed_suppliers),
                        "format": "detailed_json"
                    },
                    "suppliers": detailed_suppliers
                }
            else:
                export_data = {
                    "metadata": {
                        "export_date": datetime.now().isoformat(),
                        "count": len(suppliers),
                        "format": "simple_json"
                    },
                    "suppliers": suppliers
                }
            
            return {
                "status": "success",
                "format": "json",
                "data": export_data,
                "count": len(suppliers),
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        frappe.log_error(title="Export Suppliers Error", message=str(e))
        return {
            "status": "error",
            "message": f"Export error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@frappe.whitelist(allow_guest=False)
def supplier_migration_example():
    """EXAMPLE FOR SUPPLIER MIGRATION"""
    return {
        "status": "success",
        "examples": {
            "create_single_supplier": {
                "endpoint": "/api/method/agent.create_supplier",
                "method": "POST",
                "data": {
                    "supplier_name": "QUIMICA CLARIMEX SA DE CV",
                    "supplier_type": "Company",
                    "tax_id": "QCM850101XXX",
                    "supplier_group": "Raw Material",
                    "default_currency": "MXN",
                    "custom_rfc": "QCM850101XXX",
                    "custom_phone": "+52 55 1234 5678",
                    "custom_email": "ventas@quimicaclarimex.com.mx",
                    "addresses": [{
                        "address_title": "Main Office",
                        "address_type": "Billing",
                        "address_line1": "Av. Insurgentes Sur 1234",
                        "address_line2": "Col. Del Valle",
                        "city": "Mexico City",
                        "state": "CDMX",
                        "country": "Mexico",
                        "pincode": "03100",
                        "phone": "+52 55 1234 5678",
                        "is_primary_address": True
                    }],
                    "contacts": [{
                        "first_name": "Juan",
                        "last_name": "Pérez",
                        "designation": "Sales Manager",
                        "email_id": "juan.perez@quimicaclarimex.com.mx",
                        "phone": "+52 55 8765 4321",
                        "is_primary_contact": True
                    }]
                }
            },
            "batch_migration": {
                "endpoint": "/api/method/agent.migrate_suppliers_batch",
                "method": "POST",
                "data": {
                    "suppliers": [
                        {
                            "supplier_name": "Supplier 1",
                            "supplier_type": "Company",
                            "tax_id": "TXI001"
                        },
                        {
                            "supplier_name": "Supplier 2", 
                            "supplier_type": "Individual",
                            "tax_id": "TXI002"
                        }
                    ]
                }
            },
            "get_supplier": {
                "endpoint": "/api/method/agent.get_supplier",
                "method": "GET",
                "parameters": {
                    "supplier_name": "QUIMICA CLARIMEX SA DE CV"
                }
            }
        },
        "timestamp": datetime.now().isoformat()
    }

@frappe.whitelist(allow_guest=False)
def get_documentation():
    """Get API documentation"""
    return {
        "status": "success",
        "api_name": "AMB W TDS Production Batch & Supplier Agent",
        "version": "v5.7-complete",
        "description": "COMPLETE API for FoxPro migration with container_barrels support, Mexico e-invoice compliance, and Supplier Management",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            # Supplier endpoints
            "create_supplier": {
                "method": "POST",
                "description": "Create or update supplier with addresses and contacts"
            },
            "get_supplier": {
                "method": "GET/POST",
                "description": "Get supplier details with addresses and contacts"
            },
            "get_all_suppliers": {
                "method": "GET/POST",
                "description": "Get all suppliers with optional details"
            },
            "search_suppliers": {
                "method": "GET/POST",
                "description": "Search suppliers by name, tax ID, or RFC"
            },
            "update_supplier": {
                "method": "POST",
                "description": "Update existing supplier"
            },
            "delete_supplier": {
                "method": "POST",
                "description": "Delete supplier (with force option)"
            },
            "migrate_suppliers_batch": {
                "method": "POST",
                "description": "Migrate multiple suppliers in batch"
            },
            "get_supplier_stats": {
                "method": "GET",
                "description": "Get supplier statistics and coverage"
            },
            "export_suppliers": {
                "method": "GET",
                "description": "Export suppliers to JSON or CSV"
            },
            # Original batch endpoints
            "process": {
                "method": "POST",
                "description": "Create batch with container_barrels support"
            },
            "migrate_foxpro_invoice": {
                "method": "POST",
                "description": "Create invoices from FoxPro data with Mexico taxes"
            },
            "add_containers_to_existing_batch": {
                "method": "POST",
                "description": "Add containers to existing batch"
            },
            "get_batch_containers": {
                "method": "GET/POST",
                "description": "Get containers for a batch"
            },
            "migrate_foxpro_batch": {
                "method": "POST",
                "description": "Special endpoint for FoxPro migration data"
            },
            "batch_validate_golden": {
                "method": "POST",
                "description": "Validate batch ID against golden number pattern"
            },
            "validate_parameters": {
                "method": "POST",
                "description": "Validate parameters without creating batch"
            },
            "create_demo_batches": {
                "method": "GET",
                "description": "Demo batches endpoint"
            },
            "get_recent_batches_with_details": {
                "method": "GET",
                "description": "Get recent batches with details"
            },
            "fix_all_items_for_sales": {
                "method": "GET",
                "description": "Enable all FoxPro migration items for sales"
            },
            "batch_with_containers_example": {
                "method": "GET",
                "description": "Example API call for creating batch with container_barrels"
            }
        }
    }

# =============================================
# STARTUP MESSAGE (KEEP THIS IMPORTANT SECTION!)
# =============================================
if __name__ != "__main__":
    print("✅ Agent v5.7-complete loaded - Ready for FoxPro & Supplier migration!")
    print("📋 COMPLETE FEATURES:")
    print("   • FoxPro batch migration with container_barrels")
    print("   • Mexico e-invoice tax compliance")
    print("   • Complete supplier CRUD operations")
    print("   • Address and contact management")
    print("   • Batch migration of suppliers")
    print("   • Search and export capabilities")
    print("   • Supplier statistics and coverage reports")
    print("🎯 SUPPLIER ENDPOINTS:")
    print("   • /create_supplier - Create/update supplier")
    print("   • /get_supplier - Get supplier details")
    print("   • /get_all_suppliers - List all suppliers")
    print("   • /migrate_suppliers_batch - Batch migration")
    print("   • /get_supplier_stats - Statistics")
    print("   • /export_suppliers - Export data")
    print("🎯 ORIGINAL BATCH ENDPOINTS (still available):")
    print("   • /process - Create batch with containers")
    print("   • /migrate_foxpro_invoice - Create invoices")
    print("   • /add_containers_to_existing_batch - Add containers")
    print("   • /get_batch_containers - View containers")
    print("   • /migrate_foxpro_batch - FoxPro batch migration")
    print("   • /batch_validate_golden - Validate golden numbers")
    print("   • /validate_parameters - Parameter validation")
