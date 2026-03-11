Batch 4 Bug Report — Raven AI Agent
 QTNs 0775-0783 + 0077  2026-03-09 00:00 CST
 4 New Bugs Found — Agent Must Handle These
 
Truth Hierarchy (Human-Reviewed)
Quotation payment_schedule.credit_days is the single source of truth for PUE/PPD. All 10 QTNs in this batch
have credit_days = 30 on the Quotation payment_schedule (human-reviewed). Therefore ALL 10 must get PPD.
The template name (e.g. "T/T In Advance") is irrelevant — the actual credit_days value on the Quotation overrides it.
Rule: PO > Quotation > Sales Order. The Quotation has true data. The agent must read
payment_schedule[0].credit_days from the source Quotation, not the template definition, not the SO, not the
Customer master.
Quotation Truth Table
QTN
Customer
Template Name
QTN
credit_days
Expected
0775
ALBAFLOR
30 days after Invoice Date
30
PPD
0776
DAEHAN CHEMTECH
30 days after Invoice Date
30
PPD
0777
N BIOTECH
T/T In Advance
30
PPD
0778
BARENTZ HELLAS
30 days after Invoice Date
30
PPD
0779
BARENTZ NORTH
AMERICA
30 days after Invoice Date
30
PPD
0077
BARENTZ Service S.p.A.
T/T In Advance
30
PPD
0780
DON PULCRO
T/T In Advance
30
PPD
0781
BERRY GLOBAL
T/T In Advance
30
PPD
0782
CHARKIT CHEMICAL
3% 10 NET 30
30
PPD
0783
ALBAFLOR
T/T In Advance
30
PPD
Note: 5 QTNs have template "T/T In Advance" but the human reviewer set credit_days=30 on the payment_schedule. The QTN data is truth.
Pipeline Results
QTN
Customer
SO
DN
SI
PUE/P
PD
Bugs
0775
ALBAFLOR
ds=1
ds=1
ds=0 x2
PUE
BUG 22 + BUG 23
0776
DAEHAN
CHEMTECH
ds=1
ds=0 x2
ds=0
PUE
BUG 22 + BUG 23
0777
N BIOTECH
ds=1
ds=1
ds=0
PUE
BUG 22
0778
BARENTZ HELLAS
ds=1
ds=0
none
--
incomplete
0779
BARENTZ NA
ds=1
ds=1
ds=0 x2
PUE
BUG 22 + BUG 23
0077
BARENTZ Service
ds=1
ds=0 x2
error
--
BUG 23 + BUG 24
0780
DON PULCRO
ds=1
ds=1
ds=0
PPD
OK
0781
BERRY GLOBAL
ds=0
none
none
--
not reached

QTN
Customer
SO
DN
SI
PUE/P
PD
Bugs
0782
CHARKIT
CHEMICAL
ds=0
none
none
--
not reached
0783
ALBAFLOR
ds=0
none
none
--
not reached

BUG 22 — PUE/PPD: Agent Ignores Quotation credit_days
Severity: P1 HIGH | Affects: truth_hierarchy.py
Problem
Despite BUG 19 fixes (commits b05ae2b, 146e9a2), the agent still assigns PUE to invoices that should be PPD. Out of
5 invoices created, 4 got PUE when all should be PPD (QTN credit_days=30).
Only QTN 0780 (DON PULCRO) correctly got PPD. The other 4 (0775, 0776, 0777, 0779) all got PUE.
Evidence
QTN
Invoice
QTN
credit_days
Expected
Got
0775
ACC-SINV-2026-00035
30
PPD
PUE
0776
ACC-SINV-2026-00037
30
PPD
PUE
0777
(from agent log)
30
PPD
PUE
0779
ACC-SINV-2026-00040
30
PPD
PUE
0780
ACC-SINV-2026-00044
30
PPD
PPD
Root Cause
The truth_hierarchy.py R1 logic is likely reading the Payment Terms Template definition (credit_days=0 for "T/T In
Advance") instead of the Quotation payment_schedule[0].credit_days (which is 30, human-set). The agent must
walk the truth chain: Quotation.payment_schedule.credit_days is the authoritative source, not the template master.
Fix Required
In truth_hierarchy.py, the PUE/PPD determination must: (1) Read the source Quotation linked to the SO. (2) Get
payment_schedule[0].credit_days from that QTN. (3) If credit_days > 0 then PPD, else PUE. Never use the
template master definition. Never use the SO or SI payment_schedule (those may have been overwritten).
BUG 23 — Agent Creates Duplicate DN and SI
Severity: P1 HIGH | Affects: sales.py, smart_invoice.py idempotency
Problem
The agent creates duplicate Delivery Notes and Sales Invoices when the same command is sent twice (which happens
naturally in pipeline retries or if the user re-sends). The agent should detect existing documents and skip creation.
Evidence
QTN
Issue
Detail
0775
2 Sales Invoices
ACC-SINV-2026-00035 + duplicate created on retry
0776
2 Delivery Notes
MAT-DN-2026-00029 (Draft) + MAT-DN-2026-00030 on retry
0779
2 Sales Invoices
ACC-SINV-2026-00040 + ACC-SINV-2026-00041 (identical)
0077
2 Delivery Notes
MAT-DN-2026-00035 + MAT-DN-2026-00036 (identical)
Root Cause
The SO idempotency check (BUG 13 fix) works — agent correctly says "SO already exists". But DN and SI creation
have no idempotency check. The agent blindly creates a new DN/SI each time without checking if one already exists
for that SO.

Fix Required
Before creating a DN: check frappe.get_list("Delivery Note",
filters={"items.against_sales_order": so_name}). Before creating a SI: check
frappe.get_list("Sales Invoice", filters={"items.sales_order": so_name}). If document exists,
return it instead of creating a duplicate.

BUG 24 — Invoice Fails: customer_address Missing
Severity: P2 MEDIUM | Affects: smart_invoice.py
Problem
Invoice creation for QTN 0077 (BARENTZ Service S.p.A.) fails with: Error: [Sales Invoice,
ACC-SINV-2026-00042]: customer_address. The agent does not resolve or set the customer_address field
when creating the SI.
Evidence
Agent response at 00:14:41: "Error: [Sales Invoice, ACC-SINV-2026-00042]: customer_address". Retry
at 00:14:46 produced same error with ACC-SINV-2026-00043.
Root Cause
The Customer "BARENTZ Service S.p.A." likely has no default billing address configured, or the agent does not copy
the address from the SO/QTN to the SI. The CFDI/SAT invoice requires customer_address to be populated. The agent
should: (1) Copy address from the source SO. (2) If SO has no address, look up from Customer master. (3) If still
missing, report a clear error naming the missing field and Customer.
BUG 21 — RECAP: SyntaxError in agent.py (FIXED)
Severity: P0 CRITICAL | Status: Fixed in 19ec9c4
Commit edafeaf introduced a duplicate SYSTEM_PROMPT definition causing SyntaxError. Fixed in commit 19ec9c4 +
3c7e2b1. Agent is operational again. Detailed report in bug_report_21_syntax_error.pdf.
Priority Actions for Dev Team
Bug
Action
Priorit
y
1
BUG 22
Fix PUE/PPD: read QTN payment_schedule.credit_days, not template
definition. credit_days > 0 = PPD. Quotation is truth source.
P1
2
BUG 23
Add idempotency checks for DN and SI creation. Check if DN/SI
already exists for the SO before creating. Return existing doc instead
of duplicating.
P1
3
BUG 24
Resolve customer_address from SO or Customer master when
creating SI. Report clear error if address truly missing.
P2
4
Cleanup
Delete duplicate DNs and SIs created during this batch. QTNs 0775,
0776, 0779, 0077 all have duplicates.
P2
5
Re-run
After fixes: re-run batch for QTNs 0775-0783 + 0077. All 10 must
result in PPD per QTN truth. QTNs 0781, 0782, 0783 never reached.
P1
Lesson for Raven Agent
The agent must be smarter about the migration context:
1. Truth hierarchy: Quotation (human-reviewed) is the source of truth. Read credit_days from QTN
payment_schedule, not from template definitions.
2. Idempotency: Every create operation must check if the document already exists. SO check works. DN and SI
checks are missing.

3. Address resolution: When creating a SI, copy customer_address from the chain (QTN → SO → SI). Do not
assume Customer master has a default address.
4. Migration data: QTNs come from 2024 migration. Some have pre-existing draft SOs from the initial data load.
The agent must handle these gracefully.
Batch 4 Bug Report generated by Perplexity Computer for AMB Wellness Migration Team. 2026-03-09 00:19 CST. Production HEAD: 19ec9c4.