"""
Agent Core Engine for BOM Creator Agent v9.2.0

Main orchestration engine for multi-level BOM generation.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from .data_contracts import ParsedSpec, PlannedItem, PlannedBOM, GenerationReport, BOMItem
from .parser import ProductSpecificationParser
from .templates import MasterTemplateDB
from .erpnext_client import ItemAndBOMService
from .validators import ValidationRulesEngine, ValidationError


class AgentCoreEngine:
    """
    Core engine for BOM Creator Agent.
    
    Orchestrates the full BOM generation process:
    1. Parse specification
    2. Load template
    3. Plan items and BOMs
    4. Validate plan
    5. Execute (create items and BOMs)
    6. Return report
    """
    
    def __init__(
        self,
        templates_dir: Optional[str] = None,
        rules_file: Optional[str] = None,
        company: Optional[str] = None
    ):
        """
        Initialize the engine.
        
        Args:
            templates_dir: Path to templates directory
            rules_file: Path to business_rules.json
            company: Company for item/BOM creation
        """
        self.parser = ProductSpecificationParser()
        self.templates = MasterTemplateDB(templates_dir)
        self.erpnext = ItemAndBOMService(company)
        self.validator = ValidationRulesEngine(rules_file)
    
    def generate(
        self,
        spec: ParsedSpec,
        dry_run: bool = False
    ) -> GenerationReport:
        """
        Generate multi-level BOM from specification.
        
        Args:
            spec: Parsed product specification
            dry_run: If True, plan but don't create in database
            
        Returns:
            GenerationReport with results
        """
        start_time = time.time()
        
        items_created = []
        items_reused = []
        boms_created = []
        boms_reused = []
        errors = []
        warnings = []
        
        try:
            # 1. Load template
            template = self.templates.get_template(spec.family)
            
            # 2. Plan items and BOMs
            planned_items, planned_boms = self._plan_hierarchy(spec, template)
            
            # 3. Validate plan
            plan = {
                "spec": spec.to_dict(),
                "items": [i.to_dict() for i in planned_items],
                "boms": [b.to_dict() for b in planned_boms]
            }
            
            validation_errors = self.validator.validate_plan(plan)
            
            for ve in validation_errors:
                if ve.severity == "ERROR":
                    errors.append(ve.to_dict())
                else:
                    warnings.append(ve.to_dict())
            
            # Stop if there are validation errors
            if errors and not dry_run:
                return GenerationReport(
                    success=False,
                    spec=spec,
                    items_created=[],
                    items_reused=[],
                    boms_created=[],
                    boms_reused=[],
                    errors=errors,
                    warnings=warnings,
                    dry_run=dry_run,
                    execution_time_seconds=time.time() - start_time
                )
            
            # 4. Execute (if not dry run)
            if not dry_run:
                items_created, items_reused = self._create_items(planned_items)
                boms_created, boms_reused = self._create_boms(planned_boms)
            else:
                # In dry run, just report what would be created
                for item in planned_items:
                    if item.already_exists:
                        items_reused.append(item.item_code)
                    else:
                        items_created.append(item.item_code)
                
                for bom in planned_boms:
                    if bom.already_exists:
                        boms_reused.append(bom.item_code)
                    else:
                        boms_created.append(bom.item_code)
            
            return GenerationReport(
                success=True,
                spec=spec,
                items_created=items_created,
                items_reused=items_reused,
                boms_created=boms_created,
                boms_reused=boms_reused,
                errors=errors,
                warnings=warnings,
                dry_run=dry_run,
                execution_time_seconds=time.time() - start_time
            )
            
        except Exception as e:
            errors.append({
                "rule_id": "SYSTEM",
                "rule_name": "System Error",
                "message": str(e),
                "severity": "ERROR",
                "context": {}
            })
            
            return GenerationReport(
                success=False,
                spec=spec,
                items_created=items_created,
                items_reused=items_reused,
                boms_created=boms_created,
                boms_reused=boms_reused,
                errors=errors,
                warnings=warnings,
                dry_run=dry_run,
                execution_time_seconds=time.time() - start_time
            )
    
    def _plan_hierarchy(
        self,
        spec: ParsedSpec,
        template: Dict[str, Any]
    ) -> tuple:
        """
        Plan the item and BOM hierarchy based on template.
        
        Args:
            spec: Parsed specification
            template: Master template for this family
            
        Returns:
            Tuple of (planned_items, planned_boms)
        """
        planned_items: List[PlannedItem] = []
        planned_boms: List[PlannedBOM] = []
        
        steps = template.get("steps", [])
        previous_output = None
        
        for step in steps:
            step_num = step.get("step_number", 0)
            step_name = step.get("step_name", f"Step{step_num}")
            process_type = step.get("process_type", step_name.lower())
            
            # Generate output item code for this step
            output_item = self._generate_step_output_item(spec, step, step_num)
            
            # Check if item already exists
            item_exists = self.erpnext.item_exists(output_item["item_code"])
            
            planned_items.append(PlannedItem(
                item_code=output_item["item_code"],
                item_name=output_item["item_name"],
                item_group=output_item["item_group"],
                stock_uom=output_item["stock_uom"],
                already_exists=item_exists
            ))
            
            # Plan BOM for this step
            bom_items = self._plan_bom_items(spec, step, previous_output)
            
            # Check if BOM already exists
            bom_exists = self.erpnext.bom_exists(output_item["item_code"])
            
            planned_boms.append(PlannedBOM(
                item_code=output_item["item_code"],
                bom_items=bom_items,
                operations=step.get("operations", []),
                yield_pct=step.get("yield_percentage", 1.0),
                already_exists=bom_exists,
                step_number=step_num,
                process_type=process_type
            ))
            
            previous_output = output_item["item_code"]
        
        # Plan final FG item
        fg_item = self._generate_fg_item(spec)
        fg_exists = self.erpnext.item_exists(fg_item["item_code"])
        
        planned_items.append(PlannedItem(
            item_code=fg_item["item_code"],
            item_name=fg_item["item_name"],
            item_group=fg_item["item_group"],
            stock_uom=fg_item["stock_uom"],
            already_exists=fg_exists
        ))
        
        # Plan FG BOM (uses last step output)
        fg_bom_items = [BOMItem(
            item_code=previous_output,
            qty=1.0,
            uom=spec.target_uom,
            bom_no=self.erpnext.get_default_bom(previous_output)
        )]
        
        fg_bom_exists = self.erpnext.bom_exists(fg_item["item_code"])
        
        planned_boms.append(PlannedBOM(
            item_code=fg_item["item_code"],
            bom_items=fg_bom_items,
            operations=[],
            yield_pct=0.99,  # Packing yield
            already_exists=fg_bom_exists,
            step_number=len(steps) + 1,
            process_type="packing"
        ))
        
        return planned_items, planned_boms
    
    def _generate_step_output_item(
        self,
        spec: ParsedSpec,
        step: Dict[str, Any],
        step_num: int
    ) -> Dict[str, Any]:
        """Generate item details for a step's output."""
        step_name = step.get("step_name", f"STEP{step_num}").upper().replace(" ", "-")
        
        # SFG naming: SFG-{FAMILY}-STEP{N}-{PROCESS}
        item_code = f"SFG-{spec.family}-STEP{step_num}-{step_name}"
        
        return {
            "item_code": item_code,
            "item_name": f"{spec.family} {step_name} (Step {step_num})",
            "item_group": "Semi Finished Goods",
            "stock_uom": step.get("output_uom", "Kg")
        }
    
    def _generate_fg_item(self, spec: ParsedSpec) -> Dict[str, Any]:
        """Generate finished goods item details."""
        # FG naming: {FAMILY}-{ATTRIBUTE}-{FLAVOR}-{PACKAGING}
        item_code = f"{spec.family}-{spec.attribute}-{spec.flavor}-{spec.packaging}"
        
        return {
            "item_code": item_code,
            "item_name": f"{spec.family} {spec.attribute} {spec.flavor} ({spec.packaging})",
            "item_group": "Finished Goods",
            "stock_uom": spec.target_uom
        }
    
    def _plan_bom_items(
        self,
        spec: ParsedSpec,
        step: Dict[str, Any],
        previous_output: Optional[str]
    ) -> List[BOMItem]:
        """Plan BOM items for a step."""
        items = []
        
        # Get input items from template
        input_items = step.get("input_items", [])
        
        for input_item in input_items:
            item_pattern = input_item.get("item_pattern", "")
            qty = input_item.get("qty", 1.0)
            uom = input_item.get("uom", "Kg")
            
            # If pattern references previous step output
            if "PREV_OUTPUT" in item_pattern and previous_output:
                items.append(BOMItem(
                    item_code=previous_output,
                    qty=qty,
                    uom=uom,
                    bom_no=self.erpnext.get_default_bom(previous_output)
                ))
            else:
                # Resolve pattern to actual item code
                item_code = self._resolve_item_pattern(item_pattern, spec)
                items.append(BOMItem(
                    item_code=item_code,
                    qty=qty,
                    uom=uom
                ))
        
        # If no input items defined but we have previous output, use it
        if not items and previous_output:
            items.append(BOMItem(
                item_code=previous_output,
                qty=1.0,
                uom="Kg",
                bom_no=self.erpnext.get_default_bom(previous_output)
            ))
        
        return items
    
    def _resolve_item_pattern(
        self,
        pattern: str,
        spec: ParsedSpec
    ) -> str:
        """Resolve an item pattern to actual item code."""
        # Replace placeholders
        resolved = pattern
        resolved = resolved.replace("{FAMILY}", spec.family)
        resolved = resolved.replace("{ATTRIBUTE}", spec.attribute)
        resolved = resolved.replace("{FLAVOR}", spec.flavor)
        resolved = resolved.replace("{PACKAGING}", spec.packaging)
        
        # Remove wildcards for now (could do lookup in future)
        resolved = resolved.replace("*", "")
        
        return resolved
    
    def _create_items(
        self,
        planned_items: List[PlannedItem]
    ) -> tuple:
        """Create items in ERPNext."""
        created = []
        reused = []
        
        for item in planned_items:
            if item.already_exists:
                reused.append(item.item_code)
            else:
                self.erpnext.create_item(
                    item_code=item.item_code,
                    item_name=item.item_name,
                    item_group=item.item_group,
                    stock_uom=item.stock_uom
                )
                created.append(item.item_code)
        
        return created, reused
    
    def _create_boms(
        self,
        planned_boms: List[PlannedBOM]
    ) -> tuple:
        """Create BOMs in ERPNext."""
        created = []
        reused = []
        
        for bom in planned_boms:
            if bom.already_exists:
                reused.append(bom.item_code)
            else:
                result = self.erpnext.create_bom(
                    item_code=bom.item_code,
                    items=bom.bom_items,
                    operations=bom.operations,
                    is_default=1
                )
                
                # Set as default
                if result and result.get("name"):
                    self.erpnext.set_default_bom(bom.item_code, result["name"])
                
                created.append(bom.item_code)
        
        return created, reused


def create_engine(
    templates_dir: Optional[str] = None,
    rules_file: Optional[str] = None,
    company: Optional[str] = None
) -> AgentCoreEngine:
    """
    Factory function to create an AgentCoreEngine instance.
    
    Args:
        templates_dir: Path to templates directory
        rules_file: Path to business_rules.json
        company: Company name
        
    Returns:
        Configured AgentCoreEngine
    """
    return AgentCoreEngine(
        templates_dir=templates_dir,
        rules_file=rules_file,
        company=company
    )
