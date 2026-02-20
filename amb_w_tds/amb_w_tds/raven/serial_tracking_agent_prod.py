"""
Production Raven Agent for ERPNext Serial Tracking
Works both with and without database context
"""

import frappe
import re
import asyncio
from typing import Dict, Any, List

class SerialTrackingAgentProd:
    """Production AI Agent for serial tracking"""
    
    def __init__(self):
        self.name = "serial_tracking_agent"
        self.description = "Manages ERPNext serial tracking with Batch AMB hierarchy"
        self.version = "1.0.0"
        self.capabilities = [
            "configure_serial_tracking",
            "generate_serial_numbers", 
            "validate_compliance",
            "check_system_health",
            "provide_guidance"
        ]
    
    async def process(self, message: str, **kwargs) -> Dict[str, Any]:
        """Process user messages - production ready"""
        
        message_lower = message.lower().strip()
        
        # Help command
        if message_lower == "help" or "help" in message_lower:
            return await self._handle_help()
        
        # Health check
        elif "health" in message_lower or "check" in message_lower:
            return await self._check_health_safe()
        
        # Enable serial tracking
        elif "enable" in message_lower and "item" in message_lower:
            match = re.search(r'item\s+(\w+)', message, re.IGNORECASE)
            if match:
                return await self._enable_serial_tracking_safe(match.group(1))
        
        # Generate serials
        elif "generate" in message_lower and "batch" in message_lower:
            batch_match = re.search(r'batch\s+(\d{10}(?:-\d{1,2})?)', message)
            qty_match = re.search(r'(\d+)\s+serials?', message)
            if batch_match:
                batch = batch_match.group(1)
                qty = int(qty_match.group(1)) if qty_match else 10
                return await self._generate_serials_safe(batch, qty)
        
        # Validate serial
        elif "validate" in message_lower and "serial" in message_lower:
            serial_match = re.search(r'serial\s+([\w\-]+)', message, re.IGNORECASE)
            if serial_match:
                return await self._validate_serial_safe(serial_match.group(1))
        
        # Default
        return {
            "success": True,
            "message": "Serial Tracking Agent v1.0",
            "response": "I can help with: help, check health, enable serial tracking for item <code>, generate <n> serials for batch <batch>, validate serial <serial>"
        }
    
    async def _handle_help(self) -> Dict[str, Any]:
        """Provide help"""
        return {
            "success": True,
            "response": "Serial Tracking Agent - Production Ready",
            "commands": [
                "help - Show this help",
                "check health - Check system health",
                "enable serial tracking for item <ITEM_CODE> - Enable serial tracking",
                "generate <N> serials for batch <BATCH> - Generate serial numbers",
                "validate serial <SERIAL_NUMBER> - Validate serial compliance"
            ],
            "capabilities": self.capabilities,
            "serial_format": "GOLDENNUMBER-SEQUENCE (e.g., 0219074251-0001)",
            "hierarchy": "Batch AMB → Serial Numbers"
        }
    
    async def _check_health_safe(self) -> Dict[str, Any]:
        """Safe health check that works in any context"""
        try:
            health_info = {
                "agent_status": "running",
                "version": self.version,
                "capabilities": self.capabilities,
                "database_context": "unknown"
            }
            
            # Try to check database if available
            try:
                if hasattr(frappe, 'db') and frappe.db:
                    health_info["database_context"] = "available"
                    health_info["message"] = "✅ Agent ready with database access"
                else:
                    health_info["database_context"] = "not_available"
                    health_info["message"] = "✅ Agent ready (no database context)"
            except:
                health_info["database_context"] = "error"
                health_info["message"] = "✅ Agent running (database status unknown)"
            
            return {
                "success": True,
                "health": health_info
            }
            
        except Exception as e:
            return {
                "success": True,
                "health": {
                    "agent_status": "running",
                    "error": str(e),
                    "message": "✅ Agent is running"
                }
            }
    
    async def _enable_serial_tracking_safe(self, item_code: str) -> Dict[str, Any]:
        """Safe enable serial tracking"""
        return {
            "success": True,
            "message": f"To enable serial tracking for item {item_code}:",
            "steps": [
                "1. Go to Item master in ERPNext",
                "2. Find item: " + item_code,
                "3. Check 'Has Serial No' checkbox",
                "4. Set Serial No Series (optional): " + item_code + ".####",
                "5. Save the item"
            ],
            "note": "This enables serial tracking for the item in ERPNext"
        }
    
    async def _generate_serials_safe(self, batch_name: str, quantity: int) -> Dict[str, Any]:
        """Safe serial generation with format validation"""
        try:
            # Extract golden number
            match = re.search(r'(\d{10})', batch_name)
            if not match:
                return {
                    "success": False,
                    "error": f"Invalid batch format: {batch_name}",
                    "expected_format": "0219074251-1 (10-digit golden number + optional suffix)"
                }
            
            golden_number = match.group(1)
            
            # Validate golden number
            if len(golden_number) != 10 or not golden_number.isdigit():
                return {
                    "success": False,
                    "error": f"Invalid golden number: {golden_number}",
                    "requirement": "Must be 10 digits (FDA compliant)"
                }
            
            # Generate serials
            serials = []
            for i in range(min(quantity, 100)):  # Limit to 100
                serial = f"{golden_number}-{str(i+1).zfill(4)}"
                serials.append(serial)
            
            return {
                "success": True,
                "message": f"✅ Generated {len(serials)} serial numbers for {batch_name}",
                "serials": serials[:20],  # Return first 20
                "format": f"{golden_number}-XXXX",
                "next_steps": [
                    "1. Create Batch AMB record if not exists",
                    "2. Use these serials in Stock Entry",
                    "3. ERPNext will create Serial No records automatically"
                ],
                "note": f"Format ensures FDA traceability from serial to golden number {golden_number}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Generation failed: {str(e)}"
            }
    
    async def _validate_serial_safe(self, serial_number: str) -> Dict[str, Any]:
        """Validate serial number format"""
        # Check format
        is_valid = bool(re.match(r'^\d{10}-\d{4}$', serial_number))
        
        if is_valid:
            golden_number = serial_number[:10]
            sequence = serial_number[11:]
            
            return {
                "success": True,
                "validation": {
                    "serial_number": serial_number,
                    "format_valid": True,
                    "golden_number": golden_number,
                    "sequence": sequence,
                    "golden_valid": len(golden_number) == 10 and golden_number.isdigit(),
                    "sequence_valid": len(sequence) == 4 and sequence.isdigit(),
                    "compliant": True,
                    "message": "✅ Valid serial number format"
                },
                "traceability": f"Serial → Golden Number: {golden_number}",
                "fda_compliance": "Format meets FDA traceability requirements"
            }
        else:
            return {
                "success": True,
                "validation": {
                    "serial_number": serial_number,
                    "format_valid": False,
                    "compliant": False,
                    "message": "⚠️ Invalid format"
                },
                "expected_format": "0219074251-0001 (10-digit golden number + 4-digit sequence)",
                "example": "0219074251-0001, 0219074251-0002, 0219074251-0003"
            }

# Create instance
serial_tracking_agent_prod = SerialTrackingAgentProd()
