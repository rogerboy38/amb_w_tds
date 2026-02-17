"""
BOM Status Manager - Intelligent BOM Health Monitoring System
Phase 4 Implementation

This module provides proactive BOM health monitoring with:
1. HEALTH SCANNER - Detect structural issues before they cause problems
2. STATUS INSIGHTS - Understand BOM lifecycle and relationships
3. REPAIR ADVISOR - Suggest fixes with impact analysis

Usage:
    bench execute amb_w_tds.scripts.bom_status_manager.run_health_check
    bench execute amb_w_tds.scripts.bom_status_manager.run_health_check --kwargs '{"verbose": true}'
    bench execute amb_w_tds.scripts.bom_status_manager.get_bom_insights --kwargs '{"bom_name": "BOM-XXXX-XXX"}'
"""

import frappe
from frappe.utils import now_datetime, getdate
from collections import defaultdict
import json


# ============================================================================
# HELPER FUNCTIONS (Reused patterns from existing scripts)
# ============================================================================

def get_default_company():
    """Smart company detection - reused from bom_fixer.py"""
    company = None
    
    # Try user default
    if frappe.session.user:
        company = frappe.db.get_value("User Permission", {
            "user": frappe.session.user,
            "allow": "Company"
        }, "for_value")
    
    # Try global default
    if not company:
        company = frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Fallback to first company
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    
    return company


def format_currency(value):
    """Format currency values for display"""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def get_bom_status_label(docstatus, is_active, is_default):
    """Convert BOM states to human-readable labels"""
    if docstatus == 0:
        return "Draft"
    elif docstatus == 2:
        return "Cancelled"
    elif docstatus == 1:
        if is_default and is_active:
            return "Active (Default)"
        elif is_active:
            return "Active"
        else:
            return "Inactive"
    return "Unknown"


# ============================================================================
# HEALTH SCANNER - Core Detection Functions
# ============================================================================

def detect_circular_references():
    """
    Detect BOMs that reference themselves directly or indirectly.
    Returns list of problematic BOMs with circular path details.
    """
    issues = []
    
    # Get all active BOMs with their items
    boms = frappe.db.sql("""
        SELECT 
            b.name, b.item, b.is_active, b.is_default,
            bi.item_code, bi.bom_no
        FROM `tabBOM` b
        LEFT JOIN `tabBOM Item` bi ON bi.parent = b.name
        WHERE b.docstatus = 1
        ORDER BY b.name
    """, as_dict=True)
    
    # Build BOM dependency graph
    bom_graph = defaultdict(list)
    bom_items = {}
    
    for row in boms:
        bom_name = row['name']
        if bom_name not in bom_items:
            bom_items[bom_name] = row['item']
        if row['bom_no']:
            bom_graph[bom_name].append(row['bom_no'])
    
    # DFS to detect cycles
    def find_cycle(bom, visited, path):
        if bom in path:
            cycle_start = path.index(bom)
            return path[cycle_start:] + [bom]
        if bom in visited:
            return None
        
        visited.add(bom)
        path.append(bom)
        
        for child_bom in bom_graph.get(bom, []):
            cycle = find_cycle(child_bom, visited, path)
            if cycle:
                return cycle
        
        path.pop()
        return None
    
    visited = set()
    for bom_name in bom_graph:
        if bom_name not in visited:
            cycle = find_cycle(bom_name, visited, [])
            if cycle:
                issues.append({
                    'type': 'CIRCULAR_REFERENCE',
                    'severity': 'CRITICAL',
                    'bom': cycle[0],
                    'item': bom_items.get(cycle[0], 'Unknown'),
                    'cycle_path': ' → '.join(cycle),
                    'message': f"BOM {cycle[0]} has circular reference: {' → '.join(cycle)}"
                })
    
    return issues


def detect_orphaned_boms():
    """
    Detect BOMs for items that no longer exist or are disabled.
    """
    issues = []
    
    orphaned = frappe.db.sql("""
        SELECT 
            b.name, b.item, b.is_active, b.is_default,
            i.name as item_exists, i.disabled as item_disabled
        FROM `tabBOM` b
        LEFT JOIN `tabItem` i ON i.name = b.item
        WHERE b.docstatus = 1 
        AND b.is_active = 1
        AND (i.name IS NULL OR i.disabled = 1)
    """, as_dict=True)
    
    for row in orphaned:
        if row['item_exists'] is None:
            issues.append({
                'type': 'ORPHANED_BOM',
                'severity': 'HIGH',
                'bom': row['name'],
                'item': row['item'],
                'message': f"BOM {row['name']} references non-existent item {row['item']}"
            })
        elif row['item_disabled']:
            issues.append({
                'type': 'DISABLED_ITEM_BOM',
                'severity': 'MEDIUM',
                'bom': row['name'],
                'item': row['item'],
                'message': f"BOM {row['name']} is active but item {row['item']} is disabled"
            })
    
    return issues


def detect_missing_default_boms():
    """
    Detect manufactured items without a default BOM.
    """
    issues = []
    
    # Items with BOMs but no default
    no_default = frappe.db.sql("""
        SELECT 
            i.name as item,
            i.item_name,
            COUNT(b.name) as bom_count
        FROM `tabItem` i
        INNER JOIN `tabBOM` b ON b.item = i.name AND b.docstatus = 1 AND b.is_active = 1
        WHERE i.disabled = 0
        AND i.is_stock_item = 1
        GROUP BY i.name
        HAVING SUM(b.is_default) = 0
    """, as_dict=True)
    
    for row in no_default:
        issues.append({
            'type': 'NO_DEFAULT_BOM',
            'severity': 'MEDIUM',
            'item': row['item'],
            'item_name': row['item_name'],
            'bom_count': row['bom_count'],
            'message': f"Item {row['item']} has {row['bom_count']} active BOM(s) but none set as default"
        })
    
    return issues


def detect_multiple_default_boms():
    """
    Detect items with multiple default BOMs (data integrity issue).
    """
    issues = []
    
    multiple_defaults = frappe.db.sql("""
        SELECT 
            b.item,
            GROUP_CONCAT(b.name) as bom_names,
            COUNT(*) as default_count
        FROM `tabBOM` b
        WHERE b.docstatus = 1 
        AND b.is_active = 1 
        AND b.is_default = 1
        GROUP BY b.item
        HAVING COUNT(*) > 1
    """, as_dict=True)
    
    for row in multiple_defaults:
        issues.append({
            'type': 'MULTIPLE_DEFAULTS',
            'severity': 'HIGH',
            'item': row['item'],
            'bom_names': row['bom_names'],
            'count': row['default_count'],
            'message': f"Item {row['item']} has {row['default_count']} default BOMs: {row['bom_names']}"
        })
    
    return issues


def detect_inactive_default_boms():
    """
    Detect BOMs marked as default but not active.
    """
    issues = []
    
    inactive_defaults = frappe.db.sql("""
        SELECT name, item, is_active, docstatus
        FROM `tabBOM`
        WHERE is_default = 1 
        AND (is_active = 0 OR docstatus != 1)
    """, as_dict=True)
    
    for row in inactive_defaults:
        status = "inactive" if row['is_active'] == 0 else f"docstatus={row['docstatus']}"
        issues.append({
            'type': 'INACTIVE_DEFAULT',
            'severity': 'MEDIUM',
            'bom': row['name'],
            'item': row['item'],
            'message': f"BOM {row['name']} is marked as default but is {status}"
        })
    
    return issues


def detect_cost_anomalies(threshold_percent=50):
    """
    Detect BOMs with unusual cost patterns (very high or zero cost).
    """
    issues = []
    
    # Get BOMs with cost info
    boms_with_cost = frappe.db.sql("""
        SELECT 
            name, item, total_cost, is_active, is_default
        FROM `tabBOM`
        WHERE docstatus = 1 AND is_active = 1
    """, as_dict=True)
    
    # Group by item to compare costs
    item_costs = defaultdict(list)
    for bom in boms_with_cost:
        item_costs[bom['item']].append(bom)
    
    for item, boms in item_costs.items():
        costs = [b['total_cost'] for b in boms if b['total_cost'] and b['total_cost'] > 0]
        
        if not costs:
            continue
            
        avg_cost = sum(costs) / len(costs)
        
        for bom in boms:
            cost = bom['total_cost'] or 0
            
            # Zero cost detection
            if cost == 0:
                issues.append({
                    'type': 'ZERO_COST',
                    'severity': 'LOW',
                    'bom': bom['name'],
                    'item': item,
                    'cost': cost,
                    'message': f"BOM {bom['name']} has zero total cost"
                })
            # Cost anomaly detection (more than threshold_percent deviation)
            elif len(costs) > 1 and avg_cost > 0:
                deviation = abs(cost - avg_cost) / avg_cost * 100
                if deviation > threshold_percent:
                    issues.append({
                        'type': 'COST_ANOMALY',
                        'severity': 'LOW',
                        'bom': bom['name'],
                        'item': item,
                        'cost': cost,
                        'avg_cost': avg_cost,
                        'deviation': f"{deviation:.1f}%",
                        'message': f"BOM {bom['name']} cost ${cost:.2f} deviates {deviation:.1f}% from average ${avg_cost:.2f}"
                    })
    
    return issues


def detect_missing_components():
    """
    Detect BOMs referencing items that don't exist or are disabled.
    """
    issues = []
    
    missing = frappe.db.sql("""
        SELECT 
            bi.parent as bom,
            bi.item_code,
            bi.qty,
            b.item as bom_item,
            i.name as item_exists,
            i.disabled as item_disabled
        FROM `tabBOM Item` bi
        INNER JOIN `tabBOM` b ON b.name = bi.parent AND b.docstatus = 1 AND b.is_active = 1
        LEFT JOIN `tabItem` i ON i.name = bi.item_code
        WHERE i.name IS NULL OR i.disabled = 1
    """, as_dict=True)
    
    for row in missing:
        if row['item_exists'] is None:
            issues.append({
                'type': 'MISSING_COMPONENT',
                'severity': 'HIGH',
                'bom': row['bom'],
                'component': row['item_code'],
                'message': f"BOM {row['bom']} references non-existent component {row['item_code']}"
            })
        else:
            issues.append({
                'type': 'DISABLED_COMPONENT',
                'severity': 'MEDIUM',
                'bom': row['bom'],
                'component': row['item_code'],
                'message': f"BOM {row['bom']} uses disabled component {row['item_code']}"
            })
    
    return issues


# ============================================================================
# MAIN HEALTH CHECK RUNNER
# ============================================================================

def run_health_check(verbose=False, output_file=None):
    """
    Run comprehensive BOM health check.
    
    Args:
        verbose: Print detailed output
        output_file: Save results to file (JSON format)
    
    Returns:
        dict with health check results
    """
    print("=" * 70)
    print("BOM STATUS MANAGER - HEALTH CHECK")
    print(f"Run Time: {now_datetime()}")
    print(f"Company: {get_default_company()}")
    print("=" * 70)
    
    all_issues = []
    
    # Run all detection functions
    checks = [
        ("Circular References", detect_circular_references),
        ("Orphaned BOMs", detect_orphaned_boms),
        ("Missing Default BOMs", detect_missing_default_boms),
        ("Multiple Default BOMs", detect_multiple_default_boms),
        ("Inactive Default BOMs", detect_inactive_default_boms),
        ("Cost Anomalies", detect_cost_anomalies),
        ("Missing Components", detect_missing_components),
    ]
    
    for check_name, check_func in checks:
        print(f"\n🔍 Checking: {check_name}...")
        try:
            issues = check_func()
            all_issues.extend(issues)
            
            if issues:
                print(f"   ⚠️  Found {len(issues)} issue(s)")
                if verbose:
                    for issue in issues:
                        severity_icon = {
                            'CRITICAL': '🔴',
                            'HIGH': '🟠',
                            'MEDIUM': '🟡',
                            'LOW': '🔵'
                        }.get(issue['severity'], '⚪')
                        print(f"      {severity_icon} [{issue['severity']}] {issue['message']}")
            else:
                print(f"   ✅ No issues found")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            all_issues.append({
                'type': 'CHECK_ERROR',
                'severity': 'HIGH',
                'check': check_name,
                'message': f"Health check '{check_name}' failed: {str(e)}"
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("HEALTH CHECK SUMMARY")
    print("=" * 70)
    
    severity_counts = defaultdict(int)
    type_counts = defaultdict(int)
    
    for issue in all_issues:
        severity_counts[issue['severity']] += 1
        type_counts[issue['type']] += 1
    
    total = len(all_issues)
    
    if total == 0:
        print("✅ All checks passed! No issues detected.")
        health_status = "HEALTHY"
    else:
        print(f"Total Issues: {total}")
        print(f"  🔴 Critical: {severity_counts.get('CRITICAL', 0)}")
        print(f"  🟠 High: {severity_counts.get('HIGH', 0)}")
        print(f"  🟡 Medium: {severity_counts.get('MEDIUM', 0)}")
        print(f"  🔵 Low: {severity_counts.get('LOW', 0)}")
        
        print("\nBy Type:")
        for issue_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  - {issue_type}: {count}")
        
        if severity_counts.get('CRITICAL', 0) > 0:
            health_status = "CRITICAL"
        elif severity_counts.get('HIGH', 0) > 0:
            health_status = "UNHEALTHY"
        elif severity_counts.get('MEDIUM', 0) > 0:
            health_status = "WARNING"
        else:
            health_status = "MINOR_ISSUES"
    
    print(f"\n🏥 Overall Health Status: {health_status}")
    print("=" * 70)
    
    result = {
        'timestamp': str(now_datetime()),
        'company': get_default_company(),
        'health_status': health_status,
        'total_issues': total,
        'severity_counts': dict(severity_counts),
        'type_counts': dict(type_counts),
        'issues': all_issues
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, indent=2, fp=f)
        print(f"\n📄 Results saved to: {output_file}")
    
    return result


# ============================================================================
# STATUS INSIGHTS - BOM Relationship Analysis
# ============================================================================

def get_bom_insights(bom_name):
    """
    Get detailed insights about a specific BOM.
    
    Args:
        bom_name: The BOM to analyze
    
    Returns:
        dict with BOM insights
    """
    print(f"\n📊 BOM INSIGHTS: {bom_name}")
    print("=" * 70)
    
    if not frappe.db.exists("BOM", bom_name):
        print(f"❌ BOM {bom_name} not found")
        return None
    
    bom = frappe.get_doc("BOM", bom_name)
    
    # Basic Info
    print(f"\n📋 Basic Information:")
    print(f"   Item: {bom.item} ({bom.item_name or 'N/A'})")
    print(f"   Status: {get_bom_status_label(bom.docstatus, bom.is_active, bom.is_default)}")
    print(f"   Company: {bom.company}")
    print(f"   Total Cost: {format_currency(bom.total_cost)}")
    print(f"   Quantity: {bom.quantity} {bom.uom}")
    
    # Components
    print(f"\n🔧 Components ({len(bom.items)} items):")
    for item in bom.items[:10]:  # Limit display
        sub_bom = f" [BOM: {item.bom_no}]" if item.bom_no else ""
        print(f"   - {item.item_code}: {item.qty} {item.uom}{sub_bom}")
    if len(bom.items) > 10:
        print(f"   ... and {len(bom.items) - 10} more")
    
    # Where Used (parent BOMs)
    parent_boms = frappe.db.sql("""
        SELECT bi.parent, b.item, b.is_active, b.is_default
        FROM `tabBOM Item` bi
        INNER JOIN `tabBOM` b ON b.name = bi.parent
        WHERE bi.bom_no = %s AND b.docstatus = 1
    """, (bom_name,), as_dict=True)
    
    print(f"\n⬆️  Used In ({len(parent_boms)} parent BOMs):")
    for pb in parent_boms[:5]:
        status = get_bom_status_label(1, pb['is_active'], pb['is_default'])
        print(f"   - {pb['parent']} ({pb['item']}) [{status}]")
    if len(parent_boms) > 5:
        print(f"   ... and {len(parent_boms) - 5} more")
    
    # Work Orders
    work_orders = frappe.db.sql("""
        SELECT name, status, qty, produced_qty
        FROM `tabWork Order`
        WHERE bom_no = %s
        ORDER BY creation DESC
        LIMIT 5
    """, (bom_name,), as_dict=True)
    
    print(f"\n🏭 Recent Work Orders ({len(work_orders)} shown):")
    for wo in work_orders:
        print(f"   - {wo['name']}: {wo['status']} ({wo['produced_qty']}/{wo['qty']})")
    
    # Alternative BOMs for same item
    alt_boms = frappe.db.sql("""
        SELECT name, is_active, is_default, total_cost
        FROM `tabBOM`
        WHERE item = %s AND name != %s AND docstatus = 1
    """, (bom.item, bom_name), as_dict=True)
    
    if alt_boms:
        print(f"\n🔄 Alternative BOMs for {bom.item}:")
        for ab in alt_boms:
            status = get_bom_status_label(1, ab['is_active'], ab['is_default'])
            print(f"   - {ab['name']}: {format_currency(ab['total_cost'])} [{status}]")
    
    print("\n" + "=" * 70)
    
    return {
        'bom': bom_name,
        'item': bom.item,
        'status': get_bom_status_label(bom.docstatus, bom.is_active, bom.is_default),
        'total_cost': bom.total_cost,
        'component_count': len(bom.items),
        'parent_bom_count': len(parent_boms),
        'work_order_count': len(work_orders),
        'alternative_bom_count': len(alt_boms)
    }


# ============================================================================
# REPAIR ADVISOR - Fix Suggestions
# ============================================================================

def get_repair_suggestions(issue_type=None, limit=10):
    """
    Get repair suggestions for detected issues.
    
    Args:
        issue_type: Filter by specific issue type (optional)
        limit: Maximum suggestions to return
    
    Returns:
        list of repair suggestions
    """
    print("\n🔧 BOM REPAIR ADVISOR")
    print("=" * 70)
    
    # Run health check first
    health_result = run_health_check(verbose=False)
    issues = health_result['issues']
    
    if issue_type:
        issues = [i for i in issues if i['type'] == issue_type]
    
    suggestions = []
    
    for issue in issues[:limit]:
        suggestion = {
            'issue': issue,
            'recommended_action': None,
            'impact': None,
            'auto_fixable': False
        }
        
        if issue['type'] == 'CIRCULAR_REFERENCE':
            suggestion['recommended_action'] = "Review BOM structure and remove circular dependency"
            suggestion['impact'] = "CRITICAL - Will cause infinite loops in MRP calculations"
            suggestion['auto_fixable'] = False
            
        elif issue['type'] == 'ORPHANED_BOM':
            suggestion['recommended_action'] = f"Deactivate BOM {issue['bom']} or recreate item {issue['item']}"
            suggestion['impact'] = "HIGH - BOM references non-existent item"
            suggestion['auto_fixable'] = True
            
        elif issue['type'] == 'NO_DEFAULT_BOM':
            boms = frappe.db.get_all("BOM", 
                filters={"item": issue['item'], "docstatus": 1, "is_active": 1},
                fields=["name", "total_cost"],
                order_by="creation desc",
                limit=1
            )
            if boms:
                suggestion['recommended_action'] = f"Set {boms[0]['name']} as default BOM"
                suggestion['auto_fixable'] = True
            suggestion['impact'] = "MEDIUM - Production planning may use wrong BOM"
            
        elif issue['type'] == 'MULTIPLE_DEFAULTS':
            suggestion['recommended_action'] = f"Keep one default BOM, deactivate others: {issue['bom_names']}"
            suggestion['impact'] = "HIGH - Data integrity issue, unpredictable behavior"
            suggestion['auto_fixable'] = True
            
        elif issue['type'] == 'INACTIVE_DEFAULT':
            suggestion['recommended_action'] = f"Either activate BOM {issue['bom']} or remove default flag"
            suggestion['impact'] = "MEDIUM - Default BOM is not usable"
            suggestion['auto_fixable'] = True
            
        elif issue['type'] == 'MISSING_COMPONENT':
            suggestion['recommended_action'] = f"Create item {issue['component']} or update BOM {issue['bom']}"
            suggestion['impact'] = "HIGH - BOM cannot be used for production"
            suggestion['auto_fixable'] = False
            
        elif issue['type'] == 'DISABLED_COMPONENT':
            suggestion['recommended_action'] = f"Enable item {issue['component']} or replace in BOM {issue['bom']}"
            suggestion['impact'] = "MEDIUM - Production may fail"
            suggestion['auto_fixable'] = False
            
        elif issue['type'] == 'ZERO_COST':
            suggestion['recommended_action'] = f"Update cost rates for items in BOM {issue['bom']}"
            suggestion['impact'] = "LOW - Costing reports will be inaccurate"
            suggestion['auto_fixable'] = False
            
        elif issue['type'] == 'COST_ANOMALY':
            suggestion['recommended_action'] = f"Review and verify cost structure of BOM {issue['bom']}"
            suggestion['impact'] = "LOW - May indicate pricing or quantity errors"
            suggestion['auto_fixable'] = False
        
        suggestions.append(suggestion)
        
        print(f"\n{'='*50}")
        print(f"Issue: {issue['message']}")
        print(f"Severity: {issue['severity']}")
        print(f"Action: {suggestion['recommended_action']}")
        print(f"Impact: {suggestion['impact']}")
        print(f"Auto-fixable: {'Yes' if suggestion['auto_fixable'] else 'No'}")
    
    print("\n" + "=" * 70)
    print(f"Total suggestions: {len(suggestions)}")
    
    return suggestions


# ============================================================================
# QUICK ACCESS FUNCTIONS
# ============================================================================

def run_quick_scan():
    """Quick health scan with minimal output"""
    return run_health_check(verbose=False)


def run_full_scan():
    """Full health scan with detailed output"""
    return run_health_check(verbose=True)


def run_live():
    """Entry point for bench execute"""
    return run_health_check(verbose=True)
