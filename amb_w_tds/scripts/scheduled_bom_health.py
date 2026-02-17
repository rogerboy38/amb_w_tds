"""
Scheduled BOM Health Check - Weekly Automated Health Reports
Phase 5 Implementation

This module provides scheduled health check functionality:
- Weekly health scan of all BOMs
- Automatic reporting to Raven channel
- Known issues tracking (skip re-reporting)

Usage:
    # Manual test
    bench execute amb_w_tds.scripts.scheduled_bom_health.run
    
    # With options
    bench execute amb_w_tds.scripts.scheduled_bom_health.run --kwargs '{"post_to_raven": true}'
    
Scheduler Configuration (in hooks.py):
    scheduler_events = {
        "weekly": [
            "amb_w_tds.scripts.scheduled_bom_health.run"
        ]
    }
"""

import frappe
from frappe.utils import now_datetime, get_datetime
import json
import os


# ============================================================================
# CONFIGURATION
# ============================================================================

RAVEN_CHANNEL = "bom-hierarchy-audit"
KNOWN_ISSUES_FILE = "bom_known_issues.json"


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run(post_to_raven=True, include_known=False):
    """
    Run scheduled BOM health check.
    
    Args:
        post_to_raven: Post report to Raven channel (default: True)
        include_known: Include known/tracked issues in report (default: False)
    
    Returns:
        dict with health check results
    """
    print("=" * 70)
    print("SCHEDULED BOM HEALTH CHECK")
    print(f"Run Time: {now_datetime()}")
    print("=" * 70)
    
    # Import health check from bom_status_manager
    from amb_w_tds.scripts.bom_status_manager import run_health_check
    
    # Run the health check (dry_run implicit - no changes made)
    result = run_health_check(verbose=False)
    
    # Load known issues to filter
    known_issues = _load_known_issues()
    
    # Filter out known issues if requested
    if not include_known and known_issues:
        original_count = len(result['issues'])
        result['issues'] = _filter_known_issues(result['issues'], known_issues)
        filtered_count = original_count - len(result['issues'])
        
        if filtered_count > 0:
            print(f"\nℹ️ Filtered {filtered_count} known/tracked issues")
            result['known_issues_filtered'] = filtered_count
    
    # Recalculate summary after filtering
    result = _recalculate_summary(result)
    
    # Generate and post report
    if post_to_raven:
        _post_weekly_report(result, known_issues)
    
    print("\n" + "=" * 70)
    print("SCHEDULED CHECK COMPLETE")
    print("=" * 70)
    
    return result


# ============================================================================
# KNOWN ISSUES MANAGEMENT
# ============================================================================

def _get_known_issues_path():
    """Get full path to known issues file."""
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(scripts_dir, KNOWN_ISSUES_FILE)


def _load_known_issues():
    """Load known issues from tracking file."""
    try:
        filepath = _get_known_issues_path()
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load known issues: {str(e)}")
    return {"issues": [], "last_updated": None}


def _save_known_issues(data):
    """Save known issues to tracking file."""
    try:
        filepath = _get_known_issues_path()
        data['last_updated'] = str(now_datetime())
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Known issues saved to {KNOWN_ISSUES_FILE}")
    except Exception as e:
        print(f"❌ Could not save known issues: {str(e)}")


def _filter_known_issues(issues, known_data):
    """Filter out issues that are in the known issues list."""
    known_boms = set()
    known_items = set()
    
    for ki in known_data.get('issues', []):
        if ki.get('bom'):
            known_boms.add(ki['bom'])
        if ki.get('item'):
            known_items.add(ki['item'])
    
    filtered = []
    for issue in issues:
        # Skip if BOM or item is in known list
        if issue.get('bom') in known_boms:
            continue
        if issue.get('item') in known_items and issue.get('type') in ['COST_ANOMALY', 'MISSING_COMPONENT']:
            continue
        filtered.append(issue)
    
    return filtered


def _recalculate_summary(result):
    """Recalculate severity counts after filtering."""
    from collections import defaultdict
    
    severity_counts = defaultdict(int)
    type_counts = defaultdict(int)
    
    for issue in result['issues']:
        severity_counts[issue['severity']] += 1
        type_counts[issue['type']] += 1
    
    result['severity_counts'] = dict(severity_counts)
    result['type_counts'] = dict(type_counts)
    result['total_issues'] = len(result['issues'])
    
    # Recalculate health status
    if result['total_issues'] == 0:
        result['health_status'] = "HEALTHY"
    elif severity_counts.get('CRITICAL', 0) > 0:
        result['health_status'] = "CRITICAL"
    elif severity_counts.get('HIGH', 0) > 0:
        result['health_status'] = "UNHEALTHY"
    elif severity_counts.get('MEDIUM', 0) > 0:
        result['health_status'] = "WARNING"
    else:
        result['health_status'] = "MINOR_ISSUES"
    
    return result


# ============================================================================
# KNOWN ISSUES CRUD
# ============================================================================

def add_known_issue(bom=None, item=None, reason=None, issue_type=None):
    """
    Add a BOM or item to the known issues list.
    
    Usage:
        bench execute amb_w_tds.scripts.scheduled_bom_health.add_known_issue \
            --kwargs '{"bom": "BOM-0301-001", "reason": "0227 variant - expected cost difference"}'
    """
    if not bom and not item:
        print("❌ Must provide either 'bom' or 'item' parameter")
        return
    
    data = _load_known_issues()
    
    new_issue = {
        'added': str(now_datetime()),
        'added_by': frappe.session.user if frappe.session else 'system'
    }
    
    if bom:
        new_issue['bom'] = bom
    if item:
        new_issue['item'] = item
    if reason:
        new_issue['reason'] = reason
    if issue_type:
        new_issue['issue_type'] = issue_type
    
    # Check if already exists
    for ki in data['issues']:
        if ki.get('bom') == bom and ki.get('item') == item:
            print(f"⚠️ Issue already tracked: {bom or item}")
            return
    
    data['issues'].append(new_issue)
    _save_known_issues(data)
    
    print(f"✅ Added to known issues: {bom or item}")
    if reason:
        print(f"   Reason: {reason}")


def remove_known_issue(bom=None, item=None):
    """
    Remove a BOM or item from the known issues list.
    
    Usage:
        bench execute amb_w_tds.scripts.scheduled_bom_health.remove_known_issue \
            --kwargs '{"bom": "BOM-0301-001"}'
    """
    data = _load_known_issues()
    original_count = len(data['issues'])
    
    data['issues'] = [
        ki for ki in data['issues']
        if not (ki.get('bom') == bom or ki.get('item') == item)
    ]
    
    removed = original_count - len(data['issues'])
    
    if removed > 0:
        _save_known_issues(data)
        print(f"✅ Removed {removed} known issue(s)")
    else:
        print(f"⚠️ No matching known issue found")


def list_known_issues():
    """
    List all known/tracked issues.
    
    Usage:
        bench execute amb_w_tds.scripts.scheduled_bom_health.list_known_issues
    """
    data = _load_known_issues()
    
    print("\n📋 KNOWN/TRACKED BOM ISSUES")
    print("=" * 60)
    
    if not data['issues']:
        print("No known issues tracked.")
        return
    
    print(f"Last Updated: {data.get('last_updated', 'N/A')}")
    print(f"Total Tracked: {len(data['issues'])}")
    print("-" * 60)
    
    for i, issue in enumerate(data['issues'], 1):
        print(f"\n{i}. ", end="")
        if issue.get('bom'):
            print(f"BOM: {issue['bom']}")
        if issue.get('item'):
            print(f"   Item: {issue['item']}")
        if issue.get('reason'):
            print(f"   Reason: {issue['reason']}")
        if issue.get('issue_type'):
            print(f"   Type: {issue['issue_type']}")
        print(f"   Added: {issue.get('added', 'N/A')} by {issue.get('added_by', 'N/A')}")
    
    print("\n" + "=" * 60)


# ============================================================================
# RAVEN REPORTING
# ============================================================================

def _post_weekly_report(result, known_issues):
    """Post weekly health report to Raven."""
    try:
        # Status emoji
        status_emoji = {
            'HEALTHY': '✅',
            'MINOR_ISSUES': '🔵',
            'WARNING': '🟡',
            'UNHEALTHY': '🟠',
            'CRITICAL': '🔴'
        }
        
        emoji = status_emoji.get(result['health_status'], '❓')
        
        message = f"""**📊 Weekly BOM Health Report**
━━━━━━━━━━━━━━━━━━━━━━━━
🏥 **Status:** {emoji} {result['health_status']}
📅 **Date:** {result['timestamp'][:10]}
🏢 **Company:** {result.get('company', 'N/A')}

**Issue Summary:**
• Total New Issues: {result['total_issues']}
• 🔴 Critical: {result['severity_counts'].get('CRITICAL', 0)}
• 🟠 High: {result['severity_counts'].get('HIGH', 0)}
• 🟡 Medium: {result['severity_counts'].get('MEDIUM', 0)}
• 🔵 Low: {result['severity_counts'].get('LOW', 0)}
"""
        
        if result.get('known_issues_filtered'):
            message += f"\n_({result['known_issues_filtered']} known issues filtered)_"
        
        # Add top issues
        if result['issues']:
            message += "\n\n**Top Issues:**"
            for issue in result['issues'][:3]:
                message += f"\n• [{issue['severity']}] {issue['message'][:60]}"
        
        if result['health_status'] == 'HEALTHY':
            message += "\n\n🎉 All BOM structures are healthy!"
        else:
            message += "\n\n_Run `bom_status_manager.auto_fix` to resolve auto-fixable issues._"
        
        # Post to Raven
        from amb_w_tds.scripts.bom_fixer import post_to_raven
        post_to_raven(message[:1000], channel=RAVEN_CHANNEL)
        print(f"\n📨 Weekly report posted to Raven channel: {RAVEN_CHANNEL}")
        
    except ImportError:
        print("ℹ️ Raven integration not available - report logged only")
    except Exception as e:
        print(f"⚠️ Could not post to Raven: {str(e)[:50]}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_with_report():
    """Run health check and always post to Raven."""
    return run(post_to_raven=True)


def run_silent():
    """Run health check without posting to Raven."""
    return run(post_to_raven=False)


def run_full():
    """Run health check including known issues."""
    return run(post_to_raven=True, include_known=True)
