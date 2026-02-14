import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add Phase B fields to Container Barrels"""
    
    custom_fields = {
        "Container Barrels": [
            {
                "fieldname": "barrel_lifecycle_section",
                "label": "Barrel Lifecycle",
                "fieldtype": "Section Break",
                "insert_after": "status"
            },
            {
                "fieldname": "usage_count",
                "label": "Usage Count",
                "fieldtype": "Int",
                "default": "0",
                "insert_after": "barrel_lifecycle_section"
            },
            {
                "fieldname": "max_reuse_count",
                "label": "Max Reuse Count",
                "fieldtype": "Int",
                "default": "10",
                "insert_after": "usage_count"
            },
            {
                "fieldname": "column_break_lifecycle",
                "fieldtype": "Column Break",
                "insert_after": "max_reuse_count"
            },
            {
                "fieldname": "last_cleaned_date",
                "label": "Last Cleaned Date",
                "fieldtype": "Date",
                "insert_after": "column_break_lifecycle"
            },
            {
                "fieldname": "cleaned_by",
                "label": "Cleaned By",
                "fieldtype": "Link",
                "options": "User",
                "insert_after": "last_cleaned_date"
            },
            {
                "fieldname": "retirement_section",
                "label": "Retirement Details",
                "fieldtype": "Section Break",
                "insert_after": "cleaned_by",
                "depends_on": "eval:doc.status=='Retired'"
            },
            {
                "fieldname": "retirement_reason",
                "label": "Retirement Reason",
                "fieldtype": "Small Text",
                "insert_after": "retirement_section"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    print("✅ Phase B fields added successfully!")

if __name__ == "__main__":
    execute()
