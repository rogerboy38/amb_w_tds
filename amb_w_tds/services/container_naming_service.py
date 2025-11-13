"""
Container Naming Service
Generates golden-number-based container names
Format: 0227022253-2-C1 (golden_number-sublot-container)
"""

import frappe
from frappe import _

class ContainerNamingService:
    """Service for golden-number-based container naming"""
    
    @staticmethod
    def generate_container_name(batch, container_sequence):
        """
        Generate container name with golden number
        Args:
            batch: Batch AMB document (Level 2 or 3)
            container_sequence: Container number (C1, C2, C3, etc.)
        Returns:
            Container name: 0227022253-2-C1
        """
        try:
            # Get golden number from batch or parent
            golden_number = ContainerNamingService._get_golden_number(batch)
            
            # Get sub-lot number
            sublot_number = ContainerNamingService._get_sublot_number(batch, golden_number)
            
            # Format: golden_number-sublot-container
            container_name = f"{golden_number}-{sublot_number}-C{container_sequence}"
            
            return container_name
            
        except Exception as e:
            frappe.log_error(f"Container Naming Error: {str(e)}", "Container Naming Service")
            return None
    
    @staticmethod
    def _get_golden_number(batch):
        """Extract golden number from batch"""
        # Try direct golden number field
        if hasattr(batch, 'golden_number') and batch.golden_number:
            return batch.golden_number
        
        # Try from title
        if batch.title and '-' in batch.title:
            # Format: 0227022253-2
            parts = batch.title.split('-')
            if len(parts[0]) == 10 and parts[0].isdigit():
                return parts[0]
        
        # Try from parent batch
        if hasattr(batch, 'parent_batch') and batch.parent_batch:
            parent = frappe.get_doc("Batch AMB", batch.parent_batch)
            return ContainerNamingService._get_golden_number(parent)
        
        frappe.throw(_("Could not determine golden number for batch {0}").format(batch.name))
    
    @staticmethod
    def _get_sublot_number(batch, golden_number):
        """Extract sub-lot number from batch"""
        # If title is in format: 0227022253-2
        if batch.title and batch.title.startswith(golden_number):
            parts = batch.title.replace(golden_number, '').split('-')
            for part in parts:
                if part.isdigit():
                    return part
        
        # Default to 1 if Level 2 batch
        if hasattr(batch, 'custom_batch_level'):
            if str(batch.custom_batch_level) == '2':
                return '1'
            elif str(batch.custom_batch_level) == '3':
                # Try to extract from parent
                if hasattr(batch, 'parent_batch') and batch.parent_batch:
                    parent = frappe.get_doc("Batch AMB", batch.parent_batch)
                    return ContainerNamingService._get_sublot_number(parent, golden_number)
        
        return '1'  # Default
    
    @staticmethod
    def get_next_container_sequence(batch):
        """Get next container sequence number"""
        if not hasattr(batch, 'container_barrels'):
            return 1
        
        max_seq = 0
        for container in batch.container_barrels:
            if hasattr(container, 'container_sequence'):
                max_seq = max(max_seq, int(container.container_sequence or 0))
        
        return max_seq + 1
    
    @staticmethod
    def validate_container_name(container_name):
        """Validate container name format"""
        # Expected: 0227022253-2-C1
        parts = container_name.split('-')
        
        if len(parts) < 3:
            return False, "Container name must have format: golden_number-sublot-container"
        
        # Validate golden number (10 digits)
        if len(parts[0]) != 10 or not parts[0].isdigit():
            return False, "Golden number must be 10 digits"
        
        # Validate sublot number
        if not parts[1].isdigit():
            return False, "Sub-lot number must be numeric"
        
        # Validate container (C1, C2, etc.)
        if not parts[2].startswith('C'):
            return False, "Container must start with 'C'"
        
        return True, "Valid container name"
    
    @staticmethod
    def create_level3_batch_for_container(parent_batch, container_sequence):
        """Create Level 3 Batch AMB for a container"""
        try:
            # Generate container name
            container_name = ContainerNamingService.generate_container_name(
                parent_batch, container_sequence
            )
            
            if not container_name:
                frappe.throw(_("Failed to generate container name"))
            
            # Create Level 3 batch
            level3_batch = frappe.new_doc("Batch AMB")
            level3_batch.title = container_name
            level3_batch.custom_generated_batch_name = container_name
            level3_batch.custom_batch_level = '3'
            level3_batch.parent_batch = parent_batch.name
            
            # Copy golden number from parent
            if hasattr(parent_batch, 'golden_number'):
                level3_batch.golden_number = parent_batch.golden_number
            
            # Copy other relevant fields
            if hasattr(parent_batch, 'work_order_ref'):
                level3_batch.work_order_ref = parent_batch.work_order_ref
            
            level3_batch.insert(ignore_permissions=True)
            frappe.db.commit()
            
            return level3_batch
            
        except Exception as e:
            frappe.log_error(f"Level 3 Batch Creation Error: {str(e)}", "Container Naming Service")
            frappe.throw(_("Failed to create Level 3 batch: {0}").format(str(e)))


@frappe.whitelist()
def generate_container_name(batch_name, container_sequence):
    """API endpoint for container name generation"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        container_name = ContainerNamingService.generate_container_name(batch, container_sequence)
        
        return {
            "success": True,
            "container_name": container_name
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def create_container_batch(parent_batch_name, container_sequence):
    """API endpoint to create Level 3 batch for container"""
    try:
        parent_batch = frappe.get_doc("Batch AMB", parent_batch_name)
        level3_batch = ContainerNamingService.create_level3_batch_for_container(
            parent_batch, container_sequence
        )
        
        return {
            "success": True,
            "message": _("Container batch created"),
            "batch_name": level3_batch.name,
            "container_name": level3_batch.title
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
