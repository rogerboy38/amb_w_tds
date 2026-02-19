"""
Raven agent configuration for amb_w_tds
Version 9.2.0 - Includes Serial Tracking, BOM Tracking, and BOM Creator agents
"""

def get_agents():
    """Register all agents with Raven"""
    agents = {}
    
    # Serial Tracking Agent (existing working agent)
    try:
        from amb_w_tds.raven.serial_minimal_working import MinimalSerialAgent
        
        agents["serial_tracking"] = {
            "class": MinimalSerialAgent,
            "name": MinimalSerialAgent.agent_name,
            "description": MinimalSerialAgent.agent_description,
            "version": MinimalSerialAgent.agent_version
        }
        print("✅ Registered MinimalSerialAgent as 'serial_tracking'")
        
    except ImportError as e:
        print(f"⚠️ Could not import MinimalSerialAgent: {e}")
    
    # BOM Tracking Agent (v9.1.0 - health checks)
    try:
        from amb_w_tds.raven.bom_tracking_agent import BOMTrackingAgent
        
        agents["bom_tracking"] = {
            "class": BOMTrackingAgent,
            "name": BOMTrackingAgent.agent_name,
            "description": BOMTrackingAgent.agent_description,
            "version": BOMTrackingAgent.agent_version
        }
        print("✅ Registered BOMTrackingAgent as 'bom_tracking'")
        
    except ImportError as e:
        print(f"⚠️ Could not import BOMTrackingAgent: {e}")
    
    # BOM Creator Agent (v9.2.0-phase7 - create BOMs via chat)
    try:
        from amb_w_tds.raven.bom_creator_agent import get_agent_info, handle_raven_message, get_triggers
        
        agents["bom_creator"] = {
            "handler": handle_raven_message,
            "info": get_agent_info(),
            "triggers": get_triggers(),
            "name": "BOM Creator Agent",
            "description": "Create multi-level BOMs from natural language specifications",
            "version": "9.2.0-phase7"
        }
        print("✅ Registered BOMCreatorAgent as 'bom_creator'")
        
    except ImportError as e:
        print(f"⚠️ Could not import BOMCreatorAgent: {e}")
    
    return agents
