"""
Hierarchical BOM Service
Creates multi-level BOM structure with utilities, supplies, raw materials, and packing
"""

import frappe
from frappe import _
from frappe.utils import flt

class HierarchicalBOMService:
    """Service for creating hierarchical BOM structures"""
    
    @staticmethod
    def create_hierarchical_bom(batch):
        """
        Create hierarchical BOM structure
        Level 0: Main Product (golden_number)
        Level 1: Sub-lots (golden_number-1, golden_number-2, etc.)
        Level 2: Components (Utility, Supplies, Raw Material, Packing)
        """
        try:
            if not batch.golden_number:
                frappe.throw(_("Golden number is required for hierarchical BOM"))
            
            # Create main BOM (Level 0)
            main_bom = HierarchicalBOMService._create_main_bom(batch)
            
            # Create sub-lot BOMs (Level 1)
            sub_lot_boms = HierarchicalBOMService._create_sub_lot_boms(batch, main_bom)
            
            # Create component BOMs (Level 2) for each sub-lot
            for sub_lot_bom in sub_lot_boms:
                HierarchicalBOMService._create_component_boms(batch, sub_lot_bom)
            
            frappe.msgprint(_("Hierarchical BOM structure created successfully"))
            return main_bom.name
            
        except Exception as e:
            frappe.log_error(f"Hierarchical BOM Error: {str(e)}", "Hierarchical BOM Service")
            frappe.throw(_("Failed to create hierarchical BOM: {0}").format(str(e)))
    
    @staticmethod
    def _create_main_bom(batch):
        """Create Level 0 - Main Product BOM"""
        # Main item code = golden number
        main_item = HierarchicalBOMService._ensure_item_exists(
            batch.golden_number,
            f"Main Product {batch.golden_number}",
            "Products Powder"  # Adjust based on product type
        )
        
        bom = frappe.new_doc("BOM")
        bom.item = main_item
        bom.quantity = flt(batch.target_quantity) if hasattr(batch, 'target_quantity') else 1
        bom.is_active = 1
        bom.is_default = 1
        bom.project = batch.golden_number
        
        # Set golden number
        if frappe.db.exists("Custom Field", "BOM-golden_number"):
            bom.golden_number = batch.golden_number
        
        bom.insert(ignore_permissions=True)
        
        # Update batch
        batch.db_set('bom_reference', bom.name)
        
        return bom
    
    @staticmethod
    def _create_sub_lot_boms(batch, main_bom):
        """Create Level 1 - Sub-lot BOMs"""
        sub_lot_boms = []
        
        # Determine number of sub-lots based on batch items or barrels
        sub_lot_count = HierarchicalBOMService._calculate_sub_lot_count(batch)
        
        for i in range(1, sub_lot_count + 1):
            sub_lot_code = f"{batch.golden_number}-{i}"
            
            # Create sub-lot item
            sub_lot_item = HierarchicalBOMService._ensure_item_exists(
                sub_lot_code,
                f"Sub-lot {sub_lot_code}",
                "Products Liquid"  # Or appropriate item group
            )
            
            # Create sub-lot BOM
            sub_bom = frappe.new_doc("BOM")
            sub_bom.item = sub_lot_item
            sub_bom.quantity = flt(batch.target_quantity) / sub_lot_count if hasattr(batch, 'target_quantity') else 1
            sub_bom.is_active = 1
            sub_bom.project = batch.golden_number
            
            if frappe.db.exists("Custom Field", "BOM-golden_number"):
                sub_bom.golden_number = batch.golden_number
            
            sub_bom.insert(ignore_permissions=True)
            sub_lot_boms.append(sub_bom)
            
            # Add sub-lot to main BOM
            main_bom.append("items", {
                "item_code": sub_lot_item,
                "qty": sub_bom.quantity,
                "uom": frappe.db.get_value("Item", sub_lot_item, "stock_uom"),
                "rate": 0,  # Will be calculated from components
                "amount": 0
            })
        
        main_bom.save(ignore_permissions=True)
        frappe.db.commit()
        
        return sub_lot_boms
    
    @staticmethod
    def _create_component_boms(batch, sub_lot_bom):
        """Create Level 2 - Component BOMs (Utility, Supplies, Raw Material, Packing)"""
        sub_lot_code = sub_lot_bom.item
        
        # Create component categories
        components = {
            'Utility': HierarchicalBOMService._create_utility_bom(batch, sub_lot_code),
            'Supplies': HierarchicalBOMService._create_supplies_bom(batch, sub_lot_code),
            'Raw_Material': HierarchicalBOMService._create_raw_material_bom(batch, sub_lot_code),
            'Packing': HierarchicalBOMService._create_packing_bom(batch, sub_lot_code)
        }
        
        # Add components to sub-lot BOM
        for component_type, component_bom in components.items():
            if component_bom:
                sub_lot_bom.append("items", {
                    "item_code": component_bom.item,
                    "qty": 1,
                    "uom": frappe.db.get_value("Item", component_bom.item, "stock_uom"),
                    "rate": component_bom.total_cost if hasattr(component_bom, 'total_cost') else 0,
                    "amount": component_bom.total_cost if hasattr(component_bom, 'total_cost') else 0
                })
        
        sub_lot_bom.save(ignore_permissions=True)
        frappe.db.commit()
    
    @staticmethod
    def _create_utility_bom(batch, sub_lot_code):
        """Create Utility component BOM"""
        utility_item_code = f"{batch.product_code}-Utility-{sub_lot_code}"
        
        utility_item = HierarchicalBOMService._ensure_item_exists(
            utility_item_code,
            f"Utilities for {sub_lot_code}",
            f"{batch.product_code}-Services"
        )
        
        utility_bom = frappe.new_doc("BOM")
        utility_bom.item = utility_item
        utility_bom.quantity = 1
        utility_bom.is_active = 1
        utility_bom.project = batch.golden_number
        
        # Add utility items (electricity, gas, water, transport)
        utility_items = [
            ("ELECTRIC", "Process Electricity", 36.376, "kWh", 324.14),
            ("GAS", "Process Gas", 36.376, "Gigajoule", 360.55),
            ("WATER", "Process Water", 36.376, "Cubic Meter", 734.43),
            ("TRANSP_LEAF", "Leaf Transport Cost", 36.376, "Service", 800),
            ("TRANSP_TORTAS", "Torta Transport Cost", 1, "Service", 3000),
            ("RETIRO_LODOS", "Recoleccion de Lodos Transport Cost", 1, "Service", 3000),
            ("Maniobras", "Maniobras", 36.376, "Ton", 202.34)
        ]
        
        for item_code, item_name, qty, uom, rate in utility_items:
            # Ensure utility item exists
            HierarchicalBOMService._ensure_item_exists(item_code, item_name, "Utilities")
            
            utility_bom.append("items", {
                "item_code": item_code,
                "qty": qty,
                "uom": uom,
                "rate": rate,
                "amount": qty * rate
            })
        
        utility_bom.insert(ignore_permissions=True)
        return utility_bom
    
    @staticmethod
    def _create_supplies_bom(batch, sub_lot_code):
        """Create Supplies/Materials component BOM"""
        supplies_item_code = f"{batch.product_code}-Supplies-Material-{sub_lot_code}"
        
        supplies_item = HierarchicalBOMService._ensure_item_exists(
            supplies_item_code,
            f"Supplies for {sub_lot_code}",
            "RAW M Liquids"
        )
        
        supplies_bom = frappe.new_doc("BOM")
        supplies_bom.item = supplies_item
        supplies_bom.quantity = 1
        supplies_bom.is_active = 1
        supplies_bom.project = batch.golden_number
        
        # Add supply items
        supply_items = [
            ("M042", "061 CAE ULTRA CARBON ACTIVADO EN POLVO", 1.193821, "Kg", 61),
            ("M004", "Diatomaceous Earth Celite 512", 0.455334, "Kg", 14.88),
            ("M005", "Diatomaceous Earth Celite 501", 0.127031, "Kg", 14.88),
            ("M006", "Diatomaceous Earth Creaclar SC150", 0.083941, "Kg", 72.8),
            ("M018", "FILTRO DE HILO 1µ 30\"", 0.001865, "Piece", 13.79),
            ("M020", "FILTRO DE HILO 50µ 30\"", 0.001865, "Piece", 13.81),
            ("Q003", "Saniper 20", 1, "Litre", 87.578),
            ("Q004", "HI REMOVE SP", 0.005596, "Litre", 41.846),
            ("Q022", "LIQUID ACTIVADOR AL 50%", 0.139902, "Kg", 84),
            ("Q005", "POLIMERO IQA-320", 0.007461, "Litre", 45),
            ("Q006", "PROFLUX PARA CALDERAS", 0.011192, "Litre", 52),
            ("M045", "ENZIMA ROHAPECT", 0.026246, "Kg", 0),
            ("Q018", "Sal Comun de Primera Encostalada", 0.46634, "Kg", 0)
        ]
        
        for item_code, item_name, qty, uom, rate in supply_items:
            # Ensure supply item exists
            group = "Additives" if item_code.startswith("M") else "Chemicals"
            HierarchicalBOMService._ensure_item_exists(item_code, item_name, group)
            
            supplies_bom.append("items", {
                "item_code": item_code,
                "qty": qty,
                "uom": uom,
                "rate": rate,
                "amount": qty * rate
            })
        
        supplies_bom.insert(ignore_permissions=True)
        return supplies_bom
    
    @staticmethod
    def _create_raw_material_bom(batch, sub_lot_code):
        """Create Raw Material component BOM"""
        raw_material_item_code = f"{batch.product_code}-Raw-Material-{sub_lot_code}"
        
        raw_material_item = HierarchicalBOMService._ensure_item_exists(
            raw_material_item_code,
            f"Raw Materials for {sub_lot_code}",
            "RAW M Liquids"
        )
        
        raw_material_bom = frappe.new_doc("BOM")
        raw_material_bom.item = raw_material_item
        raw_material_bom.quantity = 1
        raw_material_bom.is_active = 1
        raw_material_bom.project = batch.golden_number
        
        # Add raw material items
        raw_items = [
            ("M033", "Aloe Vera Gel", 10.76, "Kg", 1.4)
        ]
        
        for item_code, item_name, qty, uom, rate in raw_items:
            HierarchicalBOMService._ensure_item_exists(item_code, item_name, "Raw Materials")
            
            raw_material_bom.append("items", {
                "item_code": item_code,
                "qty": qty,
                "uom": uom,
                "rate": rate,
                "amount": qty * rate
            })
        
        raw_material_bom.insert(ignore_permissions=True)
        return raw_material_bom
    
    @staticmethod
    def _create_packing_bom(batch, sub_lot_code):
        """Create Packing Material component BOM"""
        # Determine concentration type from sub_lot_code
        concentration = "1X" if "1X" in sub_lot_code else "30X"
        
        packing_item_code = f"{batch.product_code}-Packing-Material-{sub_lot_code}-{concentration}"
        
        packing_item = HierarchicalBOMService._ensure_item_exists(
            packing_item_code,
            f"Packing for {sub_lot_code} ({concentration})",
            "RAW M Liquids"
        )
        
        packing_bom = frappe.new_doc("BOM")
        packing_bom.item = packing_item
        packing_bom.quantity = 1
        packing_bom.is_active = 1
        packing_bom.project = batch.golden_number
        
        # Add packing items based on concentration
        if concentration == "1X":
            barrel_item = "E001 Template-220L BRRL-1X"
            barrel_name = "220L Barrel Blue Template-220L BRRL-1X"
            qty = 0.005335
        else:
            barrel_item = "E001-220L BRRL-30X"
            barrel_name = "220L Barrel Blue-220L BRRL-30X"
            qty = 1
        
        HierarchicalBOMService._ensure_item_exists(barrel_item, barrel_name, "Raw Materials")
        
        packing_bom.append("items", {
            "item_code": barrel_item,
            "qty": qty,
            "uom": "Piece",
            "rate": 787,
            "amount": qty * 787
        })
        
        packing_bom.insert(ignore_permissions=True)
        return packing_bom
    
    @staticmethod
    def _calculate_sub_lot_count(batch):
        """Calculate number of sub-lots needed"""
        if hasattr(batch, 'barrel_count') and batch.barrel_count:
            # One sub-lot per 3 barrels (adjustable)
            return max(1, int(flt(batch.barrel_count) / 3))
        return 1
    
    @staticmethod
    def _ensure_item_exists(item_code, item_name, item_group):
        """Ensure item exists, create if not"""
        if not frappe.db.exists("Item", item_code):
            try:
                item = frappe.new_doc("Item")
                item.item_code = item_code
                item.item_name = item_name
                item.item_group = item_group
                item.stock_uom = "Kg"  # Default, adjust as needed
                item.is_stock_item = 1
                item.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(f"Error creating item {item_code}: {str(e)}", "Item Creation")
        
        return item_code


@frappe.whitelist()
def create_hierarchical_bom(batch_name):
    """API endpoint for creating hierarchical BOM"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        bom_name = HierarchicalBOMService.create_hierarchical_bom(batch)
        
        return {
            "success": True,
            "message": _("Hierarchical BOM created successfully"),
            "bom_name": bom_name
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
