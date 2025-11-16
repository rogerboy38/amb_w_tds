import frappe

def after_install():
    create_standard_pages()

def create_standard_pages():
    """Create standard pages when app is installed"""
    pages = [
        {
            "name": "barrel_dashboard",
            "label": "Barrel Dashboard", 
            "module": "amb_w_tds"
        },
        {
            "name": "container_barrels_dashboard", 
            "label": "Container Barrels Dashboard",
            "module": "amb_w_tds"
        }
    ]
    
    for page_data in pages:
        if not frappe.db.exists("Page", page_data["name"]):
            page = frappe.new_doc("Page")
            page.update(page_data)
            page.standard = "Yes"
            page.insert()
            print(f"✅ Created page: {page_data['label']}")
