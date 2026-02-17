#!/usr/bin/env python3
"""
Create Raven channel for BOM audit reports.
Run: bench execute amb_w_tds.scripts.create_raven_channel.create_channel
"""

import frappe

def create_channel(channel_name="bom-hierarchy-audit"):
    """Create the BOM hierarchy audit Raven channel."""
    
    # Check if channel exists
    existing = frappe.db.get_value(
        "Raven Channel",
        {"channel_name": channel_name},
        "name"
    )
    
    if existing:
        print(f"✅ Channel '{channel_name}' already exists: {existing}")
        return existing
    
    try:
        channel = frappe.get_doc({
            "doctype": "Raven Channel",
            "channel_name": channel_name,
            "type": "Public",
            "channel_description": "BOM Hierarchy Audit Reports - Automated reports from BOM Repair Agent"
        })
        channel.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Created Raven channel: #{channel_name}")
        return channel.name
        
    except Exception as e:
        print(f"❌ Failed to create channel: {str(e)}")
        return None

if __name__ == "__main__":
    create_channel()
