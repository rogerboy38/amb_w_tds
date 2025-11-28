import frappe

def on_stock_entry_submit(doc, method):
    """
    Stock Entry submit hook
    This function will be called when a Stock Entry is submitted
    """
    try:
        frappe.logger().info(f"Stock Entry {doc.name} submitted successfully")
        # Add your custom logic here if needed
    except Exception as e:
        frappe.log_error(f"Error in stock entry submit hook: {str(e)}")
