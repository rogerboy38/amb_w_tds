"""
Raven AI Agents for amb_w_tds
Version 9.1.0

Available agents:
- serial_tracking: Serial number generation and validation
- bom_tracking: BOM health monitoring and inspection
"""

from amb_w_tds.raven.config import get_agents

__version__ = "1.0.0"
__all__ = ["get_agents"]
