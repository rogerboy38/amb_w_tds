# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, get_datetime, cstr
import json

class BatchAMB(Document):
    """
    Batch AMB - Production Batch Management
    """
    
    def validate(self):
        """Validation before saving"""
        self.validate_production_dates()
        self.validate_quantities()
        self.validate_work_order()
        self.validate_containers()
        self.validate_batch_level_hierarchy()
        self.validate_barrel_weights()
        self.set_item_details()
    
    def before_save(self):
        """Before save hook"""
        self.calculate_totals()
        self.set_batch_naming()
        self.update_container_sequence()
        self.calculate_costs()
        # FIXED: Update planned_qty from work_order_ref if not set
        self.update_planned_qty_from_work_order()
    
    def on_update(self):
        """After update hook"""
        self.sync_with_lote_amb()
        self.update_work_order_status()
        self.log_batch_history()
    
    def on_submit(self):
        """On submit"""
        self.create_stock_entry()
        self.create_lote_amb_if_needed()
        self.update_batch_status('Completed')
        self.notify_stakeholders()
    
    def on_cancel(self):
        """On cancel"""
        self.cancel_stock_entries()
        self.update_batch_status('Cancelled')
    
    def validate_production_dates(self):
        """Validate production dates"""
        if self.production_start_date and self.production_end_date:
            start = get_datetime(self.production_start_date)
            end = get_datetime(self.production_end_date)
            
            if end < start:
                frappe.throw(_("Production end date cannot be before start date"))
    
    def validate_quantities(self):
        """Validate quantities"""
        if self.produced_qty and flt(self.produced_qty) <= 0:
            frappe.throw(_("Produced quantity must be greater than 0"))
        
        # FIXED: Add planned_qty validation
        if self.planned_qty is not None and flt(self.planned_qty) <= 0:
            frappe.throw(_("Planned quantity must be greater than 0"))
    
    def validate_work_order(self):
        """Validate work order reference"""
        if self.work_order and not frappe.db.exists('Work Order', self.work_order):
            frappe.throw(_("Work Order {0} does not exist").format(self.work_order))
    
    def validate_containers(self):
        """Validate container data"""
        if not self.container_barrels:
            return
        
        for idx, container in enumerate(self.container_barrels, 1):
            if not container.container_id:
                container.container_id = f"CNT-{self.name}-{idx:03d}"
    
    def validate_batch_level_hierarchy(self):
        """Validate batch level hierarchy"""
        level = int(self.custom_batch_level or '1')
        
        if level > 1 and not self.parent_batch_amb:
            frappe.throw(_("Parent Batch AMB is required for level {0}").format(level))
    
    def validate_barrel_weights(self):
        """Validate barrel weights"""
        if self.custom_batch_level != '3':
            return
        
        if self.container_barrels:
            for barrel in self.container_barrels:
                if barrel.gross_weight and barrel.tara_weight:
                    net_weight = barrel.gross_weight - barrel.tara_weight
                    if net_weight <= 0:
                        frappe.throw(f'Invalid net weight for barrel {barrel.barrel_serial_number}')
                    barrel.net_weight = net_weight
    
    def set_item_details(self):
        """Set item details"""
        if self.item_to_manufacture:
            item = frappe.get_doc('Item', self.item_to_manufacture)
            self.item_name = item.item_name
            if not self.uom:
                self.uom = item.stock_uom
    
    def calculate_totals(self):
        """Calculate totals"""
        if self.container_barrels:
            self.total_container_qty = sum(flt(c.quantity or 0) for c in self.container_barrels)
            self.total_containers = len(self.container_barrels)
            self.calculate_container_weights()
        else:
            self.total_container_qty = 0
            self.total_containers = 0
    
    def calculate_costs(self):
        """Calculate costs"""
        if not self.calculate_cost:
            return
        
        total_cost = 0
        if self.bom_no:
            total_cost += self.get_bom_cost()
        if self.labor_cost:
            total_cost += flt(self.labor_cost)
        if self.overhead_cost:
            total_cost += flt(self.overhead_cost)
        
        self.total_batch_cost = total_cost
        if self.produced_qty:
            self.cost_per_unit = total_cost / flt(self.produced_qty)
    
    def get_bom_cost(self):
        """Get BOM cost"""
        if not self.bom_no:
            return 0
        bom = frappe.get_doc('BOM', self.bom_no)
        return flt(bom.total_cost) * flt(self.produced_qty)
    
    def calculate_container_weights(self):
        """Calculate container weights"""
        if not self.container_barrels:
            self.total_gross_weight = 0
            self.total_tara_weight = 0
            self.total_net_weight = 0
            self.barrel_count = 0
            return
        
        total_gross = total_tara = total_net = barrel_count = 0
        
        for barrel in self.container_barrels:
            if barrel.gross_weight:
                total_gross += flt(barrel.gross_weight)
            if barrel.tara_weight:
                total_tara += flt(barrel.tara_weight)
            if barrel.net_weight:
                total_net += flt(barrel.net_weight)
            if barrel.barrel_serial_number:
                barrel_count += 1
        
        self.total_gross_weight = total_gross
        self.total_tara_weight = total_tara
        self.total_net_weight = total_net
        self.barrel_count = barrel_count
    
    def set_batch_naming(self):
        """Set batch naming"""
        pass
    
    def update_container_sequence(self):
        """Update container sequence"""
        for idx, container in enumerate(self.container_barrels, 1):
            container.idx = idx
    
    def sync_with_lote_amb(self):
        """Sync with Lote AMB"""
        pass
    
    def update_work_order_status(self):
        """Update work order status"""
        pass
    
    def log_batch_history(self):
        """Log batch history"""
        pass
    
    def create_stock_entry(self):
        """Create stock entry"""
        pass
    
    def create_lote_amb_if_needed(self):
        """Create Lote AMB"""
        pass
    
    def cancel_stock_entries(self):
        """Cancel stock entries"""
        pass
    
    def update_batch_status(self, status):
        """Update status"""
        self.db_set('batch_status', status)
    
    def notify_stakeholders(self):
        """Notify stakeholders"""
        pass
    
    # FIXED: Updated method to work with both work_order and work_order_ref
    def update_planned_qty_from_work_order(self):
        """Update planned_qty from Work Order - FIXED VERSION"""
        try:
            work_order_name = None
            
            # Check both possible field names
            if self.work_order_ref:
                work_order_name = self.work_order_ref
            elif self.work_order:
                work_order_name = self.work_order
            
            if work_order_name:
                wo_doc = frappe.get_doc('Work Order', work_order_name)
                if hasattr(wo_doc, 'qty') and wo_doc.qty and flt(wo_doc.qty) > 0:
                    self.planned_qty = flt(wo_doc.qty)
                    return True
        except:
            frappe.log_error(f"Error updating planned_qty from work order: {str(frappe.get_traceback())}")
            pass
        return False


# ==================== MANUFACTURING BUTTON METHODS ====================

@frappe.whitelist()
def create_bom_with_wizard(batch_name, options=None):
    """Create BOM with wizard options - MAIN MANUFACTURING BUTTON"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not batch.item_to_manufacture:
            return {"success": False, "message": "No item to manufacture specified"}
        
        # Parse options
        if options and isinstance(options, str):
            options = json.loads(options)
        options = options or {}
        
        # FIXED: Use planned_qty with fallback
        bom_quantity = batch.planned_qty or batch.batch_quantity or 1
        
        # Create BOM
        bom_data = {
            "item": batch.item_to_manufacture,
            "quantity": 18000,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "custom_golden_number": batch.custom_golden_number,
            "custom_batch_reference": batch.name
        }
        
        bom = frappe.new_doc("BOM")
        bom.update(bom_data)
        
        # Add items based on options
        idx = 1
        
        # Add packaging if selected
        if options.get('include_packaging') and batch.primary_packaging:
            bom.append('items', {
                'item_code': batch.primary_packaging,
                'qty': batch.packages_count or 1,
                'uom': 'Nos'
            })
            idx += 1
        
        # Add raw materials placeholder - FIXED: Use bom_quantity
        bom.append('items', {
            'item_code': 'RAW-MATERIAL-PLACEHOLDER',
            'qty': bom_quantity,
            'uom': 'Kg'
        })
        
        bom.insert()
        
        # Link BOM to batch
        batch.bom_template = bom.name
        batch.save()
        
        return {
            "success": True,
            "bom_name": bom.name,
            "golden_number": batch.custom_golden_number,
            "message": f"BOM {bom.name} created successfully with Golden Number {batch.custom_golden_number}"
        }
        
    except Exception as e:
        frappe.log_error(f"BOM Creation Error: {str(e)}")
        return {"success": False, "message": f"Error creating BOM: {str(e)}"}

@frappe.whitelist()
def calculate_material_requirements(batch_name):
    """Calculate material requirements for MRP"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        materials = {
            "raw_materials": [],
            "packaging": [],
            "utilities": [],
            "labor": [],
            "total_cost": 0
        }
        
        # Packaging materials
        if batch.primary_packaging:
            materials["packaging"].append({
                "item": batch.primary_packaging,
                "quantity": batch.packages_count or 1,
                "uom": "Nos"
            })
        
        return {"success": True, "materials": materials}
        
    except Exception as e:
        frappe.log_error(f"MRP Calculation Error: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def create_work_order_from_batch(batch_name):
    """Create Work Order from Batch"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not batch.item_to_manufacture:
            return {"success": False, "message": "No item to manufacture specified"}
        
        wo = frappe.new_doc("Work Order")
        wo.production_item = batch.item_to_manufacture
        wo.qty = batch.planned_qty or batch.batch_quantity or 1
        wo.bom_no = batch.bom_template
        wo.planned_start_date = batch.production_start_date
        wo.company = batch.company or frappe.defaults.get_user_default("Company")
        
        wo.insert()
        
        # Link back to batch
        batch.work_order_ref = wo.name
        batch.save()
        
        return {
            "success": True,
            "work_order": wo.name,
            "message": f"Work Order {wo.name} created successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Work Order Creation Error: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def assign_golden_number_to_batch(batch_name):
    """Manual trigger for Golden Number assignment"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not batch.custom_golden_number:
            import random
            import string
            # Generate a golden number (you can customize this logic)
            golden_number = ''.join(random.choices(string.digits, k=10))
            batch.custom_golden_number = golden_number
            batch.save()
            
            return {
                "success": True,
                "golden_number": batch.custom_golden_number,
                "message": f"Golden Number {batch.custom_golden_number} assigned successfully"
            }
        
        return {
            "success": True, 
            "golden_number": batch.custom_golden_number,
            "message": f"Golden Number already assigned: {batch.custom_golden_number}"
        }
        
    except Exception as e:
        frappe.log_error(f"Golden Number Assignment Error: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def update_planned_qty_from_work_order(batch_name):
    """Manual trigger to update planned quantity from Work Order"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        work_order_name = None
        if batch.work_order_ref:
            work_order_name = batch.work_order_ref
        elif batch.work_order:
            work_order_name = batch.work_order
        
        if work_order_name:
            wo = frappe.get_doc('Work Order', work_order_name)
            batch.planned_qty = wo.qty
            batch.save()
            
            return {
                "success": True,
                "planned_qty": batch.planned_qty,
                "message": f"Planned quantity updated to {batch.planned_qty}"
            }
        else:
            return {"success": False, "message": "No work order linked to this batch"}
        
    except Exception as e:
        frappe.log_error(f"Planned Qty Update Error: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def calculate_batch_cost(batch_name):
    """Calculate batch cost for the Calculate Cost button"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        # Simple cost calculation - you can enhance this with actual BOM costs
        material_cost = batch.material_cost or 0
        labor_cost = batch.labor_cost or 0
        overhead_cost = batch.overhead_cost or 0
        
        total_batch_cost = material_cost + labor_cost + overhead_cost
        
        # Calculate cost per unit
        batch_quantity = batch.batch_quantity or 1
        cost_per_unit = total_batch_cost / batch_quantity if batch_quantity > 0 else 0
        
        return {
            "total_batch_cost": total_batch_cost,
            "cost_per_unit": cost_per_unit
        }
        
    except Exception as e:
        frappe.log_error(f"Batch Cost Calculation Error: {str(e)}")
        return {
            "total_batch_cost": 0,
            "cost_per_unit": 0
        }

@frappe.whitelist()
def duplicate_batch(source_name):
    """Duplicate a batch - for Duplicate Batch button"""
    try:
        source_batch = frappe.get_doc("Batch AMB", source_name)
        new_batch = frappe.copy_doc(source_batch)
        
        # Clear references that shouldn't be duplicated
        new_batch.work_order_ref = None
        new_batch.stock_entry_reference = None
        new_batch.lote_amb_reference = None
        new_batch.custom_generated_batch_name = None
        new_batch.custom_golden_number = None
        
        new_batch.insert()
        
        return new_batch.name
        
    except Exception as e:
        frappe.log_error(f"Batch Duplication Error: {str(e)}")
        frappe.throw(f"Error duplicating batch: {str(e)}")


# ==================== BOM CREATION METHODS ====================

@frappe.whitelist()
def check_bom_exists(batch_name):
    """Check if BOM already exists for this batch"""
    batch = frappe.get_doc('Batch AMB', batch_name)
    
    existing_bom = frappe.db.get_value('BOM Creator', 
        {'project': batch_name}, 
        ['name', 'item_code'])
    
    if existing_bom:
        return {
            'exists': True,
            'bom_name': existing_bom[0],
            'item_code': existing_bom[1]
        }
    
    return {'exists': False}


# ==================== OTHER WHITELISTED METHODS ====================

@frappe.whitelist()
def get_work_order_details(work_order):
    """Get work order details"""
    wo = frappe.get_doc('Work Order', work_order)
    return {
        'item_to_manufacture': wo.production_item,
        'planned_qty': wo.qty,
        'company': wo.company
    }


@frappe.whitelist()
def get_available_containers(warehouse=None):
    """Get available containers"""
    return []

@frappe.whitelist()
def get_running_batch_announcements(include_companies=True, include_plants=True, include_quality=True):
    """Get running batch announcements for widget"""
    try:
        batches = frappe.get_all(
            'Batch AMB',
            filters={'docstatus': ['!=', 2]},
            fields=[
                'name', 'title', 'item_to_manufacture', 'item_code',
                'wo_item_name', 'quality_status', 'target_plant',
                'production_plant_name', 'custom_plant_code',
                'custom_batch_level', 'barrel_count', 'total_net_weight',
                'wo_start_date', 'modified', 'creation'
            ],
            order_by='modified desc',
            limit=50
        )
        
        if not batches:
            return {
                'success': True,
                'message': 'No active batches',
                'announcements': [],
                'grouped_announcements': {},
                'stats': {'total': 0}
            }
        
        announcements = []
        grouped = {}
        stats = {'total': len(batches), 'high_priority': 0, 'quality_check': 0, 'container_level': 0}
        
        for batch in batches:
            company = batch.production_plant_name or batch.target_plant or 'Unknown'
            
            announcement = {
                'name': batch.name,
                'title': batch.title or batch.name,
                'batch_code': batch.name,
                'item_code': batch.item_to_manufacture or batch.item_code or 'N/A',
                'status': 'Active',
                'company': company,
                'level': batch.custom_batch_level or 'Batch',
                'priority': 'high' if batch.quality_status == 'Failed' else 'medium',
                'quality_status': batch.quality_status or 'Pending',
                'content': f"Item: {batch.wo_item_name or batch.item_code or 'N/A'}\nPlant: {batch.custom_plant_code or 'N/A'}\nWeight: {batch.total_net_weight or 0}\nBarrels: {batch.barrel_count or 0}",
                'message': f"Level {batch.custom_batch_level or '?'} batch in production",
                'modified': str(batch.modified) if batch.modified else '',
                'creation': str(batch.creation) if batch.creation else ''
            }
            
            announcements.append(announcement)
            
            if batch.quality_status == 'Failed':
                stats['high_priority'] += 1
            if batch.quality_status in ['Pending', 'In Testing']:
                stats['quality_check'] += 1
            if batch.custom_batch_level == '3':
                stats['container_level'] += 1
            
            if include_companies:
                plant = batch.custom_plant_code or '1'
                if company not in grouped:
                    grouped[company] = {}
                if plant not in grouped[company]:
                    grouped[company][plant] = []
                grouped[company][plant].append(announcement)
        
        return {
            'success': True,
            'announcements': announcements,
            'grouped_announcements': grouped,
            'stats': stats
        }
        
    except Exception as e:
        import traceback
        frappe.log_error(f"Widget error: {str(e)}\n{traceback.format_exc()}", "Batch Widget Error")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load batch data'
        }

@frappe.whitelist()
def get_packaging_from_sales_order(batch_name):
    """Get packaging info from Sales Order and map to Item Codes"""
    try:
        batch = frappe.get_doc('Batch AMB', batch_name)
        
        # Try multiple methods to find sales order
        sales_order = None
        
        # Method 1: Check sales_order_related field (auto-fetched from work_order_ref)
        if batch.sales_order_related:
            sales_order = batch.sales_order_related
        
        # Method 2: Get from work_order_ref.sales_order manually
        if not sales_order and batch.work_order_ref:
            try:
                wo = frappe.get_doc('Work Order', batch.work_order_ref)
                if hasattr(wo, 'sales_order') and wo.sales_order:
                    sales_order = wo.sales_order
            except Exception as e:
                frappe.log_error(f"Error fetching WO sales order: {str(e)}")
        
        # Method 3: Search for Work Orders linked to this batch's item
        if not sales_order and batch.item_to_manufacture:
            try:
                wo_list = frappe.get_all('Work Order',
                    filters={
                        'production_item': batch.item_to_manufacture,
                        'docstatus': ['!=', 2]
                    },
                    fields=['name', 'sales_order'],
                    order_by='creation desc',
                    limit=1
                )
                if wo_list and wo_list[0].get('sales_order'):
                    sales_order = wo_list[0]['sales_order']
            except Exception as e:
                frappe.log_error(f"Error searching WO for sales order: {str(e)}")
        
        if not sales_order:
            return {
                'success': False,
                'message': 'No Sales Order linked to this batch',
                'primary': None,
                'secondary': None,
                'net_weight': 0,
                'packages_count': 1
            }
        
        so = frappe.get_doc('Sales Order', sales_order)
        
        # Smart mapping from text to Item Code
        primary_item = map_packaging_text_to_item(so.custom_tipo_empaque)
        secondary_item = map_packaging_text_to_item(so.empaque_secundario) if so.empaque_secundario else None
        
        # Extract net weight (handle different formats: "5 Kg", "220", etc.)
        net_weight = parse_weight_from_text(so.custom_peso_neto) if so.custom_peso_neto else 220
        
        # Calculate package count
        total_weight = batch.total_net_weight or batch.total_quantity or 1000
        packages_count = int(total_weight / net_weight) if net_weight > 0 else 1
        
        return {
            'success': True,
            'primary': primary_item,
            'primary_name': frappe.db.get_value('Item', primary_item, 'item_name') if primary_item else None,
            'primary_text': so.custom_tipo_empaque,
            'secondary': secondary_item,
            'secondary_name': frappe.db.get_value('Item', secondary_item, 'item_name') if secondary_item else None,
            'secondary_text': so.empaque_secundario,
            'net_weight': net_weight,
            'packages_count': packages_count,
            'sales_order': so.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting packaging: {str(e)}", "Packaging Fetch Error")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to fetch packaging: {str(e)}'
        }


def map_packaging_text_to_item(packaging_text):
    """Smart mapping from free text to Item Code"""
    if not packaging_text:
        return None
    
    text_lower = packaging_text.lower()
    
    # Dictionary of keywords → Item Codes
    PACKAGING_MAP = {
        # Barrels
        '220l': 'E001',
        '220 l': 'E001',
        'barrel blue': 'E001',
        'barrel 220': 'E001',
        'polyethylene barrel': 'E002',
        'reused barrel': 'E002',
        
        # Drums
        '25kg': 'E003',
        '25 kg': 'E003',
        '25kg drum': 'E003',
        'drum 25': 'E003',
        '10kg': 'E004',
        '10 kg': 'E004',
        '10kg drum': 'E004',
        'drum 10': 'E004',
        
        # Jugs
        '20l': 'E005',
        '20 l': 'E005',
        'jug': 'E005',
        'white jug': 'E005',
        
        # Pallets
        'tarima': 'E006',
        'pallet 44': 'E006',
        'pino real': 'E006',
        'euro pallet': 'E007',
        'euro': 'E007',
        'reused pallet': 'E008',
        '44x44': 'E008',
        
        # Bags
        'bolsa': 'E009',
        'poly bag': 'E009',
        'polietileno': 'E009',
        '30x60': 'E009',
        'bag': 'E009'
    }
    
    # Try exact keyword matching
    for keyword, item_code in PACKAGING_MAP.items():
        if keyword in text_lower:
            return item_code
    
    # Fuzzy search in Item master
    items = frappe.get_all('Item',
        filters={
            'item_group': ['in', ['FG Packaging Materials', 'SFG Packaging Materials', 'Raw Materials']],
            'disabled': 0,
            'item_name': ['like', f'%{packaging_text.split()[0]}%']
        },
        fields=['name', 'item_name'],
        limit=1
    )
    
    if items:
        return items[0].name
    
    # Default fallback
    return 'E001'  # 220L Barrel as default


def parse_weight_from_text(weight_text):
    """Parse weight from text like '5 Kg', '220', '10.5 kg'"""
    if not weight_text:
        return 0
    
    import re
    # Extract numbers from text
    numbers = re.findall(r'\d+\.?\d*', str(weight_text))
    
    if numbers:
        return float(numbers[0])
    
    return 0

@frappe.whitelist()
def generate_batch_code(parent_batch=None, batch_level=None, work_order=None):
    """Generate batch code for automatic naming"""
    try:
        import random
        import string
        
        if batch_level == '1':
            # Level 1 - Root batch
            code = f"BATCH-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        elif batch_level == '2' and parent_batch:
            # Level 2 - Child of level 1
            parent_code = frappe.db.get_value("Batch AMB", parent_batch, "custom_generated_batch_name") or "PARENT"
            code = f"{parent_code}-SUB"
        elif batch_level == '3' and parent_batch:
            # Level 3 - Container level
            parent_code = frappe.db.get_value("Batch AMB", parent_batch, "custom_generated_batch_name") or "PARENT"
            code = f"{parent_code}-CONT"
        else:
            code = f"BATCH-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        
        return {"code": code}
        
    except Exception as e:
        frappe.log_error(f"Batch Code Generation Error: {str(e)}")
        return {"code": f"BATCH-ERROR-{str(e)[:10]}"}

@frappe.whitelist()
def get_work_order_data(work_order):
    """Get work order data for batch reference"""
    try:
        wo = frappe.get_doc("Work Order", work_order)
        return {
            "production_item": wo.production_item,
            "qty": wo.qty,
            "bom_no": wo.bom_no,
            "company": wo.company,
            "status": wo.status,
            "planned_start_date": wo.planned_start_date
        }
    except Exception as e:
        frappe.log_error(f"Work Order Data Error: {str(e)}")
        return None
