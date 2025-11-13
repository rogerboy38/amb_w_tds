"""
Template-Based BOM Service
Generates production BOMs with detailed templates for web product codes
"""

import frappe
from frappe import _
from frappe.utils import flt


class TemplateBOMService:
    """Service for template-based BOM generation"""
    
    def __init__(self):
        self.utility_items = {
            'water': 'WATER-UTILITY',
            'electricity': 'ELECTRICITY-UTILITY',
            'gas': 'GAS-UTILITY',
            'labor': 'LABOR-COST'
        }
    
    def _get_web_product_codes(self):
        """Return list of 32 web product codes"""
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
            # Liquids (8)
            '0701', '0702', '0703', '0704',
            '0705', '0706', '0707', '0708'
        ]
    
    def create_bom_from_product_code(self, product_code):
        """
        Create BOM directly from product code
        
        Args:
            product_code (str): Product code (e.g., '0307', '0401')
            
        Returns:
            str: BOM name
        """
        try:
            if not frappe.db.exists("Item", product_code):
                frappe.throw(_("Item {0} does not exist").format(product_code))
        
            item = frappe.get_doc("Item", product_code)
        
            # Build detailed template based on product family
            bom_data = None
        
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
        
            # If no detailed template, fall back to basic
            if not bom_data:
                return self._create_basic_bom(product_code, item)
     
            new_bom = frappe.get_doc(bom_data)
            new_bom.is_default = 1
            new_bom.is_active = 1
            new_bom.insert(ignore_permissions=True)
            new_bom.submit()
        
            return new_bom.name
        
        except Exception as e:
            frappe.log_error(message=str(e), title=f"BOM Creation Failed: {product_code}")
            raise

    def _build_template_spray_dried_powder(self, product_code, item):
        """Build BOM for Spray Dried Powder (03XX)"""
        import frappe
        
        # Get prices
        juice_price = frappe.get_value("Item Price", 
                                       {"item_code": "0705", "price_list": "Standard Buying"}, 
                                       "price_list_rate") or 0.82
        
        # Quantities for 100kg output
        juice_quantity = 20000
        water_quantity = 500
        electricity_quantity = 150
        gas_quantity = 50
        labor_hours = 8
        
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 1,
            "items": [
                {
                    "item_code": "0705",
                    "item_name": "Aloe Vera Juice 1:1",
                    "qty": juice_quantity,
                    "uom": "Litre",
                    "rate": juice_price,
                    "amount": juice_quantity * juice_price
                },
                {
                    "item_code": "WATER-UTILITY",
                    "item_name": "Process Water",
                    "qty": water_quantity,
                    "uom": "Litre",
                    "rate": 0.005,
                    "amount": water_quantity * 0.005
                },
                {
                    "item_code": "ELECTRICITY-UTILITY",
                    "item_name": "Electricity",
                    "qty": electricity_quantity,
                    "uom": "Nos",
                    "rate": 0.15,
                    "amount": electricity_quantity * 0.15
                },
                {
                    "item_code": "GAS-UTILITY",
                    "item_name": "Natural Gas",
                    "qty": gas_quantity,
                    "uom": "Nos",
                    "rate": 0.50,
                    "amount": gas_quantity * 0.50
                },
                {
                    "item_code": "LABOR-COST",
                    "item_name": "Direct Labor",
                    "qty": labor_hours,
                    "uom": "Nos",
                    "rate": 25.00,
                    "amount": labor_hours * 25.00
                }
            ],
            "operations": [
                {
                    "operation": "Secado Spray",
                    "workstation": "WS-Secado",
                    "time_in_mins": 240,
                    "description": "Spray drying of liquid concentrate to powder (200:1 ratio)"
                },
                {
                    "operation": "P-3-OP-030-MOLIENDA",
                    "workstation": "WS-Molienda",
                    "time_in_mins": 60,
                    "description": "Milling and particle size reduction"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_acetypol(self, product_code, item):
        """Build BOM for Aloe Acetypol (04XX)"""
        import frappe
        
        powder_price = frappe.get_value("Item Price",
                                        {"item_code": "0307", "price_list": "Standard Buying"},
                                        "price_list_rate") or 165.68
        
        powder_quantity = 105
        carbon_quantity = 5
        water_quantity = 300
        electricity_quantity = 80
        labor_hours = 6
        
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 1,
            "items": [
                {
                    "item_code": "0307",
                    "item_name": "Aloe Vera Spray Dried Powder",
                    "qty": powder_quantity,
                    "uom": "Kg",
                    "rate": powder_price,
                    "amount": powder_quantity * powder_price
                },
                {
                    "item_code": "ACTIVATED-CARBON",
                    "item_name": "Activated Carbon",
                    "qty": carbon_quantity,
                    "uom": "Kg",
                    "rate": 8.50,
                    "amount": carbon_quantity * 8.50
                },
                {
                    "item_code": "WATER-UTILITY",
                    "item_name": "Process Water",
                    "qty": water_quantity,
                    "uom": "Litre",
                    "rate": 0.005,
                    "amount": water_quantity * 0.005
                },
                {
                    "item_code": "ELECTRICITY-UTILITY",
                    "item_name": "Electricity",
                    "qty": electricity_quantity,
                    "uom": "Nos",
                    "rate": 0.15,
                    "amount": electricity_quantity * 0.15
                },
                {
                    "item_code": "LABOR-COST",
                    "item_name": "Direct Labor",
                    "qty": labor_hours,
                    "uom": "Nos",
                    "rate": 25.00,
                    "amount": labor_hours * 25.00
                }
            ],
            "operations": [
                {
                    "operation": "P-3-OP-130-Decolorado de Jugo",
                    "workstation": "WS-Decoloracion",
                    "time_in_mins": 120,
                    "description": "Activated carbon decolorization process"
                },
                {
                    "operation": "P-3-OP-140-Filtrado de Jugo",
                    "workstation": "WS-Filtrado",
                    "time_in_mins": 90,
                    "description": "Carbon filtration and clarification"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_highpol(self, product_code, item):
        """Build BOM for Aloe Highpol (05XX)"""
        import frappe
        
        retentate_price = frappe.get_value("Item Price",
                                           {"item_code": "0302", "price_list": "Standard Buying"},
                                           "price_list_rate") or 150.00
        
        retentate_quantity = 150
        water_quantity = 400
        electricity_quantity = 180
        gas_quantity = 60
        labor_hours = 10
        
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 1,
            "items": [
                {
                    "item_code": "0302",
                    "item_name": "Aloe Vera Retentate",
                    "qty": retentate_quantity,
                    "uom": "Kg",
                    "rate": retentate_price,
                    "amount": retentate_quantity * retentate_price
                },
                {
                    "item_code": "WATER-UTILITY",
                    "item_name": "Process Water",
                    "qty": water_quantity,
                    "uom": "Litre",
                    "rate": 0.005,
                    "amount": water_quantity * 0.005
                },
                {
                    "item_code": "ELECTRICITY-UTILITY",
                    "item_name": "Electricity",
                    "qty": electricity_quantity,
                    "uom": "Nos",
                    "rate": 0.15,
                    "amount": electricity_quantity * 0.15
                },
                {
                    "item_code": "GAS-UTILITY",
                    "item_name": "Natural Gas",
                    "qty": gas_quantity,
                    "uom": "Nos",
                    "rate": 0.50,
                    "amount": gas_quantity * 0.50
                },
                {
                    "item_code": "LABOR-COST",
                    "item_name": "Direct Labor",
                    "qty": labor_hours,
                    "uom": "Nos",
                    "rate": 25.00,
                    "amount": labor_hours * 25.00
                }
            ],
            "operations": [
                {
                    "operation": "P-3-OP-140-Filtrado de Jugo",
                    "workstation": "WS-Filtrado",
                    "time_in_mins": 120,
                    "description": "Membrane ultrafiltration"
                },
                {
                    "operation": "Op 500-Evaporation",
                    "workstation": "WS-Concentrado",
                    "time_in_mins": 300,
                    "description": "Vacuum concentration (5% to 10%)"
                },
                {
                    "operation": "Op 830 Almacenaje en cuarto frio",
                    "workstation": "WS-Concentrado",
                    "time_in_mins": 60,
                    "description": "Cold storage preparation (0-2°C)"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_qx_blend(self, product_code, item):
        """Build BOM for QX Blends (06XX)"""
        import frappe
        
        QX_RATIOS = {
            '0601': (5, 95), '0602': (10, 90), '0603': (15, 85),
            '0604': (20, 80), '0605': (30, 70), '0606': (40, 60),
            '0607': (50, 50), '0608': (60, 40), '0609': (70, 30),
            '0610': (80, 20), '0611': (90, 10)
        }
        
        aloe_percent, maltodextrin_percent = QX_RATIOS.get(product_code, (50, 50))
        
        powder_price = frappe.get_value("Item Price",
                                        {"item_code": "0307", "price_list": "Standard Buying"},
                                        "price_list_rate") or 165.68
        
        powder_quantity = aloe_percent
        maltodextrin_quantity = maltodextrin_percent
        water_quantity = 50
        electricity_quantity = 20
        labor_hours = 2
        
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 100,
            "uom": item.stock_uom,
            "is_active": 1,
            "is_default": 1,
            "with_operations": 1,
            "items": [
                {
                    "item_code": "0307",
                    "item_name": "Aloe Vera Spray Dried Powder",
                    "qty": powder_quantity,
                    "uom": "Kg",
                    "rate": powder_price,
                    "amount": powder_quantity * powder_price
                },
                {
                    "item_code": "MALTODEXTRIN",
                    "item_name": "Maltodextrin",
                    "qty": maltodextrin_quantity,
                    "uom": "Kg",
                    "rate": 2.50,
                    "amount": maltodextrin_quantity * 2.50
                },
                {
                    "item_code": "WATER-UTILITY",
                    "item_name": "Process Water",
                    "qty": water_quantity,
                    "uom": "Litre",
                    "rate": 0.005,
                    "amount": water_quantity * 0.005
                },
                {
                    "item_code": "ELECTRICITY-UTILITY",
                    "item_name": "Electricity",
                    "qty": electricity_quantity,
                    "uom": "Nos",
                    "rate": 0.15,
                    "amount": electricity_quantity * 0.15
                },
                {
                    "item_code": "LABOR-COST",
                    "item_name": "Direct Labor",
                    "qty": labor_hours,
                    "uom": "Nos",
                    "rate": 25.00,
                    "amount": labor_hours * 25.00
                }
            ],
            "operations": [
                {
                    "operation": "Mixing",
                    "workstation": "WS-Mixing",
                    "time_in_mins": 45,
                    "description": f"Dry blending: {aloe_percent}% aloe powder + {maltodextrin_percent}% maltodextrin"
                }
            ]
        }
        
        return bom_data
    
    def _build_template_liquid(self, product_code, item):
        """Build BOM for Innovaloe Liquids (07XX)"""
        import frappe
        
        # Detect concentration from item name
        concentration_factor = 1
        if '10:1' in item.item_name or '10/1' in item.item_name:
            concentration_factor = 10
        elif '20:1' in item.item_name or '20/1' in item.item_name:
            concentration_factor = 20
        elif '30:1' in item.item_name or '30/1' in item.item_name:
            concentration_factor = 30
        
        # Quantities for 1000L output
        aloe_leaf_quantity = 1000 * concentration_factor
        citric_quantity = 2
        sorbate_quantity = 1
        water_quantity = 2000
        electricity_quantity = 100
        labor_hours = 12
        
        # Operation times
        extraction_time = 240
        concentration_time = 60 * concentration_factor
        
        bom_data = {
            "doctype": "BOM",
            "item": product_code,
            "company": "AMB-Wellness",
            "quantity": 1000,
            "uom": "Litre",
            "is_active": 1,
            "is_default": 1,
            "with_operations": 1,
            "items": [
                {
                    "item_code": "ALOE-LEAF-FRESH",
                    "item_name": "Fresh Aloe Vera Leaves",
                    "qty": aloe_leaf_quantity,
                    "uom": "Kg",
                    "rate": 0.30,
                    "amount": aloe_leaf_quantity * 0.30
                },
                {
                    "item_code": "CITRIC-ACID",
                    "item_name": "Citric Acid",
                    "qty": citric_quantity,
                    "uom": "Kg",
                    "rate": 3.50,
                    "amount": citric_quantity * 3.50
                },
                {
                    "item_code": "POTASSIUM-SORBATE",
                    "item_name": "Potassium Sorbate",
                    "qty": sorbate_quantity,
                    "uom": "Kg",
                    "rate": 5.00,
                    "amount": sorbate_quantity * 5.00
                },
                {
                    "item_code": "WATER-UTILITY",
                    "item_name": "Process Water",
                    "qty": water_quantity,
                    "uom": "Litre",
                    "rate": 0.005,
                    "amount": water_quantity * 0.005
                },
                {
                    "item_code": "ELECTRICITY-UTILITY",
                    "item_name": "Electricity",
                    "qty": electricity_quantity,
                    "uom": "Nos",
                    "rate": 0.15,
                    "amount": electricity_quantity * 0.15
                },
                {
                    "item_code": "LABOR-COST",
                    "item_name": "Direct Labor",
                    "qty": labor_hours,
                    "uom": "Nos",
                    "rate": 25.00,
                    "amount": labor_hours * 25.00
                }
            ],
            "operations": [
                {
                    "operation": "P-3-OP-020- Lavado de hoja entera",
                    "workstation": "WS-Limpieza",
                    "time_in_mins": 120,
                    "description": "Washing and cleaning of whole aloe leaves"
                },
                {
                    "operation": "P-3-OP-030-MOLIENDA",
                    "workstation": "WS-Molienda",
                    "time_in_mins": extraction_time,
                    "description": "Extraction and pulping"
                },
                {
                    "operation": "Op 500-Evaporation",
                    "workstation": "WS-Concentrado",
                    "time_in_mins": concentration_time,
                    "description": f"Concentration to {concentration_factor}:1 ratio"
                },
                {
                    "operation": "Op 700 Pasteurizacion",
                    "workstation": "WS-Concentrado",
                    "time_in_mins": 60,
                    "description": "Pasteurization and preservation"
                }
            ]
        }
        
        return bom_data
    
    def _create_basic_bom(self, product_code, item):
        """Fallback: Create basic BOM with utilities"""
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
                    "rate": 0.005
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
                    "rate": 25.00
                }
            ]
        })
        
        bom.insert(ignore_permissions=True)
        bom.submit()
        return bom.name
