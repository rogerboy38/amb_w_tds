from frappe import _


def get_data(data):
    """Dashboard override for Batch AMB.

    Adds Sample Request AMB as a related transaction so the Connections
    section on the Batch AMB form lists Sample Requests linked via
    `batch_reference`.

    Registered in hooks.py:
        override_doctype_dashboards = {
            "Batch AMB": "amb_w_tds.amb_w_tds.utils.batch_amb_dashboard.get_data",
        }
    """
    data["transactions"].append(
        {"label": _("Sample Request"), "items": ["Sample Request AMB"]}
    )
    if "non_standard_fieldnames" not in data:
        data["non_standard_fieldnames"] = {}
    data["non_standard_fieldnames"]["Sample Request AMB"] = "batch_reference"
    return data
