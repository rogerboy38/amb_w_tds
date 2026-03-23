# amb_w_tds/api/utils.py

from typing import Callable
import frappe
from frappe.utils import today


def resolve_agent_fn(agent, fn_name: str) -> Callable:
    """
    Safely resolve a function from amb_w_tds.api.agent.

    WHY:
    - hasattr() is unreliable with @frappe.whitelist wrappers
    - getattr() + AttributeError is Frappe-safe
    - Works on frappe.cloud and bench console

    Raises:
        NotImplementedError if function is not found
    """
    try:
        fn = getattr(agent, fn_name)
    except AttributeError:
        frappe.log_error(
            title="AMB Agent Function Missing",
            message=f"Function '{fn_name}' not found in amb_w_tds.api.agent"
        )
        raise NotImplementedError(
            f"{fn_name} not found in amb_w_tds.api.agent"
        )

    if not callable(fn):
        raise NotImplementedError(
            f"{fn_name} exists but is not callable in amb_w_tds.api.agent"
        )

    return fn



@frappe.whitelist()
def create_sample_request_from_lead(lead_name):
    """Create a Sample Request AMB from a Lead with a default sample row.
    
    This fixes Bug 72 where the 'Data missing in table Samples' error occurred
    when creating a Sample Request from a Lead without any sample rows.
    
    Args:
        lead_name: The name of the Lead document
        
    Returns:
        str: The name of the newly created Sample Request AMB
    """
    lead = frappe.get_doc("Lead", lead_name)
    
    # Create the Sample Request with a default sample row
    # This ensures the child table has data and prevents validation errors
    sr = frappe.get_doc({
        "doctype": "Sample Request AMB",
        "party_type": "Lead",
        "party": lead_name,
        "request_date": today(),
        "samples": [
            {
                "doctype": "Sample Request AMB Item",
                "item": "0307"
            }
        ]
    })
    sr.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return sr.name
