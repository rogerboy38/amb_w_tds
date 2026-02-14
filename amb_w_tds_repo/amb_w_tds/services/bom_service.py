import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint
from typing import Dict, List, Optional
import json

class BOMService:
    def __init__(self):
        self.bom_doctype = "BOM"
    
    def create_mrp_bom(self, batch_doc, bom_data: Dict) -> str:
        """Create MRP BOM with hierarchical cost calculation"""
        try:
            # Validate inputs
            self._validate_bom_data(bom_data)
            
            # Calculate planned quantity from batch doc (CRITICAL FIX)
            planned_qty = batch_doc.planned_qty if hasattr(batch_doc, 'planned_qty') and batch_doc.planned_qty else 1
            bom_quantity = flt(bom_data.get("quantity", planned_qty))  # Use planned_qty as default
            
            # Create BOM document
            bom = frappe.new_doc(self.bom_doctype)
            bom.update({
                "item": bom_data.get("item_code"),
                "quantity": bom_quantity,  # ✅ Use calculated bom_quantity instead of hardcoded 1
                "is_active": 1,
                "is_default": 1,
                "rm_cost_as_per": "Valuation Rate",
                "with_operations": 1,
                "transfer_material_against": "Work Order",
                "batch_amb_reference": batch_doc.name
            })
            
            # Add BOM items with hierarchical calculation
            self._add_bom_items(bom, bom_data.get("items", []), bom_quantity)  # Pass bom_quantity
            
            # Add operations if any
            if bom_data.get("operations"):
                self._add_bom_operations(bom, bom_data.get("operations"))
            
            bom.insert(ignore_permissions=True)
            
            # Calculate and update costs
            self._calculate_and_update_bom_cost(bom.name)
            
            frappe.db.commit()
            return bom.name
            
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"MRP BOM Creation Error: {str(e)}")
            raise
    
    def create_standard_bom(self, batch_doc, bom_data: Dict) -> str:
        """Create Standard BOM based on MRP BOM with finalized costs"""
        try:
            # Get MRP BOM reference
            mrp_bom = bom_data.get("mrp_bom_reference")
            if not mrp_bom:
                frappe.throw(_("MRP BOM reference is required for Standard BOM creation"))
            
            # Create standard BOM with finalized costs
            standard_bom = frappe.copy_doc(frappe.get_doc("BOM", mrp_bom))
            standard_bom.update({
                "bom_type": "Standard",
                "is_default": 1,
                "is_active": 1,
                "batch_amb_reference": batch_doc.name
            })
            
            # Finalize costs for standard BOM
            self._finalize_bom_costs(standard_bom)
            
            standard_bom.insert(ignore_permissions=True)
            frappe.db.commit()
            
            return standard_bom.name
            
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Standard BOM Creation Error: {str(e)}")
            raise
    
    def _validate_bom_data(self, bom_data: Dict):
        """Validate BOM data structure"""
        required_fields = ["item_code", "quantity"]
        for field in required_fields:
            if not bom_data.get(field):
                frappe.throw(_("Missing required field: {0}").format(field))
    
    def _add_bom_items(self, bom, items: List[Dict], bom_quantity: float = 1):
        """Add items to BOM with hierarchical cost calculation"""
        for item_data in items:
            # Scale base quantity by bom_quantity (CRITICAL FIX)
            base_qty = flt(item_data.get("quantity", 1))
            item_qty = base_qty * bom_quantity  # Scale quantities
            
            bom_item = bom.append("items", {
                "item_code": item_data.get("item_code"),
                "qty": item_qty,  # ✅ Use scaled quantity
                "uom": item_data.get("uom") or frappe.db.get_value("Item", item_data.get("item_code"), "stock_uom"),
                "rate": flt(item_data.get("rate", 0)),
                "amount": flt(item_data.get("amount", 0)),
                "include_item_in_manufacturing": 1,
                "source_warehouse": item_data.get("source_warehouse")
            })
            
            # Handle sub-assembly BOMs
            if item_data.get("has_bom"):
                sub_bom = self._get_or_create_sub_bom(item_data)
                bom_item.bom_no = sub_bom
    
    def _calculate_and_update_bom_cost(self, bom_name: str):
        """Calculate comprehensive BOM cost including all levels"""
        bom_doc = frappe.get_doc("BOM", bom_name)
        
        # Calculate raw material cost
        raw_material_cost = sum(flt(item.amount) for item in bom_doc.items)
        
        # Calculate operation cost
        operation_cost = sum(flt(op.cost_per_unit) for op in bom_doc.operations) if bom_doc.operations else 0
        
        # Calculate overhead cost (15% of material + operation cost)
        overhead_cost = (raw_material_cost + operation_cost) * 0.15
        
        # Total cost
        total_cost = raw_material_cost + operation_cost + overhead_cost
        
        # Update BOM with calculated costs
        bom_doc.db_set({
            "raw_material_cost": raw_material_cost,
            "operation_cost": operation_cost,
            "base_operation_cost": operation_cost,
            "base_raw_material_cost": raw_material_cost,
            "scrap_material_cost": 0,
            "hour_rate": 0,
            "quantity": bom_doc.quantity,
            "total_cost": total_cost
        })
        
        # Update item valuation rate if configured
        self._update_item_standard_rate(bom_doc.item, total_cost / bom_doc.quantity)
    
    def _finalize_bom_costs(self, bom_doc):
        """Finalize costs for standard BOM - lock in rates"""
        for item in bom_doc.items:
            # Use standard rates instead of valuation rates
            standard_rate = frappe.db.get_value("Item", item.item_code, "standard_rate") or item.rate
            item.rate = standard_rate
            item.amount = flt(item.qty) * flt(standard_rate)
    
    def _add_bom_operations(self, bom, operations: List[Dict]):
        """Add operations to BOM"""
        for op_data in operations:
            bom.append("operations", {
                "operation": op_data.get("operation"),
                "time_in_mins": op_data.get("time_in_mins"),
                "hour_rate": op_data.get("hour_rate"),
                "cost_per_unit": op_data.get("cost_per_unit")
            })
    
    def _get_or_create_sub_bom(self, item_data: Dict) -> str:
        """Get existing BOM or create new one for sub-assembly"""
        # Check if BOM already exists for this item
        existing_bom = frappe.db.exists("BOM", {
            "item": item_data.get("item_code"),
            "is_active": 1
        })
        
        if existing_bom:
            return existing_bom
        else:
            # Create new sub-assembly BOM
            sub_bom = frappe.new_doc("BOM")
            sub_bom.item = item_data.get("item_code")
            sub_bom.quantity = 1
            sub_bom.is_active = 1
            sub_bom.insert(ignore_permissions=True)
            return sub_bom.name
    
    def _update_item_standard_rate(self, item_code: str, new_rate: float):
        """Update item standard rate if different from current"""
        current_rate = frappe.db.get_value("Item", item_code, "standard_rate") or 0
        if abs(flt(new_rate) - flt(current_rate)) > 0.01:  # Only update if significant change
            frappe.db.set_value("Item", item_code, "standard_rate", new_rate)
