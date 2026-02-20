# -*- coding: utf-8 -*-
from frappe.model.document import Document
import frappe
from frappe import _
import re
import json

class ContainerBarrels(Document):
    def validate(self):
        if self.barrel_serial_number:
            if not validate_serial_format(self.barrel_serial_number):
                frappe.throw(_("Invalid serial format"))

def validate_serial_format(serial_no):
    if not serial_no:
        return False
    pattern = r'^[A-Z]{3}-\d{4}-[A-Z]\d{3}-\d{4}$'
    return bool(re.match(pattern, str(serial_no).strip()))

# PHASE B1: VALIDATION
@frappe.whitelist()
def validate_serial_number(serial_no):
    try:
        serial_no = str(serial_no).strip()
        if not validate_serial_format(serial_no):
            return {"valid": False, "exists": False, "message": "Invalid serial format. Expected: AMB-2024-B001-0001"}
        barrel_name = frappe.db.get_value("Container Barrels", {"barrel_serial_number": serial_no}, "name")
        if barrel_name:
            barrel = frappe.get_doc("Container Barrels", barrel_name)
            return {"valid": True, "exists": True, "message": "Serial found",
                    "data": {"name": barrel.name, "serial_no": barrel.barrel_serial_number,
                            "status": barrel.get("status") or "Unknown",
                            "usage_count": barrel.get("usage_count") or 0,
                            "max_reuse_count": barrel.get("max_reuse_count") or 10,
                            "parent": barrel.parent}}
        else:
            return {"valid": True, "exists": False, "message": "Serial format valid but not found in system"}
    except Exception as e:
        frappe.log_error(f"Validation error: {str(e)}")
        return {"valid": False, "exists": False, "message": str(e)}

@frappe.whitelist()
def check_serial_availability(serial_no):
    try:
        barrel = frappe.db.get_value("Container Barrels", {"barrel_serial_number": serial_no},
                                     ["name", "status", "usage_count", "max_reuse_count"], as_dict=True)
        if not barrel:
            return {"available": False, "reason": "Serial not found in system"}
        status = barrel.get("status", "New")
        if status in ["In Use", "Cleaning", "Retired"]:
            return {"available": False, "reason": f"Barrel is currently {status}", "barrel": barrel}
        usage_count = barrel.get("usage_count", 0)
        max_reuse = barrel.get("max_reuse_count", 10)
        if usage_count >= max_reuse:
            return {"available": False, "reason": f"Maximum reuse limit reached ({usage_count}/{max_reuse})", "barrel": barrel}
        return {"available": True, "reason": "Barrel available for use", "barrel": barrel, "remaining_uses": max_reuse - usage_count}
    except Exception as e:
        frappe.log_error(f"Availability check error: {str(e)}")
        return {"available": False, "reason": f"Error: {str(e)}"}

@frappe.whitelist()
def bulk_validate_serials(serial_numbers):
    try:
        if isinstance(serial_numbers, str):
            serial_numbers = json.loads(serial_numbers)
        if not isinstance(serial_numbers, list):
            return {"valid": [], "invalid": [], "duplicates": [], "details": {}, "error": "Input must be a list"}
        results = {"valid": [], "invalid": [], "duplicates": [], "details": {},
                   "summary": {"total": len(serial_numbers), "valid_count": 0, "invalid_count": 0, "duplicate_count": 0}}
        seen = set()
        for serial in serial_numbers:
            serial = str(serial).strip()
            if serial in seen:
                results["duplicates"].append(serial)
                results["summary"]["duplicate_count"] += 1
                results["details"][serial] = {"valid": False, "message": "Duplicate in input list"}
                continue
            seen.add(serial)
            validation = validate_serial_number(serial)
            if validation["valid"]:
                results["valid"].append(serial)
                results["summary"]["valid_count"] += 1
            else:
                results["invalid"].append(serial)
                results["summary"]["invalid_count"] += 1
            results["details"][serial] = validation
        return results
    except Exception as e:
        frappe.log_error(f"Bulk validation error: {str(e)}")
        return {"valid": [], "invalid": [], "duplicates": [], "details": {}, "error": str(e)}

@frappe.whitelist()
def get_serial_info(serial_no):
    try:
        validation = validate_serial_number(serial_no)
        if not validation["exists"]:
            return validation
        availability = check_serial_availability(serial_no)
        return {"valid": validation["valid"], "exists": validation["exists"],
                "barrel": validation["data"], "availability": availability, "message": validation["message"]}
    except Exception as e:
        frappe.log_error(f"Get serial info error: {str(e)}")
        return {"valid": False, "message": str(e)}

@frappe.whitelist()
def validate_and_get_available_serials(serial_numbers):
    try:
        if isinstance(serial_numbers, str):
            serial_numbers = json.loads(serial_numbers)
        available = []
        unavailable = []
        for serial in serial_numbers:
            serial = str(serial).strip()
            validation = validate_serial_number(serial)
            if not validation["valid"] or not validation["exists"]:
                unavailable.append({"serial": serial, "reason": validation["message"]})
                continue
            availability = check_serial_availability(serial)
            if availability["available"]:
                available.append({"serial": serial, "barrel": availability["barrel"],
                                 "remaining_uses": availability.get("remaining_uses", 0)})
            else:
                unavailable.append({"serial": serial, "reason": availability["reason"]})
        return {"available": available, "unavailable": unavailable,
                "summary": {"total": len(serial_numbers), "available_count": len(available), "unavailable_count": len(unavailable)}}
    except Exception as e:
        frappe.log_error(f"Validate and get available error: {str(e)}")
        return {"available": [], "unavailable": [], "error": str(e)}

# PHASE B2: LIFECYCLE MANAGEMENT
@frappe.whitelist()
def get_barrel_statistics(batch_name=None):
    try:
        query = """SELECT status, COUNT(*) as count FROM `tabContainer Barrels`
                   WHERE (parent = %(parent)s OR %(parent)s IS NULL) GROUP BY status"""
        status_counts = frappe.db.sql(query, {"parent": batch_name}, as_dict=True)
        stats = {"by_status": {s.status: s.count for s in status_counts},
                 "available": 0, "in_cleaning": 0, "retired": 0, "in_use": 0, "total": 0}
        for s in status_counts:
            stats["total"] += s.count
            if s.status in ["New", "Ready for Reuse"]:
                stats["available"] += s.count
            elif s.status == "Cleaning":
                stats["in_cleaning"] = s.count
            elif s.status == "Retired":
                stats["retired"] = s.count
            elif s.status == "In Use":
                stats["in_use"] = s.count
        return stats
    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist()
def get_available_barrels(warehouse=None, limit=100):
    try:
        wh = f"AND current_warehouse = '{warehouse}'" if warehouse else ""
        query = f"""SELECT barrel_serial_number, status, usage_count, max_reuse_count, current_warehouse
                    FROM `tabContainer Barrels` WHERE status IN ('New', 'Ready for Reuse')
                    AND usage_count < max_reuse_count {wh} LIMIT {limit}"""
        barrels = frappe.db.sql(query, as_dict=True)
        return {"success": True, "barrels": barrels, "count": len(barrels)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def add_cleaning_log(serial_no, cleaning_data):
    try:
        if isinstance(cleaning_data, str):
            cleaning_data = json.loads(cleaning_data)
        barrel = frappe.get_doc("Container Barrels", {"barrel_serial_number": serial_no})
        barrel.last_cleaned_date = frappe.utils.today()
        barrel.cleaned_by = frappe.session.user
        barrel.add_comment("Comment", f"Cleaned: {cleaning_data.get('cleaning_method', 'N/A')}")
        barrel.save()
        frappe.db.commit()
        return {"success": True, "message": "Cleaning log added"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def retire_barrel(serial_no, reason, retired_by=None):
    try:
        barrel = frappe.get_doc("Container Barrels", {"barrel_serial_number": serial_no})
        barrel.status = "Retired"
        barrel.retirement_reason = reason
        barrel.add_comment("Comment", f"Retired by {retired_by or frappe.session.user}: {reason}")
        barrel.save()
        frappe.db.commit()
        return {"success": True, "message": "Barrel retired"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_barrel_lifecycle_history(serial_no):
    try:
        barrel = frappe.get_doc("Container Barrels", {"barrel_serial_number": serial_no})
        comments = frappe.get_all("Comment", filters={"reference_doctype": "Container Barrels",
                                  "reference_name": barrel.name, "comment_type": "Comment"},
                                  fields=["content", "creation", "owner"], order_by="creation desc", limit=50)
        return {"serial_no": serial_no, "current_status": barrel.status, "usage_count": barrel.usage_count,
                "max_reuse_count": barrel.max_reuse_count, "comments": comments}
    except Exception as e:
        return {"error": str(e)}
