"""
Test functions for serial tracking agent
"""

import frappe
import asyncio

def test_agent_help():
    """Test agent help command"""
    from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent
    
    async def test():
        agent = SerialTrackingAgent()
        result = await agent.process("help")
        return result
    
    result = asyncio.run(test())
    print(f"✅ Agent help test:")
    print(f"Success: {result.get('success')}")
    print(f"Response: {result.get('response')}")
    return result

def test_agent_generate():
    """Test agent generate command"""
    from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent
    
    async def test():
        agent = SerialTrackingAgent()
        result = await agent.process("generate 3 serials for batch 0219074251-10")
        return result
    
    result = asyncio.run(test())
    print(f"✅ Agent generate test:")
    print(f"Success: {result.get('success')}")
    print(f"Message: {result.get('message')}")
    if result.get('serials'):
        print(f"Serials: {result.get('serials')}")
    return result
