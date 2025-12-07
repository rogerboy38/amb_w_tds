"""
Final Raven Agent for ERPNext Serial Tracking with actual ERPNext operations
"""

import frappe
import re
import asyncio
from typing import Dict, Any, List
from frappe import _

class SerialTrackingAgentFinal:
    """AI Agent for managing serial tracking with actual ERPNext integration"""
    
    def __init__(self):
        self.name = "serial_tracking_agent"
        self.description = "Manages ERPNext serial tracking with Batch AMB hierarchy"
        self.version = "2.0.0"
        self.capabilities = [
            "configure_serial_tracking",
            "generate_serial_numbers", 
            "validate_compliance",
            "check_hierarchy_integrity",
            "fix_common_issues"
        ]
    
    async def process(self, message: str, **kwargs) -> Dict[str, Any]:
        """Process user messages with actual ERPNext operations"""
        
        message_lower = message.lower().strip()
        
        # Help command
        if message_lower == "help" or "help" in message_lower:
            return await self._handle_help()
        
        # Health check
        elif "health" in message_lower or "check" in message_lower:
            return await self._check_system_health()
        
        # Enable serial tracking
        elif "enable" in message_lower and "item" in message_lower:
            match = re.search(r'item\s+(\w+)', message, re.IGNORECASE)
            if match:
                return await self._enable_serial_tracking_actual(match.group(1))
        
        # Generate serials
        elif "generate" in message_lower and "batch" in message_lower:
            batch_match = re.search(r'batch\s+(\d{10}(?:-\d{1,2})?)', message)
            qty_match = re.search(r'(\d+)\s+serials?', message)
            if batch_match:
                batch = batch_match.group(1)
                qty = int(qty_match.group(1)) if qty_match else 10
                return await self._generate_serials_actual(batch, qty)
        
        # Validate serial
        elif "validate" in message_lower and "serial" in message_lower:
            serial_match = re.search(r'serial\s+([\w\-]+)', message, re.IGNORECASE)
            if serial_match:
                return await self._validate_serial_actual(serial_match.group(1))
        
        # Default response
        return {
            "success": True,
            "message": f"Serial Tracking Agent v{self.version}",
            "response": "Available commands: help, check health, enable serial tracking for item <code>, generate <n> serials for batch <batch>, validate serial <serial_number>"
        }
    
    async def _handle_help(self) -> Dict[str, Any]:
        """Provide help"""
        return {
            "success": True,
            "response": "Serial Tracking Agent (v2.0) - Actual ERPNext Operations",
            "commands": [
                "help - Show this help",
                "check health - Check system health with actual database",
                "enable serial tracking for item <ITEM_CODE> - Actually enable serial tracking in ERPNext",
                "generate <N> serials for batch <BATCH> - Create actual Serial No records",
                "validate serial <SERIAL_NUMBER> - Validate serial number compliance"
            ],
            "capabilities": self.capabilities,
            "format_example": "Serial format: GOLDENNUMBER-SEQUENCE (e.g., 0219074251-0001)"
        }
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health with actual database"""
        try:
            # Check items with serial tracking
            items_with_serial = frappe.db.sql("""
                SELECT COUNT(*) as count 
                FROM `tabItem` 
                WHERE has_serial_no = 1
            """, as_dict=True)[0]
            
            # Check serial numbers
            serials_count = frappe.db.sql("""
                SELECT COUNT(*) as count 
                FROM `tabSerial No`
            """, as_dict=True)[0]
            
            # Check Batch AMB records
            batch_amb_count = frappe.db.sql("""
                SELECT COUNT(*) as count 
                FROM `tabBatch AMB`
            """, as_dict=True)[0]
            
            # Check Container Barrels
            container_count = frappe.db.sql("""
                SELECT COUNT(*) as count 
                FROM `tabContainer Barrels`
            """, as_dict=True)[0]
            
            return {
                "success": True,
                "health": {
                    "agent_status": "running",
                    "version": self.version,
                    "database_connected": True,
                    "items_with_serial_tracking": items_with_serial.get('count', 0),
                    "total_serial_numbers": serials_count.get('count', 0),
                    "batch_amb_records": batch_amb_count.get('count', 0),
                    "container_barrels": container_count.get('count', 0),
                    "message": "✅ System is healthy with database connection"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Health check failed: {str(e)}",
                "health": {
                    "agent_status": "running_with_errors",
                    "database_connected": False,
                    "message": f"⚠️ Health check error: {str(e)}"
                }
            }
    
    async def _enable_serial_tracking_actual(self, item_code: str) -> Dict[str, Any]:
        """Actually enable serial tracking for an item in ERPNext"""
        try:
            if not frappe.db.exists("Item", item_code):
                return {
                    "success": False,
                    "error": f"Item {item_code} does not exist in ERPNext"
                }
            
            item = frappe.get_doc("Item", item_code)
            
            if item.has_serial_no:
                return {
                    "success": True,
                    "message": f"✅ Item {item_code} already has serial tracking enabled",
                    "item_code": item_code,
                    "has_serial_no": True
                }
            
            # Enable serial tracking
            item.has_serial_no = 1
            item.serial_no_series = f"{item_code}.####"
            item.save()
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"✅ Successfully enabled serial tracking for item: {item_code}",
                "item_code": item_code,
                "has_serial_no": True,
                "serial_no_series": item.serial_no_series,
                "note": "Item updated in ERPNext database"
            }
            
        except Exception as e:
            frappe.log_error(f"Failed to enable serial tracking for {item_code}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to enable serial tracking: {str(e)}"
            }
    
    async def _generate_serials_actual(self, batch_name: str, quantity: int) -> Dict[str, Any]:
        """Actually generate serial numbers in ERPNext"""
        try:
            # Extract golden number
            match = re.search(r'(\d{10})', batch_name)
            if not match:
                return {
                    "success": False,
                    "error": f"Could not extract golden number from {batch_name}. Expected format: 0219074251-1"
                }
            
            golden_number = match.group(1)
            
            # Check if Batch AMB exists
            if not frappe.db.exists("Batch AMB", {"golden_number": golden_number}):
                return {
                    "success": False,
                    "error": f"Batch AMB with golden number {golden_number} not found. Create it first.",
                    "suggestion": "Create Batch AMB record before generating serials"
                }
            
            # Get next sequence
            last_serial = frappe.db.sql("""
                SELECT name 
                FROM `tabSerial No` 
                WHERE name LIKE %s 
                ORDER BY name DESC 
                LIMIT 1
            """, f"{golden_number}-%", as_dict=True)
            
            start_seq = 1
            if last_serial:
                last_name = last_serial[0]['name']
                seq_match = re.search(r'-(\d{4})$', last_name)
                if seq_match:
                    start_seq = int(seq_match.group(1)) + 1
            
            # Generate and create serials
            serials = []
            created_count = 0
            
            for i in range(quantity):
                seq = start_seq + i
                serial_no = f"{golden_number}-{str(seq).zfill(4)}"
                
                # Check if serial already exists
                if not frappe.db.exists("Serial No", serial_no):
                    # Create Serial No record
                    serial_doc = frappe.new_doc("Serial No")
                    serial_doc.name = serial_no
                    serial_doc.item_code = "0219"  # Default item, can be parameterized
                    serial_doc.batch_no = batch_name
                    
                    # Add custom golden number field if it exists
                    if frappe.db.exists("Custom Field", {"fieldname": "custom_golden_number", "dt": "Serial No"}):
                        serial_doc.custom_golden_number = golden_number
                    
                    serial_doc.insert(ignore_permissions=True)
                    created_count += 1
                
                serials.append(serial_no)
            
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"✅ Created {created_count} new Serial No records for batch {batch_name}",
                "serials": serials[:20],  # Return first 20
                "total_requested": quantity,
                "total_created": created_count,
                "format": f"{golden_number}-XXXX",
                "note": f"Serial numbers saved in ERPNext database. Existing serials were not duplicated."
            }
            
        except Exception as e:
            frappe.log_error(f"Failed to generate serials for {batch_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to generate serials: {str(e)}"
            }
    
    async def _validate_serial_actual(self, serial_number: str) -> Dict[str, Any]:
        """Validate a serial number in ERPNext"""
        try:
            if not frappe.db.exists("Serial No", serial_number):
                return {
                    "success": False,
                    "error": f"Serial number {serial_number} not found in ERPNext"
                }
            
            serial_doc = frappe.get_doc("Serial No", serial_number)
            
            # Check format
            format_valid = bool(re.match(r'^\d{10}-\d{4}$', serial_number))
            
            # Extract golden number
            golden_number = serial_number[:10] if len(serial_number) >= 10 else None
            golden_valid = golden_number and len(golden_number) == 10 and golden_number.isdigit()
            
            # Check Batch AMB link
            has_batch_link = bool(serial_doc.batch_no)
            
            # Check if linked to Batch AMB
            batch_amb_exists = False
            if golden_number:
                batch_amb_exists = frappe.db.exists("Batch AMB", {"golden_number": golden_number})
            
            compliance = {
                "serial_number": serial_number,
                "exists_in_system": True,
                "format_valid": format_valid,
                "golden_number": golden_number,
                "golden_valid": golden_valid,
                "has_batch_link": has_batch_link,
                "batch_amb_exists": batch_amb_exists,
                "item_code": serial_doc.item_code,
                "status": serial_doc.status,
                "creation_date": str(serial_doc.creation) if serial_doc.creation else None,
                "compliant": all([format_valid, golden_valid, has_batch_link, batch_amb_exists])
            }
            
            if not compliance["compliant"]:
                compliance["issues"] = []
                if not format_valid:
                    compliance["issues"].append("Invalid serial number format (should be: 0219074251-0001)")
                if not golden_valid:
                    compliance["issues"].append("Invalid golden number (should be 10 digits)")
                if not has_batch_link:
                    compliance["issues"].append("Not linked to a batch in ERPNext")
                if not batch_amb_exists:
                    compliance["issues"].append(f"Golden number {golden_number} not found in Batch AMB")
            
            return {
                "success": True,
                "compliance_check": compliance,
                "message": "✅ Compliant - Full traceability established" if compliance["compliant"] else "⚠️ Non-compliant - Traceability issues found",
                "recommendations": self._get_compliance_recommendations(compliance)
            }
            
        except Exception as e:
            frappe.log_error(f"Failed to validate serial {serial_number}: {str(e)}")
            return {
                "success": False,
                "error": f"Validation failed: {str(e)}"
            }
    
    def _get_compliance_recommendations(self, compliance: Dict) -> List[str]:
        """Get recommendations for compliance issues"""
        recs = []
        
        if not compliance.get("format_valid"):
            recs.append("Serial number format should be: GOLDENNUMBER-SEQUENCE (e.g., 0219074251-0001)")
        
        if not compliance.get("golden_valid"):
            recs.append("Golden number must be 10 digits (FDA requirement)")
        
        if not compliance.get("has_batch_link"):
            recs.append("Link serial number to a batch in Stock Entry or Delivery Note")
        
        if not compliance.get("batch_amb_exists"):
            recs.append(f"Create Batch AMB record for golden number {compliance.get('golden_number')}")
        
        return recs if recs else ["All FDA compliance requirements met"]

# Create instance for Raven
serial_tracking_agent = SerialTrackingAgentFinal()
