"""
Raven agent configuration for amb_w_tds
Version 9.1.0 - Includes Serial Tracking and BOM Tracking agents
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
    
    # BOM Tracking Agent (v9.1.0 - new)
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
    
    return agents
