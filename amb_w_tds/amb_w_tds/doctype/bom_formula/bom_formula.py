import frappe
from frappe.model.document import Document
from frappe.utils import flt
from amb_w_tds.formulation import engine   # imported, not duplicated

_METHOD_MAP = {
    "mass_avg": engine.BlendMethod.MASS_AVG,
    "hplus_avg": engine.BlendMethod.PH_HPLUS,
    "worst_case": engine.BlendMethod.WORST_CASE,
    "all_pass": engine.BlendMethod.ALL_PASS,
}
_CRITICAL_METHODS = {"hplus_avg", "worst_case", "all_pass"}   # pH / micro / qualitative are release-critical
_PASS_TOKENS = {"PASS", "NEGATIVE", "NEGATIVO", "AUSENTE", "ABSENT", "CONFORMS", "OK", "COMPLIES"}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _qual(result):
    return str(result or "").strip().upper() in _PASS_TOKENS


def _fmt(v):
    if isinstance(v, bool):
        return "PASS" if v else "FAIL"
    if v is None:
        return ""
    return f"{v:.4g}" if isinstance(v, float) else str(v)


class BOMFormula(Document):
    # ---- THE DOOR: release gates on the MEASURED value, never the estimate ----
    def validate(self):
        for r in (self.get("custom_mix_predicted") or []):
            if r.confirmed and str(r.measured_value or "").strip() != "":
                r.release_ok = "Pass" if self._release_from_measured(r) else "Fail"
            else:
                r.release_ok = "Pending"     # never auto-confirm

    def _release_from_measured(self, r):
        if r.blend_method == "all_pass":
            return str(r.measured_value).strip().upper() in _PASS_TOKENS
        v = _num(r.measured_value)
        if v is None:
            return False
        if r.min_value not in (None, "") and v < flt(r.min_value):
            return False
        if r.max_value not in (None, "") and v > flt(r.max_value):
            return False
        return True

    # ---- read-only preview: predict -> (lab measures) -> confirm ----
    @frappe.whitelist()
    def simulate_blend(self):
        lots = self._build_lots()
        params = self._build_parameters()
        if not lots:
            frappe.throw("Add Mix Input Lines with a COA AMB2 before simulating.")
        if not params:
            frappe.throw("Set a TDS Target with parameter rows before simulating.")
        results = engine.blend(lots, params)
        uom = {p.name: p.uom for p in params}
        self.set("custom_mix_predicted", [])
        for name, br in results.items():
            self.append("custom_mix_predicted", {
                "parameter": name, "blend_method": br.blend_method,
                "computed_value": _fmt(br.computed_value),
                "is_estimate": 1 if br.is_estimate else 0,
                "requires_lab_measurement": 1 if br.requires_lab_measurement else 0,
                "in_spec_estimate": 1 if br.in_spec_estimate else 0,
                "critical": 1 if br.critical else 0,
                "min_value": br.min_value, "max_value": br.max_value, "uom": uom.get(name, ""),
                "measured_value": None, "confirmed": 0, "release_ok": "Pending", "note": br.note,
            })
        self.custom_total_input_kg = sum(flt(l.mass_kg) for l in lots)
        self.custom_predicted_cost = self._predicted_cost()
        self.save(ignore_permissions=True)   # DRAFT only — never submit; no Batch AMB / COA / WO created
        return {
            "lines": len(lots), "parameters": len(params), "predicted_rows": len(results),
            "total_input_kg": self.custom_total_input_kg, "predicted_cost": self.custom_predicted_cost,
            "requires_lab": sum(1 for b in results.values() if b.requires_lab_measurement),
            "out_of_spec_estimate": sum(1 for b in results.values() if b.in_spec_estimate is False),
        }

    def _build_lots(self):
        lots = []
        for line in (self.get("custom_mix_input_lines") or []):
            if not line.coa_amb2:
                continue
            vals = {}
            for p in frappe.get_all("COA Quality Test Parameter",
                                    filters={"parent": line.coa_amb2, "parenttype": "COA AMB2"},
                                    fields=["specification", "value", "result"]):
                if not p.specification:
                    continue
                v = _num(p.value)
                vals[p.specification] = v if v is not None else _qual(p.result)
            lots.append(engine.Lot(
                lot_id=line.lot_id or line.batch_amb_sublot or line.coa_amb2,
                mass_kg=flt(line.mass_kg), values=vals))
        return lots

    def _build_parameters(self):
        if not self.custom_tds_target:
            return []
        out = []
        for row in frappe.get_all("Item Quality Inspection Parameter",
                                  filters={"parent": self.custom_tds_target,
                                           "parenttype": "TDS Product Specification"},
                                  fields=["specification", "custom_blend_method", "min_value",
                                          "max_value", "numeric", "custom_uom", "custom_is_title_row"]):
            if not row.specification or row.custom_is_title_row:
                continue
            m = row.custom_blend_method or "mass_avg"
            out.append(engine.Parameter(
                name=row.specification, blend_method=_METHOD_MAP.get(m, engine.BlendMethod.MASS_AVG),
                numeric=bool(row.numeric),
                min_value=row.min_value if row.min_value not in (None, "") else None,
                max_value=row.max_value if row.max_value not in (None, "") else None,
                critical=(m in _CRITICAL_METHODS), uom=row.custom_uom or ""))
        return out

    def _predicted_cost(self):
        c = 0.0
        for line in (self.get("custom_mix_input_lines") or []):
            if not line.batch_amb_sublot:
                continue
            item = (frappe.db.get_value("Batch AMB", line.batch_amb_sublot, "item_on_batch")
                    or frappe.db.get_value("Batch AMB", line.batch_amb_sublot, "main_item"))
            rate = frappe.db.get_value("Item", item, "valuation_rate") if item else 0
            c += flt(line.mass_kg) * flt(rate)
        return c

    # QA precondition before trusting any mass-avg
    @frappe.whitelist()
    def blend_uniformity_ok(self, sample_results, rsd_max=5.0):
        import json as _j
        if isinstance(sample_results, str):
            sample_results = _j.loads(sample_results)
        return engine.blend_uniformity_ok([float(x) for x in sample_results], float(rsd_max))
