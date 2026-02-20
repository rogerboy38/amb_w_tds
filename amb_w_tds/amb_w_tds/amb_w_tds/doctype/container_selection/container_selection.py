"""
Enhanced Container Selection Controller for amb_w_tds
Integrates with Batch AMB Container Barrels bidirectional sync
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, flt, get_datetime
import json
import time

class ContainerSelection(Document):
    """Enhanced Container Selection with weight tracking and sync"""
    
    def before_save(self):
        """Execute before saving the document"""
        # Calculate weights if gross weight is provided
        if self.gross_weight:
            self.calculate_weights()
        
        # Set tara weight from Item master if not set
        if not self.tara_weight and self.container_type:
            self.set_tara_weight_from_item()
        
        # Validate partial fill if applicable
        if self.gross_weight and self.tara_weight:
            self.validate_partial_fill()
    
    def after_save(self):
        """Execute after saving the document"""
        # Trigger sync to Batch AMB if linked
        if self.batch_amb_link and self.sync_status != 'Synced':
            self.trigger_sync()
    
    def validate(self):
        """Validate container data before save"""
        # Validate weight data
        if self.gross_weight and self.tara_weight:
            if self.gross_weight < self.tara_weight:
                frappe.throw(_("Gross weight cannot be less than tara weight"))
        
        # Validate lifecycle status transitions
        self.validate_lifecycle_transition()
    
    def calculate_weights(self):
        """Calculate net weight and variance"""
        if self.gross_weight and self.tara_weight:
            self.net_weight = flt(self.gross_weight - self.tara_weight, 3)
            
            # Calculate variance percentage if expected weight exists
            if self.expected_weight:
                variance = abs(self.net_weight - self.expected_weight) / self.expected_weight
                self.weight_variance_percentage = flt(variance * 100, 2)
                
                # Check if within 1% tolerance
                self.is_within_tolerance = 1 if variance <= 0.01 else 0
    
    def set_tara_weight_from_item(self):
        """Get tara weight from Item master based on container type"""
        if self.container_type:
            try:
                # Try to get item document
                item = frappe.get_doc('Item', self.container_type)
                # Get weight from Item master (assuming weight_per_unit field)
                if hasattr(item, 'weight_per_unit') and item.weight_per_unit:
                    self.tara_weight = flt(item.weight_per_unit, 3)
                elif hasattr(item, 'net_weight') and item.net_weight:
                    self.tara_weight = flt(item.net_weight, 3)
            except:
                # If item not found, use defaults based on container type
                default_weights = {
                    '220L Barrel': 15.0,
                    '1000L IBC': 45.0,
                    '20L Pail': 2.5,
                    'Industrial Bag': 0.5
                }
                self.tara_weight = default_weights.get(self.container_type, 0.0)
    
    def validate_partial_fill(self):
        """Validate and handle partial fill scenarios"""
        if not self.net_weight:
            return
        
        # Get expected capacity from container type
        expected_capacity = self.get_container_capacity()
        if not expected_capacity:
            return
        
        # Calculate fill percentage
        fill_percentage = (self.net_weight / expected_capacity) * 100
        self.fill_percentage = flt(fill_percentage, 2)
        
        # Determine if it's a partial fill
        if fill_percentage < 10:
            # Below minimum threshold - reject
            frappe.throw(_("Fill percentage ({0}%) is below minimum threshold (10%). Container rejected.").format(fill_percentage))
        elif fill_percentage < 95:
            # Partial fill
            self.is_partial_fill = 1
            self.lifecycle_status = "Partial_Fill"
        else:
            # Normal fill
            self.is_partial_fill = 0
            if self.lifecycle_status == "Partial_Fill":
                self.lifecycle_status = "Completed"
    
    def get_container_capacity(self):
        """Get container capacity based on type"""
        capacities = {
            '220L Barrel': 220.0,
            '1000L IBC': 1000.0,
            '20L Pail': 20.0,
            'Industrial Bag': 25.0  # kg capacity
        }
        return capacities.get(self.container_type, 0.0)
    
    def validate_lifecycle_transition(self):
        """Validate container lifecycle status transitions"""
        if self.is_new():
            return
        
        old_doc = self.get_doc_before_save()
        if not old_doc or not old_doc.lifecycle_status:
            return
        
        old_status = old_doc.lifecycle_status
        new_status = self.lifecycle_status
        
        # Define valid transitions
        valid_transitions = {
            'Planned': ['Reserved', 'Available'],
            'Reserved': ['In_Use', 'Available'],
            'In_Use': ['Completed', 'Partial_Fill', 'Available'],
            'Completed': ['Available', 'Retired'],
            'Partial_Fill': ['Completed', 'Available'],
            'Available': ['Reserved', 'Retired'],
            'Retired': []  # Final state
        }
        
        if old_status != new_status:
            allowed_states = valid_transitions.get(old_status, [])
            if new_status not in allowed_states:
                frappe.throw(_("Invalid lifecycle transition from {0} to {1}").format(old_status, new_status))
    
    def trigger_sync(self):
        """Trigger synchronization with Batch AMB"""
        try:
            # Create sync log entry
            sync_log = frappe.get_doc({
                'doctype': 'Container Sync Log',
                'container_selection': self.name,
                'batch_amb': self.batch_amb_link,
                'sync_direction': 'CS_to_Batch',
                'sync_status': 'Success',
                'sync_timestamp': now(),
                'synced_fields': json.dumps({
                    'gross_weight': self.gross_weight,
                    'tara_weight': self.tara_weight,
                    'net_weight': self.net_weight,
                    'lifecycle_status': self.lifecycle_status,
                    'is_partial_fill': self.is_partial_fill
                })
            })
            sync_log.insert(ignore_permissions=True)
            
            # Update sync status
            self.sync_status = 'Synced'
            self.last_synced = now()
            
        except Exception as e:
            frappe.log_error(f"Container sync failed: {str(e)}", "Container Sync Error")
            self.sync_status = 'Error'
            self.sync_error = str(e)

# API Methods for mobile scanning and integration
@frappe.whitelist()
def scan_barcode(barcode, plant=None):
    """Handle barcode scanning for containers"""
    try:
        # Find container by barcode/serial number
        containers = frappe.get_all(
            'Container Selection',
            filters={'serial_number': barcode},
            fields=['name', 'container_type', 'lifecycle_status', 'gross_weight', 'net_weight']
        )
        
        if containers:
            container = containers[0]
            # Update scan timestamp
            frappe.db.set_value('Container Selection', container.name, {
                'barcode_scanned_at': now(),
                'scanned_by': frappe.session.user
            })
            
            return {
                'success': True,
                'container': container,
                'message': 'Container found and scan recorded'
            }
        else:
            return {
                'success': False,
                'message': 'Container not found with barcode: ' + barcode
            }
            
    except Exception as e:
        frappe.log_error(f"Barcode scan error: {str(e)}", "Barcode Scan Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def calculate_weights(container_name, gross_weight):
    """Calculate weights for a container"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        container.gross_weight = flt(gross_weight, 3)
        container.calculate_weights()
        container.save()
        
        return {
            'success': True,
            'net_weight': container.net_weight,
            'tara_weight': container.tara_weight,
            'variance_percentage': container.weight_variance_percentage,
            'is_within_tolerance': container.is_within_tolerance
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def assign_to_batch(container_name, batch_amb_name):
    """Assign container to a Batch AMB"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        container.batch_amb_link = batch_amb_name
        container.lifecycle_status = 'Reserved'
        container.reserved_date = now()
        container.save()
        
        return {
            'success': True,
            'message': f'Container assigned to batch {batch_amb_name}'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_available_containers(plant=None, container_type=None):
    """Get available containers for assignment"""
    filters = {'lifecycle_status': 'Available'}
    
    if plant:
        filters['plant'] = plant
    if container_type:
        filters['container_type'] = container_type
    
    containers = frappe.get_all(
        'Container Selection',
        filters=filters,
        fields=['name', 'serial_number', 'container_type', 'net_weight', 'last_synced'],
        order_by='creation desc'
    )
    
    return {'success': True, 'containers': containers}

@frappe.whitelist()
def update_status(container_name, new_status):
    """Update container lifecycle status"""
    try:
        container = frappe.get_doc('Container Selection', container_name)
        old_status = container.lifecycle_status
        container.lifecycle_status = new_status
        
        # Set completion date if moving to completed
        if new_status == 'Completed':
            container.completed_date = now()
        
        container.save()
        
        return {
            'success': True,
            'message': f'Status updated from {old_status} to {new_status}'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}