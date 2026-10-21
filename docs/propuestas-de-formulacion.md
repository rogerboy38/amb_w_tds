# Propuestas de Formulación

The report replaces the "propuesta de inventario" email that Calidad sends to Dirección.
Dirección compares the candidate proposals for a product against its TDS, picks one, and
that proposal becomes the Work Order BOM for Producción.

## Flow

1. **Proposal.** Formulación creates one BOM Formula per candidate blend: `formula_type`
   Mix, a draft, Mix Input lines pointing at Batch AMB sublots, and Target TDS set.
2. **Gate.** "Simular" (`simulate_blend`) resolves each line's COA (explicit link →
   the root Batch AMB's `coa_amb` / `coa_reference` → a submitted COA AMB / AMB2 by
   batch or golden number). It then writes the predicted blend per TDS parameter to
   Predicted Analytics. These are estimates; release gates on the measured value.
3. **Comparison.** Run the Script Report **Propuestas de Formulación** with `Producto`
   (and optionally `Pedido`, `TDS`):
   - **Excel/CSV:** the report's Export.
   - **PDF:** the "PDF para Dirección" button, which renders the Print Format
     **Propuestas de Formulación**. It can also be printed from any proposal's form,
     scoped to that proposal's Sales Order.
4. **Decision.** Dirección marks the chosen proposal and signs (Aprobó / Revisó /
   Elaboró).
5. **Work Order.** The chosen proposal goes to Producción as the Work Order BOM.

## What the report shows

- **Comparativo:** one row per proposal with kg, the three headline values, CUMPLE and
  N° lotes.
- **Per proposal:**
  - the lot lines: lote, kg, Acemannan, Aloína, Arsénico, % mezcla;
  - the gate's TOTAL;
  - one compliance row per TDS parameter: predicted value, Mín, Máx, ✓ / ✗.

## Rules

- **No invented numbers.**
  - Lot values come from the COA the gate resolves.
  - The TOTAL comes from the gate's stored Predicted Analytic rows, i.e. the last
    Simular. Re-run Simular after editing lines.
  - Bounds come from the TDS: the one given in the filter, else the newest submitted TDS
    whose Product Item is the product.
  - Pass/fail uses the gate's own comparator and the gate's own reading of the TDS.
- **Headline columns** are found in the TDS by name pattern (acemann…, aloin…, arsen…;
  a "total"/"content" name wins when several match). The column header shows the TDS's
  own UOM. A parameter the TDS lacks shows blank. Every TDS parameter is in the
  compliance rows regardless.
- **A line without a COA** keeps its kg and is marked "sin COA" with the gate's reason.
  It is never dropped.
- **Overall status per proposal:**
  - **CUMPLE:** every bounded TDS parameter is predicted and within bounds.
  - **NO CUMPLE:** at least one is out of bounds.
  - **INCOMPLETO:** none fail, but some lack a prediction.
  - **SIN SIMULACIÓN:** Simular has not been run.
  - **SIN TDS:** no TDS was found; values are shown without bounds or pass/fail.
- **Read-only.** The report and the print format create and write nothing.
- **Permissions.** Proposals are read through `frappe.get_list`, so a user sees only the
  BOM Formula records they may read. The report's roles match BOM Formula's four Custom
  DocPerm roles.
