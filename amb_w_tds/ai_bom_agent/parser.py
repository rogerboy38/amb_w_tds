"""
Product Specification Parser for BOM Creator Agent v9.2.0

Parses product requests for AMB-Wellness Aloe Vera production line.
Real production data aligned with ERPNext v16.

Product Families:
- 0227: Aloe Vera Gel Concentrate 30:1 (SFG, liquid, has variants)
- 0307: Aloe Vera Gel Spray Dried Powder 200:1 (FG, powder)
- 0303: Aloe Vera Normal (intermediate powder)
- 0301: Other powder products

Containers (Items, NOT UOMs):
- E001: 220L Barrel Blue (capacity ~230 Kg)
- E011: IBC Container 1000L (capacity ~1080 Kg)
- E012: Reused IBC Container
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from .data_contracts import ParsedSpec


class ProductSpecificationParser:
    """
    Parses product specifications for AMB-Wellness Aloe Vera production.
    
    Supported families: 0227, 0307, 0303, 0301
    All products measured in Kg (weight-based)
    Containers are items with FRACTIONAL Piece quantities
    """
    
    # Supported product families with their characteristics
    PRODUCT_FAMILIES = {
        "0227": {
            "name": "Aloe Vera Gel Concentrate",
            "type": "SFG",  # Sub-assembly
            "item_group": "Products Liquid",
            "default_concentration": "30X",
            "has_variants": True,
            "valid_variants": ["1X", "10X", "20X", "30X"],  # concentration ratios
            "uom": "Kg"
        },
        "0307": {
            "name": "Aloe Vera Gel Spray Dried Powder",
            "type": "FG",  # Finished Good
            "item_group": "Products Powder",
            "default_concentration": "200X",
            "has_variants": True,
            "valid_variants": ["100X", "200X"],  # powder ratios
            "uom": "Kg"
        },
        "0303": {
            "name": "Aloe Vera Normal (Powder)",
            "type": "SFG",
            "item_group": "Dry 200x",
            "default_concentration": "200X",
            "has_variants": False,
            "valid_variants": [],
            "uom": "Kg"
        },
        "0301": {
            "name": "Aloe Vera Powder Base",
            "type": "SFG",
            "item_group": "Products Powder",
            "default_concentration": "200X",
            "has_variants": False,
            "valid_variants": [],
            "uom": "Kg"
        }
    }
    
    # Concentration ratio patterns for parsing
    RATIO_PATTERNS = [
        (re.compile(r"(\d+):1", re.IGNORECASE), lambda m: f"{m.group(1)}X"),  # 30:1 -> 30X
        (re.compile(r"(\d+)X", re.IGNORECASE), lambda m: f"{m.group(1)}X"),   # 30X -> 30X
        (re.compile(r"(\d+)x", re.IGNORECASE), lambda m: f"{m.group(1)}X"),   # 30x -> 30X
    ]
    
    SUPPORTED_FAMILIES = list(PRODUCT_FAMILIES.keys())
    
    # Container definitions - Items NOT UOMs
    # Containers use FRACTIONAL Piece quantities
    CONTAINERS = {
        "E001": {
            "name": "220L Barrel Blue",
            "capacity_liters": 220,
            "capacity_kg": 230,  # Approx weight capacity
            "qty_per_kg": 0.004351,  # 1/230
            "uom": "Piece"
        },
        "E011": {
            "name": "IBC Container",
            "capacity_liters": 1000,
            "capacity_kg": 1080,  # 1000L × ~1.08 density
            "qty_per_kg": 0.000926,  # 1/1080
            "uom": "Piece"
        },
        "E012": {
            "name": "Reused IBC Container",
            "capacity_liters": 1000,
            "capacity_kg": 1080,
            "qty_per_kg": 0.000926,
            "uom": "Piece"
        }
    }
    
    # Packaging formats map to container items
    PACKAGING_FORMATS = {
        "1000L-IBC": {
            "container_item": "E011",
            "uom": "Kg",
            "capacity_kg": 1080,
            "qty_per_kg": 0.000926
        },
        "200L-DRUM": {
            "container_item": "E001",
            "uom": "Kg",
            "capacity_kg": 230,
            "qty_per_kg": 0.004351
        },
        "220L-DRUM": {
            "container_item": "E001",
            "uom": "Kg",
            "capacity_kg": 230,
            "qty_per_kg": 0.004351
        },
        "20L-PAIL": {
            "container_item": None,  # TODO: Add pail item code
            "uom": "Kg",
            "capacity_kg": 21.6,
            "qty_per_kg": 0.0463
        },
        "25KG-BAG": {
            "container_item": None,  # For powder products
            "uom": "Kg",
            "capacity_kg": 25,
            "qty_per_kg": 0.04
        }
    }
    
    # Item code patterns - Real AMB-Wellness format
    # Examples: 0227, 0307, 0303, A0303-ORGANIC-AS NC-NMT3%PS-SPD-Aloin NMT 20 PPM
    ITEM_CODE_PATTERNS = [
        # Simple numeric: 0227, 0307, 0303
        re.compile(r"^(\d{4})$"),
        # With variant suffix: 0227-XXXXX
        re.compile(r"^(\d{4})-(.+)$"),
        # Extended format: A0303-ORGANIC-AS NC-...
        re.compile(r"^[A]?(\d{4})-(.+)$", re.IGNORECASE)
    ]
    
    def parse(self, request_text: str) -> ParsedSpec:
        """
        Parse a product request into ParsedSpec.
        
        Args:
            request_text: Item code or natural language request
            
        Returns:
            ParsedSpec with extracted information
            
        Raises:
            ValueError: If parsing fails
        """
        request_text = request_text.strip()
        
        # Try parsing as item code first
        for pattern in self.ITEM_CODE_PATTERNS:
            match = pattern.match(request_text)
            if match:
                return self._parse_item_code(request_text, match)
        
        # Try natural language
        return self._parse_natural_language(request_text)
    
    def _parse_item_code(self, item_code: str, match: re.Match) -> ParsedSpec:
        """
        Parse a structured item code.
        
        Formats:
        - Simple: 0227, 0307
        - With variant: 0227-ORGANIC, 0307-STANDARD
        - Extended: A0303-ORGANIC-AS NC-NMT3%PS-SPD-Aloin NMT 20 PPM
        """
        groups = match.groups()
        family = groups[0]
        variant = groups[1] if len(groups) > 1 else None
        
        if family not in self.SUPPORTED_FAMILIES:
            raise ValueError(
                f"Unsupported product family '{family}'. "
                f"Supported: {self.SUPPORTED_FAMILIES}"
            )
        
        family_info = self.PRODUCT_FAMILIES[family]
        
        # Determine container from variant or default
        container_item = None
        container_qty_per_kg = 0.0
        packaging = None
        
        if variant:
            # Check if variant includes packaging info
            variant_upper = variant.upper()
            for pkg_key, pkg_info in self.PACKAGING_FORMATS.items():
                if pkg_key.replace("-", "") in variant_upper.replace("-", ""):
                    packaging = pkg_key
                    container_item = pkg_info.get("container_item")
                    container_qty_per_kg = pkg_info.get("qty_per_kg", 0.0)
                    break
        
        # Default packaging based on product type
        if not packaging:
            if family_info["type"] == "SFG" and "Liquid" in family_info["item_group"]:
                packaging = "1000L-IBC"
                pkg_info = self.PACKAGING_FORMATS[packaging]
                container_item = pkg_info.get("container_item")
                container_qty_per_kg = pkg_info.get("qty_per_kg", 0.0)
            elif "Powder" in family_info["item_group"]:
                packaging = "25KG-BAG"
        
        return ParsedSpec(
            family=family,
            attribute=variant.split("-")[0] if variant and "-" in variant else None,
            variant=None,  # Not used in real production
            mesh_size=None,
            packaging=packaging,
            target_uom=family_info["uom"],
            target_qty=1.0,
            container_item=container_item,
            container_qty_per_kg=container_qty_per_kg,
            raw_request=item_code,
            parsed_at=datetime.now()
        )
    
    def _extract_variant(self, request_text: str, family: str) -> Optional[str]:
        """
        Extract concentration variant from request text.
        
        Supports formats: 30:1, 30X, 30x
        Validates against family's valid_variants list.
        Falls back to default_concentration if no match.
        
        Args:
            request_text: Raw request text
            family: Product family code (e.g., "0227")
            
        Returns:
            Normalized variant string (e.g., "30X") or None
        """
        family_info = self.PRODUCT_FAMILIES.get(family, {})
        valid_variants = family_info.get("valid_variants", [])
        default = family_info.get("default_concentration")
        
        # Try each pattern to extract variant
        for pattern, normalizer in self.RATIO_PATTERNS:
            match = pattern.search(request_text)
            if match:
                normalized = normalizer(match)
                # Validate against valid_variants if list exists
                if valid_variants:
                    if normalized in valid_variants:
                        return normalized
                    # Check if numeric part matches (e.g., "200X" matches "200X")
                    for vv in valid_variants:
                        if normalized.upper() == vv.upper():
                            return vv
                else:
                    return normalized
        
        # Return default if family has variants
        if family_info.get("has_variants") and default:
            return default
        
        return None

    def _parse_natural_language(self, request_text: str) -> ParsedSpec:
        """
        Parse a natural language request.
        
        Examples:
        - "Create BOM for 0227 concentrate in IBC"
        - "0307 powder 200:1"
        - "Aloe vera gel concentrate 30:1"
        - "0227 10X in drums" -> variant=10X
        """
        text_upper = request_text.upper()
        
        # Extract family
        family = None
        for f in self.SUPPORTED_FAMILIES:
            if f in text_upper:
                family = f
                break
        
        # Try to detect family from product description
        if not family:
            if "CONCENTRATE" in text_upper or "30:1" in text_upper or "LIQUID" in text_upper:
                family = "0227"
            elif "POWDER" in text_upper or "200:1" in text_upper or "SPRAY" in text_upper:
                family = "0307"
            elif "GEL" in text_upper:
                family = "0227"
        
        if not family:
            raise ValueError(
                f"Could not determine product family. "
                f"Please specify: {self.SUPPORTED_FAMILIES} or use keywords like "
                f"'concentrate', 'powder', '30:1', '200:1'"
            )
        
        family_info = self.PRODUCT_FAMILIES[family]
        
        # Extract variant (concentration ratio)
        variant = self._extract_variant(request_text, family)
        
        # Extract packaging
        packaging = None
        container_item = None
        container_qty_per_kg = 0.0
        
        for pkg_key, pkg_info in self.PACKAGING_FORMATS.items():
            # Check various forms
            pkg_variants = [
                pkg_key,
                pkg_key.replace("-", " "),
                pkg_key.replace("-", ""),
                pkg_key.split("-")[-1]
            ]
            for v in pkg_variants:
                if v in text_upper:
                    packaging = pkg_key
                    container_item = pkg_info.get("container_item")
                    container_qty_per_kg = pkg_info.get("qty_per_kg", 0.0)
                    break
            if packaging:
                break
        
        # Default packaging
        if not packaging:
            if "Liquid" in family_info["item_group"]:
                packaging = "1000L-IBC"
                pkg_info = self.PACKAGING_FORMATS[packaging]
                container_item = pkg_info.get("container_item")
                container_qty_per_kg = pkg_info.get("qty_per_kg", 0.0)
            else:
                packaging = "25KG-BAG"
        
        return ParsedSpec(
            family=family,
            attribute=None,
            variant=variant,
            mesh_size=None,
            packaging=packaging,
            target_uom=family_info["uom"],
            target_qty=1.0,
            container_item=container_item,
            container_qty_per_kg=container_qty_per_kg,
            raw_request=request_text,
            parsed_at=datetime.now()
        )
    
    def get_family_info(self, family: str) -> Dict[str, Any]:
        """Get product family information."""
        if family not in self.PRODUCT_FAMILIES:
            raise ValueError(f"Unknown family: {family}")
        return self.PRODUCT_FAMILIES[family]
    
    def get_container_info(self, container_code: str) -> Dict[str, Any]:
        """Get container item information."""
        if container_code not in self.CONTAINERS:
            raise ValueError(f"Unknown container: {container_code}")
        return self.CONTAINERS[container_code]
    
    def validate_spec(self, spec: ParsedSpec) -> Dict[str, Any]:
        """
        Validate a ParsedSpec.
        
        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []
        
        if spec.family not in self.SUPPORTED_FAMILIES:
            errors.append(f"Invalid family: {spec.family}")
        
        if spec.container_item and spec.container_item not in self.CONTAINERS:
            errors.append(f"Invalid container: {spec.container_item}")
        
        if spec.target_uom != "Kg":
            errors.append(f"UOM must be Kg, got: {spec.target_uom}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def generate_item_code(self, spec: ParsedSpec) -> str:
        """
        Generate standard item code from ParsedSpec.
        
        For base items: just the family code (0227, 0307)
        For variants: family-variant (0227-ORGANIC)
        """
        if spec.attribute:
            return f"{spec.family}-{spec.attribute}"
        return spec.family
