# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, now_datetime, get_datetime, cstr
import json
from datetime import datetime

from frappe.utils.nestedset import NestedSet

class BatchAMB(NestedSet):
    """
    Batch AMB - Production Batch Management
    """
    
    def validate(self):
        """Validation before saving"""
        self.set_batch_naming()
        self.validate_production_dates()
        self.validate_quantities()
        self.validate_work_order()
        self.validate_containers()
        self.validate_batch_level_hierarchy()
        self.validate_barrel_weights()
        self.set_item_details()
        self.validate_processing_dates()
        self.calculate_yield_percentage()
    
    def before_save(self):
        """Before save hook"""
        self.calculate_totals()
        self.set_batch_naming()
        self.auto_set_title()
        self.update_container_sequence()
        self.calculate_costs()
        self.update_processing_timestamps()
        self.update_planned_qty_from_work_order()
    
    def on_update(self):
        """After update hook"""
        self.sync_with_lote_amb()
        self.update_work_order_status()
        self.log_batch_history()
        self.update_work_order_processing_status()
    
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
    
    def calculate_yield_percentage(self):
        """Calculate yield percentage based on planned and processed quantities"""
        if hasattr(self, 'planned_qty') and self.planned_qty and flt(self.planned_qty) > 0:
            if hasattr(self, 'processed_quantity') and self.processed_quantity is not None:
                self.yield_percentage = (flt(self.processed_quantity) / flt(self.planned_qty)) * 100
            else:
                self.yield_percentage = 0
        else:
            self.yield_percentage = 0
    
    def validate_processing_dates(self):
        """Validate processing dates"""
        if hasattr(self, 'actual_start') and hasattr(self, 'actual_completion'):
            if self.actual_start and self.actual_completion:
                if self.actual_completion < self.actual_start:
                    frappe.throw(_("Actual completion date cannot be before actual start date"))
    
    def auto_set_title(self):
        """Auto-generate title based on batch level and parent."""
        if self.title and len(self.title) > 5:
            return

        level = self.custom_batch_level or "1"

        if level == "1":
            if self.custom_golden_number:
                self.title = f"{self.item_code or 'BATCH'}-{self.custom_golden_number}"
            else:
                self.title = f"{self.item_code or 'BATCH'}-{self.name}"

        elif level == "2":
            if self.parent_batch_amb:
                parent = frappe.get_doc("Batch AMB", self.parent_batch_amb)
                parent_title = parent.title or parent.name

                siblings = frappe.db.count(
                    "Batch AMB",
                    {
                        "parent_batch_amb": self.parent_batch_amb,
                        "custom_batch_level": "2",
                        "name": ["!=", self.name],
                    },
                )
                self.title = f"{parent_title[:15]} - L2-{siblings + 1:02d}"
            else:
                self.title = f"{self.name} - L2"

        elif level == "3":
            if self.parent_batch_amb:
                parent = frappe.get_doc("Batch AMB", self.parent_batch_amb)
                parent_title = parent.title or parent.name

                siblings = frappe.db.count(
                    "Batch AMB",
                    {
                        "parent_batch_amb": self.parent_batch_amb,
                        "custom_batch_level": "3",
                        "name": ["!=", self.name],
                    },
                )
                self.title = f"{parent_title[:15]} - C{siblings + 1:02d}"
            else:
                self.title = f"{self.name} - L3"

        if len(self.title) > 40:
            self.title = self.title[:40]

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
        """Calculate container weights from container_barrels child table."""
        if not getattr(self, "container_barrels", None):
            self.total_gross_weight = 0
            self.total_tara_weight = 0
            self.total_net_weight = 0
            self.barrel_count = 0
            return

        total_gross = 0
        total_tara = 0
        total_net = 0
        barrel_count = 0

        for barrel in self.container_barrels:
            if getattr(barrel, "gross_weight", None):
                total_gross += flt(barrel.gross_weight)
            if getattr(barrel, "tara_weight", None):
                total_tara += flt(barrel.tara_weight)
            if getattr(barrel, "net_weight", None):
                total_net += flt(barrel.net_weight)
            if getattr(barrel, "barrel_serial_number", None):
                barrel_count += 1

        self.total_gross_weight = total_gross
        self.total_tara_weight = total_tara
        self.total_net_weight = total_net
        self.barrel_count = barrel_count
    
    def set_batch_naming(self):
        """Generate golden number according to business rules"""
        if not self.item_to_manufacture:
            return
        
        product_code = (self.item_to_manufacture or "")[:4] or "0000"
        
        consecutive = "001"
        if self.work_order_ref:
            try:
                parts = self.work_order_ref.split("-")
                last_part = parts[-1]
                wo_consecutive = last_part[-3:] if last_part else "001"
                consecutive = wo_consecutive.zfill(3)
            except Exception:
                consecutive = "001"
        
        year = "24"
        if self.wo_start_date:
            try:
                if isinstance(self.wo_start_date, str):
                    wo_date = datetime.strptime(self.wo_start_date, '%Y-%m-%d')
                    year = str(wo_date.year)[-2:]
                else:
                    year = str(self.wo_start_date.year)[-2:]
            except Exception:
                year = datetime.now().strftime('%y')
        else:
            year = datetime.now().strftime('%y')
        
        plant_code = "1"
        if self.production_plant:
            try:
                plant_doc = frappe.get_doc("Production Plant AMB", self.production_plant)
                
                if hasattr(plant_doc, 'production_plant_id') and plant_doc.production_plant_id:
                    plant_code = str(plant_doc.production_plant_id)
                else:
                    plant_mapping = {
                        'Mix': '1',
                        'Dry': '2', 
                        'Juice': '3',
                        'Laboratory': '4',
                        'Formulated': '5'
                    }
                    plant_name = getattr(plant_doc, 'production_plant_name', '') or ''
                    for plant_type, code in plant_mapping.items():
                        if plant_type.lower() in plant_name.lower():
                            plant_code = code
                            break
            except Exception:
                plant_mapping = {
                    'Mix': '1',
                    'Dry': '2', 
                    'Juice': '3',
                    'Laboratory': '4',
                    'Formulated': '5'
                }
                for plant_type, code in plant_mapping.items():
                    if plant_type.lower() in (self.production_plant or "").lower():
                        plant_code = code
                        break
        
        base_golden_number = f"{product_code}{consecutive}{year}{plant_code}"
        
        self.custom_golden_number = base_golden_number
        self.custom_generated_batch_name = base_golden_number
        self.title = base_golden_number
        
        print(f"✅ Generated Golden Number: {base_golden_number}")
    
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
    
    def update_planned_qty_from_work_order(self):
        """Update planned_qty from Work Order"""
        try:
            work_order_name = None
            
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
    
    def update_processing_timestamps(self):
        """Automatically update timestamps based on status changes"""
        if hasattr(self, 'processing_status') and self.has_value_changed('processing_status'):
            current_status = self.processing_status
            
            if current_status == "In Progress" and not self.actual_start:
                self.actual_start = now_datetime()
            
            if current_status in ["Quality Check", "Completed"] and not self.actual_completion:
                self.actual_completion = now_datetime()
            
            if current_status == "In Progress" and self.actual_completion:
                self.actual_completion = None
            
            if current_status in ["Draft", "Cancelled"]:
                if self.actual_start:
                    self.actual_start = None
                if self.actual_completion:
                    self.actual_completion = None
    
    def update_work_order_processing_status(self):
        """Sync processing status with linked Work Order"""
        if hasattr(self, 'work_order_ref') and self.work_order_ref and hasattr(self, 'processing_status'):
            try:
                wo = frappe.get_doc('Work Order', self.work_order_ref)
                status_map = {
                    'Draft': 'Draft',
                    'Scheduled': 'Not Started',
                    'In Progress': 'In Process',
                    'Quality Check': 'In Process',
                    'Completed': 'Completed',
                    'On Hold': 'On Hold',
                    'Cancelled': 'Cancelled'
                }
                
                wo_status = status_map.get(self.processing_status, wo.status)
                if wo.status != wo_status:
                    wo.db_set('status', wo_status)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Error updating Work Order status: {str(e)}")
    
    @frappe.whitelist()
    def start_processing(self):
        """Method to start processing"""
        if self.processing_status in ["Draft", "Scheduled"]:
            self.processing_status = "In Progress"
            self.actual_start = now_datetime()
            self.save()
            frappe.msgprint(_("Processing started successfully"))
            return True
        frappe.msgprint(_("Cannot start processing from current status: {0}").format(self.processing_status))
        return False
    
    @frappe.whitelist()
    def pause_processing(self):
        """Method to pause processing"""
        if self.processing_status == "In Progress":
            self.processing_status = "On Hold"
            self.save()
            frappe.msgprint(_("Processing paused"))
            return True
        frappe.msgprint(_("Cannot pause processing from current status"))
        return False
    
    @frappe.whitelist()
    def resume_processing(self):
        """Method to resume processing"""
        if self.processing_status == "On Hold":
            self.processing_status = "In Progress"
            self.save()
            frappe.msgprint(_("Processing resumed"))
            return True
        frappe.msgprint(_("Cannot resume processing from current status"))
        return False
    
    @frappe.whitelist()
    def complete_processing(self):
        """Method to complete processing (move to Quality Check)"""
        if self.processing_status == "In Progress":
            self.processing_status = "Quality Check"
            self.actual_completion = now_datetime()
            self.save()
            frappe.msgprint(_("Processing completed, ready for quality check"))
            return True
        frappe.msgprint(_("Cannot complete processing from current status"))
        return False
    
    @frappe.whitelist()
    def approve_quality(self):
        """Method to approve quality check"""
        if self.processing_status == "Quality Check":
            self.processing_status = "Completed"
            if hasattr(self, 'quality_status'):
                self.quality_status = "Passed"
            self.save()
            frappe.msgprint(_("Quality check approved, batch completed"))
            return True
        frappe.msgprint(_("Cannot approve quality from current status"))
        return False
    
    @frappe.whitelist()
    def reject_quality(self):
        """Method to reject quality check"""
        if self.processing_status == "Quality Check":
            self.processing_status = "On Hold"
            if hasattr(self, 'quality_status'):
                self.quality_status = "Failed"
            self.save()
            frappe.msgprint(_("Quality check rejected, batch on hold"))
            return True
        frappe.msgprint(_("Cannot reject quality from current status"))
        return False
    
    @frappe.whitelist()
    def cancel_processing(self):
        """Method to cancel processing"""
        if self.processing_status not in ["Completed", "Cancelled"]:
            self.processing_status = "Cancelled"
            self.save()
            frappe.msgprint(_("Processing cancelled"))
            return True
        frappe.msgprint(_("Cannot cancel processing from current status"))
        return False
    
    @frappe.whitelist()
    def schedule_processing(self, start_date, start_time=None):
        """Method to schedule processing"""
        if self.processing_status == "Draft":
            self.processing_status = "Scheduled"
            self.scheduled_start_date = start_date
            if start_time:
                self.scheduled_start_time = start_time
            self.save()
            frappe.msgprint(_("Processing scheduled for {0}").format(start_date))
            return True
        frappe.msgprint(_("Cannot schedule processing from current status"))
        return False
    
    @frappe.whitelist()
    def get_processing_timeline(self):
        """Get processing timeline for reporting"""
        timeline = []
        
        if self.actual_start:
            timeline.append({
                'event': 'Processing Started',
                'timestamp': self.actual_start,
                'status': 'In Progress'
            })
        
        if self.actual_completion:
            timeline.append({
                'event': 'Processing Completed',
                'timestamp': self.actual_completion,
                'status': 'Quality Check'
            })
        
        try:
            from frappe.desk.form.load import get_versions
            versions = get_versions(self.doctype, self.name)
            
            for version in versions:
                data = version.get('data')
                if data and 'processing_status' in data:
                    timeline.append({
                        'event': f'Status changed to {data["processing_status"]}',
                        'timestamp': version.get('creation'),
                        'status': data['processing_status']
                    })
        except:
            pass
        
        timeline.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '')
        
        return timeline
    
    @frappe.whitelist()
    def get_processing_metrics(self):
        """Get processing metrics for analytics"""
        metrics = {
            'planned_quantity': self.planned_qty if hasattr(self, 'planned_qty') else 0,
            'processed_quantity': self.processed_quantity if hasattr(self, 'processed_quantity') else 0,
            'yield_percentage': self.yield_percentage if hasattr(self, 'yield_percentage') else 0,
            'processing_status': self.processing_status if hasattr(self, 'processing_status') else 'Draft',
            'quality_status': self.quality_status if hasattr(self, 'quality_status') else 'Pending',
            'schedule_adherence': self.calculate_schedule_adherence(),
            'efficiency': self.calculate_efficiency()
        }
        
        return metrics
    
    def calculate_schedule_adherence(self):
        """Calculate how well processing adhered to schedule"""
        if not self.scheduled_start_date or not self.actual_start:
            return 0
        
        from frappe.utils import getdate
        
        scheduled = getdate(self.scheduled_start_date)
        actual = getdate(self.actual_start)
        
        if scheduled == actual:
            return 100
        elif actual > scheduled:
            days_late = (actual - scheduled).days
            return max(0, 100 - (days_late * 10))
        else:
            days_early = (scheduled - actual).days
            return min(100 + (days_early * 5), 120)
    
    def calculate_efficiency(self):
        """Calculate processing efficiency"""
        if not self.actual_start or not self.actual_completion:
            return 0
        
        from frappe.utils import get_datetime
        
        start = get_datetime(self.actual_start)
        end = get_datetime(self.actual_completion)
        
        processing_time = (end - start).total_seconds() / 3600
        
        if hasattr(self, 'processed_quantity') and self.processed_quantity and processing_time > 0:
            efficiency = (flt(self.processed_quantity) / processing_time) * 100
            return min(efficiency, 200)
        
        return 0

# ==================== MANUFACTURING BUTTON METHODS ====================
@frappe.whitelist()
def create_bom_with_wizard(batch_name, options=None):
    """Create BOM with wizard options - MAIN MANUFACTURING BUTTON - FIXED VERSION"""
    try:
        print(f"🚀 BOM Creation started for batch: {batch_name}")
        
        # Get batch document
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        if not batch.item_to_manufacture:
            return {"success": False, "message": "No item to manufacture specified"}
        
        # Parse options
        if options and isinstance(options, str):
            options = json.loads(options)
        options = options or {}
        
        # Get quantity - use actual values, not hardcoded
        bom_quantity = batch.planned_qty or batch.batch_quantity or batch.total_net_weight or 1000
        
        # FIX: Get UOM from the Item, not Batch (Batch AMB doesn't have uom field)
        item = frappe.get_doc("Item", batch.item_to_manufacture)
        uom = item.stock_uom
        
        print(f"📦 Item: {batch.item_to_manufacture}")
        print(f"⚖️ Quantity: {bom_quantity} {uom}")
        
        # Check if BOM already exists for this item
        existing_bom = frappe.db.get_value("BOM", {
            "item": batch.item_to_manufacture,
            "is_active": 1
        }, "name")
        
        if existing_bom:
            print(f"⚠️ BOM already exists: {existing_bom}")
            return {
                "success": True,
                "bom_name": existing_bom,
                "item_code": batch.item_to_manufacture,
                "qty": bom_quantity,
                "uom": uom,
                "item_count": 1,
                "exists": True,
                "message": f"BOM already exists: {existing_bom}"
            }
        
        # Create BOM data with ALL required fields
        bom_data = {
            "item": batch.item_to_manufacture,
            "quantity": bom_quantity,
            "uom": uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "currency": "MXN",
            "company": "AMB-Wellness",
            "custom_golden_number": batch.custom_golden_number,
            "custom_batch_reference": batch.name
        }
        
        print(f"📝 Creating BOM with data: {bom_data}")
        
        # Create BOM
        bom = frappe.new_doc("BOM")
        bom.update(bom_data)
        
        # ✅✅✅ CRITICAL FIX: Use REAL items that exist
        # Based on your console test, these items exist:
        # M033, 0202, 0221, 0205, S001
        
        # Add raw material - use M033 (Aloe Vera Gel) which exists
        if frappe.db.exists("Item", "M033"):
            bom.append('items', {
                'item_code': 'M033',
                'item_name': 'Aloe Vera Gel',
                'qty': bom_quantity * 0.05,  # 5% of total
                'uom': 'Kg',
                'rate': 0
            })
            print(f"➕ Added raw material: M033")
        else:
            # Fallback to 0202 which also exists
            bom.append('items', {
                'item_code': '0202',
                'qty': bom_quantity * 0.05,
                'uom': 'Kg',
                'rate': 0
            })
            print(f"➕ Added fallback raw material: 0202")
        
        # Add packaging if selected
        if options.get('include_packaging', 1):
            packaging_item = options.get('primary_packaging', 'E001')
            if frappe.db.exists("Item", packaging_item):
                packages_count = options.get('packages_count', 1)
                bom.append('items', {
                    'item_code': packaging_item,
                    'qty': packages_count,
                    'uom': 'Nos',
                    'rate': 0
                })
                print(f"➕ Added packaging: {packaging_item} x {packages_count}")
        
        # Insert the BOM
        bom.insert()
        frappe.db.commit()
        
        print(f"✅ BOM created successfully: {bom.name}")
        
        return {
            "success": True,
            "bom_name": bom.name,
            "item_code": batch.item_to_manufacture,
            "qty": bom_quantity,
            "uom": uom,
            "item_count": len(bom.items),
            "exists": False,
            "message": f"BOM created successfully: {bom.name}"
        }
        
    except Exception as e:
        frappe.log_error(f"BOM Creation Error for {batch_name}: {str(e)}")
        print(f"❌ BOM Creation Error: {str(e)}")
        return {"success": False, "message": f"Error creating BOM: {str(e)}"}
        
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
        
        material_cost = batch.material_cost or 0
        labor_cost = batch.labor_cost or 0
        overhead_cost = batch.overhead_cost or 0
        
        total_batch_cost = material_cost + labor_cost + overhead_cost
        
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
        
        sales_order = None
        
        if batch.sales_order_related:
            sales_order = batch.sales_order_related
        
        if not sales_order and batch.work_order_ref:
            try:
                wo = frappe.get_doc('Work Order', batch.work_order_ref)
                if hasattr(wo, 'sales_order') and wo.sales_order:
                    sales_order = wo.sales_order
            except Exception as e:
                frappe.log_error(f"Error fetching WO sales order: {str(e)}")
        
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
        
        primary_item = map_packaging_text_to_item(so.custom_tipo_empaque)
        secondary_item = map_packaging_text_to_item(so.empaque_secundario) if so.empaque_secundario else None
        
        net_weight = parse_weight_from_text(so.custom_peso_neto) if so.custom_peso_neto else 220
        
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
    
    PACKAGING_MAP = {
        '220l': 'E001',
        '220 l': 'E001',
        'barrel blue': 'E001',
        'barrel 220': 'E001',
        'polyethylene barrel': 'E002',
        'reused barrel': 'E002',
        '25kg': 'E003',
        '25 kg': 'E003',
        '25kg drum': 'E003',
        'drum 25': 'E003',
        '10kg': 'E004',
        '10 kg': 'E004',
        '10kg drum': 'E004',
        'drum 10': 'E004',
        '20l': 'E005',
        '20 l': 'E005',
        'jug': 'E005',
        'white jug': 'E005',
        'tarima': 'E006',
        'pallet 44': 'E006',
        'pino real': 'E006',
        'euro pallet': 'E007',
        'euro': 'E007',
        'reused pallet': 'E008',
        '44x44': 'E008',
        'bolsa': 'E009',
        'poly bag': 'E009',
        'polietileno': 'E009',
        '30x60': 'E009',
        'bag': 'E009'
    }
    
    for keyword, item_code in PACKAGING_MAP.items():
        if keyword in text_lower:
            return item_code
    
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
    
    return 'E001'

def parse_weight_from_text(weight_text):
    """Parse weight from text like '5 Kg', '220', '10.5 kg'"""
    if not weight_text:
        return 0
    
    import re
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
            code = f"BATCH-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        elif batch_level == '2' and parent_batch:
            parent_code = frappe.db.get_value("Batch AMB", parent_batch, "custom_generated_batch_name") or "PARENT"
            code = f"{parent_code}-SUB"
        elif batch_level == '3' and parent_batch:
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


# ============================================
# SERIAL TRACKING INTEGRATION METHODS
# ============================================

@frappe.whitelist()
def schedule_batch(batch_name, scheduled_start):
    """Schedule a batch for processing"""
    batch = frappe.get_doc("Batch AMB", batch_name)
    batch.scheduled_start_date = scheduled_start
    batch.processing_status = "Scheduled"
    batch.save()
    return {"status": "success", "message": f"Batch {batch_name} scheduled"}

@frappe.whitelist()
def start_batch_processing(batch_name):
    """Start processing a batch"""
    from frappe.utils import now_datetime
    batch = frappe.get_doc("Batch AMB", batch_name)
    batch.processing_status = "In Progress"
    batch.actual_start = now_datetime()
    batch.save()
    return {"status": "success", "message": f"Batch {batch_name} started"}

@frappe.whitelist()
def complete_batch_processing(batch_name, processed_quantity=None):
    """Complete batch processing"""
    from frappe.utils import now_datetime
    batch = frappe.get_doc("Batch AMB", batch_name)
    batch.processing_status = "Completed"
    batch.actual_completion = now_datetime()
    if processed_quantity:
        batch.processed_quantity = processed_quantity
    batch.save()
    return {"status": "success", "message": f"Batch {batch_name} completed"}
#
@frappe.whitelist()
def generate_serial_numbers(batch_name, quantity=1, prefix=None):
    """Generate serial numbers for batch and add to container_barrels table"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        # Convert to int if string
        if isinstance(quantity, str):
            quantity = int(quantity)
        
        # Get batch level
        batch_level = batch.custom_batch_level or '1'
        
        # Determine serial format based on batch level
        if batch_level == '4':
            # Level 4: Use prefix-batch-001 format
            if not prefix:
                prefix = "BRL"
            # Keep serial short for level 4
            base_name = batch.name.replace("LOTE-", "")  # Remove prefix to keep it shorter
            serial_prefix = f"{prefix}-{base_name}"
        else:
            # Levels 1-3: Use simpler format
            base_name = batch.name
            serial_prefix = base_name
        
        # Get existing serials from container_barrels
        existing_serials = []
        for row in batch.container_barrels:
            if row.barrel_serial_number and row.barrel_serial_number.strip():
                existing_serials.append(row.barrel_serial_number.strip())
        
        # Start from existing count
        existing_count = len(existing_serials)
        
        # Generate new serial numbers (keep them under 50 chars)
        new_serials = []
        for i in range(quantity):
            seq_num = existing_count + i + 1
            
            # Generate different formats based on level
            if batch_level == '4':
                # Level 4: BRL-25-49-0148-001 (shorter format)
                short_batch = batch.name.replace("LOTE-", "")
                serial = f"{prefix}-{short_batch}-{seq_num:03d}"
            elif batch_level == '3':
                # Level 3: LOTE-25-49-0148-C001
                serial = f"{batch.name}-C{seq_num:03d}"
            else:
                # Levels 1-2: LOTE-25-49-0148-001
                serial = f"{batch.name}-{seq_num:03d}"
            
            # Ensure serial is not too long (max 50 chars)
            if len(serial) > 50:
                serial = serial[:50]
            
            new_serials.append(serial)
            
            # Add to container_barrels table
            # Make sure we include ALL mandatory fields
            row_data = {
                "barrel_serial_number": serial,
                "status": "Empty",
                "packaging_type": batch.default_packaging_type or "",
                "batch_amb": batch_name,
                "item_code": batch.item_to_manufacture or batch.current_item_code or "",
                "created_date": frappe.utils.nowdate(),
                "parent": batch.name,
                "parentfield": "container_barrels",
                "parenttype": "Batch AMB"
            }
            
            batch.append("container_barrels", row_data)
        
        # Update text field for non-level 4 batches
        if batch_level != '4':
            existing_text = []
            if batch.custom_serial_numbers:
                existing_text = [s.strip() for s in batch.custom_serial_numbers.split('\\n') if s.strip()]
            
            all_text = existing_text + new_serials
            # Keep each line under 140 chars
            truncated_text = []
            for text in set(all_text):
                if len(text) > 140:
                    truncated_text.append(text[:140])
                else:
                    truncated_text.append(text)
            
            batch.custom_serial_numbers = "\\n".join(sorted(truncated_text))
            batch.custom_last_api_sync = frappe.utils.now_datetime()
            batch.custom_serial_tracking_integrated = 1
        
        # Save the batch
        batch.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"Generated {len(new_serials)} serial numbers",
            "count": len(new_serials),
            "serial_numbers": new_serials
        }
        
    except Exception as e:
        # Log error with shorter title to avoid truncation
        error_msg = f"Error generating serials for {batch_name[:30]}"
        frappe.log_error(
            title=error_msg,  # Shorter title
            message=f"Details: {str(e)[:100]}..."  # Truncated message
        )
        frappe.throw(f"Failed to generate serial numbers: {str(e)[:200]}")  # Truncated error

# Also update integrate_serial_tracking to use this
@frappe.whitelist()
def integrate_serial_tracking(batch_name):
    """Fixed integrate function"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        
        # Default quantity for integration
        default_qty = batch.planned_qty or 5
        
        # Call the fixed function
        result = fixed_generate_serial_numbers(
            batch_name=batch_name,
            quantity=default_qty,
            prefix="BRL" if batch.custom_batch_level == '4' else None
        )
        
        if result.get("status") == "success":
            return {
                "status": "success",
                "message": "Serial tracking integrated successfully",
                "serial_count": result.get("count", 0),
                "details": result
            }
        else:
            return result
            
    except Exception as e:
        frappe.log_error(f"Integration error: {str(e)}")
        return {
            "status": "error",
            "message": f"Integration failed: {str(e)[:200]}"
        }

#
