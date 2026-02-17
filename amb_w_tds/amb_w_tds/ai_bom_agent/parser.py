"""
Product Specification Parser for BOM Creator Agent v9.2.0

Parses product requests (natural language or item codes) into structured specifications.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from .data_contracts import ParsedSpec


class ProductSpecificationParser:
    """
    Parses product specifications from various input formats.
    
    Supported families: 0227, 0307
    Attributes: ORGANIC, CONVENTIONAL, KOSHER
    Packaging: 1000L-IBC, 200L-DRUM, 20L-PAIL
    """
    
    # Supported product families
    SUPPORTED_FAMILIES = ["0227", "0307"]
    
    # Supported attributes
    SUPPORTED_ATTRIBUTES = ["ORGANIC", "CONVENTIONAL", "KOSHER"]
    
    # Supported packaging formats with UOM mapping
    # Note: IBC/DRUM/PAIL are container ITEMS, not UOMs
    # E011 = IBC Container (new), E012 = Reused IBC Container
    # UOM is always Kg (weight-based measurement)
    # The "1000L" in packaging refers to container capacity, not the UOM
    # container_capacity_kg: weight capacity considering density (~1.08 for concentrated juice)
    # container_qty_per_kg: fraction of container per 1 Kg of product (1/capacity)
    PACKAGING_FORMATS = {
        "1000L-IBC": {
            "uom": "Kg",
            "volume_liters": 1000,
            "container_item": "E011",
            "container_capacity_kg": 1080,  # ~1000L × 1.08 density
            "container_qty_per_kg": 0.000926  # 1/1080
        },
        "200L-DRUM": {
            "uom": "Kg",
            "volume_liters": 200,
            "container_item": None,  # TODO: Add drum item code
            "container_capacity_kg": 216,  # ~200L × 1.08 density
            "container_qty_per_kg": 0.00463  # 1/216
        },
        "20L-PAIL": {
            "uom": "Kg",
            "volume_liters": 20,
            "container_item": None,  # TODO: Add pail item code
            "container_capacity_kg": 21.6,  # ~20L × 1.08 density
            "container_qty_per_kg": 0.0463  # 1/21.6
        },
    }
    
    # Common flavor patterns
    COMMON_FLAVORS = [
        "NATURAL", "UNFLAVORED", "STRAWBERRY", "MANGO", "PINEAPPLE",
        "ORANGE", "GRAPE", "APPLE", "LEMON", "LIME", "BERRY",
        "TROPICAL", "CITRUS", "MIXED", "PLAIN"
    ]
    
    # Pattern for item codes: FAMILY-ATTRIBUTE-FLAVOR-PACKAGING
    ITEM_CODE_PATTERN = re.compile(
        r"^(\d{4})-([A-Z]+)-([A-Z]+)-(\d+L-[A-Z]+)$",
        re.IGNORECASE
    )
    
    def parse(self, request_text: str) -> ParsedSpec:
        """
        Parse a product request (natural language or item code) into ParsedSpec.
        
        Args:
            request_text: Raw request text or item code
            
        Returns:
            ParsedSpec with extracted information
            
        Raises:
            ValueError: If parsing fails or required info is missing
        """
        request_text = request_text.strip()
        
        # Try parsing as item code first
        item_match = self.ITEM_CODE_PATTERN.match(request_text)
        if item_match:
            return self.parse_item_code(request_text)
        
        # Parse as natural language request
        return self._parse_natural_language(request_text)
    
    def parse_item_code(self, item_code: str) -> ParsedSpec:
        """
        Parse a structured item code into ParsedSpec.
        
        Expected format: FAMILY-ATTRIBUTE-FLAVOR-PACKAGING
        Example: 0227-ORGANIC-NATURAL-1000L-IBC
        
        Args:
            item_code: Item code string
            
        Returns:
            ParsedSpec with extracted components
            
        Raises:
            ValueError: If item code format is invalid
        """
        item_code = item_code.strip().upper()
        
        # Split and validate components
        parts = item_code.split("-")
        
        if len(parts) < 4:
            raise ValueError(
                f"Invalid item code format: '{item_code}'. "
                f"Expected: FAMILY-ATTRIBUTE-FLAVOR-PACKAGING"
            )
        
        family = parts[0]
        attribute = parts[1]
        flavor = parts[2]
        # Packaging might have a hyphen (e.g., 1000L-IBC)
        packaging = "-".join(parts[3:])
        
        # Validate family
        if family not in self.SUPPORTED_FAMILIES:
            raise ValueError(
                f"Unsupported family '{family}'. "
                f"Supported: {self.SUPPORTED_FAMILIES}"
            )
        
        # Validate attribute
        if attribute not in self.SUPPORTED_ATTRIBUTES:
            raise ValueError(
                f"Unsupported attribute '{attribute}'. "
                f"Supported: {self.SUPPORTED_ATTRIBUTES}"
            )
        
        # Validate packaging
        if packaging not in self.PACKAGING_FORMATS:
            raise ValueError(
                f"Unsupported packaging '{packaging}'. "
                f"Supported: {list(self.PACKAGING_FORMATS.keys())}"
            )
        
        pkg_info = self.PACKAGING_FORMATS[packaging]
        target_uom = pkg_info["uom"]
        container_item = pkg_info.get("container_item")
        container_qty_per_kg = pkg_info.get("container_qty_per_kg", 0.0)
        
        return ParsedSpec(
            family=family,
            attribute=attribute,
            flavor=flavor,
            packaging=packaging,
            target_uom=target_uom,
            container_item=container_item,
            container_qty_per_kg=container_qty_per_kg,
            raw_request=item_code,
            parsed_at=datetime.now()
        )
    
    def _parse_natural_language(self, request_text: str) -> ParsedSpec:
        """
        Parse a natural language request into ParsedSpec.
        
        Examples:
        - "Create BOM for organic aloe juice in 1000L IBC"
        - "0227 conventional natural 200L drum"
        - "Make kosher 0307 product in pails"
        
        Args:
            request_text: Natural language request
            
        Returns:
            ParsedSpec with extracted information
            
        Raises:
            ValueError: If required information cannot be extracted
        """
        text_upper = request_text.upper()
        
        # Extract family
        family = None
        for f in self.SUPPORTED_FAMILIES:
            if f in text_upper:
                family = f
                break
        
        if not family:
            raise ValueError(
                f"Could not determine product family. "
                f"Please specify one of: {self.SUPPORTED_FAMILIES}"
            )
        
        # Extract attribute
        attribute = None
        for attr in self.SUPPORTED_ATTRIBUTES:
            if attr in text_upper:
                attribute = attr
                break
        
        if not attribute:
            # Default to CONVENTIONAL if not specified
            attribute = "CONVENTIONAL"
        
        # Extract packaging
        packaging = None
        for pkg in self.PACKAGING_FORMATS:
            # Check for various forms: "1000L-IBC", "1000L IBC", "IBC", etc.
            pkg_variants = [
                pkg,
                pkg.replace("-", " "),
                pkg.replace("-", ""),
                pkg.split("-")[-1]  # Just the container type
            ]
            for variant in pkg_variants:
                if variant in text_upper:
                    packaging = pkg
                    break
            if packaging:
                break
        
        if not packaging:
            raise ValueError(
                f"Could not determine packaging format. "
                f"Please specify one of: {list(self.PACKAGING_FORMATS.keys())}"
            )
        
        # Extract flavor
        flavor = None
        for flv in self.COMMON_FLAVORS:
            if flv in text_upper:
                flavor = flv
                break
        
        if not flavor:
            # Default to NATURAL if not specified
            flavor = "NATURAL"
        
        pkg_info = self.PACKAGING_FORMATS[packaging]
        target_uom = pkg_info["uom"]
        container_item = pkg_info.get("container_item")
        container_qty_per_kg = pkg_info.get("container_qty_per_kg", 0.0)
        
        return ParsedSpec(
            family=family,
            attribute=attribute,
            flavor=flavor,
            packaging=packaging,
            target_uom=target_uom,
            container_item=container_item,
            container_qty_per_kg=container_qty_per_kg,
            raw_request=request_text,
            parsed_at=datetime.now()
        )
    
    def validate_spec(self, spec: ParsedSpec) -> Dict[str, Any]:
        """
        Validate a ParsedSpec and return validation results.
        
        Args:
            spec: ParsedSpec to validate
            
        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []
        
        if spec.family not in self.SUPPORTED_FAMILIES:
            errors.append(f"Invalid family: {spec.family}")
        
        if spec.attribute not in self.SUPPORTED_ATTRIBUTES:
            errors.append(f"Invalid attribute: {spec.attribute}")
        
        if spec.packaging not in self.PACKAGING_FORMATS:
            errors.append(f"Invalid packaging: {spec.packaging}")
        
        if not spec.flavor:
            errors.append("Flavor is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def generate_item_code(self, spec: ParsedSpec) -> str:
        """
        Generate a standard item code from a ParsedSpec.
        
        Args:
            spec: ParsedSpec with product information
            
        Returns:
            Formatted item code string
        """
        return f"{spec.family}-{spec.attribute}-{spec.flavor}-{spec.packaging}"
