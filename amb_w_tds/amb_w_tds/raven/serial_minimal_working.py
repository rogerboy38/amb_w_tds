"""
Minimal working Raven agent for serial tracking
"""

import frappe
import re

class MinimalSerialAgent:
    """Minimal working agent that doesn't inherit from Document"""
    
    agent_name = "serial_tracking"
    agent_description = "Minimal serial tracking agent"
    agent_version = "1.0.0"
    
    def __init__(self):
        """Simple constructor without Document requirements"""
        self.name = self.agent_name
        self.description = self.agent_description
        self.version = self.agent_version
    
    def handle_message(self, message, channel=None, **kwargs):
        """Handle incoming messages"""
        message_lower = str(message).lower().strip()
        
        if message_lower == "ping" or message_lower == "test":
            return {
                "content": "✅ Pong! Agent is working.",
                "type": "text"
            }
        
        elif message_lower == "help":
            return {
                "content": """🤖 **Serial Tracking Agent** v1.0.0

Commands:
- `ping` or `test` - Check if agent is alive
- `help` - Show this help
- `gen <n> <batch>` - Generate n serials for batch
- `validate <serial>` - Validate serial format

Example: `gen 5 0219074251-88`""",
                "type": "text"
            }
        
        elif message_lower.startswith("gen "):
            return self._handle_generate(message_lower)
        
        elif message_lower.startswith("validate "):
            return self._handle_validate(message_lower)
        
        else:
            return {
                "content": f"🤖 I'm your Serial Tracking Agent. You said: '{message}'\n\nTry 'help' for commands.",
                "type": "text"
            }
    
    def _handle_generate(self, message):
        """Handle generate command"""
        try:
            # Parse: gen 5 0219074251-88
            parts = message.split()
            if len(parts) >= 3:
                count = int(parts[1])
                batch = parts[2]
                
                # Extract golden number
                if '-' in batch:
                    golden = batch.split('-')[0]
                else:
                    golden = batch
                
                # Generate serials
                serials = []
                for i in range(1, count + 1):
                    serials.append(f"{golden}-{i:04d}")
                
                serials_text = "\n".join([f"• {s}" for s in serials])
                
                return {
                    "content": f"""✅ **Generated {count} serials for {batch}**

**Serials:**
{serials_text}

**Format:** {golden}-XXXX (4-digit sequence)""",
                    "type": "text",
                    "metadata": {
                        "serials": serials,
                        "count": count,
                        "batch": batch
                    }
                }
            
            return {
                "content": "❌ Usage: `gen 5 0219074251-88`",
                "type": "text"
            }
            
        except Exception as e:
            return {
                "content": f"❌ Error: {str(e)}",
                "type": "text"
            }
    
    def _handle_validate(self, message):
        """Handle validate command"""
        try:
            parts = message.split()
            if len(parts) >= 2:
                serial = parts[1]
                
                if '-' in serial:
                    golden, seq = serial.split('-')
                    
                    if golden.isdigit() and seq.isdigit() and len(seq) == 4:
                        return {
                            "content": f"""✅ **Serial Valid**

**Serial:** {serial}
**Golden:** {golden}
**Sequence:** {seq}
**Status:** ✅ Valid format""",
                            "type": "text",
                            "metadata": {
                                "valid": True,
                                "serial": serial
                            }
                        }
                    else:
                        issues = []
                        if not golden.isdigit():
                            issues.append("Golden not all digits")
                        if not seq.isdigit():
                            issues.append("Sequence not all digits")
                        if len(seq) != 4:
                            issues.append(f"Sequence not 4 digits (got {len(seq)})")
                        
                        return {
                            "content": f"""❌ **Serial Invalid**

**Serial:** {serial}
**Issues:** {', '.join(issues)}
**Status:** ❌ Invalid format""",
                            "type": "text",
                            "metadata": {
                                "valid": False,
                                "serial": serial
                            }
                        }
                
                return {
                    "content": f"❌ Invalid format. Expected: GOLDEN-SSSS\nGot: {serial}",
                    "type": "text"
                }
            
            return {
                "content": "❌ Usage: `validate 0219074251-0100`",
                "type": "text"
            }
            
        except Exception as e:
            return {
                "content": f"❌ Error: {str(e)}",
                "type": "text"
            }

# Raven registration
def get_agents():
    """Register this agent with Raven"""
    from amb_w_tds.raven.serial_minimal_working import MinimalSerialAgent
    
    return {
        "serial_tracking": {
            "class": MinimalSerialAgent,
            "name": MinimalSerialAgent.agent_name,
            "description": MinimalSerialAgent.agent_description,
            "version": MinimalSerialAgent.agent_version
        }
    }
