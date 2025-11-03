# Merged batch_amb.py - Original (647 lines) + Additional Methods (288 lines)
# Total: ~935 lines with full integration

# ==================== IMPORTS ====================
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
    Consolidated from client and server scripts with BatchL2 enhancements
    """
    
    # ==================== DOCUMENT LIFECYCLE HOOKS ====================
    
    def validate(self):
        """Validation before saving"""
        self.validate_production_dates()
        self.validate_quantities()
        self.validate_work_order()
        self.validate_containers()
        self.validate_batch_level_hierarchy()  # NEW: BatchL2 validation
        self.validate_barrel_weights()  # NEW: BatchL2 barrel validation
        self.set_item_details()
    
    def before_save(self):
        """Before save hook - Server Script: 'Batch AMB - Before Save'"""
        self.calculate_totals()
        self.set_batch_naming()
        self.update_container_sequence()
        self.calculate_costs()
    
    def on_update(self):
        """After update hook - Server Script: 'Batch AMB - On Update'"""
        self.sync_with_lote_amb()
        self.update_work_order_status()
        self.log_batch_history()
    
    def on_submit(self):
        """On submit - create related documents"""
        self.create_stock_entry()
        self.create_lote_amb_if_needed()
        self.update_batch_status('Completed')
        self.notify_stakeholders()
    
    def on_cancel(self):
        """On cancel - reverse operations"""
        self.cancel_stock_entries()
        self.update_batch_status('Cancelled')
    
    # ==================== VALIDATION METHODS ====================
    
    def validate_production_dates(self):
        """Validate production start and end dates"""
        if self.production_start_date and self.production_end_date:
            start = get_datetime(self.production_start_date)
            end = get_datetime(self.production_end_date)
            
            if end < start:
                frappe.throw(_("Production end date cannot be before start date"))
            
            # Check if dates are in the future
            if start > get_datetime(nowdate()):
                frappe.msgprint(_("Production start date is in the future"), indicator='orange')
    
    def validate_quantities(self):
        """Validate quantities"""
        if self.produced_qty:
            if flt(self.produced_qty) <= 0:
                frappe.throw(_("Produced quantity must be greater than 0"))
            
            # Validate against planned quantity if exists
            if self.planned_qty and flt(self.produced_qty) > flt(self.planned_qty) * 1.1:
                frappe.msgprint(
                    _("Produced quantity ({0}) exceeds planned quantity ({1}) by more than 10%").format(
                        self.produced_qty, self.planned_qty
                    ),
                    indicator='orange'
                )
    
    def validate_work_order(self):
        """Validate work order reference"""
        if self.work_order:
            if not frappe.db.exists('Work Order', self.work_order):
                frappe.throw(_("Work Order {0} does not exist").format(self.work_order))
            
            # Get work order details
            wo = frappe.get_doc('Work Order', self.work_order)
            
            # Validate item matches
            if self.item_to_manufacture and self.item_to_manufacture != wo.production_item:
                frappe.msgprint(
                    _("Item to manufacture ({0}) doesn't match Work Order item ({1})").format(
                        self.item_to_manufacture, wo.production_item
                    ),
                    indicator='orange'
                )
    
    def validate_containers(self):
        """Validate container/barrel data"""
        if not self.container_barrels:
            return
        
        total_from_containers = sum(flt(c.quantity or 0) for c in self.container_barrels)
        
        if self.produced_qty:
            difference = abs(total_from_containers - flt(self.produced_qty))
            
            if difference > 0.001:  # Allow small rounding differences
                frappe.msgprint(
                    _("Container total quantity ({0}) doesn't match produced quantity ({1}). Difference: {2}").format(
                        total_from_containers,
                        self.produced_qty,
                        difference
                    ),
                    indicator='orange'
                )
        
        # Validate individual containers
        for idx, container in enumerate(self.container_barrels, 1):
            if not container.container_id:
                container.container_id = f"CNT-{self.name}-{idx:03d}"
            
            if container.quantity and flt(container.quantity) <= 0:
                frappe.throw(_("Row {0}: Container quantity must be greater than 0").format(idx))
    
    # NEW: BatchL2 Enhanced Validation Methods
    def validate_batch_level_hierarchy(self):
        """Validate batch level hierarchy for BatchL2 functionality"""
        level = int(self.custom_batch_level or '1', 10)
        
        if level > 1 and not self.parent_batch_amb:
            frappe.throw(_("Parent Batch AMB is required for level {0}").format(level))
        
        if level > 1 and self.parent_batch_amb:
            if not frappe.db.exists('Batch AMB', self.parent_batch_amb):
                frappe.throw(_("Parent Batch {0} does not exist").format(self.parent_batch_amb))
            
            parent = frappe.get_doc('Batch AMB', self.parent_batch_amb)
            parent_level = int(parent.custom_batch_level or '1', 10)
            
            if parent_level >= level:
                frappe.throw(_("Parent batch level ({0}) must be lower than child level ({1})").format(parent_level, level))
    
    def validate_barrel_weights(self):
        """Validate barrel weight calculations for BatchL2 Level 3 batches"""
        if self.custom_batch_level != '3':
            return
        
        # Validate container barrels
        if not self.container_barrels:
            frappe.throw('Container barrels are required for Level 3 batches')
        
        for barrel in self.container_barrels:
            if barrel.gross_weight and barrel.tara_weight:
                net_weight = barrel.gross_weight - barrel.tara_weight
                if net_weight <= 0:
                    frappe.throw(f'Invalid net weight for barrel {barrel.barrel_serial_number}: {net_weight}')
                
                if barrel.net_weight != net_weight:
                    barrel.net_weight = net_weight
    
    def set_item_details(self):
        """Set item details from Item master"""
        if self.item_to_manufacture:
            item = frappe.get_doc('Item', self.item_to_manufacture)
            self.item_name = item.item_name
            if not self.uom:
                self.uom = item.stock_uom
    
    # ==================== CALCULATION METHODS ====================
    
    def calculate_totals(self):
        """Calculate total quantities and containers"""
        # Total from containers
        if self.container_barrels:
            self.total_container_qty = sum(flt(c.quantity or 0) for c in self.container_barrels)
            self.total_containers = len(self.container_barrels)
            
            # NEW: BatchL2 weight calculations
            self.calculate_container_weights()  # NEW: BatchL2 weight aggregation
        else:
            self.total_container_qty = 0
            self.total_containers = 0
        
        # Set produced qty if not set
        if not self.produced_qty and self.total_container_qty:
            self.produced_qty = self.total_container_qty
    
    def calculate_costs(self):
        """Calculate batch costs"""
        if not self.calculate_cost:
            return
        
        total_cost = 0
        
        # Material costs from BOM
        if self.bom_no:
            bom_cost = self.get_bom_cost()
            total_cost += bom_cost
        
        # Labor costs
        if self.labor_cost:
            total_cost += flt(self.labor_cost)
        
        # Overhead costs
        if self.overhead_cost:
            total_cost += flt(self.overhead_cost)
        
        self.total_batch_cost = total_cost
        
        # Calculate per unit cost
        if self.produced_qty:
            self.cost_per_unit = total_cost / flt(self.produced_qty)
    
    def get_bom_cost(self):
        """Get cost from BOM"""
        if not self.bom_no:
            return 0
        
        bom = frappe.get_doc('BOM', self.bom_no)
        return flt(bom.total_cost) * flt(self.produced_qty)
    
    # NEW: BatchL2 Weight Calculation Methods
    def calculate_container_weights(self):
        """Calculate total weights for BatchL2 containers"""
        if not self.container_barrels:
            self.total_gross_weight = 0
            self.total_tara_weight = 0
            self.total_net_weight = 0
            self.barrel_count = 0
            return
        
        total_gross = total_tara = total_net = 0
        barrel_count = 0
        
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
    
    # ==================== NAMING & SEQUENCING ====================
    
    def set_batch_naming(self):
        """Set batch naming based on rules"""
        # Auto-generate batch number if not set
        if not self.batch_number and self.item_to_manufacture:
            # Format: ITEM-YYYYMMDD-XXX
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            
            # Get last batch for this item
            last_batch = frappe.db.sql("""
                SELECT batch_number 
                FROM `tabBatch AMB` 
                WHERE item_to_manufacture = %s 
                AND batch_number LIKE %s 
                ORDER BY creation DESC 
                LIMIT 1
            """, (self.item_to_manufacture, f"%{date_str}%"))
            
            if last_batch:
                # Extract sequence number and increment
                last_num = int(last_batch[0][0].split('-')[-1])
                seq = last_num + 1
            else:
                seq = 1
            
            self.batch_number = f"{self.item_to_manufacture[:4]}-{date_str}-{seq:03d}"
    
    def update_container_sequence(self):
        """Update container sequence numbers"""
        for idx, container in enumerate(self.container_barrels, 1):
            container.idx = idx
            if not container.container_id:
                container.container_id = f"{self.name}-C{idx:03d}"
    
    # ==================== BATCHL2 ENHANCED METHODS ====================
    
    def generate_batch_code(self, parent_batch=None, batch_level=None, work_order=None):
        """
        Generate automatic batch code based on BatchL2 parameters
        NEW: BatchL2 functionality
        """
        try:
            # Logic for generating batch codes
            parent_batch_doc = None
            if parent_batch:
                parent_batch_doc = frappe.get_doc('Batch AMB', parent_batch)
            
            # Generate code based on batch level
            if batch_level == '1':
                # Level 1 - Root level
                code = self.generate_level1_code(work_order)
            elif batch_level == '2':
                # Level 2 - Intermediate level
                code = self.generate_level2_code(parent_batch_doc)
            elif batch_level == '3':
                # Level 3 - Container level
                code = self.generate_level3_code(parent_batch_doc)
            else:
                # Default generation
                code = self.generate_default_code()
            
            return {
                'success': True,
                'code': code,
                'message': f'Generated batch code: {code}'
            }
            
        except Exception as e:
            frappe.log_error(f"Error generating batch code: {str(e)}", "Batch Code Generation")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate batch code'
            }
    
    def generate_level1_code(self, work_order=None):
        """Generate Level 1 batch code"""
        # Implementation for level 1 code generation
        return f"BATCH-{nowdate().strftime('%Y%m%d')}-001"
    
    def generate_level2_code(self, parent_batch_doc):
        """Generate Level 2 batch code"""
        # Implementation for level 2 code generation
        return f"{parent_batch_doc.name}-L2-001"
    
    def generate_level3_code(self, parent_batch_doc):
        """Generate Level 3 batch code"""
        # Implementation for level 3 code generation
        return f"{parent_batch_doc.name}-L3-001"
    
    def generate_default_code(self):
        """Generate default batch code"""
        return f"BATCH-{nowdate().strftime('%Y%m%d')}-{frappe.utils.get_random_string(3).upper()}"
    
    def get_work_order_data(self, work_order):
        """
        Get work order data for batch generation
        NEW: Enhanced version for BatchL2
        """
        try:
            if not frappe.db.exists('Work Order', work_order):
                return {
                    'success': False,
                    'error': f'Work Order {work_order} not found',
                    'message': 'Work order does not exist'
                }
            
            wo_doc = frappe.get_doc('Work Order', work_order)
            
            # Extract relevant data for batch generation
            work_order_data = {
                'name': wo_doc.name,
                'production_item': wo_doc.production_item,
                'planned_qty': wo_doc.planned_qty,
                'company': wo_doc.company,
                'wip_warehouse': wo_doc.wip_warehouse,
                'fg_warehouse': wo_doc.fg_warehouse,
                'production_plant': getattr(wo_doc, 'custom_production_plant', '1'),
                'planned_start_date': wo_doc.planned_start_date,
                'planned_end_date': wo_doc.planned_end_date
            }
            
            return {
                'success': True,
                'data': work_order_data,
                'message': 'Work order data retrieved successfully'
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting work order data: {str(e)}", "Work Order Data")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get work order data'
            }
    
    def calculate_batch_cost(self, batch_name):
        """
        Calculate batch costs
        ENHANCED: More comprehensive calculation
        """
        try:
            if not frappe.db.exists('Batch AMB', batch_name):
                return {
                    'success': False,
                    'error': f'Batch {batch_name} not found'
                }
            
            batch_doc = frappe.get_doc('Batch AMB', batch_name)
            
            # Calculate costs based on your business logic
            total_cost = 0.0
            cost_per_unit = 0.0
            
            # Material costs (from BOM if available)
            if batch_doc.bom_no:
                bom_doc = frappe.get_doc('BOM', batch_doc.bom_no)
                total_material_cost = 0.0
                
                for item in bom_doc.items:
                    item_rate = frappe.db.get_value('Item Price', 
                        {'item_code': item.item_code, 'price_list': 'Standard Buying'}, 
                        'price_list_rate') or 0
                    total_material_cost += item_rate * item.qty
                
                total_cost += total_material_cost
            
            # Labor costs
            if batch_doc.labor_cost:
                total_cost += flt(batch_doc.labor_cost)
            
            # Overhead costs
            if batch_doc.overhead_cost:
                total_cost += flt(batch_doc.overhead_cost)
            
            # Calculate per unit cost
            produced_qty = flt(batch_doc.produced_qty) or 1
            cost_per_unit = total_cost / produced_qty
            
            return {
                'success': True,
                'total_batch_cost': total_cost,
                'cost_per_unit': cost_per_unit,
                'message': f'Costs calculated: Total={total_cost}, Per Unit={cost_per_unit}'
            }
            
        except Exception as e:
            frappe.log_error(f"Error calculating batch cost: {str(e)}", "Batch Cost Calculation")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to calculate batch costs'
            }
    
    def duplicate_batch(self, source_name):
        """
        Duplicate an existing batch
        ENHANCED: More comprehensive duplication
        """
        try:
            if not frappe.db.exists('Batch AMB', source_name):
                frappe.throw(f'Source batch {source_name} not found')
            
            source_doc = frappe.get_doc('Batch AMB', source_name)
            
            # Create new document
            new_doc = frappe.new_doc('Batch AMB')
            
            # Copy basic fields (exclude system fields)
            fields_to_copy = [
                'title', 'item_to_manufacture', 'batch_status', 'production_start_date',
                'production_end_date', 'planned_qty', 'company', 'source_warehouse',
                'target_warehouse', 'default_packaging_type', 'custom_batch_level'
            ]
            
            for field in fields_to_copy:
                if hasattr(source_doc, field) and field not in ['name', 'owner', 'creation']:
                    setattr(new_doc, field, getattr(source_doc, field))
            
            # Clear certain fields for new batch
            new_doc.name = None
            new_doc.title = f"{source_doc.title} (Copy)"
            new_doc.batch_status = 'Draft'
            new_doc.produced_qty = 0
            
            # Save new document
            new_doc.insert()
            
            return {
                'success': True,
                'new_name': new_doc.name,
                'message': f'Batch duplicated: {new_doc.name}'
            }
            
        except Exception as e:
            frappe.log_error(f"Error duplicating batch: {str(e)}", "Batch Duplication")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to duplicate batch'
            }
    
    # ==================== INTEGRATION METHODS ====================
    
    def sync_with_lote_amb(self):
        """Sync with Lote AMB for inventory tracking"""
        if not self.auto_create_lote:
            return
        
        # Check if Lote already exists
        existing_lote = frappe.db.get_value('Lote AMB', 
            {'batch_reference': self.name}, 
            'name'
        )
        
        if existing_lote:
            # Update existing
            lote = frappe.get_doc('Lote AMB', existing_lote)
            lote.quantity = self.produced_qty
            lote.status = self.batch_status
            lote.save(ignore_permissions=True)
        elif self.docstatus == 1:
            # Create new on submit
            self.create_lote_amb_if_needed()
    
    def update_work_order_status(self):
        """Update work order with batch information"""
        if not self.work_order:
            return
        
        try:
            wo = frappe.get_doc('Work Order', self.work_order)
            
            # Add batch reference if not exists
            batch_exists = False
            for batch_ref in wo.get('batch_references', []):
                if batch_ref.batch_no == self.name:
                    batch_ref.quantity = self.produced_qty
                    batch_exists = True
                    break
            
            if not batch_exists:
                wo.append('batch_references', {
                    'batch_no': self.name,
                    'quantity': self.produced_qty,
                    'production_date': self.production_end_date or nowdate()
                })
            
            # Update work order produced quantity
            total_produced = sum(flt(b.quantity) for b in wo.get('batch_references', []))
            wo.produced_qty = total_produced
            
            wo.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error updating Work Order: {str(e)}")
    
    def log_batch_history(self):
        """Log batch processing history"""
        if self.has_value_changed('batch_status') or self.has_value_changed('produced_qty'):
            history = frappe.new_doc('Batch Processing History')
            history.batch_reference = self.name
            history.timestamp = frappe.utils.now()
            history.event_type = 'Status Change' if self.has_value_changed('batch_status') else 'Quantity Update'
            history.old_value = self.get_doc_before_save().batch_status if self.has_value_changed('batch_status') else self.get_doc_before_save().produced_qty
            history.new_value = self.batch_status if self.has_value_changed('batch_status') else self.produced_qty
            history.modified_by = frappe.session.user
            history.insert(ignore_permissions=True)
    
    # ==================== DOCUMENT CREATION ====================
    
    def create_stock_entry(self):
        """Create stock entry for batch production"""
        if not self.auto_create_stock_entry:
            return
        
        if not self.item_to_manufacture or not self.produced_qty:
            return
        
        stock_entry = frappe.new_doc('Stock Entry')
        stock_entry.stock_entry_type = 'Manufacture'
        stock_entry.company = self.company or frappe.defaults.get_defaults().company
        stock_entry.posting_date = self.production_end_date or nowdate()
        stock_entry.posting_time = frappe.utils.nowtime()
        
        # Add finished goods
        stock_entry.append('items', {
            'item_code': self.item_to_manufacture,
            's_warehouse': None,
            't_warehouse': self.target_warehouse,
            'qty': self.produced_qty,
            'uom': self.uom,
            'stock_uom': self.uom,
            'batch_no': self.name,
            'basic_rate': self.cost_per_unit if hasattr(self, 'cost_per_unit') else 0
        })
        
        # Add raw materials from BOM if available
        if self.bom_no:
            self.add_bom_items_to_stock_entry(stock_entry)
        
        try:
            stock_entry.insert()
            stock_entry.submit()
            
            self.stock_entry_reference = stock_entry.name
            frappe.msgprint(_("Stock Entry {0} created successfully").format(stock_entry.name))
            
        except Exception as e:
            frappe.log_error(f"Error creating Stock Entry: {str(e)}")
            frappe.throw(_("Could not create Stock Entry: {0}").format(str(e)))
    
    def add_bom_items_to_stock_entry(self, stock_entry):
        """Add BOM items as raw materials to stock entry"""
        bom = frappe.get_doc('BOM', self.bom_no)
        
        for item in bom.items:
            required_qty = flt(item.qty) * flt(self.produced_qty) / flt(bom.quantity)
            
            stock_entry.append('items', {
                'item_code': item.item_code,
                's_warehouse': self.source_warehouse,
                't_warehouse': None,
                'qty': required_qty,
                'uom': item.uom,
                'stock_uom': item.stock_uom,
                'basic_rate': item.rate
            })
    
    def create_lote_amb_if_needed(self):
        """Create Lote AMB for inventory tracking"""
        if not self.auto_create_lote:
            return
        
        lote = frappe.new_doc('Lote AMB')
        lote.batch_reference = self.name
        lote.item = self.item_to_manufacture
        lote.quantity = self.produced_qty
        lote.production_date = self.production_end_date or nowdate()
        lote.warehouse = self.target_warehouse
        lote.status = 'Active'
        
        lote.insert(ignore_permissions=True)
        
        self.lote_amb_reference = lote.name
        frappe.msgprint(_("Lote AMB {0} created successfully").format(lote.name))
    
    def cancel_stock_entries(self):
        """Cancel related stock entries"""
        if self.stock_entry_reference:
            try:
                se = frappe.get_doc('Stock Entry', self.stock_entry_reference)
                if se.docstatus == 1:
                    se.cancel()
                    frappe.msgprint(_("Stock Entry {0} cancelled").format(se.name))
            except Exception as e:
                frappe.log_error(f"Error cancelling Stock Entry: {str(e)}")
    
    # ==================== STATUS & NOTIFICATIONS ====================
    
    def update_batch_status(self, status):
        """Update batch status"""
        self.db_set('batch_status', status)
        
        # Log status change
        self.add_comment('Info', f'Batch status changed to: {status}')
    
    def notify_stakeholders(self):
        """Send notifications to stakeholders"""
        if not self.notify_on_completion:
            return
        
        # Get users to notify
        recipients = []
        
        # Production manager
        if self.production_manager:
            recipients.append(self.production_manager)
        
        # Quality team
        quality_users = frappe.get_all('User', 
            filters={'role': ['like', '%Quality%']},
            pluck='email'
        )
        recipients.extend(quality_users)
        
        if recipients:
            frappe.sendmail(
                recipients=recipients,
                subject=f'Batch {self.name} Completed',
                message=f"""
                    <p>Batch <strong>{self.name}</strong> has been completed.</p>
                    <ul>
                        <li>Item: {self.item_to_manufacture}</li>
                        <li>Quantity: {self.produced_qty} {self.uom}</li>
                        <li>Production Date: {self.production_end_date}</li>
                    </ul>
                    <p><a href="{frappe.utils.get_url()}/app/batch-amb/{self.name}">View Batch</a></p>
                """,
                now=True
            )


# ==================== WHITELISTED API METHODS ====================

# Original methods (preserved and enhanced)
@frappe.whitelist()
def get_work_order_details(work_order):
    """Get work order details for batch creation"""
    wo = frappe.get_doc('Work Order', work_order)
    
    return {
        'item_to_manufacture': wo.production_item,
        'item_name': frappe.db.get_value('Item', wo.production_item, 'item_name'),
        'planned_qty': wo.qty,
        'company': wo.company,
        'bom_no': wo.bom_no,
        'source_warehouse': wo.source_warehouse,
        'target_warehouse': wo.fg_warehouse,
        'uom': frappe.db.get_value('Item', wo.production_item, 'stock_uom')
    }


@frappe.whitelist()
def calculate_batch_cost(batch_name):
    """Calculate total cost for a batch - ENHANCED VERSION"""
    batch = frappe.get_doc('Batch AMB', batch_name)
    return batch.calculate_batch_cost(batch_name)


@frappe.whitelist()
def get_available_containers(warehouse=None):
    """
    Get available container barrels from all batches
    
    Returns container barrels that are marked as 'Available' for reuse.
    Includes both draft and submitted batches (docstatus >= 0).
    
    Args:
        warehouse: Optional warehouse filter
    
    Returns:
        list: Available container barrels with parent batch details
    """
    try:
        # Build warehouse condition
        warehouse_condition = ""
        if warehouse:
            warehouse_condition = f"AND ba.warehouse = '{frappe.db.escape(warehouse)}'"
        
        # Query all available containers (include draft batches)
        available_containers = frappe.db.sql("""
            SELECT 
                cb.name,
                cb.barrel_serial_number,
                cb.packaging_type,
                cb.gross_weight,
                cb.tara_weight,
                cb.net_weight,
                cb.status,
                cb.parent as batch_id,
                ba.title as batch_title,
                ba.item_code,
                ba.work_order_ref,
                ba.docstatus
            FROM `tabContainer Barrels` cb
            INNER JOIN `tabBatch AMB` ba ON cb.parent = ba.name
            WHERE cb.status = 'Available'
            AND ba.docstatus >= 0
            AND cb.parenttype = 'Batch AMB'
            {warehouse_condition}
            ORDER BY cb.modified DESC
        """.format(warehouse_condition=warehouse_condition), as_dict=True)
        
        frappe.logger().info(f"Found {len(available_containers)} available container barrels")
        return available_containers
        
    except Exception as e:
        frappe.log_error(
            title="Error in get_available_containers",
            message=f"Error: {str(e)}\n{frappe.get_traceback()}"
        )
        return []


@frappe.whitelist()
def duplicate_batch(source_name):
    """Duplicate a batch for new production run - ENHANCED VERSION"""
    try:
        source = frappe.get_doc('Batch AMB', source_name)
        return source.duplicate_batch(source_name)
    except Exception as e:
        frappe.throw(f"Failed to duplicate batch: {str(e)}")


# NEW: BatchL2 API Methods
@frappe.whitelist()
def api_generate_batch_code(parent_batch=None, batch_level=None, work_order=None):
    """
    NEW API endpoint for generating batch codes with BatchL2 functionality
    """
    doc = frappe.new_doc('Batch AMB')
    return doc.generate_batch_code(parent_batch, batch_level, work_order)


@frappe.whitelist()
def api_get_work_order_data(work_order=None):
    """
    NEW API endpoint for getting work order data with BatchL2 enhancements
    """
    doc = frappe.new_doc('Batch AMB')
    return doc.get_work_order_data(work_order)


@frappe.whitelist()
def get_running_batch_announcements(include_companies=True, include_plants=True, include_quality=True):
    """
    Get running batch announcements for widget display
    Uses actual Batch AMB fields
    """
    try:
        # Get running batches with CORRECT field names
        batches = frappe.get_all(
            'Batch AMB',
            filters={
                'docstatus': ['!=', 2],  # Not cancelled
            },
            fields=[
                'name',
                'title',
                'item_to_manufacture',
                'item_code',
                'wo_item_name',
                'quality_status',
                'target_plant',
                'production_plant_name',
                'custom_plant_code',
                'custom_batch_level',
                'barrel_count',
                'total_net_weight',
                'wo_start_date',
                'modified',
                'creation'
            ],
            order_by='modified desc',
            limit=50
        )
        
        if not batches:
            return {
                'success': True,
                'message': 'No active batches found',
                'announcements': [],
                'grouped_announcements': {},
                'stats': {'total': 0}
            }
        
        announcements = []
        grouped = {}
        stats = {
            'total': len(batches),
            'high_priority': 0,
            'quality_check': 0,
            'container_level': 0
        }
        
        for batch in batches:
            # Determine company from plant
            company = 'Unknown'
            if batch.production_plant_name:
                company = batch.production_plant_name
            elif batch.target_plant:
                company = batch.target_plant
            
            # Create announcement object
            announcement = {
                'name': batch.name,
                'title': batch.title or batch.name,
                'batch_code': batch.name,
                'item_code': batch.item_to_manufacture or batch.item_code or 'N/A',
                'status': 'Active',  # No batch_status field, using default
                'company': company,
                'level': batch.custom_batch_level or 'Batch',
                'priority': 'high' if batch.quality_status == 'Failed' else 'medium',
                'quality_status': batch.quality_status or 'Pending',
                'content': (
                    f"Item: {batch.wo_item_name or batch.item_code or 'N/A'}\n"
                    f"Plant: {batch.custom_plant_code or 'N/A'}\n"
                    f"Weight: {batch.total_net_weight or 0}\n"
                    f"Barrels: {batch.barrel_count or 0}"
                ),
                'message': f"Level {batch.custom_batch_level or '?'} batch in production",
                'modified': str(batch.modified) if batch.modified else '',
                'creation': str(batch.creation) if batch.creation else ''
            }
            
            announcements.append(announcement)
            
            # Update stats
            if batch.quality_status == 'Failed':
                stats['high_priority'] += 1
            if batch.quality_status in ['Pending', 'In Testing']:
                stats['quality_check'] += 1
            if batch.custom_batch_level == '3':
                stats['container_level'] += 1
            
            # Group by company and plant
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
        error_msg = f"Error in get_running_batch_announcements: {str(e)}\n{traceback.format_exc()}"
        frappe.log_error(error_msg, "Batch Widget API Error")
        
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load batch data',
            'traceback': traceback.format_exc()
        }
