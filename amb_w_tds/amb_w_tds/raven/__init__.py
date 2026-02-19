"""
Raven AI Agents for amb_w_tds
Version 9.2.0

Available agents:
- serial_tracking: Serial number generation and validation
- bom_tracking: BOM health monitoring and inspection
- bom_creator: Create multi-level BOMs from natural language (Phase 7)
"""

from amb_w_tds.raven.config import get_agents

__version__ = "9.2.0"
__all__ = ["get_agents"]
