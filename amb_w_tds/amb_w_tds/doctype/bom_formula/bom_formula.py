import re

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from amb_w_tds.formulation import engine  # imported, not duplicated

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


# 13.12.7 (TASKS-281): the leading number of a COA cell, as coa_amb2._num / coa_amb._num read it:
# '2.22' -> 2.22, '23.5%' -> 23.5, '<10 CFU/G' -> 10 (the worst case the cell can mean), 'ND' /
# 'NEGATIVE' / '<LOQ' / '' -> None (no number). `_num` above stays float()-strict for the places that
# must not see a number inside a descriptive text (`_descriptive_text`, `_release_from_measured`).
_LEAD_NUM = re.compile(r'[-+]?\d*\.?\d+')


def _lead_num(v):
    if v is None:
        return None
    if isinstance(v, int | float) and not isinstance(v, bool):
        return float(v)
    m = _LEAD_NUM.search(str(v).replace(',', ''))
    return float(m.group()) if m else None


def _qual(result):
    return str(result or "").strip().upper() in _PASS_TOKENS


def _is_text(v):
    return v not in (None, "") and str(v).strip() != ""


def _lot_value(row, kind):
    """What one COA row contributes to the engine for its specification, by the PARAMETER'S kind
    (never by whether a number happened to parse). 13.12.7, TASKS-281 §1.1-1.2:

      numeric      (i) the leading number in `result`; (ii) else `value` when it is a PURE non-zero
                   number (float() strict: on COA AMB rows `value` carries the acceptance text --
                   'NMT 1 PPM', '3.5 - 5.0', 'Specification' -- whose digits are a LIMIT, never a
                   measurement; and the form fills "0" by default, so 0 there is unset); else NO DATA
                   (None). ND / '<LOQ' / free text carry no number -> NO DATA, never 0. '<10' -> 10.
      qualitative  the Pass-token test on `result` -> True / False (a non-token text such as ND is
                   NOT a pass and keeps today's per-lot rejection); an EMPTY result -> NO DATA.
      descriptive  nothing for the engine (the words travel in `_raw_by_lot`).
      None         a specification the TDS does not define: number if any, else token, else NO DATA.
    """
    result, value = row.get("result"), row.get("value")
    if kind == "descriptive":
        return None
    if kind == "qualitative":
        return _qual(result) if _is_text(result) else None
    n = _lead_num(result)
    if n is None:
        v = _num(value)          # strict: a pure number only, never the digits of an acceptance text
        if v is not None and v != 0:
            n = v
    if n is not None or kind == "numeric":
        return n
    return _qual(result) if _is_text(result) else None


def _row_key(row, kinds, qip_cache):
    """The parameter a COA Quality Test Parameter row belongs to. 13.12.11, TASKS-289.

    `parameter_name` (a Link to Quality Inspection Parameter) wins whenever it is set: on real
    COA AMB2 rows `specification` holds the acceptance text and may even equal ANOTHER parameter's
    name (e.g. 'NONE'), so it must never override it. Only when `parameter_name` is blank is
    `specification` taken -- and only if it names a parameter (one the TDS defines, or a Quality
    Inspection Parameter); acceptance text is never a name, so that row stays unkeyed (NO DATA,
    never guessed).
    """
    name = (row.get("parameter_name") or "").strip()
    if name:
        return name
    spec = (row.get("specification") or "").strip()
    if not spec:
        return None
    if spec in kinds:
        return spec
    if spec not in qip_cache:
        # 13.12.13 (TASKS-298): `exists` answers through MariaDB's case-insensitive collation and returns the STORED
        # name, so compare it with the input: acceptance text that equals a parameter only by case ("NONE" vs the
        # parameter "None") is not that parameter. One query per distinct spec, as before.
        qip_cache[spec] = frappe.db.exists("Quality Inspection Parameter", spec) == spec
    return spec if qip_cache[spec] else None


def _raw_text(row):
    """The cell of a COA row the reader keeps as text (and the Propuestas report shows): `result` first, else `value`.
    13.12.13: one definition for `_build_lots` and `propuestas._coa_values`."""
    result = row.get("result")
    return result if result not in (None, "") else row.get("value")


def _fmt(v):
    if isinstance(v, bool):
        return "PASS" if v else "FAIL"
    if v is None:
        return ""
    return f"{v:.4g}" if isinstance(v, float) else str(v)


# A1 R2: the golden number is a LOT key, not a row key. Sublots chain under a
# level-1 root via `parent_batch_amb`, and the COA attaches to that root, so a
# line pointing at any sublot must walk up before it looks for a certificate.
# Measured 2026-09-10: 10 of 11 goldens resolve to exactly one root, 0 ambiguous
# -- the ambiguity only appears if you count Batch AMB *rows* instead of lots.
# `batch_id` and `batch_level` are NULL on all 35 rows; never key on either.
_MAX_LOT_DEPTH = 20


def _batch_root(batch):
    """Walk `parent_batch_amb` to the root. Returns the root name, or the last
    node reached if the chain is broken/cyclic -- a bad chain must not hang the
    reader, and a partial walk is still a better key than the sublot."""
    seen = []
    cur = batch
    while cur and cur not in seen and len(seen) < _MAX_LOT_DEPTH:
        seen.append(cur)
        parent = frappe.db.get_value("Batch AMB", cur, "parent_batch_amb")
        if not parent:
            return cur
        cur = parent
    return seen[-1] if seen else batch


# 13.11.0 approval workflow "BOM Formula Aprobación" (workflow_state; BOM Formula stays
# non-submittable). The workflow drives cost_approval so state and field never diverge:
# Autorizado / Liberado mean approved, Rechazado means rejected, En Revisión means requested,
# and returning to Borrador withdraws an approval or rejection.
_STATE_COST_APPROVAL = {"Autorizado": "approved", "Liberado": "approved", "Rechazado": "rejected",
    "En Revisión": "requested"}


def cost_approval_for_state(state, current):
    """cost_approval implied by a workflow state; `current` is kept where the state implies
    nothing. No state (workflow not installed) keeps the field as the user set it."""
    if not state:
        return current
    if state in _STATE_COST_APPROVAL:
        return _STATE_COST_APPROVAL[state]
    return "" if current in ("approved", "rejected") else current


class BOMFormula(Document):
    # ---- THE DOOR: release gates on the MEASURED value, never the estimate ----
    def validate(self):
        self.cost_approval = cost_approval_for_state(self.get("workflow_state"), self.get("cost_approval"))
        self._stamp_cost_approval()
        self._fetch_cost_thresholds()
        self._recompute_mix_totals()
        if not self.get("formulation_date"):
            # Leg D: stamp the date on first save only. Never overwrite a date a
            # human set -- "today" on every save would silently rewrite history.
            self.formulation_date = frappe.utils.today()
        for r in (self.get("predicted_analytics") or []):
            if r.confirmed and str(r.measured_value or "").strip() != "":
                r.release_ok = "Pass" if self._release_from_measured(r) else "Fail"
            else:
                r.release_ok = "Pending"     # never auto-confirm
        self._release_on_transition()

    def _release_on_transition(self):
        """13.11.0: entering "Liberado" builds the standard BOM (formulation/release.py) and
        records it in bom_liberada. Only an existing record moving Autorizado -> Liberado
        releases: Frappe's workflow gates that transition to its role; anything else that
        tries to land in Liberado is refused."""
        if self.get("workflow_state") != "Liberado":
            return
        before = self.get_doc_before_save()
        if before and before.get("workflow_state") == "Liberado":
            return  # already released: saving again builds nothing
        if not before or before.get("workflow_state") != "Autorizado":
            frappe.throw(frappe._("Solo una fórmula Autorizada puede liberarse a producción."))
        from amb_w_tds.formulation.release import build_release_bom
        result = build_release_bom(self)
        self.bom_liberada = result["bom"]
        self.flags.release_result = result

    def _stamp_cost_approval(self):
        """13.10.0: Calidad's authorization lives in the existing cost_approval /
        cost_approved_by fields. cost_approved_by was read-only and nothing ever set
        it; stamp who and when on the transition to "approved", and clear both when
        the approval is withdrawn, so the record always says who authorized it."""
        if self.get("cost_approval") == "approved":
            before = self.get_doc_before_save()
            if not before or before.get("cost_approval") != "approved" or not self.get("cost_approved_by"):
                self.cost_approved_by = frappe.session.user
                self.cost_approved_on = frappe.utils.now_datetime()
        else:
            self.cost_approved_by = None
            self.cost_approved_on = None

    def _fetch_cost_thresholds(self):
        """Leg D / G-1a defect: the Single holds 600 / 800 but the document kept
        0.00, so Estado de Costo could never be anything but 'below target' and
        Alicia saw a cost gate that never fired.

        Fetched only when the field is empty (0 or None): a value typed on the
        document is a deliberate per-formula override and outranks the default.
        G-1c will compute the actual cost; this only makes the THRESHOLDS real,
        and deliberately does not touch `blended_cost_per_kg` or `cost_source`.
        """
        if not frappe.db.exists("Formulation Settings", "Formulation Settings"):
            return
        s = frappe.get_cached_doc("Formulation Settings", "Formulation Settings")
        for field in ("cost_target_per_kg", "cost_hard_max_per_kg"):
            if not flt(self.get(field)):
                self.set(field, flt(s.get(field)))

        # Derive the state from the fetched thresholds. With both at 0 this used
        # to read 'below target' for every document, which is a vacuous pass.
        cost = flt(self.get("blended_cost_per_kg"))
        target = flt(self.get("cost_target_per_kg"))
        hard = flt(self.get("cost_hard_max_per_kg"))
        if not cost or not (target or hard):
            return                      # nothing measured yet -- say nothing
        if hard and cost > hard:
            self.cost_state = "over hard max"
        elif target and cost > target:
            self.cost_state = "needs approval"
        else:
            self.cost_state = "below target"

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
        # 13.12.7: the parameters first -- their kind decides how each COA row is read.
        params = self._build_parameters()
        lots, lines_total, lines_with_coa = self._build_lots(params)
        # TASKS-282 Part B: the planner's missing-data policy. Default "No data" (a lot without a
        # number is left out and named); "TDS upper limit" assumes such a lot at the limit on its
        # own COA row and says so (`assumed_at_limit`), so `no_data` stays empty for those lots.
        policy = self.get("missing_data_policy") or engine.MISSING_NO_DATA
        assumed = engine.assume_at_limit(lots, params) if policy == engine.MISSING_TDS_LIMIT else {}

        # A COA-less formula is the normal prod state, not an error: say so and
        # predict nothing. Never a vacuous PASS on an empty list.
        if not lots:
            self.set("predicted_analytics", [])
            # A1 R3 (4): never just "no COA" -- say which line, which root, which
            # golden. A note that does not name the failing step sends Alicia
            # back to us to find out what it meant.
            why = "; ".join(f"line {r['line']}: {r['detail']}"
                            for r in getattr(self, "_resolutions", []) if r["detail"])
            msg = (f"no COA resolved on {lines_total} of {lines_total} lines — nothing predicted"
                   + (f" ({why})" if why else "")
                   if lines_total else "no Mix Input Lines — nothing predicted")
            self.prediction_note = msg
            self._recompute_mix_totals()
            self.save(ignore_permissions=True)
            frappe.msgprint(msg)
            return {"lines": lines_total, "lines_with_coa": lines_with_coa,
                    "parameters": len(params), "predicted_rows": 0, "note": msg,
                    "resolutions": getattr(self, "_resolutions", []),
                    "skipped_no_coa": list(getattr(self, "_skipped_no_coa", []))}
        if not params:
            msg = "Set a TDS Target with parameter rows before simulating — nothing predicted."
            self.set("predicted_analytics", [])
            self.prediction_note = msg
            self._recompute_mix_totals()
            self.save(ignore_permissions=True)
            frappe.msgprint(msg)
            return {"lines": lines_total, "lines_with_coa": lines_with_coa,
                    "parameters": 0, "predicted_rows": 0, "note": msg,
                    "skipped_no_coa": list(getattr(self, "_skipped_no_coa", []))}

        results = engine.blend(lots, params)
        uom = {p.name: p.uom for p in params}
        unresolved = []
        no_data = {}   # 13.12.7: {parameter: lots without a number, their mass, and the lots used}

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
            # AMENDMENT A3: THREE classes. The row count is whatever the linked
            # TDS carries -- one per parameter row, read in this transaction --
            # NOT a constant. An earlier version of this comment said "16 rows"
            # and "the 8 non-numeric rows", which were true only of the 0307 case
            # it was written against; a reader can implement a comment, so the
            # case numbers are gone and only the invariant is stated.
            #
            # `predicted_value` is a Frappe Float -- decimal(21,9) NOT NULL
            # DEFAULT 0 -- so it can never be NULL; on non-numeric rows it is 0
            # and IGNORED, and the discriminant is computed_value + blend_method.
            # Compare enum MEMBERS: BlendMethod subclasses (str, Enum), so
            # str(member) is "BlendMethod.ALL_PASS", never "all_pass", and that
            # comparison silently never matches.
            is_allpass = br.blend_method == engine.BlendMethod.ALL_PASS
            is_numeric = bool(pmap.get(name) and pmap[name].numeric) and not is_allpass

            if is_numeric:
                # class 1 — a real number the lab will confirm. 13.12.7 (TASKS-281): with no
                # number in any lot the row says NO DATA (predicted_value stays the column's 0
                # and is never read -- status "" is neither Pass nor Fail); with a number in
                # SOME lots the estimate is their average and the note names the lots left out.
                row["predicted_value"] = numeric_value
                row["computed_value"] = _fmt(br.computed_value) if br.computed_value is not None else "NO DATA"
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

            if br.lots_no_data:   # every class: a lot left out for want of data is named, with its mass
                no_data[name] = {"lots": list(br.lots_no_data), "mass_kg": br.mass_no_data_kg,
                                 "lots_used": list(br.lots_used), "mass_used_kg": br.mass_used_kg}
            for key, a in assumed.items():   # TASKS-282 Part B: never silent about an assumed value
                if key == name or key.startswith(name + "@"):
                    row["note"] = (row.get("note") or "") + (f" — ASSUMED at TDS limit {a['value']:g} ({a['bound']} on the COA row) "
                                                             f"for {', '.join(a['lots'])} ({a['mass_kg']:g} kg) — policy \"{policy}\"")
            if qp is None:
                row["computed_value"] = f"UNRESOLVED: {name}"
            self.append("predicted_analytics", row)

        self._recompute_mix_totals()
        res_txt = ", ".join(f"line {r['line']}={r['resolution']}"
                            for r in getattr(self, "_resolutions", []))
        self.prediction_note = ("Estimates only — release requires measured values "
                                "(21 CFR 111.75)"
                                + (f" · COA source: {res_txt}" if res_txt else ""))
        self.save(ignore_permissions=True)   # DRAFT only — never submit; no Batch AMB / COA / WO created
        if unresolved:
            frappe.msgprint("Parameters with no Quality Inspection Parameter master: "
                            + ", ".join(unresolved))
        warning = self._skip_warning()
        if warning:
            frappe.msgprint(warning, title="COA missing on some lines", indicator="orange")
        return {
            "lines": lines_total, "lines_with_coa": lines_with_coa,
            "parameters": len(params), "predicted_rows": len(results),
            "unresolved": len(unresolved),
            "resolutions": getattr(self, "_resolutions", []),
            "total_input_kg": self.total_input_kg, "predicted_cost": self.total_amount,
            "requires_lab": sum(1 for b in results.values() if b.requires_lab_measurement),
            "out_of_spec_estimate": sum(1 for b in results.values() if b.in_spec_estimate is False),
            "no_data_estimate": sum(1 for b in results.values() if b.computed_value is None),
            "no_data": no_data,
            "missing_data_policy": policy,
            "assumed_at_limit": assumed,   # TASKS-282 Part B: {parameter: {value, bound, lots, mass_kg}}
            "skipped_no_coa": list(getattr(self, "_skipped_no_coa", [])),
            "warning": warning,
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

    def _resolve_coa(self, line):
        """A1 R3 resolution order. Returns (doctype, name, resolution, detail).

        `resolution` is per LINE, not per parameter -- it is surfaced in the
        simulate_blend return and the Nota, deliberately NOT as a column on
        Predicted Analytic, where one line's value would be repeated across
        every parameter row.
        """
        # (1) explicit link on the line -- either doctype, via the Dynamic Link
        if line.get("source_coa_amb2"):
            dt = line.get("source_coa_doctype") or "COA AMB2"
            return dt, line.get("source_coa_amb2"), "explicit", ""

        batch = line.get("batch_amb_sublot")
        if not batch:
            return None, None, "none", "no COA linked and no Batch AMB sublot on the line"

        root = _batch_root(batch)
        golden = frappe.db.get_value("Batch AMB", root, "custom_golden_number")

        # (2) the root's own COA link. `coa_reference` is the older field and is
        # read only as a fallback; leg C writes `coa_amb` and never touches it.
        for field in ("coa_amb", "coa_reference"):
            coa = frappe.db.get_value("Batch AMB", root, field)
            if coa:
                return "COA AMB", coa, "batch_link", f"root {root} .{field}"

        # (3) a SUBMITTED COA AMB pointing at the root, or carrying its golden.
        # docstatus=1 only: drafts and cancelled never resolve. COA AMB2 is NOT a candidate here (13.12.2):
        # nothing compares its product with the batch's item, so one linked to the wrong batch would be taken
        # for that batch's certificate. A COA AMB2 resolves through the explicit line link (1) only, until Cut 2b.
        cands = {}
        for dt in ("COA AMB",):
            for r in frappe.get_all(dt, filters={"docstatus": 1, "batch_reference": root},
                                    fields=["name", "creation"]):
                cands[(dt, r.name)] = r.creation
            # COA AMB2 carries NO golden field at all (Node C blocker 153334Z,
            # ruled 153519Z): guard the golden branch by doctype rather than
            # querying a column that does not exist.
            if golden and dt == "COA AMB":
                for r in frappe.get_all(dt, filters={"docstatus": 1,
                                                     "custom_golden_number": golden},
                                        fields=["name", "creation"]):
                    cands[(dt, r.name)] = r.creation

        if cands:
            ranked = sorted(cands.items(), key=lambda kv: kv[1], reverse=True)
            (dt, name), _ = ranked[0]
            detail = f"root {root}, golden {golden}"
            if len(ranked) > 1:
                # Name the runner-up: a silent pick among several certificates is
                # exactly the kind of choice that should be visible to Alicia.
                detail += f"; {len(ranked)} candidates, runner-up {ranked[1][0][1]}"
            return dt, name, "golden_match", detail

        # (4) nothing -- say which line, which root and which golden failed
        return None, None, "none", (f"sublot {batch} -> root {root}, "
                                    f"no submitted COA linked or matching golden {golden}")

    @staticmethod
    def _parameter_kinds(params):
        """{specification: 'numeric' | 'qualitative' | 'descriptive'} from the engine's own
        Parameter rows (blend_method / numeric), as simulate_blend classes them."""
        kinds = {}
        for p in params or []:
            if p.blend_method == engine.BlendMethod.ALL_PASS:
                kinds[p.name] = "qualitative"
            elif p.numeric:
                kinds[p.name] = "numeric"
            else:
                kinds[p.name] = "descriptive"
        return kinds

    def _build_lots(self, params=None):
        """Native mix_input_lines: kg · resolved COA · batch_amb_sublot|cunete_ref.

        13.12.7 (TASKS-281): each COA row is read by the KIND of its parameter (`params`, the
        TDS rows simulate_blend builds first): a numeric parameter gets the measured number
        (`result` first), a qualitative one the Pass-token bool, a descriptive one nothing; a
        row with no usable value is left out of `values` -- NO DATA, never 0 (see `_lot_value`).
        Without `params` (direct callers) a row is typed by its content: number, else token.

        13.12.11 (TASKS-289): a COA row is filed under `parameter_name` (see `_row_key`), not under
        `specification`, which on real COA rows holds the ACCEPTANCE text ('NMT 40%', '3.5 - 5.0').
        """
        kinds = self._parameter_kinds(params)
        qip_cache = {}
        lots = []
        lines = self.get("mix_input_lines") or []
        with_coa = 0
        raw_by_lot = []
        resolutions = []
        skipped = []
        for idx, line in enumerate(lines, start=1):
            dt, coa_name, resolution, detail = self._resolve_coa(line)
            resolutions.append({"line": idx, "sublot": line.get("batch_amb_sublot"),
                                "coa_doctype": dt, "coa": coa_name,
                                "resolution": resolution, "detail": detail})
            if not coa_name:
                # 13.12.0: the line is still left out of the blend (the gate's acceptance rule is
                # unchanged) but it is now NAMED -- row number and item code only -- so a partial
                # prediction cannot pass for a whole one.
                skipped.append({"line": idx, "item_code": line.get("item_code")})
                continue
            with_coa += 1
            vals = {}
            raw = {}
            limits = {}   # TASKS-282 Part B: the bounds copied onto this COA's rows, for the "TDS upper limit" policy
            for p in frappe.get_all("COA Quality Test Parameter",
                                    filters={"parent": coa_name, "parenttype": dt},
                                    fields=["parameter_name", "specification", "value", "result",
                                            "min_value", "max_value"]):
                key = _row_key(p, kinds, qip_cache)
                if not key:
                    continue
                v = _lot_value(p, kinds.get(key))
                if v is not None:
                    vals[key] = v
                lo, hi = _num(p.get("min_value")), _num(p.get("max_value"))
                if lo or hi:
                    limits[key] = (lo or None, hi or None)
                # The engine needs a number or a bool; a DESCRIPTIVE row needs the
                # words. Booleanising loses them, so keep the raw text alongside.
                raw[key] = _raw_text(p)
            raw_by_lot.append(raw)
            lots.append(engine.Lot(
                lot_id=line.batch_amb_sublot or line.cunete_ref or line.item_code or coa_name,
                mass_kg=flt(line.kg), values=vals, limits=limits))
        self._raw_by_lot = raw_by_lot
        self._resolutions = resolutions
        self._skipped_no_coa = skipped
        return lots, len(lines), with_coa

    def _skip_warning(self):
        """The visible warning for lines left out because no COA resolved ("" when none)."""
        skipped = getattr(self, "_skipped_no_coa", None) or []
        if not skipped:
            return ""
        named = ", ".join(f"row {s['line']}" + (f" ({s['item_code']})" if s.get("item_code") else "")
                          for s in skipped)
        return (f"{len(skipped)} line(s) have no COA and are NOT in this prediction: {named}. "
                "The numbers below come only from the lines that resolved a COA.")

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
