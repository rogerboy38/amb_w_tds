import frappe
import json
from frappe.utils import flt
from datetime import datetime

@frappe.whitelist()
def validate_and_fix_bom(bom_name, auto_fix=True):
    """
    Validates and fixes BOM operation times and workstation assignments
    Based on actual production errors from MFG-WO-02225 type issues
    """
    try:
        bom = frappe.get_doc("BOM", bom_name)
        issues = []
        fixes_applied = []
        
        # Fix operation times if missing or invalid
        for operation in bom.operations:
            if not operation.time_in_mins or operation.time_in_mins <= 0:
                issue = f"Operation '{operation.operation}' missing time_in_mins"
                issues.append(issue)
                
                if auto_fix:
                    default_time = get_default_operation_time(operation.operation)
                    operation.time_in_mins = default_time
                    fix = f"Set {operation.operation} time to {default_time} minutes"
                    fixes_applied.append(fix)
        
        # Fix workstation assignments if missing
        for operation in bom.operations:
            if not operation.workstation or operation.workstation == "":
                issue = f"Operation '{operation.operation}' missing workstation"
                issues.append(issue)
                
                if auto_fix:
                    default_ws = get_default_workstation(operation.operation)
                    operation.workstation = default_ws
                    fix = f"Set {operation.operation} workstation to {default_ws}"
                    fixes_applied.append(fix)
        
        # Save changes if auto_fix is enabled
        if auto_fix and fixes_applied:
            bom.save()
            frappe.db.commit()
        
        return {
            "status": "success",
            "bom_name": bom_name,
            "issues_found": len(issues),
            "fixes_applied": len(fixes_applied),
            "issues": issues,
            "fixes": fixes_applied
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "bom_name": bom_name
        }

@frappe.whitelist()
def create_work_order_from_bom(bom_name, quantity=None, production_item=None):
    """
    Creates a work order from a BOM with all required fields populated
    Handles common MFG-WO creation errors
    """
    try:
        # Get BOM details
        bom = frappe.get_doc("BOM", bom_name)
        
        if not quantity:
            quantity = bom.quantity
            
        if not production_item:
            production_item = bom.item
            
        # Create work order
        wo_doc = frappe.new_doc("Work Order")
        wo_doc.production_item = production_item
        wo_doc.bom_no = bom_name
        wo_doc.qty = quantity
        wo_doc.fg_warehouse = get_default_fg_warehouse()
        wo_doc.wip_warehouse = get_default_wip_warehouse()
        wo_doc.scrap_warehouse = get_default_scrap_warehouse()
        
        # Set default values
        wo_doc.planned_start_date = frappe.utils.now()
        wo_doc.planned_end_date = frappe.utils.add_days(frappe.utils.now(), 7)
        wo_doc.company = frappe.defaults.get_defaults().get("company") or "AMB Wellness"
        
        # Save and submit
        wo_doc.insert()
        frappe.db.commit()
        
        return {
            "status": "success",
            "work_order": wo_doc.name,
            "bom": bom_name,
            "quantity": quantity,
            "message": f"Work Order {wo_doc.name} created successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "bom": bom_name
        }

@frappe.whitelist()
def diagnose_and_fix_work_order(work_order_name):
    """
    Comprehensive work order diagnosis and automated fixes
    Identifies and resolves MFG-WO-02225 type errors
    """
    try:
        wo = frappe.get_doc("Work Order", work_order_name)
        issues = []
        fixes = []
        
        # Check BOM validity
        if wo.bom_no:
            try:
                bom = frappe.get_doc("BOM", wo.bom_no)
                if not bom.operations:
                    issue = "BOM has no operations defined"
                    issues.append(issue)
                    fix = "Add operations to BOM or use default operations"
                    fixes.append(fix)
            except:
                issue = f"BOM {wo.bom_no} not found or invalid"
                issues.append(issue)
                fix = f"Update work order with valid BOM or set BOM to blank"
                fixes.append(fix)
        else:
            issue = "Work Order has no BOM assigned"
            issues.append(issue)
            fix = "Assign valid BOM or set BOM to allow work order creation"
            fixes.append(fix)
        
        # Check required fields
        required_fields = ["production_item", "qty", "fg_warehouse", "wip_warehouse"]
        for field in required_fields:
            if not getattr(wo, field):
                issue = f"Missing required field: {field}"
                issues.append(issue)
                fix = f"Set {field} to valid value"
                fixes.append(fix)
        
        # Fix BOM if missing and item has default BOM
        if not wo.bom_no and wo.production_item:
            default_bom = get_default_bom_for_item(wo.production_item)
            if default_bom:
                wo.bom_no = default_bom
                fix = f"Assigned default BOM {default_bom} to work order"
                fixes.append(fix)
        
        # Fix warehouses if missing
        if not wo.fg_warehouse:
            wo.fg_warehouse = get_default_fg_warehouse()
            fix = f"Set fg_warehouse to {wo.fg_warehouse}"
            fixes.append(fix)
            
        if not wo.wip_warehouse:
            wo.wip_warehouse = get_default_wip_warehouse()
            fix = f"Set wip_warehouse to {wo.wip_warehouse}"
            fixes.append(fix)
        
        # Save fixes
        if fixes:
            wo.save()
            frappe.db.commit()
        
        return {
            "status": "success",
            "work_order": work_order_name,
            "issues": issues,
            "fixes_applied": fixes,
            "total_issues": len(issues),
            "total_fixes": len(fixes)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "work_order": work_order_name
        }

@frappe.whitelist()
def quick_fix_bom_operations(bom_name):
    """
    Quick fix for BOM operation times and workstations
    Optimized for speed over comprehensive validation
    """
    try:
        bom = frappe.get_doc("BOM", bom_name)
        fixes = []
        
        for operation in bom.operations:
            # Quick time fix
            if not operation.time_in_mins or operation.time_in_mins <= 0:
                operation.time_in_mins = 30  # Default 30 minutes
                fixes.append(f"Set {operation.operation} time to 30 mins")
            
            # Quick workstation fix
            if not operation.workstation:
                operation.workstation = "Assembly Line"  # Default workstation
                fixes.append(f"Set {operation.operation} workstation to Assembly Line")
        
        if fixes:
            bom.save()
            frappe.db.commit()
        
        return {
            "status": "success",
            "bom": bom_name,
            "fixes": fixes,
            "count": len(fixes)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "bom": bom_name
        }

@frappe.whitelist()
def quick_work_order_diagnosis(work_order_name):
    """
    Quick work order error identification
    Rapid diagnosis for common issues
    """
    try:
        wo = frappe.get_doc("Work Order", work_order_name)
        errors = []
        
        # Check critical fields
        if not wo.production_item:
            errors.append("Missing production_item")
            
        if not wo.bom_no:
            errors.append("Missing BOM assignment")
            
        if not wo.qty or wo.qty <= 0:
            errors.append("Invalid quantity")
            
        if not wo.fg_warehouse:
            errors.append("Missing fg_warehouse")
            
        # Check BOM operations
        if wo.bom_no:
            try:
                bom = frappe.get_doc("BOM", wo.bom_no)
                if not bom.operations:
                    errors.append("BOM has no operations")
                else:
                    for op in bom.operations:
                        if not op.time_in_mins or op.time_in_mins <= 0:
                            errors.append(f"BOM operation '{op.operation}' missing time")
                            break
            except:
                errors.append("Invalid or missing BOM")
        
        return {
            "status": "success" if not errors else "warning",
            "work_order": work_order_name,
            "errors": errors,
            "error_count": len(errors)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "work_order": work_order_name
        }

@frappe.whitelist()
def create_work_order_simple(item_code, quantity=1):
    """
    Simplified work order creation with auto-generated BOM
    For items without existing BOMs
    """
    try:
        # Create temporary BOM
        bom_name = f"TEMP-BOM-{item_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        bom_doc = frappe.new_doc("BOM")
        bom_doc.item = item_code
        bom_doc.quantity = quantity
        bom_doc.company = frappe.defaults.get_defaults().get("company") or "AMB Wellness"
        
        # Add default operation
        operation = bom_doc.append("operations")
        operation.operation = "Manufacturing"
        operation.workstation = "Assembly Line"
        operation.time_in_mins = 60
        
        bom_doc.insert()
        frappe.db.commit()
        
        # Create work order with temp BOM
        wo_doc = frappe.new_doc("Work Order")
        wo_doc.production_item = item_code
        wo_doc.bom_no = bom_name
        wo_doc.qty = quantity
        wo_doc.fg_warehouse = get_default_fg_warehouse()
        wo_doc.wip_warehouse = get_default_wip_warehouse()
        wo_doc.planned_start_date = frappe.utils.now()
        wo_doc.company = bom_doc.company
        
        wo_doc.insert()
        frappe.db.commit()
        
        return {
            "status": "success",
            "work_order": wo_doc.name,
            "temp_bom": bom_name,
            "item": item_code,
            "quantity": quantity,
            "message": f"Work Order {wo_doc.name} created with temporary BOM"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "item": item_code
        }

# Helper functions
def get_default_operation_time(operation_name):
    """Get default operation time based on operation type"""
    operation_times = {
        "Cutting": 15,
        "Assembly": 45,
        "Quality Check": 20,
        "Packaging": 10,
        "Manufacturing": 60,
        "Processing": 30
    }
    return operation_times.get(operation_name, 30)

def get_default_workstation(operation_name):
    """Get default workstation based on operation type"""
    workstations = {
        "Cutting": "Cutting Station",
        "Assembly": "Assembly Line",
        "Quality Check": "QC Station",
        "Packaging": "Packaging Line",
        "Manufacturing": "Assembly Line",
        "Processing": "Processing Unit"
    }
    return workstations.get(operation_name, "Assembly Line")

def get_default_bom_for_item(item_code):
    """Get default BOM for an item"""
    try:
        bom_list = frappe.get_all("BOM", 
                                filters={"item": item_code, "is_active": 1},
                                fields=["name"],
                                order_by="creation desc",
                                limit=1)
        return bom_list[0].name if bom_list else None
    except:
        return None

def get_default_fg_warehouse():
    """Get default finished goods warehouse"""
    return "Finished Goods - AW"  # Adjust based on actual warehouse setup

def get_default_wip_warehouse():
    """Get default work-in-progress warehouse"""
    return "Work In Progress - AW"  # Adjust based on actual warehouse setup

def get_default_scrap_warehouse():
    """Get default scrap warehouse"""
    return "Scrap Warehouse - AW"  # Adjust based on actual warehouse setup
