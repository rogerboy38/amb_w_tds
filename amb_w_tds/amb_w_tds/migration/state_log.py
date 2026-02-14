import frappe
from frappe.utils import now
import json, os

LOG_PATH = frappe.get_site_path("private", "migration_state.jsonl")

def log_success(legacy_id, quotation_name):
    entry = {
        "legacy_id": legacy_id,
        "quotation_name": quotation_name,
        "timestamp": now(),
        "status": "success",
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

def log_failure(legacy_id, error):
    entry = {
        "legacy_id": legacy_id,
        "error": str(error),
        "timestamp": now(),
        "status": "failed",
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
