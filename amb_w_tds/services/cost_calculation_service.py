import frappe
from frappe import _
from frappe.utils import flt
from typing import Dict, List

class CostCalculationService:
    def __init__(self):
        pass
    
    def calculate_hierarchical_bom_cost(self, bom_name: str) -> Dict:
        """Calculate BOM cost including all sub-levels"""
        bom_doc = frappe.get_doc("BOM", bom_name)
        
        cost_breakdown = {
            "raw_material_cost": 0,
            "sub_assembly_cost": 0,
            "operation_cost": 0,
            "overhead_cost": 0,
            "total_cost": 0,
            "cost_per_unit": 0,
            "breakdown": []
        }
        
        # Calculate costs for each item
        for item in bom_doc.items:
            item_cost = self._calculate_item_cost(item)
            cost_breakdown["breakdown"].append(item_cost)
            
            if item.bom_no:  # Sub-assembly
                cost_breakdown["sub_assembly_cost"] += item_cost["total_amount"]
            else:  # Raw material
                cost_breakdown["raw_material_cost"] += item_cost["total_amount"]
        
        # Add operation costs
        cost_breakdown["operation_cost"] = sum(
            flt(op.cost_per_unit) for op in bom_doc.operations
        ) if bom_doc.operations else 0
        
        # Calculate overhead (15% of direct costs)
        direct_costs = cost_breakdown["raw_material_cost"] + cost_breakdown["sub_assembly_cost"] + cost_breakdown["operation_cost"]
        cost_breakdown["overhead_cost"] = direct_costs * 0.15
        
        # Total cost
        cost_breakdown["total_cost"] = direct_costs + cost_breakdown["overhead_cost"]
        cost_breakdown["cost_per_unit"] = cost_breakdown["total_cost"] / flt(bom_doc.quantity)
        
        return cost_breakdown
    
    def _calculate_item_cost(self, bom_item) -> Dict:
        """Calculate cost for individual BOM item"""
        if bom_item.bom_no:  # Sub-assembly with its own BOM
            sub_bom_cost = self.calculate_hierarchical_bom_cost(bom_item.bom_no)
            item_cost = sub_bom_cost["cost_per_unit"] * flt(bom_item.qty)
        else:  # Raw material
            # Use valuation rate or standard rate
            valuation_rate = frappe.db.get_value("Item", bom_item.item_code, "valuation_rate") or 0
            item_cost = flt(bom_item.qty) * flt(valuation_rate or bom_item.rate)
        
        return {
            "item_code": bom_item.item_code,
            "quantity": bom_item.qty,
            "rate": item_cost / flt(bom_item.qty) if bom_item.qty else 0,
            "total_amount": item_cost,
            "is_sub_assembly": bool(bom_item.bom_no)
        }
