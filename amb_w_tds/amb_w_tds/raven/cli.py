"""
CLI commands for Serial Tracking Agent
"""

import click
import asyncio
import sys

def run_async(coro):
    """Helper to run async functions"""
    return asyncio.run(coro)

@click.group()
def agent():
    """Serial Tracking Agent Commands"""
    pass

@agent.command()
@click.argument('message')
def ask(message):
    """Ask the serial tracking agent a question"""
    try:
        from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent
        
        async def process():
            agent = SerialTrackingAgent()
            return await agent.process(message)
        
        result = run_async(process())
        
        click.echo("🤖 Serial Tracking Agent Response:")
        click.echo("=" * 50)
        
        if result.get("success"):
            click.echo(f"✅ {result.get('message', 'Success')}")
            
            if "response" in result:
                click.echo(f"\n{result['response']}")
            
            if "serials" in result:
                click.echo(f"\nGenerated Serials:")
                for serial in result["serials"]:
                    click.echo(f"  {serial}")
            
            if "health" in result:
                health = result["health"]
                click.echo(f"\nHealth Status:")
                for key, value in health.items():
                    click.echo(f"  {key}: {value}")
        else:
            click.echo(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ Agent error: {str(e)}")

@agent.command()
def health():
    """Check agent health"""
    try:
        from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent
        
        async def check():
            agent = SerialTrackingAgent()
            return await agent.process("check health")
        
        result = run_async(check())
        
        click.echo("🏥 Agent Health Check:")
        click.echo("=" * 50)
        
        if result.get("success"):
            health = result.get("health", {})
            click.echo(f"✅ Status: {health.get('agent_status', 'unknown')}")
            click.echo(f"📊 Message: {health.get('message', 'No message')}")
            click.echo(f"🔧 Version: {health.get('version', 'unknown')}")
            
            if "capabilities" in health:
                click.echo(f"\n🛠️  Capabilities:")
                for capability in health["capabilities"]:
                    click.echo(f"  • {capability}")
        else:
            click.echo(f"❌ Health check failed: {result.get('error')}")
        
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ Health check error: {str(e)}")

@agent.command()
@click.argument('item_code')
def enable(item_code):
    """Enable serial tracking for an item"""
    try:
        from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent
        
        async def enable_tracking():
            agent = SerialTrackingAgent()
            return await agent.process(f"enable serial tracking for item {item_code}")
        
        result = run_async(enable_tracking())
        
        click.echo("⚙️ Enable Serial Tracking:")
        click.echo("=" * 50)
        
        if result.get("success"):
            click.echo(f"✅ {result.get('message')}")
            if "note" in result:
                click.echo(f"\n💡 {result['note']}")
        else:
            click.echo(f"❌ Failed: {result.get('error')}")
        
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ Enable error: {str(e)}")

@agent.command()
@click.argument('batch_name')
@click.option('--quantity', '-q', default=5, help='Number of serials to generate')
def generate(batch_name, quantity):
    """Generate serial numbers for a batch"""
    try:
        from amb_w_tds.raven.serial_tracking_agent import SerialTrackingAgent
        
        async def generate_serials():
            agent = SerialTrackingAgent()
            return await agent.process(f"generate {quantity} serials for batch {batch_name}")
        
        result = run_async(generate_serials())
        
        click.echo("🔢 Generate Serial Numbers:")
        click.echo("=" * 50)
        
        if result.get("success"):
            click.echo(f"✅ {result.get('message')}")
            
            if "serials" in result:
                click.echo(f"\n📋 Generated Serials ({len(result['serials'])}):")
                for serial in result["serials"]:
                    click.echo(f"  {serial}")
            
            if "format" in result:
                click.echo(f"\n📐 Format: {result['format']}")
            
            if "note" in result:
                click.echo(f"\n💡 {result['note']}")
        else:
            click.echo(f"❌ Failed: {result.get('error')}")
        
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ Generate error: {str(e)}")

if __name__ == "__main__":
    agent()
