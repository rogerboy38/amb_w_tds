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
        # Your existing validations
        self.validate_batch_items()  # Add this line
    
    def validate_batch_items(self):
        """Validate batch items for BOM generation"""
        if self.batch_items:
            for item in self.batch_items:
                if not item.item_code or flt(item.quantity) <= 0:
                    frappe.throw(_("Invalid item or quantity in batch items"))
    
    def generate_mrp_bom(self):
        """Generate MRP BOM from batch items"""
        try:
            if not self.batch_items:
                frappe.throw(_("No items in batch to generate BOM"))
            
            # Get main product item
            main_item = self.get_main_product_item()
            if not main_item:
                frappe.throw(_("Could not determine main product item"))
            
            # Create BOM
            bom = frappe.new_doc("BOM")
            bom.item = main_item
            bom.quantity = 1
            bom.is_active = 1
            bom.is_default = 1
            bom.batch_amb_reference = self.name
            bom.with_operations = 0
            
            # Add items from batch
            for item in self.batch_items:
                rate = item.rate or frappe.db.get_value("Item", item.item_code, "valuation_rate") or 0
                bom.append("items", {
                    "item_code": item.item_code,
                    "qty": item.quantity,
                    "uom": item.uom or frappe.db.get_value("Item", item.item_code, "stock_uom"),
                    "rate": rate,
                    "amount": flt(item.quantity) * flt(rate),
                    "include_item_in_manufacturing": 1
                })
            
            bom.insert(ignore_permissions=True)
            
            # Update batch with BOM reference
            self.db_set('bom_reference', bom.name)
            if hasattr(self, 'bom_status'):
                self.db_set('bom_status', 'MRP BOM Created')
            
            frappe.db.commit()
            
            frappe.msgprint(_("MRP BOM {0} created successfully").format(bom.name))
            return bom.name
            
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"BOM Creation Error: {str(e)}")
            frappe.throw(_("Failed to create BOM: {0}").format(str(e)))
    
    def get_main_product_item(self):
        """Determine the main product item for BOM"""
        # Priority: main_item field > first batch item > current_item_code
        if hasattr(self, 'main_item') and self.main_item:
            return self.main_item
        elif self.batch_items and self.batch_items[0].item_code:
            return self.batch_items[0].item_code
        elif hasattr(self, 'current_item_code') and self.current_item_code:
            return self.current_item_code
        return None

    # KEEP ALL YOUR EXISTING METHODS - they should remain as-is
    def validate_production_dates(self):
        """Keep your existing method"""
        pass
    
    def validate_quantities(self):
        """Keep your existing method"""
        pass
    
    def validate_work_order(self):
        """Keep your existing method"""
        pass
    
    def validate_containers(self):
        """Keep your existing method"""
        pass
    
    def validate_batch_level_hierarchy(self):
        """Keep your existing method"""
        pass
    
    def validate_barrel_weights(self):
        """Keep your existing method"""
        pass
    
    def set_item_details(self):
        """Keep your existing method"""
        pass
    
    def before_save(self):
        """Keep your existing method"""
        pass
    
    def calculate_totals(self):
        """Keep your existing method"""
        pass
    
    def set_batch_naming(self):
        """Keep your existing method"""
        pass
    
    def update_container_sequence(self):
        """Keep your existing method"""
        pass
    
    def calculate_costs(self):
        """Keep your existing method"""
        pass
    
    def on_update(self):
        """Keep your existing method"""
        pass
    
    def sync_with_lote_amb(self):
        """Keep your existing method"""
        pass
    
    def update_work_order_status(self):
        """Keep your existing method"""
        pass
    
    def log_batch_history(self):
        """Keep your existing method"""
        pass
    
    def on_submit(self):
        """Keep your existing method"""
        pass
    
    def create_stock_entry(self):
        """Keep your existing method"""
        pass
    
    def create_lote_amb_if_needed(self):
        """Keep your existing method"""
        pass
    
    def update_batch_status(self, status):
        """Keep your existing method"""
        pass
    
    def notify_stakeholders(self):
        """Keep your existing method"""
        pass
    
    def on_cancel(self):
        """Keep your existing method"""
        pass
    
    def cancel_stock_entries(self):
        """Keep your existing method"""
        pass

# API METHODS - ADD THESE AT THE BOTTOM
@frappe.whitelist()
def generate_mrp_bom(batch_name):
    """API endpoint to generate MRP BOM"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        bom_name = batch.generate_mrp_bom()
        
        return {
            "success": True,
            "message": _("MRP BOM {0} created successfully").format(bom_name),
            "bom_name": bom_name
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def generate_standard_bom(batch_name):
    """Create Standard BOM from MRP BOM"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not batch.bom_reference:
            return {"success": False, "message": "No MRP BOM found. Please generate MRP BOM first."}
        
        # Copy MRP BOM to create Standard BOM
        mrp_bom = frappe.get_doc("BOM", batch.bom_reference)
        standard_bom = frappe.copy_doc(mrp_bom)
        
        standard_bom.bom_type = "Standard"
        standard_bom.batch_amb_reference = batch_name
        standard_bom.is_default = 1
        
        # Finalize rates for standard BOM
        for item in standard_bom.items:
            standard_rate = frappe.db.get_value("Item", item.item_code, "standard_rate")
            if standard_rate:
                item.rate = standard_rate
                item.amount = flt(item.qty) * flt(standard_rate)
        
        standard_bom.insert(ignore_permissions=True)
        
        # Update batch
        batch.db_set('standard_bom_reference', standard_bom.name)
        if hasattr(batch, 'bom_status'):
            batch.db_set('bom_status', 'Standard BOM Created')
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Standard BOM {0} created successfully").format(standard_bom.name),
            "bom_name": standard_bom.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Standard BOM Creation Error: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def get_bom_cost_breakdown(bom_name):
    """Get BOM cost breakdown"""
    try:
        bom = frappe.get_doc("BOM", bom_name)
        
        total_material_cost = sum(flt(item.amount) for item in bom.items)
        operation_cost = bom.operation_cost or 0
        total_cost = total_material_cost + operation_cost
        cost_per_unit = total_cost / flt(bom.quantity) if bom.quantity else 0
        
        return {
            "success": True,
            "cost_breakdown": {
                "total_material_cost": total_material_cost,
                "operation_cost": operation_cost,
                "total_cost": total_cost,
                "cost_per_unit": cost_per_unit,
                "quantity": bom.quantity,
                "item_count": len(bom.items)
            }
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def create_work_order(batch_name):
    """Create Work Order from BOM"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not batch.bom_reference and not batch.standard_bom_reference:
            return {"success": False, "message": "No BOM found for this batch"}
        
        bom_name = batch.standard_bom_reference or batch.bom_reference
        bom = frappe.get_doc("BOM", bom_name)
        
        # Create Work Order
        wo = frappe.new_doc("Work Order")
        wo.production_item = bom.item
        wo.bom_no = bom.name
        wo.qty = bom.quantity
        wo.batch_amb_reference = batch_name
        wo.planned_start_date = nowdate()
        
        wo.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Work Order {0} created successfully").format(wo.name),
            "work_order_name": wo.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Work Order Creation Error: {str(e)}")
        return {"success": False, "message": str(e)}



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
    
    # ==================== GOLDEN NUMBER DEBUG FUNCTIONS ====================

@frappe.whitelist()
def debug_golden_number_step1(batch_name):
    """STEP 1: Basic batch inspection"""
    print("🔔 DEBUG STEP 1: Basic Batch Inspection")
    
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        debug_info = {
            "batch_name": batch_name,
            "work_order_ref": getattr(batch, 'work_order_ref', 'NOT FOUND'),
            "item_code": getattr(batch, 'item_code', 'NOT FOUND'),
            "has_work_order": hasattr(batch, 'work_order_ref') and bool(batch.work_order_ref)
        }
        
        print("🔔 BATCH DEBUG INFO:", debug_info)
        return debug_info
        
    except Exception as e:
        print("❌ STEP 1 ERROR:", e)
        return {"error": str(e), "step": 1}

@frappe.whitelist() 
def debug_golden_number_step2(batch_name):
    """STEP 2: Work Order inspection"""
    print("🔔 DEBUG STEP 2: Work Order Inspection")
    
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not hasattr(batch, 'work_order_ref') or not batch.work_order_ref:
            return {"error": "No work_order_ref", "step": 2}
        
        wo = frappe.get_doc("Work Order", batch.work_order_ref)
        debug_info = {
            "work_order_name": batch.work_order_ref,
            "production_item": getattr(wo, 'production_item', 'NOT FOUND'),
            "qty": getattr(wo, 'qty', 'NOT FOUND'),
            "plant_code": getattr(wo, 'custom_plant_code', 'NOT FOUND'),
            "wo_fields": [field for field in wo.as_dict().keys()]
        }
        
        print("🔔 WORK ORDER DEBUG INFO:", debug_info)
        return debug_info
        
    except Exception as e:
        print("❌ STEP 2 ERROR:", e)
        return {"error": str(e), "step": 2}

@frappe.whitelist()
def debug_golden_number_step3(batch_name):
    """STEP 3: Golden Number component extraction"""
    print("🔔 DEBUG STEP 3: Golden Number Components")
    
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not hasattr(batch, 'work_order_ref') or not batch.work_order_ref:
            return {"error": "No work_order_ref", "step": 3}
        
        wo_number = batch.work_order_ref.replace('MFG-WO-', '')
        wo = frappe.get_doc("Work Order", batch.work_order_ref)
        
        # Extract components
        components = {
            "wo_number_raw": batch.work_order_ref,
            "wo_number_clean": wo_number,
            "consecutive": wo_number[:3] if len(wo_number) >= 3 else "TOO_SHORT",
            "year": wo_number[3:5] if len(wo_number) >= 5 else "TOO_SHORT",
            "production_item": wo.production_item,
            "plant_code_raw": getattr(wo, 'custom_plant_code', 'NOT_FOUND'),
            "plant_code_clean": "NOT_CLEANED"
        }
        
        # Clean plant code
        plant_code = getattr(wo, 'custom_plant_code', '3')
        if isinstance(plant_code, str):
            if '(' in plant_code:
                plant_code = plant_code.split('(')[0].strip()
            
            # Map to numeric code
            plant_mapping = {
                'Mix': '1', '1': '1',
                'Dry': '2', '2': '2', 
                'Juice': '3', '3': '3',
                'Laboratory': '4', '4': '4',
                'Formulated': '5', '5': '5'
            }
            components["plant_code_clean"] = plant_mapping.get(plant_code, '3')
        
        print("🔔 GOLDEN NUMBER COMPONENTS:", components)
        return components
        
    except Exception as e:
        print("❌ STEP 3 ERROR:", e)
        return {"error": str(e), "step": 3}
