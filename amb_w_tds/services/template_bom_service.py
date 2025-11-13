"""
Template-Based BOM Service
Uses Standard BOM with custom_is_template=1 as templates
Generates production BOMs with golden number integration
"""

import frappe
from frappe import _
from frappe.utils import flt, cstr
import json


class TemplateBOMService:
    """Service for template-based BOM generation"""
    
    PRODUCT_TEMPLATES = {
        '0227': 'BOM-TEMPLATE-0227-CONCENTRATE',
        '0303': 'BOM-TEMPLATE-0303-POWDER',
        '0334': 'BOM-TEMPLATE-0334-FORMULATED',
        '0705': 'BOM-TEMPLATE-0705-SHIPPING'
    }
    """Service for managing template BOMs and generation"""
    
    def __init__(self):
        self.utility_items = {
            'water': 'WATER-UTILITY',
            'electricity': 'ELECTRICITY-UTILITY',
            'gas': 'GAS-UTILITY',
            'labor': 'LABOR-COST'
        }
    
    def create_from_template(self, template_name, item_code, **kwargs):
        """Create BOM from predefined template"""
        pass
    
    def get_template_by_product_family(self, product_code):
        """Retrieve template based on product code prefix"""
        pass
    
    @staticmethod
    def create_bom_from_template(batch, template_name=None):
        """
        Create production BOM from template
        Args:
            batch: Batch AMB document
            template_name: Optional specific template to use
        """
        try:
            if not batch.golden_number:
                frappe.throw(_("Golden number is required"))
            
            # Get template
            if not template_name:
                product_code = batch.golden_number[:4]
                template_name = TemplateBOMService.PRODUCT_TEMPLATES.get(product_code)
            
            if not template_name or not frappe.db.exists("BOM", template_name):
                frappe.throw(_("Template BOM not found for product code {0}").format(
                    batch.golden_number[:4]))
            
            template = frappe.get_doc("BOM", template_name)
            
            # Create main BOM (Level 0)
            main_bom = TemplateBOMService._create_main_bom(batch, template)
            
            # Create sub-lot BOMs (Level 1) if batch level > 1
            if hasattr(batch, 'custom_batch_level') and int(batch.custom_batch_level or 1) > 1:
                TemplateBOMService._create_sublot_boms(batch, main_bom, template)
            
            return main_bom.name
            
        except Exception as e:
            frappe.log_error(f"Template BOM Creation Error: {str(e)}", "Template BOM Service")
            frappe.throw(_("Failed to create BOM from template: {0}").format(str(e)))
    
    @staticmethod
    def _create_main_bom(batch, template):
        """Create main product BOM (Level 0)"""
        # Item code = golden number
        item_code = batch.golden_number
        
        # Ensure item exists
        if not frappe.db.exists("Item", item_code):
            item = TemplateBOMService._create_item_from_template(
                item_code, 
                f"Main Product {item_code}",
                template.item
            )
        
        # Create BOM
        bom = frappe.new_doc("BOM")
        bom.item = item_code
        bom.quantity = template.quantity
        bom.is_active = 1
        bom.is_default = 1
        bom.project = batch.golden_number  # Use golden number as project
        
        # Set custom fields
        bom.custom_golden_number = batch.golden_number
        bom.custom_product_code = batch.golden_number[:4]
        bom.custom_batch_level = "1"
        bom.custom_component_type = "Main Product"
        
        # Copy operations from template if any
        if hasattr(template, 'operations'):
            for op in template.operations:
                bom.append("operations", {
                    "operation": op.operation,
                    "workstation": op.workstation,
                    "time_in_mins": op.time_in_mins,
                    "operating_cost": op.operating_cost
                })
        
        bom.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Update batch
        batch.db_set('bom_reference', bom.name)
        
        frappe.msgprint(_("Main BOM {0} created").format(bom.name))
        return bom
    
    @staticmethod
    def _create_sublot_boms(batch, main_bom, template):
        """Create sub-lot BOMs (Level 1)"""
        # Determine number of sub-lots
        sub_lot_count = TemplateBOMService._calculate_sublot_count(batch)
        
        for i in range(1, sub_lot_count + 1):
            sublot_code = f"{batch.golden_number}-{i}"
            
            # Ensure sub-lot item exists
            if not frappe.db.exists("Item", sublot_code):
                TemplateBOMService._create_item_from_template(
                    sublot_code,
                    f"Sub-lot {sublot_code}",
                    template.item
                )
            
            # Create sub-lot BOM
            sublot_bom = frappe.new_doc("BOM")
            sublot_bom.item = sublot_code
            sublot_bom.quantity = flt(main_bom.quantity) / sub_lot_count
            sublot_bom.is_active = 1
            sublot_bom.project = batch.golden_number
            
            # Set custom fields
            sublot_bom.custom_golden_number = batch.golden_number
            sublot_bom.custom_product_code = batch.golden_number[:4]
            sublot_bom.custom_batch_level = "2"
            sublot_bom.custom_component_type = "Sub-Lot"
            sublot_bom.custom_parent_bom = main_bom.name
            
            # Add component BOMs (Utility, Supplies, Raw Material, Packing)
            TemplateBOMService._add_component_boms(
                batch, sublot_bom, sublot_code, template
            )
            
            sublot_bom.insert(ignore_permissions=True)
            
            # Add to main BOM
            main_bom.append("items", {
                "item_code": sublot_code,
                "qty": sublot_bom.quantity,
                "uom": frappe.db.get_value("Item", sublot_code, "stock_uom"),
                "rate": 0,  # Will be calculated
                "bom_no": sublot_bom.name
            })
        
        main_bom.save(ignore_permissions=True)
        frappe.db.commit()
    
    @staticmethod
    def _add_component_boms(batch, sublot_bom, sublot_code, template):
        """Add component BOMs (Utility, Supplies, Raw Material, Packing)"""
        product_code = batch.golden_number[:4]
        
        # Component types to create
        component_types = [
            ("Utility", f"{product_code}-Utility-{sublot_code}"),
            ("Supplies", f"{product_code}-Supplies-{sublot_code}"),
            ("Raw Material", f"{product_code}-RawMaterial-{sublot_code}"),
            ("Packing", f"{product_code}-Packing-{sublot_code}")
        ]
        
        for comp_type, comp_code in component_types:
            # Get template items for this component type
            template_items = TemplateBOMService._get_template_component_items(
                template, comp_type
            )
            
            if not template_items:
                continue
            
            # Create component item if not exists
            if not frappe.db.exists("Item", comp_code):
                TemplateBOMService._create_item_from_template(
                    comp_code,
                    f"{comp_type} for {sublot_code}",
                    template.item,
                    item_group=f"{product_code}-Services" if comp_type == "Utility" else "RAW M Liquids"
                )
            
            # Create component BOM
            comp_bom = frappe.new_doc("BOM")
            comp_bom.item = comp_code
            comp_bom.quantity = 1
            comp_bom.is_active = 1
            comp_bom.project = batch.golden_number
            
            comp_bom.custom_golden_number = batch.golden_number
            comp_bom.custom_product_code = product_code
            comp_bom.custom_batch_level = "3"
            comp_bom.custom_component_type = comp_type
            comp_bom.custom_parent_bom = sublot_bom.name
            
            # Add items from template
            for item in template_items:
                comp_bom.append("items", {
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "uom": item.uom,
                    "rate": item.rate or frappe.db.get_value("Item", item.item_code, "valuation_rate") or 0
                })
            
            comp_bom.insert(ignore_permissions=True)
            
            # Add to sub-lot BOM
            sublot_bom.append("items", {
                "item_code": comp_code,
                "qty": 1,
                "uom": frappe.db.get_value("Item", comp_code, "stock_uom"),
                "rate": 0,  # Will be calculated
                "bom_no": comp_bom.name
            })
    
    @staticmethod
    def _get_template_component_items(template, component_type):
        """Get items from template BOM for specific component type"""
        # This is where we filter template items by component type
        # For now, return items that match naming pattern
        items = []
        for item in template.items:
            item_code_lower = item.item_code.lower()
            
            if component_type == "Utility":
                if any(util in item_code_lower for util in ['electric', 'gas', 'water', 'transp', 'maniobras']):
                    items.append(item)
            elif component_type == "Supplies":
                if any(sup in item_code_lower for sup in ['m0', 'q0', 'filter', 'carbon', 'celite']):
                    items.append(item)
            elif component_type == "Raw Material":
                if 'm033' in item_code_lower or 'aloe' in item_code_lower:
                    items.append(item)
            elif component_type == "Packing":
                if any(pack in item_code_lower for pack in ['e001', 'barrel', 'ibc', 'pail']):
                    items.append(item)
        
        return items
    
    @staticmethod
    def _calculate_sublot_count(batch):
        """Calculate number of sub-lots needed"""
        if hasattr(batch, 'barrel_count') and batch.barrel_count:
            # One sub-lot per 3 barrels
            return max(1, int(flt(batch.barrel_count) / 3))
        return 1
    
    @staticmethod
    def _create_item_from_template(item_code, item_name, template_item, item_group=None):
        """Create item from template"""
        template_doc = frappe.get_doc("Item", template_item)
        
        item = frappe.new_doc("Item")
        item.item_code = item_code
        item.item_name = item_name
        item.item_group = item_group or template_doc.item_group
        item.stock_uom = template_doc.stock_uom
        item.is_stock_item = 1
        
        # Set golden number if custom field exists
        if hasattr(item, 'custom_golden_number'):
            item.custom_golden_number = item_code.split('-')[0] if '-' in item_code else item_code[:10]
        
        item.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return item.name
    
    @staticmethod
    def create_template_from_existing_bom(bom_name, product_code):
        """Convert existing BOM to template"""
        try:
            existing_bom = frappe.get_doc("BOM", bom_name)
            
            # Create template name
            template_name = f"BOM-TEMPLATE-{product_code}-{existing_bom.item}"
            
            # Copy BOM
            template = frappe.copy_doc(existing_bom)
            template.name = template_name
            template.custom_is_template = 1
            template.custom_product_code = product_code
            template.is_default = 0
            
            template.insert(ignore_permissions=True)
            frappe.db.commit()
            
            return template.name
            
        except Exception as e:
            frappe.log_error(f"Template Creation Error: {str(e)}", "Template BOM Service")
            frappe.throw(_("Failed to create template: {0}").format(str(e)))

    def _get_web_product_codes(self):
        """Return list of 29 web product codes"""
        return [
            # Spray Dried Powder (2)
            '0307', '0323',
            # Acetypol (5)
            '0401', '0417', '0433', '0449', '0465',
            # Highpol (6)
            '0501', '0517', '0533', '0549', '0565', '0581',
            # QX Blends (11)
            '0601', '0602', '0603', '0604', '0605', '0606',
            '0607', '0608', '0609', '0610', '0611',
            # Liquids Non-Organic (4)
            '0701', '0702', '0703', '0704',
            # Liquids Organic (4)
            '0705', '0706', '0707', '0708'
        ]
    #

    # ==== START Update create_bom_from_product_code Method  ====    
    
    def create_bom_from_product_code(self, product_code):
        """Create BOM directly from product code (for testing)"""
        try:
            if not frappe.db.exists("Item", product_code):
                frappe.throw(_("Item {0} does not exist").format(product_code))
        
            item = frappe.get_doc("Item", product_code)
        
            # Check for existing template in PRODUCT_TEMPLATES dict
            template_name = self.PRODUCT_TEMPLATES.get(product_code)
            if template_name and frappe.db.exists("BOM", template_name):
                # Use existing template
                template = frappe.get_doc("BOM", template_name)
                new_bom = frappe.copy_doc(template)
                new_bom.item = product_code
            else:
                # Build detailed template based on product family
                bom_data = None
            
                # Detect product family and build appropriate template
                if product_code.startswith('03'):  # Spray Dried Powder 
                    bom_data = self._build_template_spray_dried_powder(product_code, item)
                elif product_code.startswith('04'):  # Acetypol
                    bom_data = self._build_template_acetypol(product_code, item)
                elif product_code.startswith('05'):  # Highpol
                    bom_data = self._build_template_highpol(product_code, item)
                elif product_code.startswith('06'):  # QX Blends
                    bom_data = self._build_template_qx_blend(product_code, item)
                elif product_code.startswith('07'):  # Liquids
                    bom_data = self._build_template_liquid(product_code, item)
            
                # If detailed template built, use it; otherwise fall back to basic
                if bom_data:
                    new_bom = frappe.get_doc(bom_data)
                else:
                   return self._create_basic_bom(product_code, item)
     
            new_bom.is_default = 1
            new_bom.is_active = 1
            new_bom.insert(ignore_permissions=True)
            new_bom.submit()
        
            return new_bom.name
        
        except Exception as e:
            frappe.log_error(message=str(e), title=f"BOM Creation Failed: {product_code}")
            raise

    # ==== END Update create_bom_from_product_code Method  ====   

    # ==== START Implementation Plan for 0307 Template ====
    
    def _build_template_spray_dried_powder(self, product_code, item):
        """
        Build detailed BOM for Spray Dried Powder (03XX family)
    
        Process: Fresh aloe juice (0705) → Spray drying → Powder (200:1 ratio)
        Input: 20,000 kg juice (0705) → Output: 100 kg powder
        """
        # Base juice component (200:1 concentration ratio)
        base_juice_qty = 20000  # 20,000 kg juice for 100 kg powder
    
        # Check if base juice item exists
        base_juice_code = '0705'
        if not frappe.db.exists("Item", base_juice_code):
            frappe.throw(f"Base juice item {base_juice_code} not found. Create it first.")
    
        # Get base juice rate
        base_juice_item = frappe.get_doc("Item", base_juice_code)
        base_juice_rate = frappe.db.get_value("Item Price", 
            {"item_code": base_juice_code, "selling": 0}, 
            "price_list_rate") or 0.50  # Default $0.50/kg
    
        # Build BOM structure
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,  # 100 kg output
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,  # Will add operations later
            "items": [
                # Main component: Base juice
                {
                    "item_code": base_juice_code,
                    "item_name": base_juice_item.item_name,
                    "qty": base_juice_qty,
                    "uom": "Kg",
                    "rate": base_juice_rate,
                    "description": "Aloe vera juice 1:1 (200:1 concentration ratio)"
                },
                # Utilities - Higher consumption for spray drying
                {
                    "item_code": self.utility_items['water'],
                    "qty": 500,  # 500 L for washing/processing
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Process water for spray drying"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": 150,  # 150 kWh for spray dryer
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "Spray dryer electrical consumption"
                },
                {
                    "item_code": self.utility_items['gas'],
                    "qty": 50,  # 50 M3 for heating
                    "uom": "Nos",
                    "rate": 0.50,
                    "description": "Gas for spray dryer heating"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": 8,  # 8 hours labor
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Operator time for spray drying process"
                }
            ]
        }
    
        return bom_data
    
    # ==== END Implementation Plan for 0307 Template ====
    # ==== START Implement Remaining 4 Product Family Templates ====
    
    def _build_template_acetypol(self, product_code, item):
        """
        Build detailed BOM for Aloe Acetypol (04XX family)
        
        Process: Spray dried powder (0307) → Decolorization with activated carbon → Acetypol
        Input: 105 kg powder + 5 kg carbon → Output: 100 kg acetypol (5% carbon addition)
        """
        # Base powder component
        base_powder_code = '0307'
        base_powder_qty = 105  # 105 kg powder for 100 kg output (5% process loss)
        
        # Check if base powder exists
        if not frappe.db.exists("Item", base_powder_code):
            frappe.throw(f"Base powder item {base_powder_code} not found. Create it first.")
        
        # Get rates
        base_powder_item = frappe.get_doc("Item", base_powder_code)
        base_powder_rate = frappe.db.get_value("Item Price", 
            {"item_code": base_powder_code, "selling": 0}, 
            "price_list_rate") or 165.68  # Default from BOM cost
        
        # Activated carbon
        carbon_code = 'ACTIVATED-CARBON'
        carbon_qty = 5  # 5 kg carbon per 100 kg output
        carbon_rate = frappe.db.get_value("Item Price", 
            {"item_code": carbon_code, "selling": 0}, 
            "price_list_rate") or 8.50
        
        # Build BOM structure
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "items": [
                # Main component: Base powder
                {
                    "item_code": base_powder_code,
                    "qty": base_powder_qty,
                    "uom": "Kg",
                    "rate": base_powder_rate,
                    "description": "Aloe vera spray dried powder base"
                },
                # Decolorization agent
                {
                    "item_code": carbon_code,
                    "qty": carbon_qty,
                    "uom": "Kg",
                    "rate": carbon_rate,
                    "description": "Activated carbon for decolorization"
                },
                # Utilities - Medium consumption for decolorization
                {
                    "item_code": self.utility_items['water'],
                    "qty": 300,
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Process water for decolorization"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": 80,
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "Mixing and processing"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": 6,
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Operator time for decolorization process"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_highpol(self, product_code, item):
        """
        Build detailed BOM for Aloe Highpol (05XX family)
        
        Process: Retentate (0302) → Membrane filtration/concentration → Highpol
        Input: 150 kg retentate → Output: 100 kg highpol (concentration factor 1.5)
        """
        # Base retentate component
        base_retentate_code = '0302'
        base_retentate_qty = 150  # 150 kg retentate for 100 kg output
        
        # Check if base retentate exists
        if not frappe.db.exists("Item", base_retentate_code):
            frappe.throw(f"Base retentate item {base_retentate_code} not found. Create it first.")
        
        # Get rate
        base_retentate_item = frappe.get_doc("Item", base_retentate_code)
        base_retentate_rate = frappe.db.get_value("Item Price", 
            {"item_code": base_retentate_code, "selling": 0}, 
            "price_list_rate") or 100.00  # Estimated rate
        
        # Build BOM structure
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "items": [
                # Main component: Retentate
                {
                    "item_code": base_retentate_code,
                    "qty": base_retentate_qty,
                    "uom": "Kg",
                    "rate": base_retentate_rate,
                    "description": "High polysaccharide retentate from membrane filtration"
                },
                # Utilities - High consumption for ultrafiltration
                {
                    "item_code": self.utility_items['water'],
                    "qty": 400,
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Process water for ultrafiltration"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": 180,
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "Ultrafiltration unit consumption"
                },
                {
                    "item_code": self.utility_items['gas'],
                    "qty": 60,
                    "uom": "Nos",
                    "rate": 0.50,
                    "description": "Heating for concentration"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": 10,
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Operator time for filtration process"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_qx_blend(self, product_code, item):
        """
        Build detailed BOM for Aloe QX Blends (06XX family)
        
        Process: Spray dried powder (0307) + Maltodextrin → Dry blending → QX blend
        Ratios: Variable based on product code (5% to 90% aloe)
        """
        # QX blend ratios (aloe %, maltodextrin %)
        qx_ratios = {
            '0601': (5, 95),
            '0602': (10, 90),
            '0603': (15, 85),
            '0604': (20, 80),
            '0605': (30, 70),
            '0606': (40, 60),
            '0607': (50, 50),
            '0608': (60, 40),
            '0609': (70, 30),
            '0610': (80, 20),
            '0611': (90, 10)
        }
        
        # Get ratio for this product code
        if product_code not in qx_ratios:
            frappe.throw(f"Unknown QX blend code: {product_code}")
        
        aloe_percent, malto_percent = qx_ratios[product_code]
        
        # Calculate quantities for 100 kg output
        aloe_qty = aloe_percent  # Direct percentage = kg for 100 kg output
        malto_qty = malto_percent
        
        # Base powder component
        base_powder_code = '0307'
        if not frappe.db.exists("Item", base_powder_code):
            frappe.throw(f"Base powder item {base_powder_code} not found.")
        
        base_powder_rate = frappe.db.get_value("Item Price", 
            {"item_code": base_powder_code, "selling": 0}, 
            "price_list_rate") or 165.68
        
        # Maltodextrin
        malto_code = 'MALTODEXTRIN'
        if not frappe.db.exists("Item", malto_code):
            frappe.throw(f"Maltodextrin item {malto_code} not found.")
        
        malto_rate = frappe.db.get_value("Item Price", 
            {"item_code": malto_code, "selling": 0}, 
            "price_list_rate") or 2.50
        
        # Build BOM structure
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "items": [
                # Component 1: Aloe powder
                {
                    "item_code": base_powder_code,
                    "qty": aloe_qty,
                    "uom": "Kg",
                    "rate": base_powder_rate,
                    "description": f"Aloe vera powder ({aloe_percent}% blend)"
                },
                # Component 2: Maltodextrin
                {
                    "item_code": malto_code,
                    "qty": malto_qty,
                    "uom": "Kg",
                    "rate": malto_rate,
                    "description": f"Maltodextrin carrier ({malto_percent}% blend)"
                },
                # Utilities - Low consumption for dry blending
                {
                    "item_code": self.utility_items['water'],
                    "qty": 50,
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Process water for cleaning"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": 20,
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "V-blender consumption"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": 2,
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Operator time for blending"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_liquid(self, product_code, item):
        """
        Build detailed BOM for Innovaloe Liquids (07XX family)
        
        Process: Fresh aloe leaf → Extraction/concentration → Liquid product
        Concentrations: 1:1, 10:1, 20:1, 30:1 (detect from item name)
        Output: 1000 Litre batches
        """
        # Detect concentration from item name
        item_name = item.item_name.lower()
        concentration_factor = 1  # Default 1:1
        
        if '10:1' in item_name or '10-1' in item_name:
            concentration_factor = 10
        elif '20:1' in item_name or '20-1' in item_name:
            concentration_factor = 20
        elif '30:1' in item_name or '30-1' in item_name:
            concentration_factor = 30
        
        # Calculate fresh leaf requirement
        output_qty = 1000  # Litres
        fresh_leaf_qty = output_qty * concentration_factor  # kg
        
        # Fresh aloe leaf
        leaf_code = 'ALOE-LEAF-FRESH'
        if not frappe.db.exists("Item", leaf_code):
            frappe.throw(f"Fresh aloe leaf item {leaf_code} not found.")
        
        leaf_rate = frappe.db.get_value("Item Price", 
            {"item_code": leaf_code, "selling": 0}, 
            "price_list_rate") or 0.30
        
        # Preservatives
        citric_code = 'CITRIC-ACID'
        citric_qty = 2  # 2 kg per 1000L
        citric_rate = frappe.db.get_value("Item Price", 
            {"item_code": citric_code, "selling": 0}, 
            "price_list_rate") or 3.50
        
        sorbate_code = 'POTASSIUM-SORBATE'
        sorbate_qty = 1  # 1 kg per 1000L
        sorbate_rate = frappe.db.get_value("Item Price", 
            {"item_code": sorbate_code, "selling": 0}, 
            "price_list_rate") or 5.00
        
        # Build BOM structure
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": output_qty,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "items": [
                # Main component: Fresh aloe leaf
                {
                    "item_code": leaf_code,
                    "qty": fresh_leaf_qty,
                    "uom": "Kg",
                    "rate": leaf_rate,
                    "description": f"Fresh aloe vera leaf for {concentration_factor}:1 concentration"
                },
                # Preservative 1: Citric acid
                {
                    "item_code": citric_code,
                    "qty": citric_qty,
                    "uom": "Kg",
                    "rate": citric_rate,
                    "description": "Citric acid for pH adjustment"
                },
                # Preservative 2: Potassium sorbate
                {
                    "item_code": sorbate_code,
                    "qty": sorbate_qty,
                    "uom": "Kg",
                    "rate": sorbate_rate,
                    "description": "Potassium sorbate preservative"
                },
                # Utilities - High consumption for liquid processing
                {
                    "item_code": self.utility_items['water'],
                    "qty": 2000,
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Process water for extraction and cleaning"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": 100,
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "Processing equipment consumption"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": 12,
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Operator time for liquid processing"
                }
            ]
        }
        
        return bom_data
    
    # ==== START Implement Remaining 4 Product Family Templates ====

    def _create_basic_bom(self, product_code, item):
        """Create a basic BOM when no template exists"""
        bom = frappe.get_doc({
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100 if item.stock_uom == "Kg" else 1000,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "items": [
                {
                    "item_code": self.utility_items['water'],
                    "qty": 100,
                    "uom": "Litre",
                    "rate": 0.001
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": 50,
                    "uom": "Nos",
                    "rate": 0.15
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": 5,
                    "uom": "Nos",
                    "rate": 15.00
                }
            ]
        })
        
        bom.insert(ignore_permissions=True)
        bom.submit()
        return bom.name
    # ==== SPRAY DRIED POWDER TEMPLATE  ====
    def _build_template_spray_dried_powder(self, product_code, item):
        """
        Build detailed BOM template for Spray Dried Powder (03XX family)
    
        Process: Spray drying from liquid concentrate (0705) with 200:1 concentration ratio
        Input: 20,000 kg of 0705 (Juice 1:1) → Output: 100 kg spray dried powder
    
        Args:
            product_code (str): Product code (e.g., '0307', '0323')
            item (Document): Item document
    
        Returns:
            dict: BOM structure with components and operations
        """
        # Base quantity: 100 kg of finished powder
        base_qty = 100
    
        # 200:1 concentration ratio: Need 20,000 kg (20,000 L) of 0705 juice
        juice_qty = base_qty * 200  # 20,000 kg
    
        # Utility consumption estimates for spray drying 100kg
        water_qty = 500      # Litre - Process water for cleaning/cooling
        electricity_qty = 150  # kWh (as Nos) - Spray dryer power consumption
        gas_qty = 50         # M3 (as Nos) - Heat generation
        labor_qty = 8        # Hours (as Nos) - Operator time
    
        bom_template = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": base_qty,
            "uom": item.stock_uom,  # Should be "Kg"
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,  # Will be set to 1 when workstations added in Phase 2B
            "items": [
                # Main component: Aloe juice 1:1 concentrate
                {
                    "item_code": "0705",
                    "item_name": "Innovaloe Aloe Vera Gel Concentrate 1:1 Organic",
                    "qty": juice_qty,
                    "uom": "Litre",  # Assuming 1kg = 1L density
                    "rate": 0.00,  # Will be calculated from 0705's BOM if exists
                    "stock_qty": juice_qty,
                    "description": "Base aloe juice concentrate for spray drying (200:1 ratio)"
                },
                # Utilities
                {
                    "item_code": self.utility_items['water'],
                    "qty": water_qty,
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Process water for cleaning and cooling"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": electricity_qty,
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "Electrical power for spray dryer operation"
                },
                {
                    "item_code": self.utility_items['gas'],
                    "qty": gas_qty,
                    "uom": "Nos",
                    "rate": 0.50,
                    "description": "Natural gas for heat generation in spray dryer"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": labor_qty,
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Operator time for spray drying process"
                }
            ],
            "operations": []  # Operations will be added in Phase 2B when workstations exist
            # Future operation: Spray Drying - 240 mins @ Spray Dryer - Plant 2
        }
    
        return bom_template


    def _build_template_qx_blend(self, product_code, item):
        """
        Build detailed BOM template for QX Blend products (06XX family)
    
        Process: Dry blending of spray dried powder (0307) with Maltodextrin
        Variable ratios: 5% to 90% Aloe content
    
        Args:
            product_code (str): Product code (e.g., '0601' = 5% Aloe, '0611' = 90% Aloe)
            item (Document): Item document
        
        Returns:
            dict: BOM structure with components and operations
        """
        # QX Blend ratio mapping: code → (aloe_pct, maltodextrin_pct)
        QX_RATIOS = {
            '0601': (5, 95),   '0602': (10, 90),  '0603': (15, 85),
            '0604': (20, 80),  '0605': (30, 70),  '0606': (40, 60),
            '0607': (50, 50),  '0608': (60, 40),  '0609': (70, 30),
            '0610': (80, 20),  '0611': (90, 10)
        }
    
        # Get ratio for this product code
        if product_code not in QX_RATIOS:
            frappe.throw(f"Unknown QX product code: {product_code}")
    
        aloe_pct, maltodextrin_pct = QX_RATIOS[product_code]
    
        # Base quantity: 100 kg of finished blend
        base_qty = 100
    
        # Component quantities based on percentages
        aloe_powder_qty = base_qty * (aloe_pct / 100)      # kg of 0307
        maltodextrin_qty = base_qty * (maltodextrin_pct / 100)  # kg of maltodextrin
    
        # Utility consumption (minimal for dry blending)
        water_qty = 50       # Litre - Equipment cleaning
        electricity_qty = 20  # kWh - V-blender operation
        labor_qty = 2        # Hours - Operator time
        
        bom_template = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": base_qty,
            "uom": item.stock_uom,  # Should be "Kg"
            "is_active": 1,
            "is_default": 1,
            "with_operations": 0,
            "items": [
                # Component 1: Aloe spray dried powder
                {
                    "item_code": "0307",
                    "item_name": "Aloe Vera Spray Dried Powder 200:1",
                    "qty": aloe_powder_qty,
                    "uom": "Kg",
                    "rate": 0.00,
                    "stock_qty": aloe_powder_qty,
                    "description": f"Aloe powder component ({aloe_pct}% of blend)"
                },
                # Component 2: Maltodextrin carrier
                {
                    "item_code": "MALTODEXTRIN",
                    "item_name": "Maltodextrin",
                    "qty": maltodextrin_qty,
                    "uom": "Kg",
                    "rate": 2.50,
                    "stock_qty": maltodextrin_qty,
                    "description": f"Maltodextrin carrier ({maltodextrin_pct}% of blend)"
                },
                # Utilities
                {
                    "item_code": self.utility_items['water'],
                    "qty": water_qty,
                    "uom": "Litre",
                    "rate": 0.001,
                    "description": "Equipment cleaning water"
                },
                {
                    "item_code": self.utility_items['electricity'],
                    "qty": electricity_qty,
                    "uom": "Nos",
                    "rate": 0.15,
                    "description": "V-blender electrical consumption"
                },
                {
                    "item_code": self.utility_items['labor'],
                    "qty": labor_qty,
                    "uom": "Nos",
                    "rate": 15.00,
                    "description": "Blending operation labor"
                }
            ],
            "operations": []  # Future: V-Blender operation
        }
    
        return bom_template
    # ==== END SPRAY DRIED POWDER TEMPLATE ====
    
    def generate_test_boms_for_web_codes(self):
        """Generate all 29 test BOMs for web product codes"""
        web_codes = self._get_web_product_codes()
        results = {'success': [], 'failed': [], 'skipped': []}
        
        for product_code in web_codes:
            try:
                if not frappe.db.exists("Item", product_code):
                    results['skipped'].append({
                        'code': product_code,
                        'reason': 'Item does not exist'
                    })
                    continue
                
                existing_bom = frappe.db.get_value("BOM", 
                    {"item": product_code, "is_active": 1, "docstatus": 1}, 
                    "name"
                )
                
                if existing_bom:
                    results['skipped'].append({
                        'code': product_code,
                        'reason': f'Active BOM exists: {existing_bom}'
                    })
                    continue
                
                bom_name = self.create_bom_from_product_code(product_code)
                results['success'].append({'code': product_code, 'bom': bom_name})
                frappe.db.commit()
                
            except Exception as e:
                frappe.log_error(message=str(e), title=f"BOM Generation Failed: {product_code}")
                results['failed'].append({'code': product_code, 'error': str(e)})
        
        return results
    
    def validate_generated_bom(self, bom_name):
        """Validate generated BOM structure and costing"""
        bom = frappe.get_doc("BOM", bom_name)
        issues = []
        
        if not bom.items:
            issues.append("BOM has no items")
        
        try:
            bom.update_cost()
            frappe.db.commit()
        except Exception as e:
            issues.append(f"Cost calculation failed: {str(e)}")
        
        item_codes = [item.item_code for item in bom.items]
        has_utility = any(utility_code in item_codes 
                         for utility_code in self.utility_items.values())
        if not has_utility:
            issues.append("No utility items found")
        
        return {
            "bom": bom_name,
            "valid": len(issues) == 0,
            "issues": issues,
            "total_cost": bom.total_cost if hasattr(bom, 'total_cost') else 0
        }


# These should be OUTSIDE the class (no indentation)
@frappe.whitelist()
def create_bom_from_batch(batch_name):
    """API endpoint to create BOM from batch"""
    try:
        batch = frappe.get_doc("Batch AMB", batch_name)
        bom_name = TemplateBOMService.create_bom_from_template(batch)
        return {"success": True, "message": _("BOM created successfully"), "bom_name": bom_name}
    except Exception as e:
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def create_template_from_bom(bom_name, product_code):
    """API endpoint to convert BOM to template"""
    try:
        template_name = TemplateBOMService.create_template_from_existing_bom(bom_name, product_code)
        return {"success": True, "message": _("Template created successfully"), "template_name": template_name}
    except Exception as e:
        return {"success": False, "message": str(e)}
    
    @frappe.whitelist()
    def create_bom_from_batch(batch_name):
        """API endpoint to create BOM from batch"""
        try:
            batch = frappe.get_doc("Batch AMB", batch_name)
            bom_name = TemplateBOMService.create_bom_from_template(batch)
        
            return {
                "success": True,
                "message": _("BOM created successfully"),
                "bom_name": bom_name
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    # ==== ADDED METHODS WEB PRODUCT CODES ====
    
    

    @frappe.whitelist()
    def create_template_from_bom(bom_name, product_code):
        """API endpoint to convert BOM to template"""
        try:
            template_name = TemplateBOMService.create_template_from_existing_bom(bom_name, product_code)
        
            return {
                "success": True,
                "message": _("Template created successfully"),
                "template_name": template_name
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
