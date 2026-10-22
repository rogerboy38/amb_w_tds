"""Propuestas de Formulación — the read-only comparison Dirección decides from.

Replaces the manual "propuesta de inventario" email: for one product (and
optionally one Sales Order) it lists the draft Mix proposals on BOM Formula and,
per proposal, the lot lines, the gate's weighted TOTAL and the compliance of
that total against the product's TDS.

Shared by two surfaces so they can never disagree:
  - the Script Report "Propuestas de Formulación" (grid + Excel/CSV export);
  - the Print Format "Propuestas de Formulación" on BOM Formula (PDF), through
    the Jinja method `amb_propuestas_formulacion`.

Which TDS judges a proposal (13.9.1), one order for every surface:
  1. the report's explicit `tds` filter, for every proposal;
  2. else the proposal's own `target_tds`;
  3. else none: "SIN TDS".
A draft TDS is used, as the gate uses it, but every verdict on it is labelled
"TDS en borrador"; a cancelled or missing TDS is refused (no pass/fail). There is
no lookup by Item name (prod TDS name a longer Item than the proposal's SKU).

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
TDS_CANCELADA = "TDS CANCELADA"
TDS_NO_EXISTE = "TDS NO EXISTE"

# TDS status by docstatus; only "aprobada" and "borrador" may judge.
TDS_STATUS = {1: "aprobada", 0: "borrador", 2: "cancelada"}
_USABLE = ("aprobada", "borrador")

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


def resolve_tds(filter_tds, target_tds, docstatus_of):
	"""Which TDS judges one proposal: the explicit filter, else its own target_tds,
	else None (SIN TDS). `docstatus_of(name)` returns the TDS docstatus, or None
	when it does not exist. Pure, so the order is unit-tested without a site."""
	name = filter_tds or target_tds or None
	if not name:
		return None
	status = TDS_STATUS.get(docstatus_of(name), "no existe")
	return {"name": name, "source": "filtro" if filter_tds else "target_tds",
		"status": status, "usable": status in _USABLE}


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


def _overall(tds_info, predicted, compliance):
	if not tds_info:
		return SIN_TDS
	if not tds_info["usable"]:
		return TDS_CANCELADA if tds_info["status"] == "cancelada" else TDS_NO_EXISTE
	if not predicted:
		return SIN_SIMULACION
	gated = [c for c in compliance if c["kind"] != "descriptive"]
	if any(c["ok"] is False for c in gated):
		return NO_CUMPLE
	if any(c["ok"] is None for c in gated):
		return INCOMPLETO
	return CUMPLE


def _tds_box(info, params):
	"""The spec a verdict used: TDS name, status, and the bounds applied."""
	if not info:
		return None
	return {"name": info["name"], "status": info["status"], "source": info["source"], "usable": info["usable"],
		"parameters": [
			{"parameter": p.name, "uom": p.uom,
			 # a pass/fail or descriptive row has no numeric bound: its stored 0s are not limits
			 "min": p.min_value if p.numeric else None, "max": p.max_value if p.numeric else None,
			 "blend_method": p.blend_method.value, "numeric": p.numeric}
			for p in params]}


def build(producto, sales_order=None, tds=None):
	"""The whole comparison as plain data. Read-only; permission-checked through
	frappe.get_list on BOM Formula. Each proposal is judged against the TDS that
	resolve_tds gives it (filter > target_tds > none)."""
	if not producto:
		frappe.throw("Indique el producto")
	tds = tds or None

	filters = {"formula_type": "Mix", "docstatus": 0, "product_sku": producto}
	if sales_order:
		filters["sales_order"] = sales_order
	names = frappe.get_list(
		"BOM Formula", filters=filters, pluck="name",
		order_by="formulation_date asc, creation asc",
	)
	docs = [frappe.get_doc("BOM Formula", n) for n in names]

	def docstatus_of(name):
		return frappe.db.get_value("TDS Product Specification", name, "docstatus")

	params_cache = {}

	def params_for(info):
		if not (info and info["usable"]):
			return []
		if info["name"] not in params_cache:
			params_cache[info["name"]] = tds_parameters(info["name"])
		return params_cache[info["name"]]

	proposals = []
	for d in docs:
		info = resolve_tds(tds, d.target_tds, docstatus_of)
		params = params_for(info)
		predicted = _predicted(d)
		# Headline parameter names: from THIS proposal's TDS; without one, from what
		# the gate predicted for it; never from a hard-coded name.
		pool = [p.name for p in params] or list(predicted)
		picked = pick_headline(pool)
		param_by_name = {p.name: p for p in params}
		headline = {}
		for key, _label, _tokens in HEADLINE:
			spec = picked.get(key)
			p = param_by_name.get(spec)
			headline[key] = {"spec": spec, "uom": (p.uom if p else "") or "",
				"min": p.min_value if p else None, "max": p.max_value if p else None}
		wanted = {h["spec"] for h in headline.values() if h["spec"]}

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
				"values": {k: (vals.get(h["spec"]) if h["spec"] else None) for k, h in headline.items()},
			})
		compliance = _compliance(params, predicted)
		ok_by_param = {c["parameter"]: c["ok"] for c in compliance}
		total = {k: ((predicted.get(h["spec"]) or {}).get("value") if h["spec"] else None)
			for k, h in headline.items()}
		total_ok = {k: (ok_by_param.get(h["spec"]) if h["spec"] else None) for k, h in headline.items()}

		notes = []
		if info and info["status"] == "borrador":
			notes.append(f"TDS en borrador ({info['name']}): veredicto contra límites aún no aprobados")
		elif info and not info["usable"]:
			notes.append(f"{info['name']}: TDS {info['status']}, sin veredicto")
		if tds and d.target_tds and d.target_tds != tds:
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
			"tds": _tds_box(info, params),
			"tds_label": tds_label(info),
			"borrador": bool(info and info["status"] == "borrador"),
			"headline": headline,
			"lines": lines,
			"n_lotes": len(lines),
			"n_sin_coa": sin_coa,
			"total": total,
			"total_ok": total_ok,
			"compliance": compliance,
			"overall": _overall(info, predicted, compliance),
			"notes": notes,
		})

	return {
		"producto": producto,
		"item_name": frappe.db.get_value("Item", producto, "item_name"),
		"sales_order": sales_order,
		"tds_filter": tds,
		"tds": shared_tds(proposals, tds, lambda: _tds_box(resolve_tds(tds, None, docstatus_of),
			params_for(resolve_tds(tds, None, docstatus_of)))),
		"headline": headline_columns(proposals),
		"proposals": proposals,
	}


def tds_label(info) -> str:
	"""'TDS-X', 'TDS-X (borrador)', 'TDS-X (cancelada)' or 'SIN TDS'."""
	if not info:
		return SIN_TDS
	return info["name"] if info["status"] == "aprobada" else f"{info['name']} ({info['status']})"


def shared_tds(proposals, tds_filter, filter_box):
	"""One spec header only when every proposal was judged by the same TDS with the
	same status (an explicit filter always is); else None = a spec box per proposal."""
	if not proposals:
		return filter_box() if tds_filter else None
	boxes = [p["tds"] for p in proposals]
	if any(b is None for b in boxes):
		return None
	keys = {(b["name"], b["status"]) for b in boxes}
	return boxes[0] if len(keys) == 1 else None


def headline_columns(proposals):
	"""The three headline columns. A column's UOM goes in the header only when every
	proposal that has the parameter agrees on it; otherwise `uniform` is False and
	each proposal's own parameter name and UOM are shown with its value."""
	cols = []
	for key, label, _tokens in HEADLINE:
		used = [p["headline"][key] for p in proposals if p["headline"][key]["spec"]]
		specs = {(h["spec"], h["uom"]) for h in used}
		uniform = len(specs) <= 1
		uom = next(iter(specs))[1] if (uniform and specs) else ""
		cols.append({"key": key, "label": label, "uom": uom, "uniform": uniform})
	return cols


def mark(ok) -> str:
	"""A pass/fail mark that survives black-and-white printing."""
	return "✓ Cumple" if ok is True else "✗ No cumple" if ok is False else "— sin dato"


def amb_propuestas_formulacion(producto, sales_order=None, tds=None):
	"""Jinja method (hooks.jinja) for the Print Format."""
	data = build(producto, sales_order=sales_order, tds=tds)
	data["mark"] = mark
	return data
