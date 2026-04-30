import frappe

def execute():
    """Fix TDS Approval Workflow states to set correct docstatus"""
    
    workflow_name = "TDS Approval Workflow"
    
    if not frappe.db.exists("Workflow", workflow_name):
        print(f"Workflow {workflow_name} not found, skipping")
        return
    
    workflow = frappe.get_doc("Workflow", workflow_name)
    changed = False
    
    # States that should be "Submitted" (docstatus=1)
    submitted_states = ["Approved", "Frozen", "Certificate Shared", "Auto Approved"]
    
    for state in workflow.states:
        if state.state in submitted_states and state.doc_status != 1:
            state.doc_status = 1
            changed = True
            print(f"✅ Updated {state.state}: docstatus -> 1 (Submitted)")
        elif state.state == "Draft" and state.doc_status != 0:
            state.doc_status = 0
            changed = True
            print(f"✅ Updated {state.state}: docstatus -> 0 (Draft)")
    
    if changed:
        workflow.save()
        frappe.db.commit()
        print(f"✅ Updated workflow {workflow_name}")
        
        # Update existing TDS documents that are in approved states
        result = frappe.db.sql("""
            UPDATE `tabTDS Product Specification`
            SET docstatus = 1
            WHERE workflow_state IN ('Approved', 'Frozen', 'Certificate Shared', 'Auto Approved')
            AND docstatus = 0
        """)
        frappe.db.commit()
        print(f"✅ Updated {result[0] if result else 0} existing TDS documents to docstatus=1")
    else:
        print("No changes needed")

if __name__ == "__main__":
    execute()
