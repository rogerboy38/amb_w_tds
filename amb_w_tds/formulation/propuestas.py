"""Propuestas de Formulación — the read-only comparison Dirección decides from.

Replaces the manual "propuesta de inventario" email: for one product (and
optionally one Sales Order) it lists the draft Mix proposals on BOM Formula and,
per proposal, the lot lines, the gate's weighted TOTAL and the compliance of
that total against the product's TDS.

Shared by two surfaces so they can never disagree:
  - the Script Report "Propuestas de Formulación" (grid + Excel/CSV export);
  - the Print Format "Propuestas de Formulación" on BOM Formula (PDF), through
    the Jinja method `amb_propuestas_formulacion`.

⛔ Nothing here computes a quality value. Every number comes from a COA row or
from the gate's stored Predicted Analytic rows (the last "Simular"); the only
computation is the pass/fail of that stored value against the TDS bounds, and it
uses the gate's own comparator (`engine._within_spec`) and the gate's own TDS
reader (`BOMFormula._build_parameters`). Lot COAs resolve through the gate's
`BOMFormula._resolve_coa`, so a line resolves here exactly as it does in
simulate_blend. The report creates and writes nothing.
"""

from __future__ import annotations

import unicodedata

import frappe
from frappe.utils import flt

from amb_w_tds.formulation import engine

# The three headline columns of the approved format. These are NAME PATTERNS for
# finding the parameter in the product's TDS (whose wording varies: "Acemannan",
# "Polysaccharides Measured As Acemannan", "Aloin Content", "Total Aloin A +
# Aloin B", "Arsenic"...) -- never a bound. Bounds always come from the TDS.
HEADLINE = (
	("acemannan", "Acemannan NMR", ("acemann",)),
	("aloina", "Aloína", ("aloin",)),
	("arsenico", "Arsénico", ("arsen",)),
)
# When several TDS rows match a pattern (Aloin A / Aloin B / Total Aloin A + B),
# a name carrying one of these words is the blend-level figure and wins.
_PREFERRED_WORDS = ("total", "content", "contenido")

SIN_COA = "sin COA"
SIN_TDS = "SIN TDS"
SIN_SIMULACION = "SIN SIMULACIÓN"
CUMPLE = "CUMPLE"
NO_CUMPLE = "NO CUMPLE"
INCOMPLETO = "INCOMPLETO"

_DESCRIPTIVE_PREFIX = "DESCRIPTIVE"
_UNRESOLVED_PREFIX = "UNRESOLVED: "


def _fold(text) -> str:
	"""Lower-case, accent-free form used only for pattern matching names."""
	text = unicodedata.normalize("NFKD", str(text or ""))
	return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _num(value):
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def default_tds(producto):
	"""The product's TDS: the newest SUBMITTED TDS Product Specification whose
	product_item is the product. None when the product has none."""
	rows = frappe.get_all(
		"TDS Product Specification",
		filters={"product_item": producto, "docstatus": 1},
		fields=["name"],
		order_by="approval_date desc, modified desc",
		limit=1,
	)
	return rows[0].name if rows else None


def tds_parameters(tds):
	"""The gate's own reading of a TDS (BOMFormula._build_parameters), on an
	unsaved in-memory document: same rows, same blend methods, same bounds."""
	if not tds:
		return []
	probe = frappe.new_doc("BOM Formula")
	probe.target_tds = tds
	return probe._build_parameters()


def pick_headline(names):
	"""Map each headline key to the first matching parameter name (preferring a
	'total'/'content' name), or None. `names` keeps the TDS order."""
	out = {}
	for key, _label, tokens in HEADLINE:
		matches = [n for n in names if any(t in _fold(n) for t in tokens)]
		preferred = [n for n in matches if any(w in _fold(n) for w in _PREFERRED_WORDS)]
		out[key] = (preferred or matches or [None])[0]
	return out


def _predicted(doc):
	"""{specification: {"value": float|None, "text": str, "numeric": bool}} from the
	gate's stored Predicted Analytic rows. A numeric row with an empty computed
	value had no lot data: value None (predicted_value is a NOT NULL float, so its
	0 there means nothing and is never read)."""
	out = {}
	for r in doc.get("predicted_analytics") or []:
		text = str(r.computed_value or "").strip()
		spec = r.parameter
		if not spec and text.startswith(_UNRESOLVED_PREFIX):
			spec = text[len(_UNRESOLVED_PREFIX):]
		if not spec:
			continue
		numeric = bool(r.is_estimate) and r.blend_method != "all_pass"
		value = flt(r.predicted_value) if (numeric and text and not text.startswith(_UNRESOLVED_PREFIX)) else None
		out[spec] = {"value": value, "text": text, "numeric": numeric, "blend_method": r.blend_method}
	return out


def _coa_values(doctype, name, specs):
	"""{specification: raw value} for the wanted specifications on one COA."""
	if not (doctype and name and specs):
		return {}
	out = {}
	for p in frappe.get_all(
		"COA Quality Test Parameter",
		filters={"parent": name, "parenttype": doctype, "specification": ("in", list(specs))},
		fields=["specification", "value", "result"],
		order_by="idx asc",
	):
		if p.specification in out:
			continue
		raw = p.value if p.value not in (None, "") else p.result
		out[p.specification] = raw if raw not in (None, "") else None
	return out


def _compliance(params, predicted):
	"""Per TDS parameter: the stored prediction against the TDS bounds, through
	the gate's comparator. ok = True / False / None (no prediction)."""
	rows = []
	for p in params:
		method = p.blend_method.value
		pred = predicted.get(p.name)
		if method == engine.BlendMethod.ALL_PASS.value:
			text = (pred or {}).get("text") or ""
			ok = True if text == "PASS" else False if text == "FAIL" else None
			rows.append({"parameter": p.name, "uom": p.uom, "min": None, "max": None,
				"value": text or None, "ok": ok, "kind": "all_pass"})
			continue
		if not p.numeric:
			rows.append({"parameter": p.name, "uom": p.uom, "min": p.min_value, "max": p.max_value,
				"value": (pred or {}).get("text") or None, "ok": None, "kind": "descriptive"})
			continue
		if p.min_value is None and p.max_value is None:
			continue
		value = (pred or {}).get("value")
		ok = None if value is None else engine._within_spec(value, p.min_value, p.max_value, method)
		rows.append({"parameter": p.name, "uom": p.uom, "min": p.min_value, "max": p.max_value,
			"value": value, "ok": ok, "kind": "numeric"})
	return rows


def _overall(has_tds, predicted, compliance):
	if not has_tds:
		return SIN_TDS
	if not predicted:
		return SIN_SIMULACION
	gated = [c for c in compliance if c["kind"] != "descriptive"]
	if any(c["ok"] is False for c in gated):
		return NO_CUMPLE
	if any(c["ok"] is None for c in gated):
		return INCOMPLETO
	return CUMPLE


def build(producto, sales_order=None, tds=None):
	"""The whole comparison as plain data. Read-only; permission-checked through
	frappe.get_list on BOM Formula."""
	if not producto:
		frappe.throw("Indique el producto")
	tds_name = tds or default_tds(producto)
	params = tds_parameters(tds_name)

	filters = {"formula_type": "Mix", "docstatus": 0, "product_sku": producto}
	if sales_order:
		filters["sales_order"] = sales_order
	names = frappe.get_list(
		"BOM Formula", filters=filters, pluck="name",
		order_by="formulation_date asc, creation asc",
	)

	docs = [frappe.get_doc("BOM Formula", n) for n in names]
	predicted_by_doc = {d.name: _predicted(d) for d in docs}

	# Headline parameter names: from the TDS; without a TDS, from what the gate
	# predicted; in either case never from a hard-coded name.
	name_pool = [p.name for p in params]
	if not name_pool:
		for pred in predicted_by_doc.values():
			name_pool += [n for n in pred if n not in name_pool]
	headline = pick_headline(name_pool)
	param_by_name = {p.name: p for p in params}
	headline_cols = []
	for key, label, _tokens in HEADLINE:
		spec = headline.get(key)
		uom = param_by_name[spec].uom if spec in param_by_name else ""
		headline_cols.append({"key": key, "label": label, "spec": spec, "uom": uom or "",
			"min": param_by_name[spec].min_value if spec in param_by_name else None,
			"max": param_by_name[spec].max_value if spec in param_by_name else None})
	wanted = {c["spec"] for c in headline_cols if c["spec"]}

	proposals = []
	for d in docs:
		lines = []
		for idx, line in enumerate(d.get("mix_input_lines") or [], start=1):
			dt, coa, resolution, detail = d._resolve_coa(line)
			vals = _coa_values(dt, coa, wanted)
			lines.append({
				"idx": idx,
				"lote": line.batch_amb_sublot or line.cunete_ref or line.item_code or "",
				"item_code": line.item_code,
				"kg": flt(line.kg),
				"pct": flt(line.pct) if line.pct not in (None, "") else None,
				"coa_doctype": dt, "coa": coa, "resolution": resolution,
				"nota": "" if coa else f"{SIN_COA}: {detail}",
				"values": {c["key"]: (vals.get(c["spec"]) if c["spec"] else None) for c in headline_cols},
			})
		predicted = predicted_by_doc[d.name]
		compliance = _compliance(params, predicted)
		ok_by_param = {c["parameter"]: c["ok"] for c in compliance}
		total = {c["key"]: ((predicted.get(c["spec"]) or {}).get("value") if c["spec"] else None)
			for c in headline_cols}
		total_ok = {c["key"]: (ok_by_param.get(c["spec"]) if c["spec"] else None) for c in headline_cols}
		notes = []
		if tds_name and d.target_tds and d.target_tds != tds_name:
			notes.append(f"simulada con TDS {d.target_tds}")
		if not predicted:
			notes.append("sin Predicted Analytics: ejecute Simular en la propuesta")
		sin_coa = sum(1 for ln in lines if not ln["coa"])
		if sin_coa:
			# the gate averages only lines whose COA resolved; say so next to its TOTAL
			notes.append(f"{sin_coa} línea(s) {SIN_COA}: el TOTAL de la puerta no las incluye")
		proposals.append({
			"name": d.name,
			"formula_name": d.formula_name,
			"formula_type": d.formula_type,
			"fecha": d.formulation_date,
			"total_kg": flt(d.total_input_kg),
			"batch_size_kg": flt(d.batch_size_kg),
			"sales_order": d.sales_order,
			"target_tds": d.target_tds,
			"blend_status": d.blend_status,
			"prediction_note": d.prediction_note,
			"lines": lines,
			"n_lotes": len(lines),
			"n_sin_coa": sin_coa,
			"total": total,
			"total_ok": total_ok,
			"compliance": compliance,
			"overall": _overall(bool(tds_name), predicted, compliance),
			"notes": notes,
		})

	tds_info = None
	if tds_name:
		tds_info = {"name": tds_name, "parameters": [
			{"parameter": p.name, "uom": p.uom, "min": p.min_value, "max": p.max_value,
			 "blend_method": p.blend_method.value, "numeric": p.numeric}
			for p in params]}
	return {
		"producto": producto,
		"item_name": frappe.db.get_value("Item", producto, "item_name"),
		"sales_order": sales_order,
		"tds": tds_info,
		"headline": headline_cols,
		"proposals": proposals,
	}


def mark(ok) -> str:
	"""A pass/fail mark that survives black-and-white printing."""
	return "✓ Cumple" if ok is True else "✗ No cumple" if ok is False else "— sin dato"


def amb_propuestas_formulacion(producto, sales_order=None, tds=None):
	"""Jinja method (hooks.jinja) for the Print Format."""
	data = build(producto, sales_order=sales_order, tds=tds)
	data["mark"] = mark
	return data
