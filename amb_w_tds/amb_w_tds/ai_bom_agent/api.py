"""
API Endpoints for BOM Creator Agent v9.2.0

Frappe whitelisted methods for external access.
"""

import frappe
from frappe import _
import json
from typing import Optional


@frappe.whitelist()
def create_multi_level_bom_from_spec(
    request_text: str,
    dry_run: bool = False
) -> dict:
    """
    Create a multi-level BOM hierarchy from a product specification.
    
    This is the main API entry point for the BOM Creator Agent.
    
    Args:
        request_text: Product specification (item code or natural language)
        dry_run: If True, plan but don't create in database
        
    Returns:
        GenerationReport as dict with:
        - success: bool
        - items_created: list of new item codes
        - items_reused: list of existing item codes
        - boms_created: list of new BOM item codes
        - boms_reused: list of existing BOM item codes
        - errors: list of error dicts
        - warnings: list of warning dicts
        - dry_run: bool
        - execution_time_seconds: float
    
    Example:
        # Via bench execute
        bench --site mysite execute amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec \\
            --kwargs '{"request_text": "0227-ORGANIC-NATURAL-1000L-IBC", "dry_run": True}'
        
        # Via frappe.call
        frappe.call(
            "amb_w_tds.ai_bom_agent.api.create_multi_level_bom_from_spec",
            request_text="0227-ORGANIC-NATURAL-1000L-IBC",
            dry_run=True
        )
    """
    from .parser import ProductSpecificationParser
    from .engine import AgentCoreEngine
    
    # Handle string boolean from CLI
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in ("true", "1", "yes")
    
    # Parse specification
    parser = ProductSpecificationParser()
    
    try:
        spec = parser.parse(request_text)
    except ValueError as e:
        return {
            "success": False,
            "errors": [{
                "rule_id": "PARSE",
                "rule_name": "Parse Error",
                "message": str(e),
                "severity": "ERROR",
                "context": {"request_text": request_text}
            }],
            "warnings": [],
            "items_created": [],
            "items_reused": [],
            "boms_created": [],
            "boms_reused": [],
            "dry_run": dry_run,
            "execution_time_seconds": 0
        }
    
    # Run engine
    engine = AgentCoreEngine()
    report = engine.generate(spec, dry_run=dry_run)
    
    return report.to_dict()


@frappe.whitelist()
def parse_product_spec(request_text: str) -> dict:
    """
    Parse a product specification without creating anything.
    
    Args:
        request_text: Product specification to parse
        
    Returns:
        ParsedSpec as dict or error
    """
    from .parser import ProductSpecificationParser
    
    parser = ProductSpecificationParser()
    
    try:
        spec = parser.parse(request_text)
        return {
            "success": True,
            "spec": spec.to_dict()
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def list_available_families() -> dict:
    """
    List all product families with available templates.
    
    Returns:
        Dict with families list
    """
    from .templates import MasterTemplateDB
    
    templates = MasterTemplateDB()
    families = templates.list_families()
    
    return {
        "success": True,
        "families": families
    }


@frappe.whitelist()
def get_template(family: str) -> dict:
    """
    Get the master template for a product family.
    
    Args:
        family: Product family code
        
    Returns:
        Template dict or error
    """
    from .templates import MasterTemplateDB
    
    templates = MasterTemplateDB()
    
    try:
        template = templates.get_template(family)
        return {
            "success": True,
            "template": template
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def validate_item_code(item_code: str) -> dict:
    """
    Validate an item code format.
    
    Args:
        item_code: Item code to validate
        
    Returns:
        Validation result
    """
    from .parser import ProductSpecificationParser
    
    parser = ProductSpecificationParser()
    
    try:
        spec = parser.parse_item_code(item_code)
        validation = parser.validate_spec(spec)
        
        return {
            "success": True,
            "valid": validation["valid"],
            "errors": validation["errors"],
            "parsed": spec.to_dict()
        }
    except ValueError as e:
        return {
            "success": False,
            "valid": False,
            "errors": [str(e)]
        }


@frappe.whitelist()
def get_business_rules() -> dict:
    """
    Get all business rules for BOM creation.
    
    Returns:
        Dict with rules list
    """
    from .validators import ValidationRulesEngine
    
    validator = ValidationRulesEngine()
    rules = validator.list_rules()
    
    return {
        "success": True,
        "rules": rules
    }


@frappe.whitelist()
def preview_bom_hierarchy(request_text: str) -> dict:
    """
    Preview the BOM hierarchy that would be created.
    
    This is a convenience wrapper around create_multi_level_bom_from_spec
    with dry_run=True.
    
    Args:
        request_text: Product specification
        
    Returns:
        GenerationReport with planned items/BOMs
    """
    return create_multi_level_bom_from_spec(request_text, dry_run=True)
