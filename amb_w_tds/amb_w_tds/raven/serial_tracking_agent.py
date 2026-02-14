"""
Simple Raven Agent for ERPNext Serial Tracking
"""

import frappe
import re
import asyncio
from typing import Dict, Any

class SerialTrackingAgent:
    """Simple AI Agent for managing serial tracking"""
    
    def __init__(self):
        self.name = "serial_tracking_agent"
        self.description = "Manages ERPNext serial tracking with Batch AMB hierarchy"
        self.version = "1.0.0"
        self.capabilities = [
            "configure_serial_tracking",
            "generate_serial_numbers",
            "validate_compliance",
            "basic_health_checks"
        ]
    
    async def process(self, message: str, **kwargs) -> Dict[str, Any]:
        """Process user messages"""
        
        message_lower = message.lower().strip()
        
        # Help command
        if message_lower == "help" or "help" in message_lower:
            return await self._handle_help()
        
        # Health check commands
        elif "health" in message_lower or "check" in message_lower:
            return await self._handle_health()
        
        # Enable serial tracking
        elif "enable" in message_lower and "item" in message_lower:
            match = re.search(r'item\s+(\w+)', message, re.IGNORECASE)
            if match:
                return await self._enable_serial_tracking(match.group(1))
        
        # Generate serials
        elif "generate" in message_lower and "batch" in message_lower:
            batch_match = re.search(r'batch\s+(\d{10}(?:-\d{1,2})?)', message)
            qty_match = re.search(r'(\d+)\s+serials?', message)
            if batch_match:
                batch = batch_match.group(1)
                qty = int(qty_match.group(1)) if qty_match else 10
                return await self._generate_serials(batch, qty)
        
        # Default response
        return {
            "success": True,
            "message": f"Serial Tracking Agent: {message}",
            "response": "I can help with: help, check health, enable serial tracking for item <code>, generate <n> serials for batch <batch>"
        }
    
    async def _handle_help(self) -> Dict[str, Any]:
        """Provide help"""
        return {
            "success": True,
            "response": "Serial Tracking Agent Help",
            "commands": [
                "help - Show this help",
                "check health - Check agent health",
                "enable serial tracking for item <ITEM_CODE> - Enable serial tracking",
                "generate <N> serials for batch <BATCH> - Generate serial numbers"
            ],
            "capabilities": self.capabilities
        }
    
    async def _handle_health(self) -> Dict[str, Any]:
        """Check system health"""
        return {
            "success": True,
            "health": {
                "agent_status": "running",
                "version": self.version,
                "capabilities": self.capabilities,
                "message": "✅ Agent is working and ready to manage serial tracking"
            }
        }
    
    async def _enable_serial_tracking(self, item_code: str) -> Dict[str, Any]:
        """Enable serial tracking for an item"""
        return {
            "success": True,
            "message": f"✅ Would enable serial tracking for item: {item_code}",
            "note": "In production, this would update the Item doctype in ERPNext with has_serial_no = 1"
        }
    
    async def _generate_serials(self, batch_name: str, quantity: int) -> Dict[str, Any]:
        """Generate serial numbers"""
        try:
            # Extract golden number
            match = re.search(r'(\d{10})', batch_name)
            if not match:
                return {
                    "success": False,
                    "error": f"Could not extract golden number from {batch_name}"
                }
            
            golden_number = match.group(1)
            serials = []
            
            for i in range(min(quantity, 20)):  # Limit to 20 for demo
                serial = f"{golden_number}-{str(i+1).zfill(4)}"
                serials.append(serial)
            
            return {
                "success": True,
                "message": f"✅ Generated {len(serials)} serial numbers for batch {batch_name}",
                "serials": serials,
                "format": f"{golden_number}-XXXX",
                "note": f"In production, would create {quantity} Serial No records in ERPNext"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate serials: {str(e)}"
            }
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health with actual database"""
        try:
            # Try to get database stats if connected
            database_connected = False
            stats = {}
            
            try:
                # Check if we have a database connection
                if hasattr(frappe, 'db') and frappe.db:
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
                    
                    stats = {
                        "database_connected": True,
                        "items_with_serial_tracking": items_with_serial.get('count', 0),
                        "total_serial_numbers": serials_count.get('count', 0)
                    }
                    database_connected = True
                else:
                    stats = {"database_connected": False, "message": "No active database connection"}
                    
            except Exception as db_error:
                stats = {
                    "database_connected": False,
                    "error": str(db_error),
                    "message": "Database connection failed"
                }
            
            return {
                "success": True,
                "health": {
                    "agent_status": "running",
                    "version": self.version,
                    **stats,
                    "capabilities": self.capabilities,
                    "message": "✅ Agent is running" + (" with database connection" if database_connected else " (no database context)")
                }
            }
            
        except Exception as e:
            return {
                "success": True,  # Still return success for agent
                "health": {
                    "agent_status": "running",
                    "database_connected": False,
                    "error": str(e),
                    "message": "⚠️ Agent running without database context"
                }
            }
