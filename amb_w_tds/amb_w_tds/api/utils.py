# amb_w_tds/api/utils.py

from typing import Callable
import frappe


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
