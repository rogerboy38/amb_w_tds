# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
import json
import re
import hashlib
import random
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, now_datetime

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
            from frappe.utils import get_datetime
            start = get_datetime(self.production_start_date)
            end = get_datetime(self.production_end_date)
            
            if end < start:
                frappe.throw(_("Production end date cannot be before start date"))
    
    def validate_quantities(self):
        """Validate quantities"""
        if self.produced_qty and flt(self.produced_qty) <= 0:
            frappe.throw(_("Produced quantity must be greater than 0"))
    
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

# ==================== BOM CREATION WITH DUPLICATE PROTECTION ====================

@frappe.whitelist()
def create_bom_with_wizard(batch_name, options):
    """Create STANDARD BOM with wizard options - DUPLICATE PROTECTED"""
    try:
        import json
        
        if isinstance(options, str):
            options = json.loads(options)
        
        batch = frappe.get_doc('Batch AMB', batch_name)
        
        item_code = batch.item_to_manufacture or batch.current_item_code
        if not item_code:
            frappe.throw(_('Item Code not found in batch'))
        
        # Check if BOM already exists for this batch
        existing = check_bom_exists(batch_name)
        if existing.get('exists'):
            frappe.throw(_('BOM already exists for this batch: {0}').format(existing['bom_name']))
        
        # Use STANDARD BOM
        bom = frappe.new_doc("BOM")
        
        # Set standard BOM fields
        bom.item = item_code
        bom.item_name = frappe.db.get_value('Item', item_code, 'item_name') or item_code
        bom.quantity = get_batch_quantity(batch)
        bom.uom = get_item_uom(item_code)
        bom.company = get_company(batch)
        bom.batch_amb = batch_name
        bom.is_active = 1
        bom.with_operations = 0
        
        # Set BOM type
        bom.bom_type = "Product BOM"
        bom.bom_level = 0
        
        # Generate guaranteed unique BOM name
        bom_name = generate_guaranteed_unique_bom_name(batch)
        bom.name = bom_name
        
        # Add items based on options
        add_bom_items_based_on_options(bom, batch, options)
        
        # Save BOM
        bom.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.logger().info(f"✅ BOM {bom.name} created successfully for batch {batch_name}")
        
        return {
            'success': True,
            'bom_name': bom.name,
            'item_code': bom.item,
            'qty': bom.quantity,
            'uom': bom.uom,
            'item_count': len(bom.items),
            'batch_reference': batch_name,
            'doctype': 'BOM',
            'message': 'BOM created successfully'
        }
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = f"BOM creation failed for batch {batch_name}: {str(e)}"
        frappe.log_error(error_msg, "BOM Creation")
        frappe.throw(_("Failed to create BOM: {0}").format(str(e)))

def generate_guaranteed_unique_bom_name(batch):
    """Generate guaranteed unique BOM name"""
    base_identifier = batch.title or batch.custom_generated_batch_name or batch.name
    
    # Clean the base identifier
    base_identifier_clean = re.sub(r'[^a-zA-Z0-9-]', '-', base_identifier)
    
    # Create base name
    base_name = f"BOM-{base_identifier_clean}"
    
    # Add timestamp for uniqueness
    timestamp = now_datetime().strftime("%Y%m%d-%H%M%S")
    candidate_name = f"{base_name}-{timestamp}"
    
    # Ensure name length is within limits
    max_length = 140
    if len(candidate_name) > max_length:
        # Truncate and add hash
        name_hash = hashlib.md5(candidate_name.encode()).hexdigest()[:8]
        candidate_name = candidate_name[:max_length-9] + "-" + name_hash
    
    # Final uniqueness check with retry
    final_name = candidate_name
    counter = 1
    while frappe.db.exists("BOM", final_name) and counter <= 10:
        final_name = f"{candidate_name}-{counter}"
        counter += 1
    
    if counter > 10:
        # Last resort: use random number
        final_name = f"{candidate_name}-{random.randint(10000, 99999)}"
    
    return final_name

def add_bom_items_based_on_options(bom, batch, options):
    """Add items to BOM based on wizard options"""
    # Add containers if requested
    if options.get('include_containers') and hasattr(batch, 'container_barrels') and batch.container_barrels:
        for barrel in batch.container_barrels:
            if barrel.net_weight and barrel.net_weight > 0:
                bom.append('items', {
                    'item_code': determine_container_item_code(barrel),
                    'qty': barrel.net_weight,
                    'uom': 'Kg',
                    'rate': 0
                })
    
    # Add packaging if requested
    if options.get('include_packaging'):
        primary_pkg = options.get('primary_packaging')
        if primary_pkg:
            bom.append('items', {
                'item_code': primary_pkg,
                'qty': cint(options.get('packages_count', 1)),
                'uom': 'Nos',
                'rate': 0
            })
    
    # Add utilities if requested
    if options.get('include_utilities'):
        kpi_factors = get_latest_kpi_factors_helper()
        if kpi_factors:
            qty_kg = bom.quantity or 1000
            
            water_cost = kpi_factors.get('Water Cost per Kg Concentrate', 0)
            if water_cost:
                bom.append('items', {
                    'item_code': 'WATER',
                    'qty': qty_kg,
                    'uom': 'Kg',
                    'rate': water_cost
                })
            
            energy_cost = kpi_factors.get('Energy Cost per kg Concentrate', 0)
            if energy_cost:
                bom.append('items', {
                    'item_code': 'ELECTRIC',
                    'qty': qty_kg * 0.5,
                    'uom': 'kWh',
                    'rate': energy_cost
                })
    
    # Add labor if requested
    if options.get('include_labor'):
        kpi_factors = get_latest_kpi_factors_helper()
        mo_cost = kpi_factors.get('MO Cost per kg concentrate', 0)
        if mo_cost:
            qty_kg = bom.quantity or 1000
            bom.append('items', {
                'item_code': 'MO-LABOR',
                'qty': qty_kg,
                'uom': 'Kg',
                'rate': mo_cost
            })
    
    # Add product-specific items
    product_type = options.get('product_type', 'Juice')
    if product_type == 'Juice':
        bom.append('items', {
            'item_code': 'M033',
            'qty': (bom.quantity or 1000) * 10.76,
            'uom': 'Kg',
            'rate': 1.4
        })
    elif product_type == 'Mix':
        bom.append('items', {
            'item_code': 'MIX-BASE-FORMULA',
            'qty': 1,
            'uom': 'Kg',
            'rate': 0
        })

@frappe.whitelist()
def check_bom_exists(batch_name):
    """Check if BOM already exists for this batch"""
    try:
        # Check in standard BOM
        bom_exists = frappe.db.exists("BOM", {"batch_amb": batch_name})
        if bom_exists:
            bom = frappe.get_doc("BOM", bom_exists)
            return {
                "exists": True, 
                "bom_name": bom.name,
                "item_code": bom.item,
                "created_date": bom.creation
            }
        
        return {"exists": False, "bom_name": None}
    except Exception as e:
        frappe.log_error(f"Error in check_bom_exists: {str(e)}")
        return {"exists": False, "bom_name": None}

def get_batch_quantity(batch):
    """Get batch quantity for BOM"""
    try:
        if hasattr(batch, 'total_net_weight') and batch.total_net_weight:
            return batch.total_net_weight
        elif hasattr(batch, 'batch_quantity') and batch.batch_quantity:
            return batch.batch_quantity
        elif hasattr(batch, 'produced_qty') and batch.produced_qty:
            return batch.produced_qty
        else:
            return 1000
    except:
        return 1000

def get_item_uom(item_code):
    """Get UOM from item"""
    if item_code:
        uom = frappe.db.get_value('Item', item_code, 'stock_uom')
        if uom:
            return uom
    return 'Kg'

def get_company(batch):
    """Get company"""
    if hasattr(batch, 'company') and batch.company:
        return batch.company
    return frappe.defaults.get_user_default("Company")

def determine_container_item_code(barrel):
    """Determine container item code"""
    if hasattr(barrel, 'packaging_type') and barrel.packaging_type:
        if frappe.db.exists('Item', barrel.packaging_type):
            return barrel.packaging_type
    return 'CONTAINER-GENERIC'

def get_latest_kpi_factors_helper():
    """Get KPI factors"""
    kpi_docs = frappe.get_all('AMB KPI FACTORS',
        fields=['name'],
        order_by='creation desc',
        limit=1)
    
    if not kpi_docs:
        return {}
    
    try:
        kpi = frappe.get_doc('AMB KPI FACTORS', kpi_docs[0].name)
        factors = {}
        
        if hasattr(kpi, 'kpi_factors'):
            for row in kpi.kpi_factors:
                factors[row.factor_name] = flt(row.calculated_factor_value or row.factor_value)
        
        return factors
    except:
        return {}

# ==================== OTHER WHITELISTED METHODS ====================

@frappe.whitelist()
def get_work_order_details(work_order):
    """Get work order details"""
    try:
        wo = frappe.get_doc('Work Order', work_order)
        return {
            'item_to_manufacture': wo.production_item,
            'planned_qty': wo.qty,
            'company': wo.company
        }
    except Exception as e:
        return {'error': f'Work order not found: {str(e)}'}

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
        
        if not batch.sales_order_related:
            return {
                'success': False,
                'message': 'No Sales Order linked to this batch',
                'primary': None,
                'secondary': None,
                'net_weight': 0,
                'packages_count': 1
            }
        
        so = frappe.get_doc('Sales Order', batch.sales_order_related)
        
        # Smart mapping from text to Item Code
        primary_item = map_packaging_text_to_item(so.custom_tipo_empaque)
        secondary_item = map_packaging_text_to_item(so.empaque_secundario) if so.empaque_secundario else None
        
        # Extract net weight (handle different formats: "5 Kg", "220", etc.)
        net_weight = parse_weight_from_text(so.custom_peso_neto) if so.custom_peso_neto else 220
        
        # Calculate package count
        total_weight = batch.total_net_weight or batch.total_net_weight or 1000
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
    
    # Extract numbers from text
    numbers = re.findall(r'\d+\.?\d*', str(weight_text))
    
    if numbers:
        return float(numbers[0])
    
    return 0

# ==================== MANUFACTURING BUTTON METHODS ====================

@frappe.whitelist()
def show_bom_creation_button(batch_name):
    """Check if BOM creation button should be shown"""
    try:
        if not frappe.db.exists('Batch AMB', batch_name):
            return {'show_button': False, 'reason': 'Batch not found'}
        
        batch = frappe.get_doc('Batch AMB', batch_name)
        
        if not batch.item_to_manufacture:
            return {'show_button': False, 'reason': 'No manufacturing item specified'}
        
        existing_bom = frappe.db.exists("BOM", {"batch_amb": batch_name})
        if existing_bom:
            return {'show_button': False, 'reason': f'BOM already exists: {existing_bom}'}
        
        return {'show_button': True, 'reason': 'Ready for BOM creation'}
        
    except Exception as e:
        return {'show_button': False, 'reason': f'Error: {str(e)}'}

@frappe.whitelist()
def get_bom_creation_status(batch_name):
    """Get BOM creation status for UI"""
    try:
        existing_bom = frappe.db.exists("BOM", {"batch_amb": batch_name})
        
        if existing_bom:
            bom = frappe.get_doc("BOM", existing_bom)
            return {
                'has_bom': True,
                'bom_name': bom.name,
                'item_count': len(bom.items) if hasattr(bom, 'items') else 0,
                'created_date': bom.creation
            }
        else:
            return {
                'has_bom': False,
                'bom_name': None,
                'ready_for_creation': True
            }
            
    except Exception as e:
        return {'has_bom': False, 'error': str(e)}
