"""
BOM Creator Agent for Raven AI Integration - Phase 7
Allows users to create BOMs via Raven chat interface.

Commands:
- bom create <spec>: Create a new BOM from specification
- bom plan <spec>: Plan a BOM (dry run) without creating
- bom help: Show available commands

Examples:
- @ai bom create 0227 EU organic 30:1 in 1000L IBC
- @ai bom plan HIGHPOL 20/25 100 mesh for customer XYZ
"""

import json
import frappe
from frappe import _
from typing import Dict, Any, Optional


def get_erpnext_url() -> str:
    """Get the ERPNext base URL for generating links."""
    return frappe.utils.get_url()


def format_erpnext_link(doctype: str, name: str) -> str:
    """Generate ERPNext document link."""
    base_url = get_erpnext_url()
    return f"{base_url}/app/{doctype.lower().replace(' ', '-')}/{name}"


def process_bom_command(message: str, channel: str = None, user: str = None) -> Dict[str, Any]:
    """
    Process BOM-related commands from Raven chat.
    
    Args:
        message: The chat message text
        channel: Raven channel (optional)
        user: User who sent the message (optional)
        
    Returns:
        Dict with response message and metadata
    """
    message_lower = message.lower().strip()
    
    # Parse command
    if message_lower.startswith("bom help") or message_lower == "bom":
        return _handle_help()
    
    if message_lower.startswith("bom create "):
        spec_text = message[len("bom create "):].strip()
        return _handle_create(spec_text, dry_run=False, user=user)
    
    if message_lower.startswith("bom plan "):
        spec_text = message[len("bom plan "):].strip()
        return _handle_create(spec_text, dry_run=True, user=user)
    
    # Check for natural language patterns
    if any(kw in message_lower for kw in ["create bom", "make bom", "new bom"]):
        # Extract spec from natural language
        spec_text = message
        for prefix in ["create bom for ", "make bom for ", "new bom for ", "create bom ", "make bom ", "new bom "]:
            if message_lower.startswith(prefix):
                spec_text = message[len(prefix):].strip()
                break
        
        dry_run = "(dry run)" in message_lower or "(plan)" in message_lower
        return _handle_create(spec_text, dry_run=dry_run, user=user)
    
    return {
        "success": False,
        "message": "Unknown BOM command. Use `bom help` to see available commands.",
        "command_type": "unknown"
    }


def _handle_help() -> Dict[str, Any]:
    """Return help message for BOM commands."""
    help_text = """## BOM Creator Agent Commands

### Create BOM
```
bom create <specification>
```
Creates a new multi-level BOM from the specification.

### Plan BOM (Dry Run)
```
bom plan <specification>
```
Shows what would be created without actually creating.

### Examples
- `bom create 0227 EU organic 30:1 in 1000L IBC`
- `bom plan HIGHPOL 20/25 100 mesh fair trade 25kg bags`
- `bom create 0307 200:1 powder for customer XYZ`
- `bom plan 0227 10X conventional in drums`

### Supported Product Families
- **0227**: Aloe Vera Gel Concentrate (liquid)
- **0307**: Aloe Vera Spray Dried Powder
- **HIGHPOL**: Highpol Powder (polysaccharide variants)
- **ACETYPOL**: Acetypol Powder (acemannan variants)

### Certifications
ORG-EU, ORG-NOP, ORG-KR, KOS-ORG, FT (Fair Trade), CONV, HALAL, COSMOS

### Mesh Sizes (Powder Only)
60, 80, 100, 120, 200 mesh
"""
    
    return {
        "success": True,
        "message": help_text,
        "command_type": "help"
    }


def _handle_create(spec_text: str, dry_run: bool = False, user: str = None) -> Dict[str, Any]:
    """
    Handle BOM creation or planning command.
    
    Args:
        spec_text: Product specification text
        dry_run: If True, plan only without creating
        user: User who initiated the command
        
    Returns:
        Dict with response message and metadata
    """
    try:
        # Import the API function
        from amb_w_tds.ai_bom_agent.api import create_multi_level_bom_from_spec
        
        # Call the BOM creator API
        result = create_multi_level_bom_from_spec(
            request_text=spec_text,
            dry_run=dry_run
        )
        
        # Format response
        return _format_result(result, spec_text, dry_run)
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Error processing BOM request:\n```\n{str(e)}\n```",
            "command_type": "create" if not dry_run else "plan",
            "error": str(e)
        }


def _format_result(result: Dict[str, Any], spec_text: str, dry_run: bool) -> Dict[str, Any]:
    """
    Format the BOM creation result for Raven chat display.
    
    Args:
        result: Result dict from create_multi_level_bom_from_spec
        spec_text: Original specification text
        dry_run: Whether this was a dry run
        
    Returns:
        Formatted response dict
    """
    success = result.get("success", False)
    spec = result.get("spec", {})
    mode = "📋 Plan (Dry Run)" if dry_run else "✅ Created"
    
    # Build header
    status_icon = "✅" if success else "❌"
    header = f"{status_icon} **BOM {mode}**"
    
    if not success:
        errors = result.get("errors", [])
        error_text = "\n".join([f"- {e}" for e in errors[:5]])
        return {
            "success": False,
            "message": f"{header}\n\n**Errors:**\n{error_text}",
            "command_type": "create" if not dry_run else "plan",
            "result": result
        }
    
    # Build summary section
    lines = [header, ""]
    
    # Specification summary
    lines.append("### Specification")
    lines.append(f"- **Family:** {spec.get('family', 'N/A')}")
    lines.append(f"- **Certification:** {spec.get('attribute', 'N/A')}")
    
    if spec.get("variant"):
        lines.append(f"- **Variant:** {spec.get('variant')}")
    
    if spec.get("mesh_size"):
        lines.append(f"- **Mesh Size:** {spec.get('mesh_size')}")
    
    lines.append(f"- **Packaging:** {spec.get('packaging', 'N/A')}")
    
    if spec.get("customer"):
        lines.append(f"- **Customer:** {spec.get('customer')}")
    
    # Items section
    items_created = result.get("items_created", [])
    items_reused = result.get("items_reused", [])
    
    if items_created or items_reused:
        lines.append("")
        lines.append("### Items")
        
        if items_created:
            lines.append(f"**{'Would Create' if dry_run else 'Created'}:** {len(items_created)}")
            for item in items_created[:5]:
                link = format_erpnext_link("Item", item)
                lines.append(f"- [{item}]({link})")
            if len(items_created) > 5:
                lines.append(f"- ... and {len(items_created) - 5} more")
        
        if items_reused:
            lines.append(f"**Reused:** {len(items_reused)}")
    
    # BOMs section
    boms_created = result.get("boms_created", [])
    boms_reused = result.get("boms_reused", [])
    
    if boms_created or boms_reused:
        lines.append("")
        lines.append("### BOMs")
        
        if boms_created:
            lines.append(f"**{'Would Create' if dry_run else 'Created'}:** {len(boms_created)}")
            for bom in boms_created[:5]:
                link = format_erpnext_link("BOM", bom)
                lines.append(f"- [{bom}]({link})")
            if len(boms_created) > 5:
                lines.append(f"- ... and {len(boms_created) - 5} more")
        
        if boms_reused:
            lines.append(f"**Reused:** {len(boms_reused)}")
    
    # Batch tracking info (Phase 7)
    batch_tracking = result.get("batch_tracking", {})
    if batch_tracking.get("enabled"):
        lines.append("")
        lines.append("### Batch Tracking")
        lines.append("✅ Items created with batch tracking enabled")
        if batch_tracking.get("template"):
            lines.append(f"- Suggested batch template: `{batch_tracking.get('template')}`")
    
    # Warnings
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("### Warnings")
        for w in warnings[:3]:
            if isinstance(w, dict):
                lines.append(f"- {w.get('message', str(w))}")
            else:
                lines.append(f"- {w}")
    
    # Footer
    lines.append("")
    exec_time = result.get("execution_time_seconds", 0)
    lines.append(f"_Execution time: {exec_time:.2f}s_")
    
    return {
        "success": True,
        "message": "\n".join(lines),
        "command_type": "create" if not dry_run else "plan",
        "result": result
    }


# ==================== Raven Integration Functions ====================

def handle_raven_message(message: str, channel: str = None, user: str = None) -> str:
    """
    Main entry point for Raven AI integration.
    Called by Raven when a BOM-related message is detected.
    
    Args:
        message: The chat message text
        channel: Raven channel name
        user: User who sent the message
        
    Returns:
        Formatted response string for Raven
    """
    result = process_bom_command(message, channel, user)
    return result.get("message", "Error processing request")


def get_triggers() -> list:
    """
    Return list of trigger keywords for this agent.
    Raven uses these to detect when to invoke this agent.
    """
    return [
        "bom create",
        "bom plan", 
        "bom help",
        "create bom",
        "make bom",
        "new bom",
        "0227",
        "0307",
        "HIGHPOL",
        "ACETYPOL"
    ]


def get_agent_info() -> Dict[str, Any]:
    """Return agent metadata for Raven registration."""
    return {
        "name": "BOM Creator Agent",
        "description": "Create multi-level BOMs from natural language specifications",
        "version": "9.2.0-phase7",
        "triggers": get_triggers(),
        "commands": ["bom create", "bom plan", "bom help"],
        "author": "AMB Wellness"
    }


# ==================== API Endpoint ====================

@frappe.whitelist()
def bom_skill_api(request_text: str, dry_run: bool = True, customer: str = None) -> Dict[str, Any]:
    """
    Raven skill API endpoint for BOM creation.
    
    Args:
        request_text: Product specification text
        dry_run: If True, plan only (default)
        customer: Optional customer code
        
    Returns:
        Result dict with formatted message
    """
    # Append customer to request if provided
    if customer and "customer" not in request_text.lower():
        request_text = f"{request_text} for customer {customer}"
    
    return process_bom_command(f"bom {'plan' if dry_run else 'create'} {request_text}")
