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
_DESCRIPTIVE = "DESCRIPTIVE — lab confirms"
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
        self._recompute_mix_totals()
        for r in (self.get("predicted_analytics") or []):
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
        if r.tds_min not in (None, "") and v < flt(r.tds_min):
            return False
        if r.tds_max not in (None, "") and v > flt(r.tds_max):
            return False
        return True

    # ---- Mix tab arithmetic: totals and the Σ% / Σkg check ----
    def _recompute_mix_totals(self):
        lines = self.get("mix_input_lines") or []
        for line in lines:
            line.amount = flt(line.kg) * flt(line.unit_cost)
        self.total_input_kg = sum(flt(l.kg) for l in lines)
        self.total_pct = sum(flt(l.pct) for l in lines)
        self.total_amount = sum(flt(l.amount) for l in lines)
        self.blended_cost_per_kg = (
            flt(self.total_amount) / flt(self.total_input_kg) if flt(self.total_input_kg) else 0
        )
        if not lines:
            self.sum_check = ""
            return
        d_pct = flt(self.total_pct) - 100.0
        d_kg = flt(self.total_input_kg) - flt(self.batch_size_kg)
        ok_pct = abs(d_pct) <= 0.01
        ok_kg = abs(d_kg) <= 0.1 if flt(self.batch_size_kg) else True
        self.sum_check = "OK" if (ok_pct and ok_kg) else (
            f"Δ% {d_pct:+.2f} · Δkg {d_kg:+.2f}"
        )

    # ---- read-only preview: predict -> (lab measures) -> confirm ----
    @frappe.whitelist()
    def simulate_blend(self):
        lots, lines_total, lines_with_coa = self._build_lots()
        params = self._build_parameters()

        # A COA-less formula is the normal prod state, not an error: say so and
        # predict nothing. Never a vacuous PASS on an empty list.
        if not lots:
            self.set("predicted_analytics", [])
            msg = (f"no COA AMB2 on {lines_total} of {lines_total} lines — nothing predicted"
                   if lines_total else "no Mix Input Lines — nothing predicted")
            self.prediction_note = msg
            self._recompute_mix_totals()
            self.save(ignore_permissions=True)
            frappe.msgprint(msg)
            return {"lines": lines_total, "lines_with_coa": lines_with_coa,
                    "parameters": len(params), "predicted_rows": 0, "note": msg}
        if not params:
            msg = "Set a TDS Target with parameter rows before simulating — nothing predicted."
            self.set("predicted_analytics", [])
            self.prediction_note = msg
            self._recompute_mix_totals()
            self.save(ignore_permissions=True)
            frappe.msgprint(msg)
            return {"lines": lines_total, "lines_with_coa": lines_with_coa,
                    "parameters": 0, "predicted_rows": 0, "note": msg}

        results = engine.blend(lots, params)
        uom = {p.name: p.uom for p in params}
        unresolved = []

        pmap = {p.name: p for p in params}
        self.set("predicted_analytics", [])
        for name, br in results.items():
            qp = self._resolve_parameter(name)
            if qp is None:
                unresolved.append(name)
            numeric_value = br.computed_value if isinstance(br.computed_value, (int, float)) \
                and not isinstance(br.computed_value, bool) else None
            row = {
                "parameter": qp,
                "predicted_value": 0,
                "blend_method": br.blend_method,
                "tds_min": br.min_value,
                "tds_max": br.max_value,
                "uom": uom.get(name, ""),
                "is_estimate": 0,
                "requires_lab_measurement": 1,
                "in_spec_estimate": 1 if br.in_spec_estimate else 0,
                "critical": 1 if br.critical else 0,
                "status": "" if br.in_spec_estimate is None else ("Pass" if br.in_spec_estimate else "Fail"),
                "measured_value": None,
                "confirmed": 0,
                "release_ok": "Pending",
                "note": br.note,
            }
            # AMENDMENT A3: 16 rows in THREE classes. `predicted_value` is a Frappe
            # Float — decimal(21,9) NOT NULL DEFAULT 0 — so it can never be NULL;
            # for the 8 non-numeric rows it is 0 and IGNORED, and the discriminant
            # is computed_value + blend_method. Compare enum members: BlendMethod
            # subclasses (str, Enum), so str(member) is "BlendMethod.ALL_PASS",
            # never "all_pass", and that comparison silently never matches.
            is_allpass = br.blend_method == engine.BlendMethod.ALL_PASS
            is_numeric = bool(pmap.get(name) and pmap[name].numeric) and not is_allpass

            if is_numeric:
                # class 1 — a real number the lab will confirm
                row["predicted_value"] = numeric_value
                row["computed_value"] = _fmt(br.computed_value)
                row["is_estimate"] = 1
                row["requires_lab_measurement"] = 1 if br.requires_lab_measurement else 0
            elif is_allpass:
                # class 3 — a contaminant passes only if EVERY lot's COA row passes.
                # A lot missing the row is NO DATA, never a vacuous PASS.
                state = self._all_pass_state(lots, name)
                row["computed_value"] = state
                row["per_lot_pass"] = 1 if state == "PASS" else 0
            else:
                # class 2 — descriptive. Averaging a string is the one thing that
                # must never happen: report the agreed per-lot text, or say it is
                # descriptive. Never a number, and never empty.
                row["computed_value"] = self._descriptive_text(lots, name)

            if qp is None:
                row["computed_value"] = f"UNRESOLVED: {name}"
            self.append("predicted_analytics", row)

        self._recompute_mix_totals()
        self.prediction_note = ("Estimates only — release requires measured values "
                                "(21 CFR 111.75)")
        self.save(ignore_permissions=True)   # DRAFT only — never submit; no Batch AMB / COA / WO created
        if unresolved:
            frappe.msgprint("Parameters with no Quality Inspection Parameter master: "
                            + ", ".join(unresolved))
        return {
            "lines": lines_total, "lines_with_coa": lines_with_coa,
            "parameters": len(params), "predicted_rows": len(results),
            "unresolved": len(unresolved),
            "total_input_kg": self.total_input_kg, "predicted_cost": self.total_amount,
            "requires_lab": sum(1 for b in results.values() if b.requires_lab_measurement),
            "out_of_spec_estimate": sum(1 for b in results.values() if b.in_spec_estimate is False),
        }

    def _resolve_parameter(self, specification):
        """predicted_analytics.parameter is a Link; the engine speaks specification
        strings. Unresolvable names are reported, never raised on."""
        if not specification:
            return None
        if frappe.db.exists("Quality Inspection Parameter", specification):
            return specification
        return None

    def _per_lot_pass(self, lots, name):
        seen = False
        for lot in lots:
            if name not in lot.values:
                continue
            seen = True
            v = lot.values.get(name)
            if isinstance(v, bool):
                if not v:
                    return False
            elif not _qual(v):
                return False
        return seen

    def _all_pass_state(self, lots, name):
        """PASS / FAIL / NO DATA for a contaminant (A3 class 3).

        A lot that simply lacks the COA row is NO DATA — never a vacuous PASS.
        An empty lot list is NO DATA for the same reason.
        """
        if not lots:
            return "NO DATA"
        for lot in lots:
            if name not in lot.values:
                return "NO DATA"
        return "PASS" if self._per_lot_pass(lots, name) else "FAIL"

    def _descriptive_text(self, lots, name):
        """The agreed per-lot text, else a fixed descriptive marker (A3 class 2).

        Never a number and never empty — an empty computed_value on a descriptive
        row is a STOP. Truncated to the varchar(140) the column actually holds.
        """
        raw = getattr(self, "_raw_by_lot", []) or []
        seen = [str(d.get(name, "")).strip() for d in raw if str(d.get(name, "")).strip()]
        if seen and len(seen) == len(lots) and len(set(seen)) == 1:
            text = seen[0]
            if _num(text) is None:          # never report a bare number here
                return text[:140]
        return _DESCRIPTIVE

    def _build_lots(self):
        """Native mix_input_lines: kg · source_coa_amb2 · batch_amb_sublot|cunete_ref."""
        lots = []
        lines = self.get("mix_input_lines") or []
        with_coa = 0
        raw_by_lot = []
        for line in lines:
            if not line.source_coa_amb2:
                continue
            with_coa += 1
            vals = {}
            raw = {}
            for p in frappe.get_all("COA Quality Test Parameter",
                                    filters={"parent": line.source_coa_amb2, "parenttype": "COA AMB2"},
                                    fields=["specification", "value", "result"]):
                if not p.specification:
                    continue
                v = _num(p.value)
                vals[p.specification] = v if v is not None else _qual(p.result)
                # The engine needs a number or a bool; a DESCRIPTIVE row needs the
                # words. Booleanising loses them, so keep the raw text alongside.
                raw[p.specification] = p.result if p.result not in (None, "") else p.value
            raw_by_lot.append(raw)
            lots.append(engine.Lot(
                lot_id=line.batch_amb_sublot or line.cunete_ref or line.item_code or line.source_coa_amb2,
                mass_kg=flt(line.kg), values=vals))
        self._raw_by_lot = raw_by_lot
        return lots, len(lines), with_coa

    def _build_parameters(self):
        if not self.target_tds:
            return []
        out = []
        for row in frappe.get_all("Item Quality Inspection Parameter",
                                  filters={"parent": self.target_tds,
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
        """kg × unit_cost per line, falling back to the Batch AMB item valuation."""
        c = 0.0
        for line in (self.get("mix_input_lines") or []):
            if flt(line.unit_cost):
                c += flt(line.kg) * flt(line.unit_cost)
                continue
            if not line.batch_amb_sublot:
                continue
            item = (frappe.db.get_value("Batch AMB", line.batch_amb_sublot, "item_on_batch")
                    or frappe.db.get_value("Batch AMB", line.batch_amb_sublot, "main_item"))
            rate = frappe.db.get_value("Item", item, "valuation_rate") if item else 0
            c += flt(line.kg) * flt(rate)
        return c

    # QA precondition before trusting any mass-avg
    @frappe.whitelist()
    def blend_uniformity_ok(self, sample_results, rsd_max=5.0):
        import json as _j
        if isinstance(sample_results, str):
            sample_results = _j.loads(sample_results)
        return engine.blend_uniformity_ok([float(x) for x in sample_results], float(rsd_max))
