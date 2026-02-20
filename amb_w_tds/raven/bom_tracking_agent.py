"""
BOM Tracking Agent for Raven AI
Phase 6 Implementation

Provides BOM health monitoring and inspection via Raven chat interface.

Commands:
- bom health - Run health check and show summary
- bom inspect <BOM-NAME> - Inspect specific BOM details
- bom status <ITEM-CODE> - Show BOM status for an item
- bom issues - Show known issues from tracking file
- help - Show available commands
"""

import frappe
import json
import os


class BOMTrackingAgent:
    """Raven agent for BOM health monitoring and inspection"""
    
    agent_name = "bom_tracking"
    agent_description = "BOM health monitoring and inspection agent"
    agent_version = "1.0.0"
    
    def __init__(self):
        self.name = self.agent_name
        self.description = self.agent_description
        self.version = self.agent_version
    
    def handle_message(self, message, channel=None, **kwargs):
        """Handle incoming Raven messages"""
        message_lower = str(message).lower().strip()
        
        # Help command
        if message_lower in ["help", "bom help", "bom"]:
            return self._help()
        
        # Health check
        elif message_lower in ["bom health", "health", "check health", "bom check"]:
            return self._health_check()
        
        # Inspect specific BOM
        elif message_lower.startswith("bom inspect "):
            bom_name = message.strip().split(" ", 2)[-1].upper()
            return self._inspect_bom(bom_name)
        
        # Status for item code
        elif message_lower.startswith("bom status "):
            item_code = message.strip().split(" ", 2)[-1]
            return self._item_status(item_code)
        
        # Known issues
        elif message_lower in ["bom issues", "issues", "known issues"]:
            return self._known_issues()
        
        # Ping/test
        elif message_lower in ["ping", "test"]:
            return {
                "content": "✅ BOM Tracking Agent is active!",
                "type": "text"
            }
        
        # Default
        else:
            return {
                "content": f"🤖 BOM Tracking Agent received: '{message}'\n\nType `help` for available commands.",
                "type": "text"
            }
    
    def _help(self):
        """Show help message"""
        return {
            "content": """🤖 **BOM Tracking Agent** v1.0.0

**Commands:**
- `bom health` - Run health check and show summary
- `bom inspect <BOM-NAME>` - Inspect specific BOM (e.g., `bom inspect BOM-0307-001`)
- `bom status <ITEM-CODE>` - Show BOM status for item (e.g., `bom status 0307`)
- `bom issues` - Show known/tracked issues
- `ping` - Check if agent is alive
- `help` - Show this help

**Examples:**
```
bom health
bom inspect BOM-0307-001
bom status 0307
bom issues
```""",
            "type": "text"
        }
    
    def _health_check(self):
        """Run BOM health check and return summary"""
        try:
            from amb_w_tds.scripts.bom_status_manager import run_health_check
            
            # Run health check (returns dict)
            result = run_health_check(verbose=False, post_to_raven=False)
            
            if isinstance(result, str):
                result = json.loads(result)
            
            health_status = result.get("health_status", "UNKNOWN")
            total_issues = result.get("total_issues", 0)
            issues = result.get("issues", [])
            
            # Build response
            if health_status == "HEALTHY":
                emoji = "✅"
                status_text = "All checks passed!"
            elif health_status == "MINOR_ISSUES":
                emoji = "⚠️"
                status_text = f"{total_issues} minor issue(s) detected"
            else:
                emoji = "❌"
                status_text = f"{total_issues} issue(s) require attention"
            
            content = f"""{emoji} **BOM Health Status: {health_status}**

{status_text}

**Summary:**
- Total Issues: {total_issues}
- Timestamp: {result.get('timestamp', 'N/A')}
"""
            
            # Add issue breakdown if any
            if issues:
                content += "\n**Issues Found:**\n"
                for issue in issues[:5]:  # Show first 5
                    content += f"- {issue.get('bom', 'N/A')}: {issue.get('type', 'N/A')} ({issue.get('severity', 'N/A')})\n"
                if len(issues) > 5:
                    content += f"- ... and {len(issues) - 5} more\n"
            
            return {
                "content": content,
                "type": "text",
                "metadata": result
            }
            
        except Exception as e:
            return {
                "content": f"❌ Error running health check: {str(e)}",
                "type": "text"
            }
    
    def _inspect_bom(self, bom_name):
        """Inspect a specific BOM"""
        try:
            # Normalize BOM name
            if not bom_name.startswith("BOM-"):
                bom_name = f"BOM-{bom_name}"
            if bom_name.count("-") == 1:
                bom_name = f"{bom_name}-001"
            
            if not frappe.db.exists("BOM", bom_name):
                return {
                    "content": f"❌ BOM `{bom_name}` not found.",
                    "type": "text"
                }
            
            bom = frappe.get_doc("BOM", bom_name)
            items = frappe.get_all(
                "BOM Item",
                filters={"parent": bom_name},
                fields=["item_code", "qty", "uom", "bom_no"]
            )
            
            # Status text
            if bom.docstatus == 0:
                status = "📝 Draft"
            elif bom.docstatus == 2:
                status = "🗑️ Cancelled"
            elif bom.is_active and bom.is_default:
                status = "✅ Active (Default)"
            elif bom.is_active:
                status = "✅ Active"
            else:
                status = "⚠️ Inactive"
            
            content = f"""📋 **BOM Inspection: {bom_name}**

**Basic Info:**
- Item: `{bom.item}`
- Status: {status}
- Quantity: {bom.quantity} {bom.uom}
- Total Cost: ${bom.total_cost:,.2f}

**Components ({len(items)}):**
"""
            for item in items[:10]:
                sub_bom = f" → {item.bom_no}" if item.bom_no else ""
                content += f"- `{item.item_code}` × {item.qty} {item.uom}{sub_bom}\n"
            
            if len(items) > 10:
                content += f"- ... and {len(items) - 10} more components\n"
            
            return {
                "content": content,
                "type": "text",
                "metadata": {
                    "bom_name": bom_name,
                    "item": bom.item,
                    "is_active": bom.is_active,
                    "is_default": bom.is_default,
                    "total_cost": bom.total_cost,
                    "components": len(items)
                }
            }
            
        except Exception as e:
            return {
                "content": f"❌ Error inspecting BOM: {str(e)}",
                "type": "text"
            }
    
    def _item_status(self, item_code):
        """Show BOM status for an item code"""
        try:
            # Find all BOMs for this item
            boms = frappe.get_all(
                "BOM",
                filters={"item": ["like", f"%{item_code}%"]},
                fields=["name", "item", "is_active", "is_default", "docstatus", "total_cost"],
                order_by="is_default desc, is_active desc"
            )
            
            if not boms:
                return {
                    "content": f"❌ No BOMs found for item containing `{item_code}`",
                    "type": "text"
                }
            
            content = f"""📊 **BOM Status for `{item_code}`**

Found {len(boms)} BOM(s):

"""
            for bom in boms[:10]:
                if bom.docstatus == 2:
                    status = "🗑️"
                elif bom.is_default:
                    status = "⭐"
                elif bom.is_active:
                    status = "✅"
                else:
                    status = "⚠️"
                
                content += f"{status} `{bom.name}` - ${bom.total_cost:,.2f}\n"
            
            if len(boms) > 10:
                content += f"\n... and {len(boms) - 10} more\n"
            
            return {
                "content": content,
                "type": "text",
                "metadata": {"item_code": item_code, "bom_count": len(boms)}
            }
            
        except Exception as e:
            return {
                "content": f"❌ Error checking item status: {str(e)}",
                "type": "text"
            }
    
    def _known_issues(self):
        """Show known issues from tracking file"""
        try:
            # Find the known issues file
            issues_file = os.path.join(
                os.path.dirname(__file__), 
                "..", "scripts", "bom_known_issues.json"
            )
            
            if not os.path.exists(issues_file):
                return {
                    "content": "ℹ️ No known issues file found. System is clean!",
                    "type": "text"
                }
            
            with open(issues_file, "r") as f:
                data = json.load(f)
            
            issues = data.get("issues", [])
            last_updated = data.get("last_updated", "N/A")
            
            if not issues:
                return {
                    "content": "✅ No known issues tracked. System is healthy!",
                    "type": "text"
                }
            
            content = f"""📋 **Known BOM Issues**

Last Updated: {last_updated}
Total Tracked: {len(issues)}

**Issues:**
"""
            for issue in issues:
                bom = issue.get("bom", issue.get("item", "N/A"))
                issue_type = issue.get("issue_type", "UNKNOWN")
                reason = issue.get("reason", "No reason specified")
                content += f"- `{bom}` ({issue_type}): {reason}\n"
            
            return {
                "content": content,
                "type": "text",
                "metadata": data
            }
            
        except Exception as e:
            return {
                "content": f"❌ Error reading known issues: {str(e)}",
                "type": "text"
            }


# Raven registration
def get_agents():
    """Register this agent with Raven"""
    return {
        "bom_tracking": {
            "class": BOMTrackingAgent,
            "name": BOMTrackingAgent.agent_name,
            "description": BOMTrackingAgent.agent_description,
            "version": BOMTrackingAgent.agent_version
        }
    }
