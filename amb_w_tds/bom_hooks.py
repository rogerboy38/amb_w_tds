"""
BOM Event Hooks - Automated BOM Validation on Save/Submit
Phase 5 Implementation

This module provides Frappe doc_events hooks for BOM doctype:
- on_submit: Validate BOM structure, warn via Raven (non-blocking)
- on_update: Check for self-references, circular dependencies

All validations are NON-BLOCKING - they post warnings to Raven but 
allow the user to proceed with the operation.

Usage:
    Automatically triggered by Frappe when BOM documents are saved/submitted.
    Configure in hooks.py:
        doc_events = {
            "BOM": {
                "on_submit": "amb_w_tds.amb_w_tds.bom_hooks.on_bom_submit",
                "on_update": "amb_w_tds.amb_w_tds.bom_hooks.on_bom_update"
            }
        }
"""

import frappe
from frappe.utils import now_datetime
import json


# ============================================================================
# CONFIGURATION
# ============================================================================

RAVEN_CHANNEL = "bom-hierarchy-audit"
ENABLE_RAVEN_NOTIFICATIONS = True
MAX_DEPTH_CHECK = 10  # Maximum BOM hierarchy depth to check


# ============================================================================
# MAIN HOOK FUNCTIONS
# ============================================================================

def on_bom_submit(doc, method=None):
    """
    Hook triggered when a BOM is submitted.
    Validates BOM structure and posts warnings to Raven.
    NON-BLOCKING - always allows submission to proceed.
    """
    try:
        issues = []
        
        # Check 1: Self-reference (BOM item references itself)
        self_ref = _check_self_reference(doc)
        if self_ref:
            issues.append(self_ref)
        
        # Check 2: Circular dependency
        circular = _check_circular_dependency(doc)
        if circular:
            issues.append(circular)
        
        # Check 3: Flat structure warning (no sub-BOMs for manufactured items)
        flat_warning = _check_flat_structure(doc)
        if flat_warning:
            issues.append(flat_warning)
        
        # Check 4: Missing component items
        missing = _check_missing_components(doc)
        if missing:
            issues.extend(missing)
        
        # Check 5: Inactive sub-BOMs
        inactive = _check_inactive_sub_boms(doc)
        if inactive:
            issues.extend(inactive)
        
        # Post to Raven if issues found
        if issues:
            _post_bom_warning(doc, issues, event="SUBMIT")
            
    except Exception as e:
        # Log error but don't block submission
        frappe.log_error(
            f"BOM Hook Error (on_submit): {str(e)}\nBOM: {doc.name}",
            "BOM Hook Error"
        )


def on_bom_update(doc, method=None):
    """
    Hook triggered when a BOM is updated/saved.
    Performs lightweight validation checks.
    NON-BLOCKING - always allows save to proceed.
    """
    try:
        issues = []
        
        # Only check for critical issues on update
        self_ref = _check_self_reference(doc)
        if self_ref:
            issues.append(self_ref)
        
        # Check for duplicate items
        duplicates = _check_duplicate_items(doc)
        if duplicates:
            issues.append(duplicates)
        
        # Post warning only for critical issues
        if issues and any(i.get('severity') in ['CRITICAL', 'HIGH'] for i in issues):
            _post_bom_warning(doc, issues, event="UPDATE")
            
    except Exception as e:
        frappe.log_error(
            f"BOM Hook Error (on_update): {str(e)}\nBOM: {doc.name}",
            "BOM Hook Error"
        )


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def _check_self_reference(doc):
    """Check if BOM contains itself as a component."""
    for item in doc.items:
        if item.bom_no == doc.name:
            return {
                'type': 'SELF_REFERENCE',
                'severity': 'CRITICAL',
                'message': f"BOM {doc.name} references itself in item {item.item_code}"
            }
        # Also check if sub-BOM is for the same item
        if item.bom_no:
            sub_bom_item = frappe.db.get_value("BOM", item.bom_no, "item")
            if sub_bom_item == doc.item:
                return {
                    'type': 'SELF_REFERENCE',
                    'severity': 'CRITICAL', 
                    'message': f"BOM {doc.name} has sub-BOM {item.bom_no} for same item {doc.item}"
                }
    return None


def _check_circular_dependency(doc, visited=None, depth=0):
    """Check for circular dependencies in BOM hierarchy."""
    if visited is None:
        visited = set()
    
    if depth > MAX_DEPTH_CHECK:
        return {
            'type': 'DEEP_HIERARCHY',
            'severity': 'MEDIUM',
            'message': f"BOM {doc.name} hierarchy exceeds {MAX_DEPTH_CHECK} levels"
        }
    
    if doc.name in visited:
        return {
            'type': 'CIRCULAR_REFERENCE',
            'severity': 'CRITICAL',
            'message': f"Circular dependency detected: BOM {doc.name} appears in its own hierarchy"
        }
    
    visited.add(doc.name)
    
    for item in doc.items:
        if item.bom_no:
            try:
                sub_doc = frappe.get_doc("BOM", item.bom_no)
                result = _check_circular_dependency(sub_doc, visited.copy(), depth + 1)
                if result:
                    return result
            except Exception:
                pass  # Sub-BOM doesn't exist or can't be loaded
    
    return None


def _check_flat_structure(doc):
    """Check if BOM has flat structure (no sub-assemblies) for items that might need them."""
    # Count items with sub-BOMs
    sub_bom_count = sum(1 for item in doc.items if item.bom_no)
    
    # If BOM has many items but no sub-assemblies, might be flat
    if len(doc.items) > 10 and sub_bom_count == 0:
        return {
            'type': 'FLAT_STRUCTURE_WARNING',
            'severity': 'LOW',
            'message': f"BOM {doc.name} has {len(doc.items)} items but no sub-assemblies. Consider hierarchical structure."
        }
    return None


def _check_missing_components(doc):
    """Check for components that don't exist or are disabled."""
    issues = []
    
    for item in doc.items:
        item_exists = frappe.db.exists("Item", item.item_code)
        if not item_exists:
            issues.append({
                'type': 'MISSING_COMPONENT',
                'severity': 'HIGH',
                'message': f"Component {item.item_code} does not exist"
            })
        else:
            is_disabled = frappe.db.get_value("Item", item.item_code, "disabled")
            if is_disabled:
                issues.append({
                    'type': 'DISABLED_COMPONENT',
                    'severity': 'MEDIUM',
                    'message': f"Component {item.item_code} is disabled"
                })
    
    return issues


def _check_inactive_sub_boms(doc):
    """Check for sub-BOMs that are not active."""
    issues = []
    
    for item in doc.items:
        if item.bom_no:
            bom_info = frappe.db.get_value("BOM", item.bom_no, 
                ["is_active", "docstatus"], as_dict=True)
            
            if bom_info:
                if bom_info.get('docstatus') != 1:
                    issues.append({
                        'type': 'DRAFT_SUB_BOM',
                        'severity': 'HIGH',
                        'message': f"Sub-BOM {item.bom_no} is not submitted"
                    })
                elif not bom_info.get('is_active'):
                    issues.append({
                        'type': 'INACTIVE_SUB_BOM',
                        'severity': 'MEDIUM',
                        'message': f"Sub-BOM {item.bom_no} is inactive"
                    })
    
    return issues


def _check_duplicate_items(doc):
    """Check for duplicate item codes in BOM."""
    item_codes = [item.item_code for item in doc.items]
    duplicates = set([x for x in item_codes if item_codes.count(x) > 1])
    
    if duplicates:
        return {
            'type': 'DUPLICATE_ITEMS',
            'severity': 'MEDIUM',
            'message': f"Duplicate items found: {', '.join(duplicates)}"
        }
    return None


# ============================================================================
# RAVEN NOTIFICATION
# ============================================================================

def _post_bom_warning(doc, issues, event="SUBMIT"):
    """Post BOM validation warnings to Raven channel."""
    if not ENABLE_RAVEN_NOTIFICATIONS:
        return
    
    try:
        # Format severity icons
        severity_icons = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🔵'
        }
        
        # Build message
        message = f"""**⚠️ BOM Validation Warning** ({event})
━━━━━━━━━━━━━━━━━━━━━━━━
📄 **BOM:** {doc.name}
📦 **Item:** {doc.item}
👤 **User:** {frappe.session.user}
🕐 **Time:** {now_datetime()}

**Issues Found ({len(issues)}):**
"""
        
        for issue in issues[:5]:  # Limit to 5 issues
            icon = severity_icons.get(issue.get('severity', 'LOW'), '⚪')
            message += f"\n{icon} [{issue['severity']}] {issue['message']}"
        
        if len(issues) > 5:
            message += f"\n\n... and {len(issues) - 5} more issues"
        
        message += "\n\n_This is a warning only. The BOM operation was allowed to proceed._"
        
        # Post to Raven
        from amb_w_tds.scripts.bom_fixer import post_to_raven
        post_to_raven(message[:1000], channel=RAVEN_CHANNEL)
        
    except ImportError:
        # Raven not available, log instead
        frappe.log_error(
            f"BOM Warning (Raven unavailable):\nBOM: {doc.name}\nIssues: {json.dumps(issues, indent=2)}",
            "BOM Validation Warning"
        )
    except Exception as e:
        frappe.log_error(
            f"Failed to post BOM warning to Raven: {str(e)}",
            "BOM Hook Raven Error"
        )


# ============================================================================
# MANUAL VALIDATION FUNCTION (for bench execute)
# ============================================================================

def validate_bom(bom_name):
    """
    Manually validate a specific BOM.
    
    Usage:
        bench execute amb_w_tds.amb_w_tds.bom_hooks.validate_bom --kwargs '{"bom_name": "BOM-XXXX-XXX"}'
    """
    if not frappe.db.exists("BOM", bom_name):
        print(f"❌ BOM {bom_name} not found")
        return None
    
    doc = frappe.get_doc("BOM", bom_name)
    
    print(f"\n🔍 Validating BOM: {bom_name}")
    print(f"   Item: {doc.item}")
    print(f"   Status: {'Submitted' if doc.docstatus == 1 else 'Draft' if doc.docstatus == 0 else 'Cancelled'}")
    print("=" * 50)
    
    issues = []
    
    # Run all checks
    checks = [
        ("Self Reference", _check_self_reference(doc)),
        ("Circular Dependency", _check_circular_dependency(doc)),
        ("Flat Structure", _check_flat_structure(doc)),
        ("Missing Components", _check_missing_components(doc)),
        ("Inactive Sub-BOMs", _check_inactive_sub_boms(doc)),
        ("Duplicate Items", _check_duplicate_items(doc)),
    ]
    
    for check_name, result in checks:
        if result:
            if isinstance(result, list):
                issues.extend(result)
                print(f"⚠️  {check_name}: {len(result)} issue(s)")
            else:
                issues.append(result)
                print(f"⚠️  {check_name}: {result['message']}")
        else:
            print(f"✅ {check_name}: OK")
    
    print("=" * 50)
    if issues:
        print(f"Total issues: {len(issues)}")
    else:
        print("✅ BOM passed all validation checks")
    
    return issues
