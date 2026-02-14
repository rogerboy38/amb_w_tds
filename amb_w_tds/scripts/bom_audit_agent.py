#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOM Hierarchy Audit Agent - Phase 1
Analyzes current BOMs against the expected logical hierarchy.

Run via: bench --site [sitename] execute amb_w_tds.scripts.bom_audit_agent.run_audit
"""

import frappe
from frappe import _
from datetime import datetime
import json


# =============================================================================
# EXPECTED BOM HIERARCHY (from create_innovaloe_boms.py)
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
    }
}


class BOMAuditAgent:
    """Agent for auditing BOM hierarchy against expected structure."""
    
    def __init__(self):
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "site": frappe.local.site if hasattr(frappe.local, 'site') else "unknown",
            "summary": {},
            "details": {
                "missing_boms": [],
                "flat_boms": [],
                "correct_hierarchy": [],
                "unexpected_boms": [],
                "inactive_boms": []
            },
            "recommendations": []
        }
    
    def run_audit(self):
        """Execute full BOM hierarchy audit."""
        print("=" * 80)
        print("BOM HIERARCHY AUDIT - Phase 1")
        print("=" * 80)
        print(f"Timestamp: {self.audit_results['timestamp']}")
        print(f"Site: {self.audit_results['site']}")
        print("=" * 80)
        
        # Step 1: Get all existing BOMs
        existing_boms = self._get_existing_boms()
        
        # Step 2: Audit semi-finished products
        self._audit_category("semi_finished", existing_boms)
        
        # Step 3: Audit specialized mixes
        self._audit_category("specialized_mixes", existing_boms)
        
        # Step 4: Audit standard variants
        self._audit_category("standard_variants", existing_boms)
        
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
            filters={"docstatus": ["<", 2]},  # Not cancelled
            fields=[
                "name", "item", "is_active", "is_default", 
                "docstatus", "creation", "modified"
            ]
        )
        
        # Create lookup dict by item code
        bom_lookup = {}
        for bom in boms:
            item = bom.get("item", "")
            if item not in bom_lookup:
                bom_lookup[item] = []
            bom_lookup[item].append(bom)
        
        print(f"   Found {len(boms)} total BOMs for {len(bom_lookup)} unique items")
        return bom_lookup
    
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
        
        print(f"\n🔍 Auditing {category_name}...")
        print("-" * 60)
        
        for item_code, spec in expected.items():
            self._audit_single_item(item_code, spec, existing_boms)
    
    def _audit_single_item(self, item_code, spec, existing_boms):
        """Audit a single item against expected hierarchy."""
        boms = existing_boms.get(item_code, [])
        
        if not boms:
            # No BOM exists
            self.audit_results["details"]["missing_boms"].append({
                "item_code": item_code,
                "expected_name": spec.get("name", ""),
                "expected_type": spec.get("type", ""),
                "expected_parents": spec.get("parents", [spec.get("parent", "")])
            })
            print(f"   ❌ {item_code}: NO BOM EXISTS")
            return
        
        # Get the active/default BOM
        active_bom = next((b for b in boms if b.get("is_active") and b.get("is_default")), boms[0])
        
        # Check if BOM is inactive
        if not active_bom.get("is_active"):
            self.audit_results["details"]["inactive_boms"].append({
                "item_code": item_code,
                "bom_name": active_bom.get("name"),
                "expected_name": spec.get("name", "")
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
        
        # Check if BOM has proper hierarchy (contains expected parent items)
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
    
    def _generate_summary(self):
        """Generate audit summary statistics."""
        details = self.audit_results["details"]
        
        total_expected = sum(len(cat) for cat in EXPECTED_HIERARCHY.values())
        
        self.audit_results["summary"] = {
            "total_expected_boms": total_expected,
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
            print(f"   {label}: {value}{'%' if 'rate' in key else ''}")
    
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
                "script": "Run create_innovaloe_boms.py to create missing BOMs"
            })
        
        if details["flat_boms"]:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Flat BOMs",
                "action": f"Update {len(details['flat_boms'])} BOMs to include proper parent items",
                "items": [b["item_code"] for b in details["flat_boms"]],
                "details": "These BOMs exist but don't reference their parent semi-finished items"
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
            if len(rec.get('items', [])) <= 10:
                print(f"   Items: {', '.join(rec.get('items', []))}")
            else:
                print(f"   Items: {', '.join(rec.get('items', [])[:5])}... (+{len(rec['items'])-5} more)")
    
    def post_to_raven(self, channel_name="bom-hierarchy-audit"):
        """Post audit results to Raven channel."""
        try:
            # Check if channel exists, create if not
            channel = self._get_or_create_channel(channel_name)
            
            if not channel:
                print(f"\n⚠️  Could not post to Raven: Channel '{channel_name}' not available")
                return False
            
            # Format message
            summary = self.audit_results["summary"]
            message = self._format_raven_message()
            
            # Create Raven Message
            raven_msg = frappe.get_doc({
                "doctype": "Raven Message",
                "channel_id": channel,
                "message_type": "Text",
                "text": message,
                "json": json.dumps(self.audit_results)
            })
            raven_msg.insert(ignore_permissions=True)
            frappe.db.commit()
            
            print(f"\n✅ Posted audit results to Raven channel: #{channel_name}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error posting to Raven: {str(e)}")
            frappe.log_error(f"BOM Audit Raven Error: {str(e)}")
            return False
    
    def _get_or_create_channel(self, channel_name):
        """Get existing Raven channel or return None."""
        try:
            channel = frappe.db.get_value(
                "Raven Channel",
                {"channel_name": channel_name},
                "name"
            )
            return channel
        except Exception:
            return None
    
    def _format_raven_message(self):
        """Format audit results as a Raven message."""
        summary = self.audit_results["summary"]
        details = self.audit_results["details"]
        
        message = f"""## 📊 BOM Hierarchy Audit Report

**Timestamp:** {self.audit_results['timestamp']}
**Site:** {self.audit_results['site']}

### Summary
| Metric | Value |
|--------|-------|
| Total Expected BOMs | {summary['total_expected_boms']} |
| ✅ Correct Hierarchy | {summary['correct_hierarchy']} |
| ⚠️ Flat BOMs | {summary['flat_boms']} |
| ❌ Missing BOMs | {summary['missing_boms']} |
| 💤 Inactive BOMs | {summary['inactive_boms']} |
| **Compliance Rate** | **{summary['compliance_rate']}%** |

"""
        
        if details["missing_boms"]:
            items = [b["item_code"] for b in details["missing_boms"][:10]]
            message += f"\n### ❌ Missing BOMs ({len(details['missing_boms'])})\n"
            message += f"`{', '.join(items)}`"
            if len(details["missing_boms"]) > 10:
                message += f" ... +{len(details['missing_boms'])-10} more"
        
        if details["flat_boms"]:
            items = [b["item_code"] for b in details["flat_boms"][:10]]
            message += f"\n\n### ⚠️ Flat BOMs (need hierarchy update) ({len(details['flat_boms'])})\n"
            message += f"`{', '.join(items)}`"
            if len(details["flat_boms"]) > 10:
                message += f" ... +{len(details['flat_boms'])-10} more"
        
        if self.audit_results["recommendations"]:
            message += "\n\n### 📋 Recommendations\n"
            for rec in self.audit_results["recommendations"]:
                message += f"- **[{rec['priority']}]** {rec['action']}\n"
        
        return message
    
    def save_report(self, filepath=None):
        """Save audit results to JSON file."""
        if not filepath:
            filepath = f"/tmp/bom_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.audit_results, f, indent=2, default=str)
        
        print(f"\n📁 Audit report saved to: {filepath}")
        return filepath


def run_audit(post_to_raven=True, save_json=True):
    """
    Main entry point for BOM audit.
    
    Usage:
        bench --site [sitename] execute amb_w_tds.scripts.bom_audit_agent.run_audit
    
    Args:
        post_to_raven: Whether to post results to Raven channel
        save_json: Whether to save results to JSON file
    """
    agent = BOMAuditAgent()
    results = agent.run_audit()
    
    if save_json:
        agent.save_report()
    
    if post_to_raven:
        agent.post_to_raven()
    
    return results


# Allow direct execution for testing
if __name__ == "__main__":
    run_audit()
