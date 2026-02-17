"""
Serial Tracking Agent for Raven AI
Synchronous agent compatible with Raven message handler

Commands:
- ping/test - Check if agent is alive
- help - Show available commands
- gen <n> <batch> - Generate n serials for batch
- validate <serial> - Validate serial format
"""

import re


class SerialTrackingAgent:
    """Raven agent for serial number management"""
    
    agent_name = "serial_tracking"
    agent_description = "Serial number generation and validation"
    agent_version = "1.0.0"
    
    def __init__(self):
        self.name = self.agent_name
        self.description = self.agent_description
        self.version = self.agent_version
    
    def handle_message(self, message, channel=None, **kwargs):
        """Handle incoming Raven messages"""
        message_lower = str(message).lower().strip()
        
        if message_lower in ["ping", "test"]:
            return {
                "content": "✅ Pong! Serial Tracking Agent is working.",
                "type": "text"
            }
        
        elif message_lower == "help":
            return {
                "content": """🤖 **Serial Tracking Agent** v1.0.0

**Commands:**
- `ping` or `test` - Check if agent is alive
- `help` - Show this help
- `gen <n> <batch>` - Generate n serials for batch
- `validate <serial>` - Validate serial format

**Examples:**
```
gen 5 0219074251-88
validate 0219074251-0001
```""",
                "type": "text"
            }
        
        elif message_lower.startswith("gen "):
            return self._handle_generate(message_lower)
        
        elif message_lower.startswith("validate "):
            return self._handle_validate(message_lower)
        
        else:
            return {
                "content": f"🤖 Serial Tracking Agent received: '{message}'\n\nType `help` for commands.",
                "type": "text"
            }
    
    def _handle_generate(self, message):
        """Handle generate command"""
        try:
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
                for i in range(1, min(count + 1, 21)):  # Limit to 20
                    serials.append(f"{golden}-{i:04d}")
                
                serials_text = "\n".join([f"• {s}" for s in serials])
                
                return {
                    "content": f"""✅ **Generated {len(serials)} serials for {batch}**

**Serials:**
{serials_text}

**Format:** {golden}-XXXX (4-digit sequence)""",
                    "type": "text",
                    "metadata": {
                        "serials": serials,
                        "count": len(serials),
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
                    golden, seq = serial.split('-', 1)
                    
                    if golden.isdigit() and seq.isdigit() and len(seq) == 4:
                        return {
                            "content": f"""✅ **Serial Valid**

**Serial:** {serial}
**Golden:** {golden}
**Sequence:** {seq}
**Status:** Valid format""",
                            "type": "text",
                            "metadata": {"valid": True, "serial": serial}
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
**Issues:** {', '.join(issues)}""",
                            "type": "text",
                            "metadata": {"valid": False, "serial": serial}
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
    return {
        "serial_tracking": {
            "class": SerialTrackingAgent,
            "name": SerialTrackingAgent.agent_name,
            "description": SerialTrackingAgent.agent_description,
            "version": SerialTrackingAgent.agent_version
        }
    }
