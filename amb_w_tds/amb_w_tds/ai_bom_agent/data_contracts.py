"""
Data Contracts for BOM Creator Agent v9.2.0
Dataclasses for type-safe data exchange between components
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class ParsedSpec:
    """Parsed product specification from user request"""
    family: str  # e.g., "0227", "0307"
    attribute: str  # e.g., "ORGANIC", "CONVENTIONAL", "KOSHER"
    variant: Optional[str] = None  # e.g., "HIGHPOL", "ACETYPOL", concentration ratios
    mesh_size: Optional[str] = None  # e.g., "100M" (for powder families)
    packaging: str = ""  # e.g., "1000L-IBC", "25KG-BAG"
    target_uom: str = "Kg"
    target_qty: float = 1.0
    container_item: Optional[str] = None  # e.g., "E011" for IBC Container
    container_qty_per_kg: float = 0.0  # Fraction of container per Kg (e.g., 0.000926 for IBC)
    raw_request: str = ""
    parsed_at: datetime = field(default_factory=datetime.now)
    # Phase 7: Customer-specific naming
    customer: Optional[str] = None  # e.g., "XYZ"
    customer_code: Optional[str] = None  # e.g., "XYZ"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "attribute": self.attribute,
            "variant": self.variant,
            "mesh_size": self.mesh_size,
            "packaging": self.packaging,
            "target_uom": self.target_uom,
            "target_qty": self.target_qty,
            "container_item": self.container_item,
            "container_qty_per_kg": self.container_qty_per_kg,
            "raw_request": self.raw_request,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None,
            "customer": self.customer,
            "customer_code": self.customer_code
        }
    
    def get_variant(self) -> str:
        """Get variant identifier (variant for juice, mesh for powder)"""
        return self.variant or self.mesh_size or "PLAIN"
    
    def get_fg_code(self) -> str:
        """Generate finished good item code"""
        variant = self.get_variant()
        return f"{self.family}-{self.attribute}-{variant}-{self.packaging}".replace("--", "-")


@dataclass
class PlannedItem:
    """Planned item to be created or reused"""
    item_code: str
    item_name: str
    item_group: str
    stock_uom: str
    description: str = ""
    is_stock_item: int = 1
    is_purchase_item: int = 0
    is_sales_item: int = 0
    already_exists: bool = False
    step_number: Optional[int] = None
    item_type: str = "sfg"  # sfg, fg, rm, pkg
    # Phase 7: Batch tracking flags
    has_batch_no: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "item_group": self.item_group,
            "stock_uom": self.stock_uom,
            "description": self.description,
            "is_stock_item": self.is_stock_item,
            "is_purchase_item": self.is_purchase_item,
            "is_sales_item": self.is_sales_item,
            "already_exists": self.already_exists,
            "step_number": self.step_number,
            "item_type": self.item_type,
            "has_batch_no": self.has_batch_no
        }


@dataclass
class BOMItem:
    """Single item in a BOM"""
    item_code: str
    qty: float
    uom: str
    bom_no: Optional[str] = None  # Link to sub-BOM for SFGs
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "item_code": self.item_code,
            "qty": self.qty,
            "uom": self.uom
        }
        if self.bom_no:
            result["bom_no"] = self.bom_no
        return result


@dataclass
class BOMOperation:
    """Operation in BOM routing"""
    operation: str
    workstation: str
    time_in_mins: float = 0
    hour_rate: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "workstation": self.workstation,
            "time_in_mins": self.time_in_mins,
            "hour_rate": self.hour_rate
        }


@dataclass
class PlannedBOM:
    """Planned BOM to be created or reused"""
    item_code: str
    bom_items: List[BOMItem] = field(default_factory=list)
    operations: List[BOMOperation] = field(default_factory=list)
    yield_pct: float = 100.0
    quantity: float = 1.0
    uom: str = "Nos"
    already_exists: bool = False
    existing_bom_name: Optional[str] = None
    step_number: Optional[int] = None
    process_type: Optional[str] = None  # concentration, standardization, packing, etc.
    is_default: int = 1
    is_active: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_code": self.item_code,
            "bom_items": [item.to_dict() for item in self.bom_items],
            "operations": [op.to_dict() for op in self.operations],
            "yield_pct": self.yield_pct,
            "quantity": self.quantity,
            "uom": self.uom,
            "already_exists": self.already_exists,
            "existing_bom_name": self.existing_bom_name,
            "step_number": self.step_number,
            "process_type": self.process_type,
            "is_default": self.is_default,
            "is_active": self.is_active
        }


@dataclass
class ValidationError:
    """Validation error or warning"""
    rule_id: str
    category: str  # mandatory, warning, informational
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "message": self.message,
            "context": self.context
        }


@dataclass
class GenerationPlan:
    """Complete plan for BOM generation"""
    spec: ParsedSpec
    items: List[PlannedItem] = field(default_factory=list)
    boms: List[PlannedBOM] = field(default_factory=list)
    validation_errors: List[ValidationError] = field(default_factory=list)
    validation_warnings: List[ValidationError] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "boms": [bom.to_dict() for bom in self.boms],
            "validation_errors": [e.to_dict() for e in self.validation_errors],
            "validation_warnings": [w.to_dict() for w in self.validation_warnings]
        }
    
    def is_valid(self) -> bool:
        """Check if plan has no mandatory errors"""
        return len(self.validation_errors) == 0


@dataclass
class GenerationReport:
    """Report of BOM generation execution"""
    success: bool
    spec: ParsedSpec
    items_created: List[str] = field(default_factory=list)
    items_reused: List[str] = field(default_factory=list)
    boms_created: List[str] = field(default_factory=list)
    boms_reused: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dry_run: bool = False
    execution_time_seconds: float = 0.0
    plan: Optional[GenerationPlan] = None
    # Phase 7: Batch tracking summary
    batch_tracking: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "spec": self.spec.to_dict() if self.spec else None,
            "items_created": self.items_created,
            "items_reused": self.items_reused,
            "boms_created": self.boms_created,
            "boms_reused": self.boms_reused,
            "errors": self.errors,
            "warnings": self.warnings,
            "dry_run": self.dry_run,
            "execution_time_seconds": self.execution_time_seconds,
            "plan": self.plan.to_dict() if self.plan else None,
            "batch_tracking": self.batch_tracking
        }
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        mode = "(DRY RUN)" if self.dry_run else ""
        lines = [
            f"{status} {mode}",
            f"Items: {len(self.items_created)} created, {len(self.items_reused)} reused",
            f"BOMs: {len(self.boms_created)} created, {len(self.boms_reused)} reused",
            f"Time: {self.execution_time_seconds:.2f}s"
        ]
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
        return "\n".join(lines)
