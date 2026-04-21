# V13.5.0 P2 — Retained Untagged Notifications

**Date:** 2026-04-20
**Scope:** ERPNext core system notifications (is_standard=1)

The following 13 notifications remain with `module=NULL` in the database
and are **NOT** exported to any app's fixtures. They belong to ERPNext
core and are recreated automatically on fresh installs.

## Retained Notifications (13)

1. Integration Request
2. Error Log
3. Material Request Cancelled - Email
4. Material Request Submitted - Email
5. Purchase Order Cancelled - Email
6. Purchase Order Submitted - Email
7. Sales Order Cancelled - Email
8. Sales Order Submitted - Email
9. Supplier Quotation Cancelled - Email
10. Supplier Quotation Submitted - Email
11. Work Order Cancelled - Email
12. Work Order Submitted - Email
13. User Account Created - Email

## Rationale

These notifications are part of ERPNext core framework. Exporting them
to custom app fixtures would cause duplication and migration conflicts.
The `is_standard=1` flag identifies them as core system notifications.

## Verification

Query used to identify retained notifications:
\`\`\`sql
SELECT name FROM \`tabNotification\` 
WHERE (module IS NULL OR module = '') 
  AND is_standard = 1;
\`\`\`
Count: 13 records as of 2026-04-20 sandbox state.

No Action Required
These notifications are intentionally left untagged and will not appear
in any V13.5.0 app's fixtures. This is correct and compliant behavior.
