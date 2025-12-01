#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INNOVALOE BOM Creation Script
Creates BOMs for products 0301-0342
Run via: bench --site [sitename] execute create_innovaloe_boms.py
"""

import frappe
from frappe import _
from datetime import datetime

def create_bom(item_code, bom_data):
    """Create a single BOM with error handling"""
    try:
        # Check if BOM already exists
        existing = frappe.db.exists("BOM", {"item": item_code, "docstatus": ["<", 2]})
        if existing:
            print(f"⚠️  BOM already exists for {item_code}: {existing}")
            return existing
        
        # Create new BOM
        bom = frappe.get_doc({
            "doctype": "BOM",
            "item": item_code,
            "company": bom_data.get("company", "AMB-Wellness"),
            "quantity": bom_data.get("quantity", 1.0),
            "uom": bom_data.get("uom", "Kg"),
            "is_active": 1,
            "is_default": 1,
            "with_operations": bom_data.get("with_operations", 1),
            "allow_alternative_item": bom_data.get("allow_alternative_item", 0),
            "rm_cost_as_per": "Valuation Rate",
            "currency": "MXN",
            "items": bom_data.get("items", []),
            "operations": bom_data.get("operations", []),
            "scrap_items": bom_data.get("scrap_items", [])
        })
        
        bom.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Created BOM for {item_code}: {bom.name}")
        return bom.name
        
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Error creating BOM for {item_code}: {str(e)}")
        frappe.log_error(f"BOM Creation Error: {item_code}\n{str(e)}")
        return None


def create_semi_finished_powder_bom(item_code, liquid_source, powder_type):
    """
    Create BOM for semi-finished powders (0301, 0302, 0303)
    
    Args:
        item_code: Product code (e.g., "0301")
        liquid_source: Liquid concentrate source (e.g., "0227-PERMEADO")
        powder_type: Type name for logging (e.g., "Permeado")
    """
    
    bom_data = {
        "company": "AMB-Wellness",
        "quantity": 1.0,  # 1 Kg output
        "uom": "Kg",
        "with_operations": 1,
        "allow_alternative_item": 0,  # Semi-finished are pure, no alternatives
        
        # Raw materials
        "items": [
            {
                "item_code": liquid_source,
                "qty": 10.0,  # Assumption: 10 Kg liquid → 1 Kg powder (10:1 ratio)
                "uom": "Kg",
                "rate": 0,  # Will be fetched from valuation
                "stock_uom": "Kg"
            },
            {
                "item_code": "ELECTRIC",
                "qty": 50,  # kWh for spray drying
                "uom": "kWh",
                "rate": 324.14,
                "stock_uom": "kWh"
            },
            {
                "item_code": "GAS",
                "qty": 20,  # Gigajoules for drying
                "uom": "Gigajoule",
                "rate": 360.55,
                "stock_uom": "Gigajoule"
            },
            {
                "item_code": "LABOR",
                "qty": 5,  # Hours
                "uom": "Hour",
                "rate": 6242.06,
                "stock_uom": "Hour"
            },
            # Packaging - 25KG Drum (default for semi-finished)
            {
                "item_code": "E003",
                "qty": 0.04,  # 1/25 of a drum per Kg
                "uom": "Piece",
                "rate": 259.00,
                "stock_uom": "Piece"
            }
        ],
        
        # Operations
        "operations": [
            {
                "operation": "P-3-OP-420-Secado Spray Dry",
                "workstation": "WS-Secado",
                "time_in_mins": 240,
                "operating_cost": 830.00,
                "description": "Spray drying liquid to powder"
            },
            {
                "operation": "P-3-OP-030-MOLIENDA",
                "workstation": "P-3-OP-030-MOLIENDA",
                "time_in_mins": 60,
                "operating_cost": 200.50,
                "description": "Milling to desired particle size"
            }
        ],
        
        # Scrap/Co-products
        "scrap_items": [
            {
                "item_code": "0304",  # Raspaduras
                "qty": 0.03,  # 3% as puntas/colas
                "stock_uom": "Kg",
                "rate": 0  # Will be calculated
            }
        ]
    }
    
    return create_bom(item_code, bom_data)


def create_final_product_bom(item_code, formulation):
    """
    Create BOM for final products (0305-0342)
    
    Args:
        item_code: Product code (e.g., "0307")
        formulation: Dict with ingredient specifications
    """
    
    items = []
    
    # Add powder inputs (with alternatives enabled)
    for powder in formulation.get("powders", []):
        items.append({
            "item_code": powder["code"],
            "qty": powder["qty"],
            "uom": "Kg",
            "rate": 0,
            "stock_uom": "Kg",
            "allow_alternative_item": 1  # Enable substitution
        })
    
    # Add Goma BB if needed
    if formulation.get("goma_bb_qty", 0) > 0:
        items.append({
            "item_code": "GOMA-BB",
            "qty": formulation["goma_bb_qty"],
            "uom": "Kg",
            "rate": 0,
            "stock_uom": "Kg"
        })
    
    # Add packaging
    pkg = formulation.get("packaging", "E003")  # Default 25KG drum
    pkg_qty = formulation.get("packaging_qty", 0.04)
    items.append({
        "item_code": pkg,
        "qty": pkg_qty,
        "uom": "Piece",
        "rate": 0,
        "stock_uom": "Piece"
    })
    
    bom_data = {
        "company": "AMB-Wellness",
        "quantity": 1.0,
        "uom": "Kg",
        "with_operations": 1,
        "allow_alternative_item": 1,  # Allow alternatives for final products
        "items": items,
        "operations": [
            {
                "operation": "Mixing",
                "workstation": "WS-Mixing",
                "time_in_mins": 30,
                "operating_cost": 100.00,
                "description": "Mix powders and additives"
            },
            {
                "operation": "Packaging",
                "workstation": "WS-Packaging",
                "time_in_mins": 15,
                "operating_cost": 50.00,
                "description": "Final packaging"
            }
        ]
    }
    
    return create_bom(item_code, bom_data)


def main():
    """Main execution function"""
    
    print("=" * 80)
    print("INNOVALOE BOM CREATION - STARTING")
    print("=" * 80)
    print(f"Timestamp: {datetime.now()}")
    print(f"Site: {frappe.local.site}")
    print("=" * 80)
    
    created_boms = []
    failed_boms = []
    
    # ========================================================================
    # PHASE 1: SEMI-FINISHED POWDERS (0301, 0302, 0303)
    # ========================================================================
    
    print("\n📦 PHASE 1: Creating Semi-Finished Powder BOMs")
    print("-" * 80)
    
    semi_finished = [
        ("0301", "0227-PERMEADO", "Permeado Powder"),
        ("0302", "0227-RETENIDO", "Retenido Powder"),
        ("0303", "0227-NORMAL", "Normal Powder")
    ]
    
    for item_code, liquid_source, powder_type in semi_finished:
        print(f"\nCreating BOM for {item_code} ({powder_type})...")
        bom_name = create_semi_finished_powder_bom(item_code, liquid_source, powder_type)
        
        if bom_name:
            created_boms.append(bom_name)
        else:
            failed_boms.append(item_code)
    
    # ========================================================================
    # PHASE 2: SPECIALIZED MIXES (0304, 0305, 0306)
    # ========================================================================
    
    print("\n📦 PHASE 2: Creating Specialized Mix BOMs")
    print("-" * 80)
    
    # 0304: Permeado 90% Aloe / 10% Goma BB
    print("\nCreating BOM for 0304 (90% Aloe / 10% Goma BB)...")
    bom_name = create_final_product_bom("0304", {
        "powders": [
            {"code": "0301", "qty": 0.9}  # 90% Permeado
        ],
        "goma_bb_qty": 0.1,  # 10% Goma BB
        "packaging": "E003",
        "packaging_qty": 0.04
    })
    if bom_name:
        created_boms.append(bom_name)
    else:
        failed_boms.append("0304")
    
    # 0305: Permeado NMT 3%PS
    print("\nCreating BOM for 0305 (Permeado NMT 3%PS)...")
    bom_name = create_final_product_bom("0305", {
        "powders": [
            {"code": "0301", "qty": 1.0}  # 100% Permeado
        ],
        "packaging": "E003",
        "packaging_qty": 0.04
    })
    if bom_name:
        created_boms.append(bom_name)
    else:
        failed_boms.append("0305")
    
    # 0306: Permeado 70% Aloe / 30% Goma BB
    print("\nCreating BOM for 0306 (70% Aloe / 30% Goma BB)...")
    bom_name = create_final_product_bom("0306", {
        "powders": [
            {"code": "0301", "qty": 0.7}  # 70% Permeado
        ],
        "goma_bb_qty": 0.3,  # 30% Goma BB
        "packaging": "E003",
        "packaging_qty": 0.04
    })
    if bom_name:
        created_boms.append(bom_name)
    else:
        failed_boms.append("0306")
    
    # ========================================================================
    # PHASE 3: STANDARD VARIANTS (0307-0342)
    # ========================================================================
    
    print("\n📦 PHASE 3: Creating Standard Variant BOMs (0307-0342)")
    print("-" * 80)
    print("ℹ️  All variants use same base formulation")
    print("ℹ️  Differences tracked via Item Attributes (HAD/AS/PS/WLM/COSMOS/IASC)")
    
    for item_code in range(307, 343):  # 0307 to 0342
        code = f"0{item_code}"
        print(f"\nCreating BOM for {code}...")
        
        bom_name = create_final_product_bom(code, {
            "powders": [
                {"code": "0301", "qty": 1.0}  # Base: 100% Permeado (can substitute)
            ],
            "packaging": "E003",
            "packaging_qty": 0.04
        })
        
        if bom_name:
            created_boms.append(bom_name)
        else:
            failed_boms.append(code)
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("INNOVALOE BOM CREATION - COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully created: {len(created_boms)"}
