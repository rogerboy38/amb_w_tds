# Fix and verify
import frappe
from raven_ai_agent.agents.sales_order_followup_agent import SalesOrderFollowupAgent
agent = SalesOrderFollowupAgent()

# Run fix
result = agent.fix_so_from_quotation("SO-01059-ALBAFLOR")
print(f"Fix result: {result}")

# Check DB directly
items = frappe.get_all("Sales Order Item", 
    filters={"parent": "SO-01059-ALBAFLOR"},
    fields=["name", "item_code", "custom_tds_amb"]
)

print(f"\n=== SO Items After Fix ===")
for item in items:
    print(f"  Item: {item.item_code} | custom_tds_amb: {item.custom_tds_amb}")
