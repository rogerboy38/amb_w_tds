# Bug Status Report: Raven AI Agent - Sales Invoice Creation Issues

## Executive Summary

The Raven AI Agent's `create_sales_invoice` function is experiencing multiple validation errors when attempting to automatically create Sales Invoices from Sales Orders in ERPNext. Despite incremental fixes, the agent continues to encounter validation errors that require proactive handling of missing or invalid data in the ERP documents.

## Environment

- **Platform**: ERPNext on Frappe Framework
- **Raven AI Agent Version**: Custom AI Agent for workflow automation
- **Module**: `sales_order_followup_agent.py`
- **Use Case**: `@ai @batch create invoices for to bill` - Bulk invoice creation from Sales Orders

## Error History (Chronological)

### Iteration 1: Unknown Column Error
```
Error: (1054, "Unknown column 'currency' in 'WHERE'")
Location: Line ~299 in sales_order_followup_agent.py
Cause: Querying Account doctype with non-existent 'currency' field
Status: Fixed by removing currency filter
```

### Iteration 2: Import Error
```
Error: cannot import name 'get_default_receivable_account' 
from 'erpnext.controllers.accounts_controller'
Cause: Function not available at this import path in ERPNext version
Status: Fixed by using frappe.get_value instead
```

### Iteration 3: Missing MX Fields
```
Error: [Sales Invoice]: mx_payment_option, mode_of_payment
Cause: Sales Invoice missing Mexico-specific CFDI fields
Status: Fixed by adding fallback values
```

### Iteration 4: Mixed Results (3/6 Success)
```
Success: 3 invoices created
Errors:
- Cost Center is a group cost center
- customer_address missing
- "Billing Address does not belong to the Partially Fixed
 customer"
Status:```

### Iteration 5: Current State (2 SOs Remaining)
```
Remaining Errors:
1. SO-01825-Barentz Italia Specchiasol: mx_product_service_key missing
2. SO-02125-Barentz Italia Specchiasol: Could not find Customer Address: 
   "Barentz Italia Specchiasol-Verified-Billing"
```

## Root Cause Analysis

The fundamental issue is **data inconsistency** in the source documents:

1. **Address Links**: ERPNext validates that `customer_address` and `billing_address` must have a valid **Dynamic Link** to the Customer. Simply setting the `customer` field on an Address document is not sufficient.

2. **Truth Hierarchy Failure**: The agent attempts to find addresses from:
   - Quotation (truth source)
   - Customer's existing addresses
   - Delivery Note
   - Auto-creation
   
   But the addresses found or created often lack proper Dynamic Link records.

3. **Missing CFDI Fields**: Mexico-specific fields (`mx_payment_option`, `mx_cfdi_use`, `mx_product_service_key`) are not always populated from source documents.

4. **Group Cost Centers**: Sales Orders may reference Cost Centers that are marked as "Group" which cannot be used in transactions.

## Current Code Approach

The agent implements a "Smart Validation" pattern:

```python
def _smart_validate_and_fix_sales_invoice(self, si, so, so_name, from_dn):
    # 1. Address Resolution (Truth Hierarchy)
    # 2. MX CFDI Fields
    # 3. Debit To Account
    # 4. Cost Center
    # 5. Final validation
```

## Questions for the Community

1. **Best Practice**: What is the recommended way to programmatically create/validate Customer Addresses in ERPNext to ensure they pass the `validate_links()` check?

2. **API Access**: Is there a helper function in ERPNext to get a valid billing address for a Customer that already has Dynamic Links?

3. **Truth Source**: For Sales Orders created from Quotations, should we always pull addresses from the Quotation even if the Customer has addresses?

4. **CFDI Fields**: What's the best source for `mx_product_service_key` (product/service code for CFDI) - Item Master or transaction level?

## Files Modified

- `raven_ai_agent/agents/sales_order_followup_agent.py`

## Related Documentation

- ERPNext Sales Invoice: https://docs.erpnext.com/docs/v14/user/manual/en/accounts/sales-invoice
- CFDI Mexico: https://docs.erpnext.com/docs/v14/user/manual/en/regional/mexico
- Dynamic Link: https://docs.erpnext.com/docs/v14/user/manual/en/customize-erpnext/articles/static-dynamic-links

---

**Status**: In Development - Iterative Fixes
**Last Updated**: 2026-03-11
**Author**: Raven AI Agent Development Team
