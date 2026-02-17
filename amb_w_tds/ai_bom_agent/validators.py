"""
Validation Rules Engine for BOM Creator Agent v9.2.0

Validates BOM generation plans against business rules.
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""
    rule_id: str
    rule_name: str
    message: str
    severity: str  # ERROR, WARNING
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "message": self.message,
            "severity": self.severity,
            "context": self.context
        }


class ValidationRulesEngine:
    """
    Engine for validating BOM generation plans against business rules.
    
    Loads rules from business_rules.json and validates plans accordingly.
    """
    
    # Hardcoded business rules (also loadable from JSON)
    DEFAULT_RULES = [
        {
            "id": "B1",
            "name": "Mandatory Steps for 0227",
            "description": "If family=0227, steps 1,2,3 ALL mandatory",
            "family": "0227",
            "type": "mandatory_steps",
            "required_steps": [1, 2, 3]
        },
        {
            "id": "B2",
            "name": "Shared Concentrate SFG",
            "description": "Concentrate SFG SHARED across flavors (same family+attribute)",
            "type": "shared_sfg",
            "step": 1,
            "sharing_keys": ["family", "attribute"]
        },
        {
            "id": "B3",
            "name": "Yield Rules",
            "description": "Standard yield percentages by process",
            "type": "yield_check",
            "yields": {
                "concentration": 0.95,
                "standardization": 0.98,
                "packing": 0.99
            }
        },
        {
            "id": "B4",
            "name": "UOM Conversion",
            "description": "1000L = 1 IBC",
            "type": "uom_conversion",
            "conversions": {
                "L_to_IBC": 0.001  # 1L = 0.001 IBC
            }
        },
        {
            "id": "B5",
            "name": "SFG Item Group",
            "description": "All SFGs item_group = Semi Finished Goods",
            "type": "item_attribute",
            "item_pattern": "SFG-*",
            "required_attributes": {
                "item_group": "Semi Finished Goods"
            }
        },
        {
            "id": "B6",
            "name": "SFG Stock Item",
            "description": "All SFGs is_stock_item = 1",
            "type": "item_attribute",
            "item_pattern": "SFG-*",
            "required_attributes": {
                "is_stock_item": 1
            }
        }
    ]
    
    def __init__(self, rules_file: Optional[str] = None):
        """
        Initialize the validation engine.
        
        Args:
            rules_file: Path to business_rules.json (optional)
        """
        self.rules = self._load_rules(rules_file)
    
    def _load_rules(self, rules_file: Optional[str]) -> List[Dict[str, Any]]:
        """
        Load business rules from file or use defaults.
        
        Args:
            rules_file: Path to rules JSON file
            
        Returns:
            List of rule definitions
        """
        if rules_file and os.path.exists(rules_file):
            with open(rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", self.DEFAULT_RULES)
        
        return self.DEFAULT_RULES
    
    def validate_plan(
        self, 
        plan: Dict[str, Any]
    ) -> List[ValidationError]:
        """
        Validate a BOM generation plan against all rules.
        
        Args:
            plan: Generation plan with spec, items, boms
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        
        spec = plan.get("spec", {})
        planned_items = plan.get("items", [])
        planned_boms = plan.get("boms", [])
        
        for rule in self.rules:
            rule_errors = self._apply_rule(rule, spec, planned_items, planned_boms)
            errors.extend(rule_errors)
        
        return errors
    
    def _apply_rule(
        self,
        rule: Dict[str, Any],
        spec: Dict[str, Any],
        items: List[Dict],
        boms: List[Dict]
    ) -> List[ValidationError]:
        """
        Apply a single rule to the plan.
        
        Args:
            rule: Rule definition
            spec: Parsed specification
            items: Planned items
            boms: Planned BOMs
            
        Returns:
            List of validation errors from this rule
        """
        rule_type = rule.get("type")
        
        if rule_type == "mandatory_steps":
            return self._validate_mandatory_steps(rule, spec, boms)
        elif rule_type == "yield_check":
            return self._validate_yields(rule, boms)
        elif rule_type == "item_attribute":
            return self._validate_item_attributes(rule, items)
        elif rule_type == "shared_sfg":
            return self._validate_shared_sfg(rule, spec, items)
        
        return []
    
    def _validate_mandatory_steps(
        self,
        rule: Dict[str, Any],
        spec: Dict[str, Any],
        boms: List[Dict]
    ) -> List[ValidationError]:
        """Validate that mandatory steps are present."""
        errors = []
        
        # Check if rule applies to this family
        rule_family = rule.get("family")
        spec_family = spec.get("family")
        
        if rule_family and spec_family != rule_family:
            return []  # Rule doesn't apply
        
        required_steps = rule.get("required_steps", [])
        
        # Extract steps from planned BOMs
        planned_steps = set()
        for bom in boms:
            step_num = bom.get("step_number")
            if step_num:
                planned_steps.add(step_num)
        
        missing_steps = set(required_steps) - planned_steps
        
        if missing_steps:
            errors.append(ValidationError(
                rule_id=rule["id"],
                rule_name=rule["name"],
                message=f"Missing mandatory steps: {sorted(missing_steps)}",
                severity="ERROR",
                context={"missing_steps": list(missing_steps)}
            ))
        
        return errors
    
    def _validate_yields(
        self,
        rule: Dict[str, Any],
        boms: List[Dict]
    ) -> List[ValidationError]:
        """Validate yield percentages are within expected ranges."""
        errors = []
        expected_yields = rule.get("yields", {})
        
        for bom in boms:
            process_type = bom.get("process_type", "").lower()
            actual_yield = bom.get("yield_pct", 1.0)
            
            if process_type in expected_yields:
                expected = expected_yields[process_type]
                
                # Allow 5% tolerance
                if abs(actual_yield - expected) > 0.05:
                    errors.append(ValidationError(
                        rule_id=rule["id"],
                        rule_name=rule["name"],
                        message=f"Yield for {process_type}: expected {expected}, got {actual_yield}",
                        severity="WARNING",
                        context={
                            "process_type": process_type,
                            "expected_yield": expected,
                            "actual_yield": actual_yield
                        }
                    ))
        
        return errors
    
    def _validate_item_attributes(
        self,
        rule: Dict[str, Any],
        items: List[Dict]
    ) -> List[ValidationError]:
        """Validate item attributes match requirements."""
        errors = []
        
        pattern = rule.get("item_pattern", "")
        required_attrs = rule.get("required_attributes", {})
        
        for item in items:
            item_code = item.get("item_code", "")
            
            # Check if pattern matches
            if not self._matches_pattern(item_code, pattern):
                continue
            
            # Check required attributes
            for attr, expected in required_attrs.items():
                actual = item.get(attr)
                
                if actual != expected:
                    errors.append(ValidationError(
                        rule_id=rule["id"],
                        rule_name=rule["name"],
                        message=f"Item {item_code}: {attr} should be {expected}, got {actual}",
                        severity="ERROR",
                        context={
                            "item_code": item_code,
                            "attribute": attr,
                            "expected": expected,
                            "actual": actual
                        }
                    ))
        
        return errors
    
    def _validate_shared_sfg(
        self,
        rule: Dict[str, Any],
        spec: Dict[str, Any],
        items: List[Dict]
    ) -> List[ValidationError]:
        """Validate shared SFG rules (concentrate sharing)."""
        # This is more of a planning rule than validation
        # Just check that SFGs exist as planned
        return []
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """
        Simple pattern matching with * wildcard.
        
        Args:
            value: String to match
            pattern: Pattern with * wildcards
            
        Returns:
            True if value matches pattern
        """
        if not pattern:
            return True
        
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return value == pattern
        
        # Handle prefix/suffix wildcards
        if pattern.startswith("*") and pattern.endswith("*"):
            return pattern[1:-1] in value
        elif pattern.startswith("*"):
            return value.endswith(pattern[1:])
        elif pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        
        return False
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific rule by ID.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Rule definition or None
        """
        for rule in self.rules:
            if rule.get("id") == rule_id:
                return rule
        return None
    
    def list_rules(self) -> List[Dict[str, str]]:
        """
        List all rules with basic info.
        
        Returns:
            List of {id, name, description} dicts
        """
        return [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "description": r.get("description")
            }
            for r in self.rules
        ]
