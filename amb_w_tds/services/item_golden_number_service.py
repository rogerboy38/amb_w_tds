"""
Item Golden Number Propagation Service
Ensures golden number is propagated to all related items and BOMs
"""

import frappe
from frappe import _

class ItemGoldenNumberService:
    """Service for propagating golden number to items"""
    
    @staticmethod
    def propagate_to_items(batch):
        """
        Propagate golden number to all items created from this batch
        Level 0: Main product item (golden_number)
        Level 1: Sub-lot items (golden_number-1, golden_number-2)
        Level 2: Component items (golden_number-Utility-1, etc.)
        """
        try:
            if not batch.golden_number:
                frappe.throw(_("Golden number is required"))
            
            # Add golden number custom field to Item if not exists
            ItemGoldenNumberService._ensure_item_custom_field()
            
            # Propagate to main product item
            ItemGoldenNumberService._set_item_golden_number(
                batch.golden_number,
                batch.golden_number
            )
            
            # Propagate to all related items from BOMs
            if batch.bom_reference:
                ItemGoldenNumberService._propagate_to_bom_items(
                    batch.bom_reference,
                    batch.golden_number
                )
            
            frappe.msgprint(_("Golden number propagated to all items"))
            
        except Exception as e:
            frappe.log_error(f"Item Golden Number Propagation Error: {str(e)}", 
                           "Item Golden Number Service")
            frappe.throw(_("Failed to propagate golden number: {0}").format(str(e)))
    
    @staticmethod
    def _ensure_item_custom_field():
        """Ensure Item has golden_number custom field"""
        if not frappe.db.exists("Custom Field", "Item-golden_number"):
            custom_field = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Item",
                "fieldname": "golden_number",
                "fieldtype": "Data",
                "label": "Golden Number",
                "read_only": 1,
                "insert_after": "item_code",
                "description": "Golden number from batch manufacturing"
            })
            custom_field.insert(ignore_permissions=True)
            frappe.db.commit()
    
    @staticmethod
    def _set_item_golden_number(item_code, golden_number):
        """Set golden number for an item"""
        if frappe.db.exists("Item", item_code):
            try:
                item = frappe.get_doc("Item", item_code)
                if hasattr(item, 'golden_number'):
                    item.golden_number = golden_number
                    item.save(ignore_permissions=True)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Error setting golden number for {item_code}: {str(e)}", 
                               "Item Golden Number")
    
    @staticmethod
    def _propagate_to_bom_items(bom_name, golden_number):
        """Propagate golden number to all items in BOM hierarchy"""
        try:
            bom = frappe.get_doc("BOM", bom_name)
            
            # Set golden number for all items in this BOM
            for item in bom.items:
                ItemGoldenNumberService._set_item_golden_number(
                    item.item_code,
                    golden_number
                )
                
                # If item has its own BOM, propagate recursively
                item_bom = frappe.db.get_value("Item", item.item_code, "default_bom")
                if item_bom:
                    ItemGoldenNumberService._propagate_to_bom_items(
                        item_bom,
                        golden_number
                    )
        
        except Exception as e:
            frappe.log_error(f"Error propagating to BOM items: {str(e)}", 
                           "Item Golden Number")
    
    @staticmethod
    def validate_item_golden_number(item_code, expected_golden_number):
        """Validate that item has correct golden number"""
        if not frappe.db.exists("Item", item_code):
            return False, "Item does not exist"
        
        item = frappe.get_doc("Item", item_code)
        
        if not hasattr(item, 'golden_number'):
            return False, "Item does not have golden_number field"
        
        if item.golden_number != expected_golden_number:
            return False, f"Golden number mismatch: expected {expected_golden_number}, got {item.golden_number}"
        
        return True, "Valid"
    
    @staticmethod
    def sync_golden_numbers_across_hierarchy(batch):
        """
        Sync golden numbers across entire hierarchy
        Batch AMB → BOM → Items → Work Orders → Projects
        """
        try:
            if not batch.golden_number:
                return
            
            # 1. Propagate to items
            ItemGoldenNumberService.propagate_to_items(batch)
            
            # 2. Ensure BOM has golden number
            if batch.bom_reference:
                ItemGoldenNumberService._sync_bom_golden_number(
                    batch.bom_reference,
                    batch.golden_number
                )
            
            # 3. Ensure Work Order has golden number
            if batch.work_order_ref:
                ItemGoldenNumberService._sync_work_order_golden_number(
                    batch.work_order_ref,
                    batch.golden_number
                )
            
            # 4. Ensure Project exists with golden number as ID
            ItemGoldenNumberService._ensure_project_exists(
                batch.golden_number,
                batch
            )
            
            frappe.msgprint(_("Golden numbers synced across hierarchy"))
            
        except Exception as e:
            frappe.log_error(f"Hierarchy Sync Error: {str(e)}", 
                           "Golden Number Hierarchy")
    
    @staticmethod
    def _sync_bom_golden_number(bom_name, golden_number):
        """Sync golden number to BOM"""
        if frappe.db.exists("Custom Field", "BOM-golden_number"):
            bom = frappe.get_doc("BOM", bom_name)
            if hasattr(bom, 'golden_number'):
                bom.golden_number = golden_number
                bom.project = golden_number  # Use golden number as project
                bom.save(ignore_permissions=True)
                frappe.db.commit()
    
    @staticmethod
    def _sync_work_order_golden_number(work_order_name, golden_number):
        """Sync golden number to Work Order"""
        if frappe.db.exists("Custom Field", "Work Order-golden_number"):
            wo = frappe.get_doc("Work Order", work_order_name)
            if hasattr(wo, 'golden_number'):
                wo.golden_number = golden_number
                wo.project = golden_number  # Use golden number as project
                wo.save(ignore_permissions=True)
                frappe.db.commit()
    
    @staticmethod
    def _ensure_project_exists(golden_number, batch):
        """Ensure project exists with golden number as ID"""
        if not frappe.db.exists("Project", golden_number):
            try:
                project = frappe.new_doc("Project")
                project.project_name = golden_number
                project.name = golden_number
                project.status = "Open"
                
                # Set dates if available
                if hasattr(batch, 'production_start_date') and batch.production_start_date:
                    project.expected_start_date = batch.production_start_date
                if hasattr(batch, 'production_end_date') and batch.production_end_date:
                    project.expected_end_date = batch.production_end_date
                
                project.insert(ignore_permissions=True)
                frappe.db.commit()
                
            except Exception as e:
                frappe.log_error(f"Error creating project {golden_number}: {str(e)}", 
                               "Project Creation")


@frappe.whitelist()
def propagate_golden_number(batch_name):
    """API endpoint for propagating golden number"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        ItemGoldenNumberService.propagate_to_items(batch)
        
        return {
            "success": True,
            "message": _("Golden number propagated successfully")
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def sync_hierarchy(batch_name):
    """API endpoint for syncing entire hierarchy"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        ItemGoldenNumberService.sync_golden_numbers_across_hierarchy(batch)
        
        return {
            "success": True,
            "message": _("Hierarchy synced successfully")
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
