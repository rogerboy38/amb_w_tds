# amb_w_tds/api/template_bom_service.py

import frappe


class TemplateBOMService:
    """
    Helper to create / normalize BOMs for web product codes
    (03xx–07xx finished goods) with hierarchical structure.
    """

    def _get_web_product_codes(self) -> list[str]:
        """
        Get all web product codes (finished goods for sale).
        Adjust filters to match your real web codes logic.
        """
        codes = frappe.get_all(
            "Item",
            filters={
                "is_sales_item": 1,
                "disabled": 0,
                # Optionally filter by item group or code pattern
                # "item_group": "WEB Finished Goods",
                # "item_code": ["like", "0%"],
            },
            pluck="name",
        )
        return codes

    def _ensure_basic_bom_for_item(self, item_code: str) -> str | None:
        """
        Ensure there is at least one BOM for this item.
        Returns BOM name if exists or created.
        """
        existing = frappe.get_all(
            "BOM",
            filters={"item": item_code, "is_active": 1},
            pluck="name",
        )
        if existing:
            return existing[0]

        # Create a minimal BOM (placeholder) as default
        company = frappe.defaults.get_global_default("company")
        
        bom = frappe.get_doc(
            {
                "doctype": "BOM",
                "item": item_code,
                "quantity": 1,
                "is_active": 1,
                "is_default": 1,
                "company": company,
                "items": [],
            }
        )

        bom.insert()
        bom.submit()
        return bom.name

    def generate_test_boms_for_web_codes(self) -> list[str]:
        """
        Public method to ensure every web code has at least one BOM.
        Returns list of BOM names (existing or newly created).
        """
        bom_names: list[str] = []

        codes = self._get_web_product_codes()
        print(f"Found {len(codes)} web product codes")

        for code in codes:
            print(f"Processing code: {code}")
            bom_name = self._ensure_basic_bom_for_item(code)
            print(f"  -> BOM: {bom_name}")
            if bom_name:
                bom_names.append(bom_name)

        print(f"Final BOM list ({len(bom_names)} BOMs):")
        for bom in bom_names:
            print(f"  - {bom}")

        return bom_names

    def create_hierarchical_bom(
        self,
        top_item_code: str,
        container_bom_name: str,
        shipping_label_item: str = "LBL0334",
    ) -> str:
        """
        Create a hierarchical BOM structure:
        Level 1 (top): shipping label + container BOM reference
        Level 2 (container): handled separately
        Level 3 (lot): handled separately
        
        Args:
            top_item_code: The sold finished good item code (e.g. "0334")
            container_bom_name: The BOM for the container configuration
            shipping_label_item: The shipping label item code
        
        Returns:
            Name of the created top-level BOM
        """
        company = frappe.defaults.get_global_default("company")
        
        # Check if top BOM already exists
        existing = frappe.get_all(
            "BOM",
            filters={"item": top_item_code, "is_default": 1},
            pluck="name",
        )
        
        if existing:
            print(f"Top BOM already exists: {existing[0]}")
            return existing[0]
        
        # Create top-level BOM
        bom = frappe.get_doc(
            {
                "doctype": "BOM",
                "item": top_item_code,
                "quantity": 1,
                "is_active": 1,
                "is_default": 1,
                "company": company,
                "items": [
                    # Shipping label
                    {
                        "item_code": shipping_label_item,
                        "qty": 1,
                        "uom": frappe.db.get_value("Item", shipping_label_item, "stock_uom"),
                    },
                    # Container BOM as sub-assembly
                    {
                        "item_code": top_item_code,
                        "qty": 1,
                        "uom": frappe.db.get_value("Item", top_item_code, "stock_uom"),
                        "bom_no": container_bom_name,
                    },
                ],
            }
        )
        
        bom.insert()
        bom.submit()
        
        print(f"Created hierarchical BOM: {bom.name}")
        return bom.name
