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
        self.description = "Manages ERPNext serial tracking"
        self.version = "1.0.0"
        print("✅ Agent created")
    
    async def process(self, message: str, **kwargs) -> Dict[str, Any]:
        """Process user messages"""
        
        message_lower = message.lower()
        
        if "help" in message_lower:
            return await self._handle_help()
        elif "health" in message_lower or "check" in message_lower:
            return await self._handle_health()
        elif "enable" in message_lower and "item" in message_lower:
            match = re.search(r'item\s+(\w+)', message, re.IGNORECASE)
            if match:
                return await self._enable_serial_tracking(match.group(1))
        
        return {
            "success": True,
            "message": f"I'm the Serial Tracking Agent. You said: {message}",
            "response": "Try: 'help', 'check health', or 'enable serial tracking for item 0219'"
        }
    
    async def _handle_help(self) -> Dict[str, Any]:
        """Provide help"""
        return {
            "success": True,
            "response": "Serial Tracking Agent Help",
            "commands": [
                "help - Show this help",
                "check health - Check system health",
                "enable serial tracking for item <ITEM_CODE> - Enable serial tracking"
            ]
        }
    
    async def _handle_health(self) -> Dict[str, Any]:
        """Check system health"""
        try:
            items_count = frappe.db.sql("""
                SELECT COUNT(*) as count FROM `tabItem` WHERE has_serial_no = 1
            """, as_dict=True)[0]
            
            serials_count = frappe.db.sql("""
                SELECT COUNT(*) as count FROM `tabSerial No`
            """, as_dict=True)[0]
            
            return {
                "success": True,
                "health": {
                    "items_with_serial_tracking": items_count.get('count', 0),
                    "total_serial_numbers": serials_count.get('count', 0),
                    "status": "healthy"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Health check failed: {str(e)}"
            }
    
    async def _enable_serial_tracking(self, item_code: str) -> Dict[str, Any]:
        """Enable serial tracking for an item"""
        try:
            if not frappe.db.exists("Item", item_code):
                return {
                    "success": False,
                    "error": f"Item {item_code} not found"
                }
            
            item = frappe.get_doc("Item", item_code)
            item.has_serial_no = 1
            item.serial_no_series = f"{item_code}.####"
            item.save()
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"Enabled serial tracking for {item_code}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to enable serial tracking: {str(e)}"
            }
