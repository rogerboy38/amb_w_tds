"""
Golden Number Generation Service
Format: 0227022253 = Product(4) + Consecutive(3) + Year(2) + Plant(1)
"""

import frappe
from frappe import _
from datetime import datetime

class GoldenNumberService:
    """Service for generating and managing golden numbers"""
    
    PRODUCT_CODES = {
        '0227': 'Concentrate',
        '0303': 'Powder',
        '0334': 'Formulated',
        '0705': 'Shipping Product'
    }
    
    @staticmethod
    def generate_from_work_order(work_order_name):
        """
        Generate golden number from Work Order
        Args:
            work_order_name: Work Order ID (e.g., "MFG-WO-02225")
        Returns:
            dict with golden_number and components
        """
        try:
            wo = frappe.get_doc("Work Order", work_order_name)
            
            # Extract product code from production item
            product_code = GoldenNumberService._get_product_code(wo.production_item)
            
            # Extract consecutive and year from WO name
            consecutive, year = GoldenNumberService._extract_wo_numbers(work_order_name)
            
            # Get plant code
            plant_code = GoldenNumberService._get_plant_code(wo)
            
            # Build golden number
            golden_number = f"{product_code}{consecutive}{year}{plant_code}"
            
            return {
                'golden_number': golden_number,
                'product_code': product_code,
                'consecutive_number': consecutive,
                'year_code': year,
                'plant_code': plant_code,
                'product_name': GoldenNumberService.PRODUCT_CODES.get(product_code, 'Unknown')
            }
            
        except Exception as e:
            frappe.log_error(f"Golden Number Generation Error: {str(e)}", "Golden Number Service")
            return None
    
    @staticmethod
    def _get_product_code(item_code):
        """Extract product code from item code"""
        if not item_code:
            return "0227"  # Default
            
        for code in GoldenNumberService.PRODUCT_CODES.keys():
            if item_code.startswith(code):
                return code
        
        return "0227"  # Default fallback
    
    @staticmethod
    def _extract_wo_numbers(work_order_name):
        """
        Extract consecutive and year from WO name
        MFG-WO-02225 -> consecutive=022, year=25
        """
        if 'MFG-WO-' in work_order_name:
            wo_number = work_order_name.replace('MFG-WO-', '')
            consecutive = wo_number[:3]  # First 3 digits
            year = wo_number[3:5]        # Next 2 digits
            return consecutive, year
        
        # Fallback: use current date
        now = datetime.now()
        consecutive = "001"
        year = now.strftime("%y")
        return consecutive, year
    
    @staticmethod
    def _get_plant_code(work_order):
        """Get plant code from Work Order"""
        plant_code = getattr(work_order, 'custom_plant_code', '3')
        
        # Clean plant code - remove descriptive text
        if isinstance(plant_code, str):
            plant_code = plant_code.split('(')[0].strip()
        
        return plant_code
    
    @staticmethod
    def validate_golden_number(golden_number):
        """
        Validate golden number format
        Must be exactly 10 characters: 0227022253
        """
        if not golden_number:
            return False, "Golden number is empty"
        
        if len(golden_number) != 10:
            return False, f"Golden number must be 10 characters, got {len(golden_number)}"
        
        # Validate product code
        product_code = golden_number[:4]
        if product_code not in GoldenNumberService.PRODUCT_CODES:
            return False, f"Invalid product code: {product_code}"
        
        # Validate consecutive (3 digits)
        try:
            int(golden_number[4:7])
        except ValueError:
            return False, "Consecutive number must be 3 digits"
        
        # Validate year (2 digits)
        try:
            int(golden_number[7:9])
        except ValueError:
            return False, "Year must be 2 digits"
        
        # Validate plant (1 digit)
        try:
            int(golden_number[9])
        except ValueError:
            return False, "Plant code must be 1 digit"
        
        return True, "Valid golden number"
    
    @staticmethod
    def get_next_consecutive(product_code, year_code, plant_code):
        """Get next consecutive number for given product/year/plant"""
        # Query existing golden numbers with same product/year/plant
        pattern = f"{product_code}%{year_code}{plant_code}"
        
        existing = frappe.db.sql("""
            SELECT golden_number 
            FROM `tabBatch AMB` 
            WHERE golden_number LIKE %s 
            ORDER BY golden_number DESC 
            LIMIT 1
        """, (pattern,))
        
        if existing and existing[0][0]:
            last_golden = existing[0][0]
            last_consecutive = int(last_golden[4:7])
            next_consecutive = str(last_consecutive + 1).zfill(3)
        else:
            next_consecutive = "001"
        
        return next_consecutive

@frappe.whitelist()
def generate_golden_number(work_order_name):
    """API endpoint for golden number generation"""
    result = GoldenNumberService.generate_from_work_order(work_order_name)
    if result:
        return {
            'success': True,
            'data': result
        }
    else:
        return {
            'success': False,
            'message': 'Failed to generate golden number'
        }

@frappe.whitelist()
def validate_golden_number(golden_number):
    """API endpoint for golden number validation"""
    is_valid, message = GoldenNumberService.validate_golden_number(golden_number)
    return {
        'valid': is_valid,
        'message': message
    }
