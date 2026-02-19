#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOM Repair Agent - Phase 2
Audits ALL active FG BOMs and repairs discrepancies.

Features:
- Expanded audit coverage (not just create_innovaloe_boms.py items)
- Auto-discovery of all active FG BOMs in the system
- BOM repair capabilities (create missing, fix flat, activate inactive)
- Raven channel integration

Run via: bench --site [sitename] execute amb_w_tds.scripts.bom_repair_agent.run_repair
"""

import frappe
from frappe import _
from datetime import datetime
import json


# =============================================================================
# EXPANDED EXPECTED HIERARCHY (Phase 2)
# =============================================================================

EXPECTED_HIERARCHY = {
    # Level 1: Raw Material Processing (Liquid → Powder)
    "semi_finished": {
        "0301": {"name": "Permeado Powder", "parent": "0227-PERMEADO", "type": "Semi-Finished"},
        "0302": {"name": "Retenido Powder", "parent": "0227-RETENIDO", "type": "Semi-Finished"},
        "0303": {"name": "Normal Powder", "parent": "0227-NORMAL", "type": "Semi-Finished"},
    },
    
    # Level 2: Specialized Mixes
    "specialized_mixes": {
        "0304": {"name": "90% Aloe / 10% Goma BB", "parents": ["0301"], "goma_bb": 0.1, "type": "Finished"},
        "0305": {"name": "Permeado NMT 3%PS", "parents": ["0301"], "type": "Finished"},
        "0306": {"name": "70% Aloe / 30% Goma BB", "parents": ["0301"], "goma_bb": 0.3, "type": "Finished"},
    },
    
    # Level 3: Standard Variants (0307-0342)
    "standard_variants": {
        f"0{i}": {"name": f"Standard Variant 0{i}", "parents": ["0301"], "type": "Finished"}
        for i in range(307, 343)
    },
    
    # Additional FG items discovered in system (Phase 2 expansion)
    "additional_fg": {
        "0705": {"name": "INNOVALOE ALOE VERA GEL JUICE 1:1 ORGANIC", "parents": [], "type": "Finished"},
        "0803-KOSHER-ORGANIC": {"name": "ORGANIC INNER LEAF POWDER", "parents": [], "type": "Finished"},
        "A0303": {"name": "ALOE VERA NORMAL (Dry 200x)", "parents": ["0227-NORMAL"], "type": "Finished"},
        "0300 M": {"name": "Master BOM", "parents": [], "type": "Master"},
    }
}

# Patterns to match additional items not in explicit hierarchy
ITEM_PATTERNS = [
    r"^ITEM_0227",       # CONCENTRATE 30:1 variants
    r"^0334-.*Fair.*",   # Fair Trade VLAM variants
    r"^A0303",           # ALOE VERA NORMAL variants
]


class BOMRepairAgent:
    """Agent for auditing and repairing BOM hierarchy."""
    
    def __init__(self, dry_run=True):
        """
        Initialize repair agent.
        
        Args:
            dry_run: If True, only report issues without making changes
        """
        self.dry_run = dry_run
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "site": frappe.local.site if hasattr(frappe.local, 'site') else "unknown",
            "mode": "DRY RUN" if dry_run else "LIVE REPAIR",
            "summary": {},
            "details": {
                "missing_boms": [],
                "flat_boms": [],
                "correct_hierarchy": [],
                "inactive_boms": [],
                "discovered_fg": [],  # FG items not in expected hierarchy
                "repairs_made": []
            },
            "recommendations": []
        }
        self.all_fg_items = set()
    
    def run_full_audit(self):
        """Execute comprehensive BOM audit across ALL FG items."""
        print("=" * 80)
        print("BOM REPAIR AGENT - Phase 2")
        print(f"Mode: {'DRY RUN (no changes)' if self.dry_run else 'LIVE REPAIR'}")
        print("=" * 80)
        
        # Step 1: Get all existing BOMs
        existing_boms = self._get_existing_boms()
        
        # Step 2: Discover all FG items in system
        self._discover_all_fg_items(existing_boms)
        
        # Step 3: Audit expected hierarchy items
        for category in ["semi_finished", "specialized_mixes", "standard_variants", "additional_fg"]:
            self._audit_category(category, existing_boms)
        
        # Step 4: Audit discovered FG items not in expected hierarchy
        self._audit_discovered_items(existing_boms)
        
        # Step 5: Generate summary
        self._generate_summary()
        
        # Step 6: Generate recommendations
        self._generate_recommendations()
        
        return self.audit_results
    
    def _get_existing_boms(self):
        """Fetch all existing BOMs from the database."""
        print("\n📊 Fetching existing BOMs from database...")
        
        boms = frappe.get_all(
            "BOM",
            filters={"docstatus": ["<", 2]},
            fields=[
                "name", "item", "is_active", "is_default", 
                "docstatus", "creation", "modified"
            ]
        )
        
        bom_lookup = {}
        for bom in boms:
            item = bom.get("item", "")
            if item not in bom_lookup:
                bom_lookup[item] = []
            bom_lookup[item].append(bom)
        
        print(f"   Found {len(boms)} total BOMs for {len(bom_lookup)} unique items")
        return bom_lookup
    
    def _discover_all_fg_items(self, existing_boms):
        """Discover all FG items with active BOMs in the system."""
        print("\n🔎 Discovering all FG items with active BOMs...")
        
        # Get items with active default BOMs
        active_fg = frappe.get_all(
            "BOM",
            filters={
                "is_active": 1,
                "is_default": 1,
                "docstatus": 1
            },
            fields=["item"],
            distinct=True
        )
        
        for item in active_fg:
            item_code = item.get("item", "")
            self.all_fg_items.add(item_code)
        
        print(f"   Found {len(self.all_fg_items)} items with active default BOMs")
        
        # Identify items NOT in expected hierarchy
        expected_items = set()
        for category in EXPECTED_HIERARCHY.values():
            expected_items.update(category.keys())
        
        discovered = self.all_fg_items - expected_items
        if discovered:
            print(f"   Discovered {len(discovered)} additional FG items not in expected hierarchy:")
            for item_code in sorted(discovered)[:10]:
                print(f"      - {item_code}")
                self.audit_results["details"]["discovered_fg"].append(item_code)
            if len(discovered) > 10:
                print(f"      ... +{len(discovered)-10} more")
    
    def _get_bom_items(self, bom_name):
        """Get BOM items (raw materials) for a specific BOM."""
        items = frappe.get_all(
            "BOM Item",
            filters={"parent": bom_name},
            fields=["item_code", "qty", "uom"]
        )
        return items
    
    def _audit_category(self, category, existing_boms):
        """Audit a category of expected BOMs."""
        expected = EXPECTED_HIERARCHY.get(category, {})
        category_name = category.replace("_", " ").title()
        
        print(f"\n🔍 Auditing {category_name} ({len(expected)} items)...")
        print("-" * 60)
        
        for item_code, spec in expected.items():
            self._audit_single_item(item_code, spec, existing_boms)
    
    def _audit_discovered_items(self, existing_boms):
        """Audit discovered FG items not in expected hierarchy."""
        discovered = self.audit_results["details"]["discovered_fg"]
        if not discovered:
            return
        
        print(f"\n🔍 Auditing Discovered FG Items ({len(discovered)} items)...")
        print("-" * 60)
        
        for item_code in discovered:
            # Create a generic spec for discovered items
            spec = {
                "name": item_code,
                "parents": [],  # Unknown parents
                "type": "Discovered"
            }
            self._audit_single_item(item_code, spec, existing_boms, is_discovered=True)
    
    def _audit_single_item(self, item_code, spec, existing_boms, is_discovered=False):
        """Audit a single item against expected hierarchy."""
        boms = existing_boms.get(item_code, [])
        
        if not boms:
            if not is_discovered:  # Only report missing for expected items
                self.audit_results["details"]["missing_boms"].append({
                    "item_code": item_code,
                    "expected_name": spec.get("name", ""),
                    "expected_type": spec.get("type", ""),
                    "expected_parents": spec.get("parents", [spec.get("parent", "")])
                })
                print(f"   ❌ {item_code}: NO BOM EXISTS")
            return
        
        # Get the active/default BOM
        active_bom = next(
            (b for b in boms if b.get("is_active") and b.get("is_default")),
            next((b for b in boms if b.get("is_active")), boms[0])
        )
        
        # Check if BOM is inactive
        if not active_bom.get("is_active"):
            self.audit_results["details"]["inactive_boms"].append({
                "item_code": item_code,
                "bom_name": active_bom.get("name"),
                "expected_name": spec.get("name", ""),
                "docstatus": active_bom.get("docstatus")
            })
            print(f"   ⚠️  {item_code}: BOM exists but INACTIVE ({active_bom.get('name')})")
            return
        
        # Get BOM items and check hierarchy
        bom_items = self._get_bom_items(active_bom.get("name"))
        item_codes_in_bom = [i.get("item_code") for i in bom_items]
        
        # Determine expected parents
        expected_parents = spec.get("parents", [])
        if not expected_parents and spec.get("parent"):
            expected_parents = [spec.get("parent")]
        
        # For discovered items or items with no expected parents, just report structure
        if is_discovered or not expected_parents:
            print(f"   📋 {item_code}: Active BOM ({active_bom.get('name')}) with {len(bom_items)} items")
            return
        
        # Check if BOM has proper hierarchy
        has_hierarchy = False
        found_parents = []
        
        for expected_parent in expected_parents:
            if expected_parent in item_codes_in_bom:
                has_hierarchy = True
                found_parents.append(expected_parent)
        
        if has_hierarchy:
            self.audit_results["details"]["correct_hierarchy"].append({
                "item_code": item_code,
                "bom_name": active_bom.get("name"),
                "expected_name": spec.get("name", ""),
                "found_parents": found_parents,
                "all_items": item_codes_in_bom
            })
            print(f"   ✅ {item_code}: Correct hierarchy (parents: {found_parents})")
        else:
            self.audit_results["details"]["flat_boms"].append({
                "item_code": item_code,
                "bom_name": active_bom.get("name"),
                "expected_name": spec.get("name", ""),
                "expected_parents": expected_parents,
                "actual_items": item_codes_in_bom
            })
            print(f"   ⚠️  {item_code}: FLAT BOM - missing parent items {expected_parents}")
            print(f"      Current items: {item_codes_in_bom[:5]}{'...' if len(item_codes_in_bom) > 5 else ''}")
    
    def _generate_summary(self):
        """Generate audit summary statistics."""
        details = self.audit_results["details"]
        
        total_expected = sum(len(cat) for cat in EXPECTED_HIERARCHY.values())
        total_audited = total_expected + len(details["discovered_fg"])
        
        self.audit_results["summary"] = {
            "total_expected_boms": total_expected,
            "total_audited": total_audited,
            "discovered_fg_items": len(details["discovered_fg"]),
            "missing_boms": len(details["missing_boms"]),
            "flat_boms": len(details["flat_boms"]),
            "correct_hierarchy": len(details["correct_hierarchy"]),
            "inactive_boms": len(details["inactive_boms"]),
            "compliance_rate": round(
                len(details["correct_hierarchy"]) / total_expected * 100, 1
            ) if total_expected > 0 else 0
        }
        
        print("\n" + "=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)
        for key, value in self.audit_results["summary"].items():
            label = key.replace("_", " ").title()
            suffix = "%" if "rate" in key else ""
            print(f"   {label}: {value}{suffix}")
    
    def _generate_recommendations(self):
        """Generate actionable recommendations based on audit results."""
        details = self.audit_results["details"]
        recommendations = []
        
        if details["missing_boms"]:
            recommendations.append({
                "priority": "HIGH",
                "category": "Missing BOMs",
                "action": f"Create {len(details['missing_boms'])} missing BOMs",
                "items": [b["item_code"] for b in details["missing_boms"]],
            })
        
        if details["flat_boms"]:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Flat BOMs",
                "action": f"Update {len(details['flat_boms'])} BOMs to include proper parent items",
                "items": [b["item_code"] for b in details["flat_boms"]],
            })
        
        if details["inactive_boms"]:
            recommendations.append({
                "priority": "LOW",
                "category": "Inactive BOMs",
                "action": f"Review and activate {len(details['inactive_boms'])} inactive BOMs",
                "items": [b["item_code"] for b in details["inactive_boms"]]
            })
        
        self.audit_results["recommendations"] = recommendations
        
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        for rec in recommendations:
            print(f"\n   [{rec['priority']}] {rec['category']}")
            print(f"   Action: {rec['action']}")
            items = rec.get('items', [])
            if len(items) <= 10:
                print(f"   Items: {', '.join(items)}")
            else:
                print(f"   Items: {', '.join(items[:5])}... (+{len(items)-5} more)")
    
    # =========================================================================
    # REPAIR METHODS (Phase 2)
    # =========================================================================
    
    def repair_missing_boms(self):
        """Create missing BOMs based on expected hierarchy."""
        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes will be made")
            return []
        
        missing = self.audit_results["details"]["missing_boms"]
        if not missing:
            print("\n✅ No missing BOMs to create")
            return []
        
        print(f"\n🔧 Creating {len(missing)} missing BOMs...")
        created = []
        
        for item in missing:
            item_code = item["item_code"]
            expected_parents = item.get("expected_parents", [])
            
            try:
                bom = self._create_bom_from_spec(item_code, expected_parents)
                if bom:
                    created.append({
                        "item_code": item_code,
                        "bom_name": bom.name,
                        "action": "CREATED"
                    })
                    print(f"   ✅ Created: {bom.name} for {item_code}")
            except Exception as e:
                print(f"   ❌ Failed to create BOM for {item_code}: {str(e)}")
        
        self.audit_results["details"]["repairs_made"].extend(created)
        return created
    
    def repair_flat_boms(self):
        """Update flat BOMs to include proper parent items."""
        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes will be made")
            return []
        
        flat_boms = self.audit_results["details"]["flat_boms"]
        if not flat_boms:
            print("\n✅ No flat BOMs to repair")
            return []
        
        print(f"\n🔧 Repairing {len(flat_boms)} flat BOMs...")
        repaired = []
        
        for item in flat_boms:
            item_code = item["item_code"]
            bom_name = item["bom_name"]
            expected_parents = item.get("expected_parents", [])
            
            try:
                success = self._add_parent_to_bom(bom_name, expected_parents)
                if success:
                    repaired.append({
                        "item_code": item_code,
                        "bom_name": bom_name,
                        "action": "UPDATED",
                        "added_parents": expected_parents
                    })
                    print(f"   ✅ Updated: {bom_name} - added parents {expected_parents}")
            except Exception as e:
                print(f"   ❌ Failed to update {bom_name}: {str(e)}")
        
        self.audit_results["details"]["repairs_made"].extend(repaired)
        return repaired
    
    def activate_inactive_boms(self):
        """Activate inactive BOMs."""
        if self.dry_run:
            print("\n⚠️  DRY RUN - No changes will be made")
            return []
        
        inactive = self.audit_results["details"]["inactive_boms"]
        if not inactive:
            print("\n✅ No inactive BOMs to activate")
            return []
        
        print(f"\n🔧 Activating {len(inactive)} inactive BOMs...")
        activated = []
        
        for item in inactive:
            bom_name = item["bom_name"]
            docstatus = item.get("docstatus", 0)
            
            try:
                bom = frappe.get_doc("BOM", bom_name)
                
                # If draft, submit first
                if bom.docstatus == 0:
                    bom.submit()
                
                # Activate
                bom.is_active = 1
                bom.is_default = 1
                bom.save()
                frappe.db.commit()
                
                activated.append({
                    "item_code": item["item_code"],
                    "bom_name": bom_name,
                    "action": "ACTIVATED"
                })
                print(f"   ✅ Activated: {bom_name}")
                
            except Exception as e:
                print(f"   ❌ Failed to activate {bom_name}: {str(e)}")
        
        self.audit_results["details"]["repairs_made"].extend(activated)
        return activated
    
    def _create_bom_from_spec(self, item_code, expected_parents):
        """Create a new BOM based on item specification."""
        # Get item details
        item = frappe.get_doc("Item", item_code)
        
        # Build BOM items list
        bom_items = []
        
        # Add parent items (semi-finished goods)
        for parent_code in expected_parents:
            if frappe.db.exists("Item", parent_code):
                bom_items.append({
                    "item_code": parent_code,
                    "qty": 1.0,
                    "uom": frappe.db.get_value("Item", parent_code, "stock_uom") or "Kg"
                })
        
        if not bom_items:
            print(f"   ⚠️  No valid parent items for {item_code}")
            return None
        
        # Create BOM
        bom = frappe.get_doc({
            "doctype": "BOM",
            "item": item_code,
            "quantity": 1.0,
            "is_active": 1,
            "is_default": 1,
            "items": bom_items
        })
        
        bom.insert()
        bom.submit()
        frappe.db.commit()
        
        return bom
    
    def _add_parent_to_bom(self, bom_name, expected_parents):
        """Add parent items to an existing flat BOM."""
        bom = frappe.get_doc("BOM", bom_name)
        
        # Cancel if submitted
        if bom.docstatus == 1:
            bom.cancel()
            # Create new version
            bom = frappe.copy_doc(bom)
            bom.docstatus = 0
        
        # Add parent items
        existing_items = [i.item_code for i in bom.items]
        
        for parent_code in expected_parents:
            if parent_code not in existing_items and frappe.db.exists("Item", parent_code):
                bom.append("items", {
                    "item_code": parent_code,
                    "qty": 1.0,
                    "uom": frappe.db.get_value("Item", parent_code, "stock_uom") or "Kg"
                })
        
        bom.save()
        bom.submit()
        
        # Set as default
        bom.is_active = 1
        bom.is_default = 1
        bom.save()
        frappe.db.commit()
        
        return True
    
    # =========================================================================
    # RAVEN INTEGRATION
    # =========================================================================
    
    def post_to_raven(self, channel_name="bom-hierarchy-audit"):
        """Post audit results to Raven channel."""
        try:
            channel = frappe.db.get_value(
                "Raven Channel",
                {"channel_name": channel_name},
                "name"
            )
            
            if not channel:
                print(f"\n⚠️  Raven channel '{channel_name}' not found")
                return False
            
            message = self._format_raven_message()
            
            raven_msg = frappe.get_doc({
                "doctype": "Raven Message",
                "channel_id": channel,
                "message_type": "Text",
                "text": message,
                "json": json.dumps(self.audit_results)
            })
            raven_msg.insert(ignore_permissions=True)
            frappe.db.commit()
            
            print(f"\n✅ Posted to Raven: #{channel_name}")
            return True
            
        except Exception as e:
            print(f"\n❌ Raven error: {str(e)}")
            return False
    
    def _format_raven_message(self):
        """Format audit results for Raven."""
        s = self.audit_results["summary"]
        d = self.audit_results["details"]
        
        message = f"""## 📊 BOM Repair Agent Report

**Mode:** {self.audit_results['mode']}
**Time:** {self.audit_results['timestamp']}

### Summary
| Metric | Value |
|--------|-------|
| Total Audited | {s.get('total_audited', 0)} |
| Discovered FG Items | {s.get('discovered_fg_items', 0)} |
| ✅ Correct | {s['correct_hierarchy']} |
| ⚠️ Flat BOMs | {s['flat_boms']} |
| ❌ Missing | {s['missing_boms']} |
| 💤 Inactive | {s['inactive_boms']} |
| **Compliance** | **{s['compliance_rate']}%** |

"""
        
        if d.get("repairs_made"):
            message += f"\n### 🔧 Repairs Made ({len(d['repairs_made'])})\n"
            for r in d["repairs_made"][:5]:
                message += f"- {r['item_code']}: {r['action']}\n"
            if len(d["repairs_made"]) > 5:
                message += f"- ... +{len(d['repairs_made'])-5} more\n"
        
        if d.get("discovered_fg"):
            message += f"\n### 🔎 Discovered FG Items ({len(d['discovered_fg'])})\n"
            message += f"`{', '.join(d['discovered_fg'][:10])}`"
            if len(d["discovered_fg"]) > 10:
                message += f" +{len(d['discovered_fg'])-10} more"
        
        return message
    
    def save_report(self, filepath=None):
        """Save audit results to JSON file."""
        if not filepath:
            filepath = f"/tmp/bom_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.audit_results, f, indent=2, default=str)
        
        print(f"\n📁 Report saved: {filepath}")
        return filepath


# =============================================================================
# ENTRY POINTS
# =============================================================================

def run_audit(post_to_raven=True, save_json=True):
    """
    Run expanded audit only (no repairs).
    
    Usage:
        bench execute amb_w_tds.scripts.bom_repair_agent.run_audit
    """
    agent = BOMRepairAgent(dry_run=True)
    results = agent.run_full_audit()
    
    if save_json:
        agent.save_report()
    
    if post_to_raven:
        agent.post_to_raven()
    
    return results


def run_repair(dry_run=True, post_to_raven=True, save_json=True):
    """
    Run audit and repair (dry_run=True by default for safety).
    
    Usage:
        # Dry run (default - safe)
        bench execute amb_w_tds.scripts.bom_repair_agent.run_repair
        
        # Live repair (makes changes)
        bench execute amb_w_tds.scripts.bom_repair_agent.run_repair --kwargs '{"dry_run": false}'
    """
    agent = BOMRepairAgent(dry_run=dry_run)
    
    # Run audit first
    results = agent.run_full_audit()
    
    if not dry_run:
        print("\n" + "=" * 80)
        print("EXECUTING REPAIRS")
        print("=" * 80)
        
        # Execute repairs in order
        agent.repair_missing_boms()
        agent.repair_flat_boms()
        agent.activate_inactive_boms()
    
    if save_json:
        agent.save_report()
    
    if post_to_raven:
        agent.post_to_raven()
    
    return results


if __name__ == "__main__":
    run_audit()
