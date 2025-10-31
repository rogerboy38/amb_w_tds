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
    Consolidated from client and server scripts
    """
    
    def validate(self):
        """Validation before saving"""
        self.validate_production_dates()
        self.validate_quantities()
        self.validate_work_order()
        self.validate_containers()
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


# ==================== WHITELISTED METHODS ====================

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
    """Calculate total cost for a batch"""
    batch = frappe.get_doc('Batch AMB', batch_name)
    batch.calculate_costs()
    
    return {
        'total_batch_cost': batch.total_batch_cost,
        'cost_per_unit': batch.cost_per_unit
    }

@frappe.whitelist()
def get_available_containers(warehouse=None):
    """
    Get available empty containers from Container Barrels across all batches
    
    Returns container barrels that are marked as 'Available' for reuse.
    Container Barrels now have a 'status' field to track availability.
    
    Args:
        warehouse: Optional warehouse filter (not yet implemented)
    
    Returns:
        list: Available container barrels with details
    """
    try:
        # Get all submitted batches
        batches = frappe.get_all(
            'Batch AMB',
            filters={'docstatus': 1},  # Only submitted batches
            fields=['name', 'title']
        )
        
        available_containers = []
        
        for batch in batches:
            # Get available container barrels from this batch
            containers = frappe.get_all(
                'Container Barrels',
                filters={
                    'parent': batch.name,
                    'parenttype': 'Batch AMB',
                    'status': 'Available'
                },
                fields=[
                    'name', 
                    'barrel_serial_number', 
                    'packaging_type',
                    'gross_weight',
                    'tara_weight',
                    'net_weight',
                    'status',
                    'parent as batch_name'
                ],
                order_by='barrel_serial_number'
            )
            
            # Add batch title to each container
            for container in containers:
                container['batch_title'] = batch.title
            
            available_containers.extend(containers)
        
        return available_containers
        
    except Exception as e:
        frappe.log_error(
            f"Error in get_available_containers: {str(e)}", 
            "Batch AMB - Get Available Containers"
        )
        return []

@frappe.whitelist()
def duplicate_batch(source_name):
    """Duplicate a batch for new production run"""
    source = frappe.get_doc('Batch AMB', source_name)
    
    new_batch = frappe.copy_doc(source)
    new_batch.batch_status = 'Draft'
    new_batch.docstatus = 0
    new_batch.produced_qty = 0
    new_batch.production_start_date = None
    new_batch.production_end_date = None
    new_batch.stock_entry_reference = None
    new_batch.lote_amb_reference = None
    
    # Clear container data
    new_batch.container_barrels = []
    
    new_batch.insert()
    
    return new_batch.name
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
