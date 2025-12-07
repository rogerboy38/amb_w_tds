"""
API-Enabled Raven Agent for ERPNext Serial Tracking
Can work internally or via REST API
"""

import re
import asyncio
import aiohttp
import json
from typing import Dict, Any, List
from urllib.parse import urljoin

class SerialTrackingAgentAPI:
    """API-Enabled AI Agent for serial tracking"""
    
    def __init__(self, api_config=None):
        self.name = "serial_tracking_agent"
        self.description = "Manages ERPNext serial tracking via API"
        self.version = "1.0.0"
        self.capabilities = [
            "configure_serial_tracking",
            "generate_serial_numbers", 
            "validate_compliance",
            "check_system_health",
            "api_integration"
        ]
        
        # API configuration
        self.api_config = api_config or {
            "base_url": None,  # e.g., "https://your-site.frappe.cloud"
            "api_key": None,
            "api_secret": None,
            "site_name": None
        }
        
        # Check if running inside Frappe
        self.has_frappe_context = False
        try:
            import frappe
            self.has_frappe_context = True
        except ImportError:
            pass
    
    async def process(self, message: str, **kwargs) -> Dict[str, Any]:
        """Process user messages - works with API or internal"""
        
        message_lower = message.lower().strip()
        
        # Help command
        if message_lower == "help" or "help" in message_lower:
            return await self._handle_help()
        
        # Health check
        elif "health" in message_lower or "check" in message_lower:
            return await self._check_health()
        
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
        
        # Validate serial
        elif "validate" in message_lower and "serial" in message_lower:
            serial_match = re.search(r'serial\s+([\w\-]+)', message, re.IGNORECASE)
            if serial_match:
                return await self._validate_serial(serial_match.group(1))
        
        # API configuration
        elif "api setup" in message_lower or "configure api" in message_lower:
            return await self._handle_api_setup(message)
        
        # Default
        return {
            "success": True,
            "message": "API-Enabled Serial Tracking Agent v1.0",
            "response": "Commands: help, check health, enable serial tracking for item <code>, generate <n> serials for batch <batch>, validate serial <serial>, api setup <url> <key> <secret>"
        }
    
    async def _handle_help(self) -> Dict[str, Any]:
        """Provide help"""
        return {
            "success": True,
            "response": "API-Enabled Serial Tracking Agent",
            "commands": [
                "help - Show this help",
                "check health - Check system and API health",
                "enable serial tracking for item <ITEM_CODE> - Enable serial tracking",
                "generate <N> serials for batch <BATCH> - Generate serial numbers",
                "validate serial <SERIAL_NUMBER> - Validate serial compliance",
                "api setup <URL> <API_KEY> <API_SECRET> - Configure API connection"
            ],
            "capabilities": self.capabilities,
            "connection_mode": "Internal Frappe" if self.has_frappe_context else "External API" if self.api_config.get('base_url') else "Standalone",
            "api_configured": bool(self.api_config.get('base_url')),
            "serial_format": "GOLDENNUMBER-SEQUENCE (e.g., 0219074251-0001)"
        }
    
    async def _check_health(self) -> Dict[str, Any]:
        """Check system health"""
        health_info = {
            "agent_status": "running",
            "version": self.version,
            "connection_mode": "Internal Frappe" if self.has_frappe_context else "External API" if self.api_config.get('base_url') else "Standalone"
        }
        
        # Check API connection if configured
        if self.api_config.get('base_url'):
            api_status = await self._test_api_connection()
            health_info.update(api_status)
        
        # Check internal database if available
        if self.has_frappe_context:
            try:
                import frappe
                if hasattr(frappe, 'db') and frappe.db:
                    health_info["database_connection"] = "available"
                else:
                    health_info["database_connection"] = "not_available"
            except:
                health_info["database_connection"] = "error"
        
        return {
            "success": True,
            "health": health_info
        }
    
    async def _enable_serial_tracking(self, item_code: str) -> Dict[str, Any]:
        """Enable serial tracking via API or internal"""
        
        # If we have API config, use API
        if self.api_config.get('base_url'):
            return await self._enable_via_api(item_code)
        
        # If internal Frappe context
        elif self.has_frappe_context:
            try:
                import frappe
                if frappe.db.exists("Item", item_code):
                    return {
                        "success": True,
                        "message": f"Item {item_code} exists in ERPNext",
                        "steps": [
                            f"1. Go to: Item > {item_code}",
                            "2. Check 'Has Serial No' checkbox",
                            f"3. Set Serial No Series: {item_code}.####",
                            "4. Save the item"
                        ]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Item {item_code} not found",
                        "suggestion": "Create the item first in ERPNext"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Internal error: {str(e)}"
                }
        
        # Standalone mode
        else:
            return {
                "success": True,
                "message": f"To enable serial tracking for {item_code}:",
                "api_method": "POST /api/resource/Item/{item_code}",
                "api_payload": {
                    "has_serial_no": 1,
                    "serial_no_series": f"{item_code}.####"
                },
                "note": "Update item via ERPNext REST API"
            }
    
    async def _generate_serials(self, batch_name: str, quantity: int) -> Dict[str, Any]:
        """Generate serial numbers"""
        try:
            # Extract golden number
            match = re.search(r'(\d{10})', batch_name)
            if not match:
                return {
                    "success": False,
                    "error": f"Invalid batch format: {batch_name}",
                    "expected_format": "0219074251-1"
                }
            
            golden_number = match.group(1)
            
            # Validate golden number
            if len(golden_number) != 10 or not golden_number.isdigit():
                return {
                    "success": False,
                    "error": f"Invalid golden number: {golden_number}",
                    "requirement": "Must be 10 digits"
                }
            
            # Generate serials
            serials = []
            for i in range(min(quantity, 100)):
                serial = f"{golden_number}-{str(i+1).zfill(4)}"
                serials.append(serial)
            
            result = {
                "success": True,
                "message": f"✅ Generated {len(serials)} serials for {batch_name}",
                "serials": serials[:20],
                "format": f"{golden_number}-XXXX",
                "total_generated": len(serials)
            }
            
            # If API is configured, also show how to create via API
            if self.api_config.get('base_url'):
                result["api_creation"] = {
                    "method": "POST /api/resource/Serial No",
                    "note": "Create each serial via API with batch_no and item_code"
                }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Generation failed: {str(e)}"
            }
    
    async def _validate_serial(self, serial_number: str) -> Dict[str, Any]:
        """Validate serial number"""
        # Check format
        is_valid = bool(re.match(r'^\d{10}-\d{4}$', serial_number))
        
        if is_valid:
            golden_number = serial_number[:10]
            
            # Try to validate via API if configured
            api_validation = None
            if self.api_config.get('base_url'):
                api_validation = await self._validate_via_api(serial_number)
            
            result = {
                "success": True,
                "validation": {
                    "serial_number": serial_number,
                    "format_valid": True,
                    "golden_number": golden_number,
                    "sequence": serial_number[11:],
                    "golden_valid": len(golden_number) == 10,
                    "compliant": True,
                    "message": "✅ Valid format"
                }
            }
            
            if api_validation:
                result["api_validation"] = api_validation
            
            return result
        else:
            return {
                "success": True,
                "validation": {
                    "serial_number": serial_number,
                    "format_valid": False,
                    "compliant": False,
                    "message": "⚠️ Invalid format"
                },
                "expected_format": "0219074251-0001"
            }
    
    async def _handle_api_setup(self, message: str) -> Dict[str, Any]:
        """Handle API configuration"""
        # Parse API config from message
        parts = message.split()
        if len(parts) >= 4:
            # Format: api setup <url> <key> <secret>
            url = parts[2]
            api_key = parts[3]
            api_secret = parts[4] if len(parts) > 4 else ""
            
            self.api_config.update({
                "base_url": url,
                "api_key": api_key,
                "api_secret": api_secret
            })
            
            # Test connection
            api_status = await self._test_api_connection()
            
            return {
                "success": True,
                "message": "✅ API configuration updated",
                "api_config": {
                    "base_url": url,
                    "status": api_status.get("api_status", "unknown")
                }
            }
        else:
            return {
                "success": False,
                "error": "Invalid API setup format",
                "format": "api setup <url> <api_key> <api_secret>",
                "example": "api setup https://your-site.frappe.cloud key_123 secret_456"
            }
    
    async def _test_api_connection(self) -> Dict[str, Any]:
        """Test API connection"""
        try:
            headers = {
                "Authorization": f"token {self.api_config['api_key']}:{self.api_config['api_secret']}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Test with a simple ping
                url = urljoin(self.api_config['base_url'], "/api/method/ping")
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return {
                            "api_status": "connected",
                            "api_url": self.api_config['base_url'],
                            "message": "✅ API connection successful"
                        }
                    else:
                        return {
                            "api_status": "failed",
                            "status_code": response.status,
                            "message": f"❌ API connection failed: {response.status}"
                        }
        except Exception as e:
            return {
                "api_status": "error",
                "error": str(e),
                "message": "❌ API connection error"
            }
    
    async def _enable_via_api(self, item_code: str) -> Dict[str, Any]:
        """Enable serial tracking via API"""
        try:
            headers = {
                "Authorization": f"token {self.api_config['api_key']}:{self.api_config['api_secret']}",
                "Content-Type": "application/json"
            }
            
            # First get the item
            url = urljoin(self.api_config['base_url'], f"/api/resource/Item/{item_code}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        item_data = await response.json()
                        
                        # Update with serial tracking
                        update_data = {
                            "has_serial_no": 1,
                            "serial_no_series": f"{item_code}.####"
                        }
                        
                        update_url = urljoin(self.api_config['base_url'], f"/api/resource/Item/{item_code}")
                        async with session.put(update_url, headers=headers, json={"data": update_data}) as update_response:
                            if update_response.status in [200, 202]:
                                return {
                                    "success": True,
                                    "message": f"✅ Enabled serial tracking for {item_code} via API",
                                    "api_response": "Item updated successfully"
                                }
                            else:
                                return {
                                    "success": False,
                                    "error": f"API update failed: {update_response.status}",
                                    "item_exists": True
                                }
                    else:
                        return {
                            "success": False,
                            "error": f"Item {item_code} not found via API",
                            "status_code": response.status
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"API operation failed: {str(e)}"
            }
    
    async def _validate_via_api(self, serial_number: str) -> Dict[str, Any]:
        """Validate serial via API"""
        try:
            headers = {
                "Authorization": f"token {self.api_config['api_key']}:{self.api_config['api_secret']}",
                "Content-Type": "application/json"
            }
            
            url = urljoin(self.api_config['base_url'], f"/api/resource/Serial No/{serial_number}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        serial_data = await response.json()
                        return {
                            "exists_in_erpnext": True,
                            "status": "found",
                            "data_available": True,
                            "message": "✅ Serial exists in ERPNext"
                        }
                    elif response.status == 404:
                        return {
                            "exists_in_erpnext": False,
                            "status": "not_found",
                            "message": "Serial not found in ERPNext"
                        }
                    else:
                        return {
                            "exists_in_erpnext": None,
                            "status": "api_error",
                            "status_code": response.status,
                            "message": f"API error: {response.status}"
                        }
                        
        except Exception as e:
            return {
                "exists_in_erpnext": None,
                "status": "connection_error",
                "error": str(e),
                "message": "API connection failed"
            }

# Create instance for Raven
serial_tracking_agent_api = SerialTrackingAgentAPI()
