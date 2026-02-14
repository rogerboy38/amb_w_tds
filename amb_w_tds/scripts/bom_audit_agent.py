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

EXPECTED_HIERARCHY = {
    "semi_finished": {
        "0301": {"name": "Permeado Powder", "parent": "0227-PERMEADO", "type": "Semi-Finished"},
        "0302": {"name": "Retenido Powder", "parent": "0227-RETENIDO", "type": "Semi-Finished"},
        "0303": {"name": "Normal Powder", "parent": "0227-NORMAL", "type": "Semi-Finished"},
    },
    "specialized_mixes": {
        "0304": {"name": "90% Aloe / 10% Goma BB", "parents": ["0301"], "goma_bb": 0.1, "type": "Finished"},
        "0305": {"name": "Permeado NMT 3%PS", "parents": ["0301"], "type": "Finished"},
        "0306": {"name": "70% Aloe / 30% Goma BB", "parents": ["0301"], "goma_bb": 0.3, "type": "Finished"},
    },
    "standard_variants": {
        f"0{i}": {"name": f"Standard Variant 0{i}", "parents": ["0301"], "type": "Finished"}
        for i in range(307, 343)
    }
}

class BOMAuditAgent:
    def __init__(self):
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "site": frappe.local.site if hasattr(frappe.local, 'site') else "unknown",
            "summary": {},
            "details": {"missing_boms": [], "flat_boms": [], "correct_hierarchy": [], "unexpected_boms": [], "inactive_boms": []},
            "recommendations": []
        }

    def run_audit(self):
        print("=" * 80)
        print("BOM HIERARCHY AUDIT - Phase 1")
        print("=" * 80)
        existing_boms = self._get_existing_boms()
        self._audit_category("semi_finished", existing_boms)
        self._audit_category("specialized_mixes", existing_boms)
        self._audit_category("standard_variants", existing_boms)
        self._generate_summary()
        self._generate_recommendations()
        return self.audit_results

    def _get_existing_boms(self):
        print("\n📊 Fetching existing BOMs from database...")
        boms = frappe.get_all("BOM", filters={"docstatus": ["<", 2]}, fields=["name", "item", "is_active", "is_default", "docstatus"])
        bom_lookup = {}
        for bom in boms:
            item = bom.get("item", "")
            if item not in bom_lookup:
                bom_lookup[item] = []
            bom_lookup[item].append(bom)
        print(f"   Found {len(boms)} total BOMs for {len(bom_lookup)} unique items")
        return bom_lookup

    def _get_bom_items(self, bom_name):
        return frappe.get_all("BOM Item", filters={"parent": bom_name}, fields=["item_code", "qty", "uom"])

    def _audit_category(self, category, existing_boms):
        expected = EXPECTED_HIERARCHY.get(category, {})
        print(f"\n🔍 Auditing {category.replace('_', ' ').title()}...")
        for item_code, spec in expected.items():
            self._audit_single_item(item_code, spec, existing_boms)

    def _audit_single_item(self, item_code, spec, existing_boms):
        boms = existing_boms.get(item_code, [])
        if not boms:
            self.audit_results["details"]["missing_boms"].append({"item_code": item_code, "expected_name": spec.get("name", "")})
            print(f"   ❌ {item_code}: NO BOM EXISTS")
            return
        active_bom = next((b for b in boms if b.get("is_active") and b.get("is_default")), boms[0])
        if not active_bom.get("is_active"):
            self.audit_results["details"]["inactive_boms"].append({"item_code": item_code, "bom_name": active_bom.get("name")})
            print(f"   ⚠️  {item_code}: BOM exists but INACTIVE")
            return
        bom_items = self._get_bom_items(active_bom.get("name"))
        item_codes_in_bom = [i.get("item_code") for i in bom_items]
        expected_parents = spec.get("parents", [spec.get("parent", "")] if spec.get("parent") else [])
        found_parents = [p for p in expected_parents if p in item_codes_in_bom]
        if found_parents:
            self.audit_results["details"]["correct_hierarchy"].append({"item_code": item_code, "bom_name": active_bom.get("name"), "found_parents": found_parents})
            print(f"   ✅ {item_code}: Correct hierarchy (parents: {found_parents})")
        else:
            self.audit_results["details"]["flat_boms"].append({"item_code": item_code, "bom_name": active_bom.get("name"), "expected_parents": expected_parents})
            print(f"   ⚠️  {item_code}: FLAT BOM - missing parent items {expected_parents}")

    def _generate_summary(self):
        details = self.audit_results["details"]
        total = sum(len(cat) for cat in EXPECTED_HIERARCHY.values())
        self.audit_results["summary"] = {
            "total_expected_boms": total,
            "missing_boms": len(details["missing_boms"]),
            "flat_boms": len(details["flat_boms"]),
            "correct_hierarchy": len(details["correct_hierarchy"]),
            "inactive_boms": len(details["inactive_boms"]),
            "compliance_rate": round(len(details["correct_hierarchy"]) / total * 100, 1) if total else 0
        }
        print("\n" + "=" * 80 + "\nAUDIT SUMMARY\n" + "=" * 80)
        for k, v in self.audit_results["summary"].items():
            print(f"   {k.replace('_', ' ').title()}: {v}{'%' if 'rate' in k else ''}")

    def _generate_recommendations(self):
        details = self.audit_results["details"]
        recs = []
        if details["missing_boms"]:
            recs.append({"priority": "HIGH", "action": f"Create {len(details['missing_boms'])} missing BOMs"})
        if details["flat_boms"]:
            recs.append({"priority": "MEDIUM", "action": f"Update {len(details['flat_boms'])} flat BOMs"})
        self.audit_results["recommendations"] = recs

    def save_report(self, filepath=None):
        if not filepath:
            filepath = f"/tmp/bom_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(self.audit_results, f, indent=2, default=str)
        print(f"\n📁 Report saved to: {filepath}")

def run_audit(post_to_raven=False, save_json=True):
    agent = BOMAuditAgent()
    results = agent.run_audit()
    if save_json:
        agent.save_report()
    return results

if __name__ == "__main__":
    run_audit()
