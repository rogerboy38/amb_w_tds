# BUG 72B Fix: Container Type Field Filter
# 
# This script changes the container_type field in Sample Request AMB Item
# from a Data field to a Link field that filters items by item_group
# "Sample Packaging Materials"
#
# Run in bench console on sandbox:
# exec(open('/path/to/bug_72b_fix.py').read())

import frappe

def fix_container_type_field():
    """Update container_type field to be a Link field filtered by item_group."""
    
    # Get the current field definition
    field = frappe.get_doc("DocField", {
        "parent": "Sample Request AMB Item",
        "fieldname": "container_type"
    })
    
    print(f"Current field type: {field.fieldtype}")
    print(f"Current field options: {field.options}")
    
    # Update the field to be a Link field to Item with filtered by item_group
    field.fieldtype = "Link"
    field.options = "Item"
    field.query = "select name from tabItem where item_group = 'Sample Packaging Materials'"
    
    field.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Clear cache
    frappe.clear_cache()
    
    print("Container type field updated successfully!")
    print("- Fieldtype: Data -> Link")
    print("- Options: (none) -> Item")
    print("- Query: filtered by item_group = 'Sample Packaging Materials'")

if __name__ == "__main__":
    fix_container_type_field()
