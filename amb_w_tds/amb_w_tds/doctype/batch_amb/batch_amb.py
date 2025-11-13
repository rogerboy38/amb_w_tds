# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, get_datetime, cstr, today
import json
from amb_w_tds.services.golden_number_service import GoldenNumberService

class BatchAMB(Document):
    """
    Batch AMB - Production Batch Management with Golden Number Integration
    """
    
    def validate(self):
        """Validation before saving"""
        # Generate golden number if Work Order is linked
        if self.work_order_ref and not self.golden_number:
            self.set_golden_number_from_work_order()
        
        # Validate golden number if present
        if self.golden_number:
            is_valid, message = GoldenNumberService.validate_golden_number(self.golden_number)
            if not is_valid:
                frappe.throw(_(f"Invalid golden number: {message}"))
        
        # Set title and custom_generated_batch_name from golden number
        if self.golden_number:
            self.title = self.golden_number
            self.custom_generated_batch_name = self.golden_number
        
        # Existing validations
        self.validate_batch_items()
        self.validate_production_dates()
        self.validate_quantities()
        self.validate_work_order()
        self.validate_containers()
        self.validate_batch_level_hierarchy()
        self.validate_barrel_weights()
        self.set_item_details()
    
    def set_golden_number_from_work_order(self):
        """Generate and set golden number from linked Work Order"""
        if not self.work_order_ref:
            return
        
        try:
            # Generate golden number
            result = GoldenNumberService.generate_from_work_order(self.work_order_ref)
            
            if result:
                self.golden_number = result['golden_number']
                self.product_code = result['product_code']
                self.consecutive_number = result['consecutive_number']
                self.year_code = result['year_code']
                self.plant_code = result['plant_code']
                
                # Set title and custom_generated_batch_name
                self.title = self.golden_number
                self.custom_generated_batch_name = self.golden_number
                
                frappe.msgprint(_(f"Golden Number generated: {self.golden_number}"), 
                               indicator='green', alert=True)
                
        except Exception as e:
            frappe.log_error(f"Error setting golden number: {str(e)}", "Batch AMB Golden Number")
            frappe.throw(_("Failed to generate golden number. Please check Work Order details."))
    
    def validate_batch_items(self):
        """Validate batch items for BOM generation"""
        if self.batch_items:
            for item in self.batch_items:
                if not item.item_code or flt(item.quantity) <= 0:
                    frappe.throw(_("Invalid item or quantity in batch items"))
    
    def validate_production_dates(self):
        """Validate production start and end dates"""
        if hasattr(self, 'production_start_date') and hasattr(self, 'production_end_date'):
            if self.production_start_date and self.production_end_date:
                if get_datetime(self.production_end_date) < get_datetime(self.production_start_date):
                    frappe.throw(_("Production End Date cannot be before Start Date"))
    
    def validate_quantities(self):
        """Validate batch quantities"""
        if hasattr(self, 'target_quantity') and self.target_quantity:
            if flt(self.target_quantity) <= 0:
                frappe.throw(_("Target Quantity must be greater than zero"))
    
    def validate_work_order(self):
        """Validate linked Work Order"""
        if self.work_order_ref:
            if not frappe.db.exists("Work Order", self.work_order_ref):
                frappe.throw(_("Work Order {0} does not exist").format(self.work_order_ref))
    
    def validate_containers(self):
        """Validate container-related fields"""
        if hasattr(self, 'barrel_count') and self.barrel_count:
            if flt(self.barrel_count) < 0:
                frappe.throw(_("Barrel Count cannot be negative"))
    
    def validate_batch_level_hierarchy(self):
        """Validate batch level hierarchy"""
        if hasattr(self, 'custom_batch_level') and self.custom_batch_level:
            valid_levels = ['1', '2', '3']
            if str(self.custom_batch_level) not in valid_levels:
                frappe.throw(_("Batch Level must be 1, 2, or 3"))
    
    def validate_barrel_weights(self):
        """Validate barrel weights"""
        if hasattr(self, 'total_net_weight') and self.total_net_weight:
            if flt(self.total_net_weight) < 0:
                frappe.throw(_("Total Net Weight cannot be negative"))
    
    def set_item_details(self):
        """Auto-populate item details from linked items"""
        for item in self.batch_items:
            if item.item_code and not item.item_name:
                item.item_name = frappe.db.get_value("Item", item.item_code, "item_name")
            
            if item.item_code and not item.uom:
                item.uom = frappe.db.get_value("Item", item.item_code, "stock_uom")
            
            if item.item_code and not item.rate:
                item.rate = frappe.db.get_value("Item", item.item_code, "valuation_rate") or 0
            
            # Calculate amount
            item.amount = flt(item.quantity) * flt(item.rate)
    
    def before_save(self):
        """Before save hook"""
        self.calculate_totals()
        self.set_batch_naming()
        self.update_container_sequence()
        self.calculate_costs()
    
    def calculate_totals(self):
        """Calculate total quantities and amounts"""
        total_qty = 0
        total_amount = 0
        
        for item in self.batch_items:
            total_qty += flt(item.quantity)
            total_amount += flt(item.amount)
        
        if hasattr(self, 'total_quantity'):
            self.total_quantity = total_qty
        if hasattr(self, 'total_amount'):
            self.total_amount = total_amount
    
    def set_batch_naming(self):
        """Set batch naming based on golden number"""
        if self.golden_number and not self.name:
            # Name will be auto-generated by Frappe
            pass
    
    def update_container_sequence(self):
        """Update container sequence numbers"""
        if hasattr(self, 'containers'):
            for idx, container in enumerate(self.containers, start=1):
                container.sequence = idx
    
    def calculate_costs(self):
        """Calculate batch costs"""
        material_cost = sum(flt(item.amount) for item in self.batch_items)
        
        if hasattr(self, 'material_cost'):
            self.material_cost = material_cost
        
        # Add overhead if configured
        if hasattr(self, 'overhead_percentage') and self.overhead_percentage:
            overhead = material_cost * flt(self.overhead_percentage) / 100
            if hasattr(self, 'overhead_cost'):
                self.overhead_cost = overhead
            if hasattr(self, 'total_cost'):
                self.total_cost = material_cost + overhead
    
    def on_update(self):
        """After save hook"""
        self.sync_with_lote_amb()
        self.update_work_order_status()
        self.log_batch_history()
    
    def sync_with_lote_amb(self):
        """Sync with Lote AMB if linked"""
        if hasattr(self, 'lote_amb_reference') and self.lote_amb_reference:
            try:
                lote = frappe.get_doc("Lote AMB", self.lote_amb_reference)
                lote.batch_status = self.status if hasattr(self, 'status') else None
                lote.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error syncing with Lote AMB: {str(e)}", "Batch AMB Sync")
    
    def update_work_order_status(self):
        """Update Work Order status based on batch progress"""
        if self.work_order_ref:
            try:
                wo = frappe.get_doc("Work Order", self.work_order_ref)
                # Update custom fields if they exist
                if hasattr(wo, 'custom_batch_status'):
                    wo.custom_batch_status = self.status if hasattr(self, 'status') else None
                    wo.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error updating Work Order: {str(e)}", "Batch AMB WO Update")
    
    def log_batch_history(self):
        """Log batch status changes"""
        if self.has_value_changed('status'):
            try:
                frappe.get_doc({
                    "doctype": "Comment",
                    "comment_type": "Info",
                    "reference_doctype": self.doctype,
                    "reference_name": self.name,
                    "content": f"Status changed to: {self.status}"
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error logging batch history: {str(e)}", "Batch AMB History")
    
    def on_submit(self):
        """On submit actions"""
        self.create_stock_entry()
        self.create_lote_amb_if_needed()
        self.update_batch_status("Submitted")
        self.notify_stakeholders()
    
    def create_stock_entry(self):
        """Create stock entry for batch production"""
        if not self.batch_items:
            return
        
        try:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Manufacture"
            stock_entry.company = self.company if hasattr(self, 'company') else frappe.defaults.get_user_default("Company")
            stock_entry.posting_date = today()
            stock_entry.batch_amb_reference = self.name
            
            # Add items from batch
            for item in self.batch_items:
                stock_entry.append("items", {
                    "item_code": item.item_code,
                    "qty": item.quantity,
                    "uom": item.uom,
                    "basic_rate": item.rate,
                    "s_warehouse": item.source_warehouse if hasattr(item, 'source_warehouse') else None,
                    "batch_no": item.batch_no if hasattr(item, 'batch_no') else None
                })
            
            stock_entry.insert(ignore_permissions=True)
            frappe.msgprint(_("Stock Entry {0} created").format(stock_entry.name))
            
        except Exception as e:
            frappe.log_error(f"Error creating Stock Entry: {str(e)}", "Batch AMB Stock Entry")
    
    def create_lote_amb_if_needed(self):
        """Create Lote AMB if configured"""
        if hasattr(self, 'auto_create_lote') and self.auto_create_lote:
            if not self.lote_amb_reference:
                try:
                    lote = frappe.new_doc("Lote AMB")
                    lote.batch_amb_reference = self.name
                    lote.golden_number = self.golden_number
                    lote.title = self.title
                    lote.insert(ignore_permissions=True)
                    
                    self.db_set('lote_amb_reference', lote.name)
                    frappe.msgprint(_("Lote AMB {0} created").format(lote.name))
                    
                except Exception as e:
                    frappe.log_error(f"Error creating Lote AMB: {str(e)}", "Batch AMB Lote Creation")
    
    def update_batch_status(self, status):
        """Update batch status"""
        self.db_set('status', status)
    
    def notify_stakeholders(self):
        """Send notifications to stakeholders"""
        if hasattr(self, 'notify_on_submit') and self.notify_on_submit:
            # Implement notification logic
            pass
    
    def on_cancel(self):
        """On cancel actions"""
        self.cancel_stock_entries()
        self.update_batch_status("Cancelled")
    
    def cancel_stock_entries(self):
        """Cancel related stock entries"""
        stock_entries = frappe.get_all("Stock Entry", 
            filters={"batch_amb_reference": self.name, "docstatus": 1},
            pluck="name"
        )
        
        for entry in stock_entries:
            try:
                se = frappe.get_doc("Stock Entry", entry)
                se.cancel()
                frappe.msgprint(_("Stock Entry {0} cancelled").format(entry))
            except Exception as e:
                frappe.log_error(f"Error cancelling Stock Entry {entry}: {str(e)}", "Batch AMB Cancel")
    
    # ==================== BOM GENERATION METHODS ====================
    
    def generate_mrp_bom(self):
        """Generate MRP BOM from batch items with golden number integration"""
        try:
            if not self.batch_items:
                frappe.throw(_("No items in batch to generate BOM"))
            
            if not self.golden_number:
                frappe.throw(_("Golden number is required to generate BOM"))
            
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
            
            # Set golden number and project
            if frappe.db.exists("Custom Field", "BOM-golden_number"):
                bom.golden_number = self.golden_number
            
            bom.project = self.golden_number
            
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
            frappe.log_error(f"BOM Creation Error: {str(e)}", "Batch AMB BOM")
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
        elif hasattr(self, 'item_to_manufacture') and self.item_to_manufacture:
            return self.item_to_manufacture
        return None


# ==================== API METHODS ====================

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
        
        # Copy golden number
        if frappe.db.exists("Custom Field", "BOM-golden_number") and batch.golden_number:
            standard_bom.golden_number = batch.golden_number
        
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
        operation_cost = bom.operation_cost if hasattr(bom, 'operation_cost') else 0
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
        
        # Set golden number if custom field exists
        if frappe.db.exists("Custom Field", "Work Order-golden_number") and batch.golden_number:
            wo.golden_number = batch.golden_number
        
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
                'name', 'title', 'golden_number', 'item_to_manufacture', 'item_code',
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
            
            content_text = f"Golden Number: {batch.golden_number or 'N/A'}\n"
            content_text += f"Item: {batch.wo_item_name or batch.item_code or 'N/A'}\n"
            content_text += f"Plant: {batch.custom_plant_code or 'N/A'}\n"
            content_text += f"Weight: {batch.total_net_weight or 0}\n"
            content_text += f"Barrels: {batch.barrel_count or 0}"
            
            announcement = {
                'name': batch.name,
                'title': batch.title or batch.golden_number or batch.name,
                'batch_code': batch.name,
                'golden_number': batch.golden_number,
                'item_code': batch.item_to_manufacture or batch.item_code or 'N/A',
                'status': 'Active',
                'company': company,
                'level': batch.custom_batch_level or 'Batch',
                'priority': 'high' if batch.quality_status == 'Failed' else 'medium',
                'quality_status': batch.quality_status or 'Pending',
                'content': content_text,
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
        frappe.log_error("Widget error: " + str(e) + "\n" + traceback.format_exc(), "Batch Widget Error")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load batch data'
        }

@frappe.whitelist()
def generate_golden_number_from_wo(work_order_name):
    """Generate golden number from Work Order - API endpoint"""
    try:
        result = GoldenNumberService.generate_from_work_order(work_order_name)
        if result:
            return {
                'success': True,
                'data': result
            }
        else:
            return {
                'success': False,
                'message': 'Failed to generate golden number'
            }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }

    def generate_bom_from_template(self):
        """Generate BOM from template using golden number"""
        from amb_w_tds.services.template_bom_service import TemplateBOMService
        
        try:
            bom_name = TemplateBOMService.create_bom_from_template(self)
            self.db_set('bom_reference', bom_name)
            
            frappe.msgprint(_("BOM {0} created from template").format(bom_name))
            return bom_name
            
        except Exception as e:
            frappe.log_error(f"BOM Template Generation Error: {str(e)}", "Batch AMB")
            frappe.throw(_("Failed to generate BOM from template: {0}").format(str(e)))
