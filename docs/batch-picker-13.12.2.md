# Batch Reference picker and the BOM Formula gate (13.12.2)

## The picker
`COA AMB` and `COA AMB2` both set `frm.set_query('batch_reference', { query: 'amb_w_tds.amb_w_tds.api.batch_picker.search_batches' })`. The terms live in `amb_w_tds/amb_w_tds/api/batch_picker.py` only:

| term | value |
|---|---|
| `batch_status` | not `Cancelled` |
| `quality_status` | `Pending`, `Hold`, or empty (a batch nobody has assessed yet) |
| item | **no filter**; shown on each line |
| text | matches batch id, title, golden number, item |
| order / page | newest first, `creation desc, name desc`; the form's page size |
| line shown | batch id, item (`item_to_manufacture`), `quality status / batch status` |

Passed and Failed batches and Cancelled ones are not listed. Why no item filter: the COA's product is a variant Item and the batch holds the base item (REPLY-TASKS-237 A.1), so no string rule was right; the person chooses with the item in view. The server still accepts any batch name typed or sent through the API: the picker is a UI list, not a validation.

## The gate
`BOMFormula._resolve_coa` resolves a line's certificate in this order: (1) the explicit line link; (2) the root batch's `coa_amb` / `coa_reference`; (3) a **submitted COA AMB** whose `batch_reference` is the root or whose golden number matches; (4) none. As of 13.12.2 step 3 does not look at COA AMB2: nothing compares its product with the batch's item. A COA AMB2 is used through (1) only, until Cut 2b.
`Formulation Settings.default_coa_source` is not read by this function or by any other code; the gate gives the same answer under both values (a test asserts it).

## By hand on VPT after the cut
1. Open a new COA AMB2, open Batch Reference: a list of batches with their items (N on the sandbox: 76; VPT and prod will differ).
2. Pick one, save, submit: one Info comment ("Batch not updated: link to COA AMB2 not available yet"), the batch unchanged.
3. A BOM Formula whose line's root batch is that batch must **not** take that COA AMB2 as the batch's certificate: the line reads "no COA" (resolution `none`) unless the line names the COA AMB2 itself or something else certifies the batch (the root batch's own COA AMB link, or a submitted COA AMB).
