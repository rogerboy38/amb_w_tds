import frappe

class BatchRepository:
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
