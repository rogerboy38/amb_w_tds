FIX REQUEST
BUG 22 — P1 CRITICAL
 March 9, 2026
 
PUE/PPD Misresolution: truth_hierarchy
Reads SO Instead of Tracing Back to QTN
Root cause analysis for BUG 22 with database evidence, code trace, and proposed Tier 0 fix.
Affects 8 of 10 Batch 4 QTNs — all should be PPD (credit_days=30) but resolved as PUE.
Executive Summary
The truth_hierarchy.resolve_pue_ppd() function reads SO.payment_schedule.credit_days as its Tier 1
(ground truth). However, the Sales Orders for Batch 4 were bulk-imported on Jan 5 with credit_days=0,
while the human-reviewed Quotations have credit_days=30. Since the agent passes the SO (not the QTN)
as source_doc, the function reads 0 and returns PUE instead of PPD.
The fix requires adding a Tier 0 to truth_hierarchy.resolve_pue_ppd() that traces the SO back to its linked
Quotation and reads the QTN's payment_schedule.credit_days first, honoring the user-defined truth
hierarchy: PO > Quotation > Sales Order.
AFFECTED
ROOT CAUSE
PROPOSED FIX
8 of 10 QTNs show PUE
instead of PPD on SI
SO.payment_schedule has
credit_days=0 (from import)
Add Tier 0: trace SO to
linked QTN, read QTN data
Call Chain Trace
The exact code path from agent command to PUE/PPD decision:
Step
Location
Code
What Happens
1
sales.py:788
self._discover_mx_cfdi_fields(so)
Passes SO as source_doc
2
sales.py:32-36
resolve_mx_cfdi_fields(source_doc=so, ...)
Delegates to truth_hierarchy
3
truth_hierarchy.py:
313
resolve_pue_ppd(source_doc=so, ...)
Enters PUE/PPD resolver
4
truth_hierarchy.py:
101-102
schedule = source_doc.payment_schedule
Reads SO's schedule (Tier 1)
5
truth_hierarchy.py:
112
cd = getattr(row, 'credit_days', 0)
Gets credit_days = 0
6
truth_hierarchy.py:
122-125
return 'PUE'
ALL credit_days=0 -> PUE (WRONG)
The problem is at Step 4: the function trusts SO.payment_schedule as ground truth, but the SO's
credit_days was corrupted during the Jan 5 bulk import (set to 0 instead of 30). The QTN
(human-reviewed) has the correct credit_days=30.

Database Evidence
Direct MariaDB query results from production (erp.sysmayal2.cloud) comparing QTN vs SO
payment_schedule.credit_days for all 10 Batch 4 Quotations:
QTN
Customer
QTN
credit_da
ys
SO Name
SO
credit_da
ys
Expected
Actual
0775
ALBAFLOR
30
SO-00775-ALBAFLOR
0
PPD
PUE
0776
DAEHAN
30
SO-00776-DAEHAN...
0
PPD
PUE
0777
N BIOTECH
30
SO-00777-N BIOTECH...
0
PPD
PUE
0778
BARENTZ
HELLAS
30
SO-00778-BARENTZ H...
0
PPD
PUE
0779
BARENTZ NA
30
SO-00779-BARENTZ NA...
0
PPD
PUE
0077
BARENTZ Svc
30
SO-118626-BARENTZ...
30
PPD
PPD
0780
DON PULCRO
30
SO-00780-DON PULCRO...
30
PPD
PPD
0781
BERRY GLOBAL
30
SO-00781-BERRY...
0
PPD
PUE
0782
CHARKIT
30
SO-00782-CHARKIT...
0
PPD
PUE
0783
ALBAFLOR
30
SO-00783-ALBAFLOR
0
PPD
PUE
Key Observations
ALL 10 QTNs have credit_days=30 (human-reviewed, correct)
8 of 10 SOs have credit_days=0 (from Jan 5 bulk import, corrupted)
SO-00780 (DON PULCRO) kept credit_days=30 during import (the only correctly imported SO)
SO-118626 (BARENTZ Service) was created fresh by raven_ai_agent via make_sales_order() on March
9 — correctly mapped credit_days=30 from QTN
This confirms: when ERPNext's make_sales_order() creates an SO from a QTN, it correctly maps
Payment Schedule rows including credit_days. The problem is ONLY with pre-imported SOs.
However, architecturally, the truth_hierarchy should ALWAYS trace back to the QTN as the definitive
source per the user's truth hierarchy: PO > QTN > SO
Payment Terms Template Definitions
Template
Payment Term
credit_days
Meaning
T/T In Advance
100% payment in advance
0
Immediate = PUE
30 days after Invoice Date
30 days after Invoice Date
30
Credit = PPD
3% 10 NET 30
30 days after Invoice Date
30
Credit = PPD
Note: Some QTNs have payment_terms_template = 'T/T In Advance' (which has credit_days=0 in the
template) but the human reviewer set payment_schedule.credit_days=30 on the QTN itself. This is why Tier
1 (document data) MUST prevail over Tier 2 (template DB) — and why tracing back to the QTN document is
essential.

Proposed Fix: Add Tier 0
Add a Tier 0 at the top of resolve_pue_ppd() that traces the source_doc (SO) back to its linked Quotation
and reads the QTN's payment_schedule.credit_days. This honors the truth hierarchy: PO > QTN > SO.
Modified truth_hierarchy.resolve_pue_ppd()
def resolve_pue_ppd(source_doc=None, ...) -> str:
doc_name = getattr(source_doc, "name", None)
 
--- TIER 0: Trace back to Quotation (NEW) ---
if source_doc and source_doc.doctype == "Sales Order":
try:
qtn_name = frappe.db.get_value(
"Sales Order Item",
{"parent": source_doc.name},
"prevdoc_docname"
)
if qtn_name:
qtn = frappe.get_doc("Quotation", qtn_name)
qtn_schedule = getattr(qtn, "payment_schedule", [])
if qtn_schedule:
max_cd = max(
int(getattr(r,"credit_days",0) or 0)
for r in qtn_schedule
)
if max_cd > 0:
log_decision("mx_payment_option","PPD",0,
f"Tier 0: QTN {qtn_name} has cd={max_cd}",
doc_name, audit)
return "PPD"
else:
log_decision("mx_payment_option","PUE",0,
f"Tier 0: QTN {qtn_name} ALL cd=0",
doc_name, audit)
return "PUE"
except Exception:
pass Fall through to existing Tier 1
 
--- TIER 1: Document payment_schedule (existing) ---
schedule = ...
(rest unchanged)
Changes Required
File
Function
Change

truth_hierarchy.py
resolve_pue_ppd()
Add Tier 0 block before Tier 1 (~20 lines). When source_doc is a Sales
Order, trace SO -> QTN via Sales Order Item.prevdoc_docname, then read
QTN.payment_schedule.credit_days.
truth_hierarchy.py
log_decision()
Add tier=0 to tier_labels dict: {0: 'QTN Traceback', 1: 'Document', ...}
truth_hierarchy.py
validate_pipeline()
Update CFDI validation at line 507 to also pass QTN reference for better
audit messages.
Updated Resolution Order
Tier
Name
Data Source
Status
Tier 0
QTN Traceback
SO -> linked QTN -> QTN.payment_schedule.credit_days
NEW
Tier 1
Document
source_doc.payment_schedule.credit_days
Existing
Tier 2
Template DB
Payment Terms Template Detail.credit_days
Existing
Tier 3
Keywords
Pattern match on template name
Existing
Tier 4
Default
PUE (no credit data found)
Existing

Testing & Validation Plan
Test Cases
ID
Scenario
Expected Result
Notes
TC-1
SO with QTN credit_days=30, SO
credit_days=0
PPD (from Tier 0 QTN)
Validates fix for the 8 failing QTNs
TC-2
SO with QTN credit_days=30, SO
credit_days=30
PPD (from Tier 0 QTN)
Both agree, Tier 0 wins
TC-3
SO with QTN credit_days=0, SO
credit_days=0
PUE (from Tier 0 QTN)
True advance payment case
TC-4
SO with no linked QTN (direct SO)
Falls to Tier 1 (SO data)
Backward compatible
TC-5
SO with QTN not found (deleted)
Falls to Tier 1 (SO data)
Graceful fallback
TC-6
DN passed as source_doc
Tier 1 reads DN schedule
No Tier 0 for non-SO docs
Batch 4 Expected Results After Fix
After deploying the Tier 0 fix, re-running Batch 4 should produce PPD for all 10 QTNs. However, BUGs 23
(duplicate DN/SI) and 24 (customer_address) must also be fixed first to avoid creating additional
duplicates.
QTN
Before Fix
After Fix
Tier Used
0775 ALBAFLOR
PUE
PPD
Tier 0 (QTN cd=30)
0776 DAEHAN
PUE
PPD
Tier 0 (QTN cd=30)
0777 N BIOTECH
PUE
PPD
Tier 0 (QTN cd=30)
0778 BARENTZ HELLAS
PUE
PPD
Tier 0 (QTN cd=30)
0779 BARENTZ NA
PUE
PPD
Tier 0 (QTN cd=30)
0077 BARENTZ Svc
PPD
PPD
Tier 0 (QTN cd=30)
0780 DON PULCRO
PPD
PPD
Tier 0 (QTN cd=30)
0781 BERRY GLOBAL
N/A (not reached)
PPD
Tier 0 (QTN cd=30)
0782 CHARKIT
N/A (not reached)
PPD
Tier 0 (QTN cd=30)
0783 ALBAFLOR
N/A (not reached)
PPD
Tier 0 (QTN cd=30)
Deployment Notes
File to modify: raven_ai_agent/api/truth_hierarchy.py
Production HEAD: 19ec9c4 (post BUG-21 fix)
No changes needed to sales.py or workflow_orchestrator.py — the fix is self-contained in
truth_hierarchy.py
Backward compatible: if source_doc is not a Sales Order, or if QTN lookup fails, falls through to
existing Tier 1
Deploy: git pull upstream main + restart 5 containers

Risk: LOW — adds a read-only DB lookup before existing logic, does not modify any document
Report generated by Perplexity Computer for AMB Wellness migration team. Production data queried on March 9, 2026 from erp.sysmayal2.cloud.