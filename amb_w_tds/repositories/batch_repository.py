import frappe
from frappe import _
from typing import Dict, List, Optional

class BatchRepository:
    def __init__(self):
        self.doctype = "Batch AMB"
    """Data access layer for Batch AMB"""
    
    @staticmethod
    def get_batch_with_bom(batch_name):
        """Retrieve batch with associated BOM details"""
        return frappe.get_doc("Batch AMB", batch_name)
    
    @staticmethod
    def get_batches_by_product_code(product_code):
        """Get all batches for specific product code"""
        return frappe.get_all("Batch AMB",
            filters={"item_code": product_code},
            fields=["name", "title", "bom_reference", "quality_status"]
        )


    
    def get_batch_with_items(self, batch_name: str) -> Dict:
        """Get batch document with preloaded items"""
        batch = frappe.get_doc(self.doctype, batch_name)
        
        return {
            "name": batch.name,
            "status": batch.status,
            "posting_date": batch.posting_date,
            "items": self._get_batch_items(batch_name),
            "bom_references": self._get_bom_references(batch_name)
        }
    
    def _get_batch_items(self, batch_name: str) -> List[Dict]:
        """Get batch items with item details"""
        items = frappe.get_all("Batch AMB Item",
            filters={"parent": batch_name},
            fields=["*"]
        )
        
        # Enrich with item data
        for item in items:
            item_details = frappe.get_cached_doc("Item", item.item_code)
            item.update({
                "item_name": item_details.item_name,
                "stock_uom": item_details.stock_uom,
                "standard_rate": item_details.standard_rate,
                "valuation_rate": item_details.valuation_rate
            })
        
        return items
    
    def _get_bom_references(self, batch_name: str) -> Dict:
        """Get related BOMs for this batch"""
        boms = frappe.get_all("BOM",
            filters={"batch_amb_reference": batch_name},
            fields=["name", "bom_type", "total_cost", "is_active"]
        )
        
        return {
            "mrp_bom": next((bom for bom in boms if bom.bom_type == "MRP"), None),
            "standard_bom": next((bom for bom in boms if bom.bom_type == "Standard"), None)
        }
