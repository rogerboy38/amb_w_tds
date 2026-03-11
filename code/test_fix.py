# Quick fix for custom_tds_amb
import frappe
from raven_ai_agent.agents.sales_order_followup_agent import SalesOrderFollowupAgent
agent = SalesOrderFollowupAgent()

# Test on one SO
result = agent.fix_so_from_quotation("SO-01059-ALBAFLOR")
print(result)

# Check if data was copied
so = frappe.get_doc("Sales Order", "SO-01059-ALBAFLOR")
for item in so.items:
    val = getattr(item, 'custom_tds_amb', None)
    print(f"Item {item.item_code}: custom_tds_amb = {val}")
