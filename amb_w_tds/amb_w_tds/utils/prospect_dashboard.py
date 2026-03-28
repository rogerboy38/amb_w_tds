from frappe import _

def get_data(data):
    data["transactions"].append(
        {"label": _("Sample Request"), "items": ["Sample Request AMB"]}
    )
    # Add non_standard_fieldnames if not present
    if "non_standard_fieldnames" not in data:
        data["non_standard_fieldnames"] = {}
    data["non_standard_fieldnames"]["Sample Request AMB"] = "party"
    return data
