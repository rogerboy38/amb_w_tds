"""
Master Template Database for BOM Creator Agent v9.2.0

Manages loading and caching of BOM master templates.
"""

import json
import os
from typing import Dict, List, Optional, Any
from functools import lru_cache


class MasterTemplateDB:
    """
    Database for BOM master templates.
    
    Loads templates from JSON files and provides caching for performance.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template database.
        
        Args:
            templates_dir: Path to templates directory. Defaults to ./templates/
        """
        if templates_dir is None:
            # Default to templates/ subdirectory relative to this file
            self.templates_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "templates"
            )
        else:
            self.templates_dir = templates_dir
        
        self._template_cache: Dict[str, Dict] = {}
        self._rules_cache: Dict[str, Any] = {}
    
    def get_template(self, family: str) -> Dict[str, Any]:
        """
        Get the master template for a product family.
        
        Args:
            family: Product family code (e.g., "0227", "0307")
            
        Returns:
            Template dictionary with steps, operations, etc.
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template is invalid
        """
        # Check cache first
        if family in self._template_cache:
            return self._template_cache[family]
        
        # Load from file
        template_file = os.path.join(
            self.templates_dir, 
            f"template_{family}_master.json"
        )
        
        if not os.path.exists(template_file):
            raise FileNotFoundError(
                f"Template not found for family '{family}'. "
                f"Expected file: {template_file}"
            )
        
        with open(template_file, "r", encoding="utf-8") as f:
            template = json.load(f)
        
        # Validate basic structure
        self._validate_template(template, family)
        
        # Cache and return
        self._template_cache[family] = template
        return template
    
    def _validate_template(self, template: Dict, family: str) -> None:
        """
        Validate template structure.
        
        Args:
            template: Template dictionary to validate
            family: Expected family code
            
        Raises:
            ValueError: If template is invalid
        """
        required_keys = ["family", "version", "steps"]
        
        for key in required_keys:
            if key not in template:
                raise ValueError(
                    f"Template for '{family}' missing required key: {key}"
                )
        
        if template["family"] != family:
            raise ValueError(
                f"Template family mismatch: expected '{family}', "
                f"got '{template['family']}'"
            )
        
        if not isinstance(template["steps"], list) or len(template["steps"]) == 0:
            raise ValueError(
                f"Template for '{family}' must have at least one step"
            )
    
    def list_families(self) -> List[str]:
        """
        List all available product families with templates.
        
        Returns:
            List of family codes
        """
        families = []
        
        if not os.path.exists(self.templates_dir):
            return families
        
        for filename in os.listdir(self.templates_dir):
            if filename.startswith("template_") and filename.endswith("_master.json"):
                # Extract family from filename: template_XXXX_master.json
                parts = filename.replace("template_", "").replace("_master.json", "")
                families.append(parts)
        
        return sorted(families)
    
    def get_business_rules(self) -> Dict[str, Any]:
        """
        Load business validation rules.
        
        Returns:
            Dictionary of business rules
        """
        if "business_rules" in self._rules_cache:
            return self._rules_cache["business_rules"]
        
        rules_file = os.path.join(self.templates_dir, "business_rules.json")
        
        if not os.path.exists(rules_file):
            return {"rules": []}
        
        with open(rules_file, "r", encoding="utf-8") as f:
            rules = json.load(f)
        
        self._rules_cache["business_rules"] = rules
        return rules
    
    def get_yield_loss_rules(self) -> Dict[str, Any]:
        """
        Load yield and loss rules.
        
        Returns:
            Dictionary of yield/loss rules by process type
        """
        if "yield_loss" in self._rules_cache:
            return self._rules_cache["yield_loss"]
        
        rules_file = os.path.join(self.templates_dir, "yield_loss_rules.json")
        
        if not os.path.exists(rules_file):
            return {"processes": {}}
        
        with open(rules_file, "r", encoding="utf-8") as f:
            rules = json.load(f)
        
        self._rules_cache["yield_loss"] = rules
        return rules
    
    def get_uom_conversions(self) -> Dict[str, Any]:
        """
        Load UOM conversion rules.
        
        Returns:
            Dictionary of UOM conversions
        """
        if "uom_conversions" in self._rules_cache:
            return self._rules_cache["uom_conversions"]
        
        rules_file = os.path.join(self.templates_dir, "uom_conversions.json")
        
        if not os.path.exists(rules_file):
            return {"conversions": []}
        
        with open(rules_file, "r", encoding="utf-8") as f:
            rules = json.load(f)
        
        self._rules_cache["uom_conversions"] = rules
        return rules
    
    def get_operations_mapping(self) -> Dict[str, Any]:
        """
        Load operations and workstation mappings.
        
        Returns:
            Dictionary of operations mappings
        """
        if "operations" in self._rules_cache:
            return self._rules_cache["operations"]
        
        rules_file = os.path.join(self.templates_dir, "operations_mapping.json")
        
        if not os.path.exists(rules_file):
            return {"operations": []}
        
        with open(rules_file, "r", encoding="utf-8") as f:
            rules = json.load(f)
        
        self._rules_cache["operations"] = rules
        return rules
    
    def get_naming_conventions(self) -> str:
        """
        Load naming conventions documentation.
        
        Returns:
            Naming conventions markdown content
        """
        conv_file = os.path.join(self.templates_dir, "naming_conventions.md")
        
        if not os.path.exists(conv_file):
            return ""
        
        with open(conv_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def clear_cache(self) -> None:
        """Clear all cached templates and rules."""
        self._template_cache.clear()
        self._rules_cache.clear()
    
    def reload_template(self, family: str) -> Dict[str, Any]:
        """
        Force reload a template from disk.
        
        Args:
            family: Product family code
            
        Returns:
            Reloaded template dictionary
        """
        if family in self._template_cache:
            del self._template_cache[family]
        return self.get_template(family)
