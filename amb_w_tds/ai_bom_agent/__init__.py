# AI BOM Agent - v9.2.0
# Hierarchical BOM Creation System for AMB W TDS

"""
BOM Creator Agent v9.2.0

AI-powered multi-level BOM creation system for ERPNext.

Modules:
- data_contracts: Dataclasses for structured data
- parser: Product specification parser
- templates: Master template database
- erpnext_client: ERPNext Item/BOM operations
- validators: Business rule validation
- engine: Core orchestration engine
- api: Frappe API endpoints
"""

__version__ = "9.2.0"

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Available product families
SUPPORTED_FAMILIES = ["0227", "0307"]

# Legacy helper functions (use MasterTemplateDB for new code)
def get_template(family: str) -> dict:
    """Load master template for a product family"""
    import json
    template_file = TEMPLATES_DIR / f"template_{family}_master.json"
    if template_file.exists():
        with open(template_file) as f:
            return json.load(f)
    return None

def get_schema() -> dict:
    """Load template schema"""
    import json
    schema_file = TEMPLATES_DIR / "template_schema.json"
    with open(schema_file) as f:
        return json.load(f)

def get_business_rules() -> dict:
    """Load business validation rules"""
    import json
    rules_file = TEMPLATES_DIR / "business_rules.json"
    with open(rules_file) as f:
        return json.load(f)

def get_yield_rules() -> dict:
    """Load yield and loss rules"""
    import json
    yield_file = TEMPLATES_DIR / "yield_loss_rules.json"
    with open(yield_file) as f:
        return json.load(f)

def get_uom_conversions() -> dict:
    """Load UOM conversion rules"""
    import json
    uom_file = TEMPLATES_DIR / "uom_conversions.json"
    with open(uom_file) as f:
        return json.load(f)

def get_operations_mapping() -> dict:
    """Load operations and workstation mappings"""
    import json
    ops_file = TEMPLATES_DIR / "operations_mapping.json"
    with open(ops_file) as f:
        return json.load(f)

# Import core classes for external access
from .data_contracts import ParsedSpec, PlannedItem, PlannedBOM, GenerationReport
from .parser import ProductSpecificationParser
from .templates import MasterTemplateDB
from .erpnext_client import ItemAndBOMService
from .validators import ValidationRulesEngine, ValidationError
from .engine import AgentCoreEngine, create_engine

__all__ = [
    "ParsedSpec",
    "PlannedItem",
    "PlannedBOM",
    "GenerationReport",
    "ProductSpecificationParser",
    "MasterTemplateDB",
    "ItemAndBOMService",
    "ValidationRulesEngine",
    "ValidationError",
    "AgentCoreEngine",
    "create_engine",
    "TEMPLATES_DIR",
    "SUPPORTED_FAMILIES",
    "get_template",
    "get_schema",
    "get_business_rules",
    "get_yield_rules",
    "get_uom_conversions",
    "get_operations_mapping",
]
