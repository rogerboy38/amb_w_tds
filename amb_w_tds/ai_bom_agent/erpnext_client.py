"""
ERPNext Client for BOM Creator Agent v9.2.0

Handles all ERPNext Item and BOM CRUD operations with idempotency.
"""

import frappe
from frappe import _
from typing import Optional, Dict, List, Any


class ItemAndBOMService:
    """
    Service for creating and managing Items and BOMs in ERPNext.
    
    All methods are idempotent - safe to call multiple times.
    """
    
    # Phase 7: Families that require batch tracking
    BATCH_TRACKING_FAMILIES = ["0227", "0307", "HIGHPOL", "ACETYPOL"]
    
    def __init__(self, company: Optional[str] = None):
        """
        Initialize the service.
        
        Args:
            company: Company name. Defaults to first company in system.
        """
        self.company = company or frappe.defaults.get_defaults().get("company")
    
    # ==================== Item Operations ====================
    
    def item_exists(self, item_code: str) -> bool:
        """
        Check if an item exists.
        
        Args:
            item_code: Item code to check
            
        Returns:
            True if item exists, False otherwise
        """
        return frappe.db.exists("Item", item_code) is not None
    
    def get_item(self, item_code: str) -> Optional[Dict[str, Any]]:
        """
        Get item details.
        
        Args:
            item_code: Item code to fetch
            
        Returns:
            Item document as dict, or None if not found
        """
        if not self.item_exists(item_code):
            return None
        
        return frappe.get_doc("Item", item_code).as_dict()
    
    def create_item(
        self,
        item_code: str,
        item_name: str,
        item_group: str = "SFG Semi Finished Goods",
        stock_uom: str = "Kg",
        is_stock_item: int = 1,
        include_item_in_manufacturing: int = 1,
        default_warehouse: Optional[str] = None,
        description: Optional[str] = None,
        has_batch_no: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create an item if it doesn't exist.
        
        Args:
            item_code: Unique item code
            item_name: Display name
            item_group: Item group (default: Semi Finished Goods)
            stock_uom: Stock UOM (default: Kg)
            is_stock_item: Whether to track stock (default: 1)
            include_item_in_manufacturing: Include in MRP (default: 1)
            default_warehouse: Default warehouse
            description: Item description
            has_batch_no: Enable batch tracking (Phase 7)
            **kwargs: Additional item fields
            
        Returns:
            Created or existing item as dict
        """
        # Idempotent: return existing if found
        if self.item_exists(item_code):
            return self.get_item(item_code)
        
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_name = item_name
        item.item_group = item_group
        item.stock_uom = stock_uom
        item.is_stock_item = is_stock_item
        item.include_item_in_manufacturing = include_item_in_manufacturing
        
        # Phase 7: Set batch tracking flag
        # Auto-enable for batch-tracked families
        if has_batch_no or self._should_enable_batch_tracking(item_code):
            item.has_batch_no = 1
        
        # Set mandatory custom fields for Mexico compliance
        item.product_key = kwargs.pop("product_key", item_code)
        item.mx_product_service_key = kwargs.pop("mx_product_service_key", "01010101")
        
        if default_warehouse:
            item.default_warehouse = default_warehouse
        
        if description:
            item.description = description
        else:
            item.description = item_name
        
        # Apply any additional fields
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        item.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return item.as_dict()
    
    # ==================== BOM Operations ====================
    
    def bom_exists(self, item_code: str, version: Optional[int] = None) -> bool:
        """
        Check if a BOM exists for an item.
        
        Args:
            item_code: Item code to check
            version: Specific BOM version (optional)
            
        Returns:
            True if BOM exists, False otherwise
        """
        filters = {"item": item_code, "docstatus": ["!=", 2]}
        
        if version:
            filters["bom_no"] = f"BOM-{item_code}-{version:03d}"
        
        return frappe.db.exists("BOM", filters) is not None
    
    def get_default_bom(self, item_code: str) -> Optional[str]:
        """
        Get the default BOM for an item.
        
        Args:
            item_code: Item code
            
        Returns:
            Default BOM name, or None if not found
        """
        return frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_default": 1, "is_active": 1, "docstatus": 1},
            "name"
        )
    
    def get_bom(self, bom_name: str) -> Optional[Dict[str, Any]]:
        """
        Get BOM details.
        
        Args:
            bom_name: BOM document name
            
        Returns:
            BOM document as dict, or None if not found
        """
        if not frappe.db.exists("BOM", bom_name):
            return None
        
        return frappe.get_doc("BOM", bom_name).as_dict()
    
    def create_bom(
        self,
        item_code: str,
        items: List[Dict[str, Any]],
        operations: Optional[List[Dict[str, Any]]] = None,
        quantity: float = 1.0,
        uom: str = "Kg",
        is_active: int = 1,
        is_default: int = 0,
        with_operations: int = 0,
        company: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a BOM if it doesn't exist.
        
        CRITICAL: Use 'bom_no' field in items to link sub-BOMs for multi-level.
        
        Args:
            item_code: FG/SFG item code
            items: List of BOM items [{item_code, qty, uom, bom_no (optional)}]
            operations: List of operations (optional)
            quantity: BOM quantity (default: 1.0)
            uom: BOM UOM (default: Kg)
            is_active: Whether BOM is active (default: 1)
            is_default: Whether this is default BOM (default: 0)
            with_operations: Include operations (default: 0)
            company: Company (uses default if not specified)
            **kwargs: Additional BOM fields
            
        Returns:
            Created or existing BOM as dict
        """
        # Idempotent: if active BOM exists for this item, return it
        existing_bom = frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_active": 1, "docstatus": ["!=", 2]},
            "name"
        )
        
        if existing_bom:
            return self.get_bom(existing_bom)
        
        bom = frappe.new_doc("BOM")
        bom.item = item_code
        bom.quantity = quantity
        bom.uom = uom
        bom.is_active = is_active
        bom.is_default = is_default
        bom.with_operations = with_operations
        bom.company = company or self.company
        
        # Add BOM items
        for item in items:
            bom_item = bom.append("items", {})
            bom_item.item_code = item.get("item_code")
            bom_item.qty = item.get("qty", 1.0)
            bom_item.uom = item.get("uom", "Kg")
            
            # CRITICAL: Link sub-BOM for multi-level explosion
            if item.get("bom_no"):
                bom_item.bom_no = item["bom_no"]
        
        # Add operations if provided
        if operations and with_operations:
            for op in operations:
                bom_op = bom.append("operations", {})
                bom_op.operation = op.get("operation")
                bom_op.workstation = op.get("workstation")
                bom_op.time_in_mins = op.get("time_in_mins", 0)
                bom_op.hour_rate = op.get("hour_rate", 0)
        
        # Apply any additional fields
        for key, value in kwargs.items():
            if hasattr(bom, key):
                setattr(bom, key, value)
        
        bom.insert(ignore_permissions=True)
        
        # Submit the BOM
        bom.submit()
        frappe.db.commit()
        
        return bom.as_dict()
    
    def set_default_bom(self, item_code: str, bom_name: str) -> bool:
        """
        Set a BOM as the default for an item.
        
        Args:
            item_code: Item code
            bom_name: BOM name to set as default
            
        Returns:
            True if successful, False otherwise
        """
        if not frappe.db.exists("BOM", bom_name):
            return False
        
        # Unset any existing default
        frappe.db.sql("""
            UPDATE `tabBOM` 
            SET is_default = 0 
            WHERE item = %s AND is_default = 1
        """, item_code)
        
        # Set new default
        frappe.db.set_value("BOM", bom_name, "is_default", 1)
        
        # Update item's default_bom field
        frappe.db.set_value("Item", item_code, "default_bom", bom_name)
        
        frappe.db.commit()
        return True
    
    # ==================== Utility Methods ====================
    
    def get_item_default_warehouse(self, item_code: str) -> Optional[str]:
        """Get the default warehouse for an item."""
        return frappe.db.get_value("Item", item_code, "default_warehouse")
    
    def validate_item_for_bom(self, item_code: str) -> Dict[str, Any]:
        """
        Validate an item is suitable for BOM creation.
        
        Args:
            item_code: Item code to validate
            
        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []
        
        if not self.item_exists(item_code):
            errors.append(f"Item '{item_code}' does not exist")
            return {"valid": False, "errors": errors}
        
        item = frappe.get_doc("Item", item_code)
        
        if not item.is_stock_item:
            errors.append(f"Item '{item_code}' is not a stock item")
        
        if item.disabled:
            errors.append(f"Item '{item_code}' is disabled")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def get_existing_sfgs_for_family(
        self, 
        family: str, 
        attribute: Optional[str] = None
    ) -> List[str]:
        """
        Get existing SFG items for a product family.
        
        Args:
            family: Product family code
            attribute: Optional attribute filter
            
        Returns:
            List of SFG item codes
        """
        pattern = f"SFG-{family}-%"
        
        if attribute:
            pattern = f"SFG-{family}-%-{attribute}%"
        
        return frappe.db.sql_list("""
            SELECT item_code 
            FROM `tabItem` 
            WHERE item_code LIKE %s
            AND item_group = 'SFG Semi Finished Goods'
            AND disabled = 0
        """, pattern)

    def _should_enable_batch_tracking(self, item_code: str) -> bool:
        """
        Phase 7: Determine if an item should have batch tracking enabled.
        
        Returns True if item_code starts with a batch-tracked family code.
        
        Args:
            item_code: Item code to check
            
        Returns:
            True if batch tracking should be enabled
        """
        item_upper = item_code.upper()
        for family in self.BATCH_TRACKING_FAMILIES:
            if item_upper.startswith(family) or item_upper.startswith(f"SFG-{family}"):
                return True
        return False
