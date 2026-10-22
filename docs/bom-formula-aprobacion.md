# BOM Formula: approval and release (13.11.0)

Formula → authorize → release → standard BOM → Work Order, all inside ERPNext.

| step | state | who | what happens |
|---|---|---|---|
| 1 | **Borrador** | Calidad (Quality Engineer / Manager), Formulación | Prepare the proposal; run *Simular*. Check cost and the TDS verdict (report *Propuestas de Formulación*). |
| 2 | **En Revisión** | Quality Engineer: *Enviar a revisión* | Awaits Calidad's authorization. |
| 3 | **Autorizado** | Quality Manager: *Autorizar* (or *Devolver* to Borrador) | `cost_approval` = approved; *Autorizado por* / *Fecha de autorización* are recorded. |
| 4 | **Liberado** | Marketing Manager (Dirección): *Liberar a producción* | A **standard BOM** is built and submitted for the product. `BOM.bom_formula` points to the formula, and the formula's *BOM liberada* points to the BOM. |
| 4' | **Rechazado** | Marketing Manager: *Rechazar* (or *Devolver a Calidad*) | No BOM. `cost_approval` = rejected (or withdrawn when returned). |
| 5 | — | Planeación | Creates the **Work Order** for the product using that BOM (normal ERPNext; the release creates no Work Order). |

## The release

**Each Mix Input row becomes one BOM item:** the row's Item (else its Batch AMB sublot's
item), with qty = kg, uom Kg. The BOM quantity is the total kg.

**If any row can't be resolved, nothing is created.** That covers a row with no item, a
kg ≤ 0, or a product whose stock unit isn't Kg. The release is refused with a message
naming the rows.

**Releasing again reuses** the BOM recorded in *BOM liberada* while it is submitted and
active.

**Default BOM.** The BOM is created with "default" off. ERPNext still makes it the
product's default if the product has no default BOM yet; it never replaces an existing
default.

## Notes

- **BOM Formula is never submitted.** The approval lives in its state (`workflow_state`).
- **Sample formulas never stay released.** The `FMIX-*` / `MEMCAL-*` samples are
  re-created by every migrate, so they return to Borrador. Release real proposals only.
