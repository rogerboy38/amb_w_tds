"""
Raven agent configuration for amb_w_tds
Updated to use working minimal agent
"""

def get_agents():
    """Register agents with Raven"""
    agents = {}
    
    # Try to import the working minimal agent
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
        print(f"❌ Could not import MinimalSerialAgent: {e}")
        # Return empty dict - no agents registered
    
    return agents
