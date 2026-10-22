# Script Report "Propuestas de Formulación" -- the grid / Excel surface.
# All logic lives in amb_w_tds.formulation.propuestas (shared with the PDF Print Format).

import frappe

from amb_w_tds.formulation.propuestas import CUMPLE, build, mark


def _fmt_bound(v):
	return "" if v is None else f"{v:g}"


def _columns(headline):
	cols = [
		{"fieldname": "seccion", "label": "Sección", "fieldtype": "Data", "width": 150},
		{"fieldname": "propuesta", "label": "Propuesta", "fieldtype": "Link", "options": "BOM Formula", "width": 170},
		{"fieldname": "concepto", "label": "Lote / Parámetro", "fieldtype": "Data", "width": 220},
		{"fieldname": "tds_aplicada", "label": "TDS aplicada", "fieldtype": "Data", "width": 170},
		{"fieldname": "cantidad_kg", "label": "Cantidad (kg)", "fieldtype": "Float", "precision": 3, "width": 110},
	]
	for h in headline:
		# the UOM is in the header only when every proposal's parameter agrees on it;
		# otherwise each proposal's own parameter (UOM) is named in its "Nota"
		label = f"{h['label']} ({h['uom']})" if (h["uniform"] and h["uom"]) else h["label"]
		cols.append({"fieldname": h["key"], "label": label, "fieldtype": "Data", "width": 120})
	cols += [
		{"fieldname": "pct_mezcla", "label": "% mezcla", "fieldtype": "Percent", "width": 90},
		{"fieldname": "minimo", "label": "Mín TDS", "fieldtype": "Data", "width": 80},
		{"fieldname": "maximo", "label": "Máx TDS", "fieldtype": "Data", "width": 80},
		{"fieldname": "cumplimiento", "label": "Cumplimiento", "fieldtype": "Data", "width": 130},
		{"fieldname": "n_lotes", "label": "N° lotes", "fieldtype": "Int", "width": 80},
		{"fieldname": "nota", "label": "Nota", "fieldtype": "Data", "width": 320},
	]
	return cols


def _cell(v):
	"""A number stays a number (so the Excel export is numeric); COA text such as
	"<0.05" or "Negative" is kept verbatim, never coerced."""
	if v is None or v == "":
		return None
	if isinstance(v, (int, float)):
		return v
	try:
		return float(v)
	except (TypeError, ValueError):
		return str(v)


def _verdict(p):
	"""Overall status, stamped when the TDS that judged it is a draft."""
	return f"{p['overall']} (TDS en borrador)" if p["borrador"] else p["overall"]


def _headline_note(p, headline):
	"""When a headline column mixes parameters/UOMs across proposals, say which
	parameter this proposal's value is."""
	parts = []
	for h in headline:
		ph = p["headline"][h["key"]]
		if not h["uniform"] and ph["spec"]:
			parts.append(f"{h['label']} = {ph['spec']}" + (f" ({ph['uom']})" if ph["uom"] else ""))
	return "; ".join(parts)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = build(filters.get("producto"), sales_order=filters.get("sales_order"), tds=filters.get("tds"))
	headline = data["headline"]
	rows = []

	# 1. Comparativo para decisión: one row per proposal
	for p in data["proposals"]:
		nota = "; ".join(x for x in [_headline_note(p, headline)] + p["notes"] if x)
		row = {"seccion": "Comparativo", "propuesta": p["name"], "concepto": p["formula_name"],
			"tds_aplicada": p["tds_label"], "cantidad_kg": p["total_kg"], "cumplimiento": _verdict(p),
			"n_lotes": p["n_lotes"], "nota": nota, "indent": 0}
		for h in headline:
			row[h["key"]] = _cell(p["total"][h["key"]])
		rows.append(row)

	# 2. Per proposal: lot lines, the gate's TOTAL, the compliance per TDS parameter
	for p in data["proposals"]:
		tds = p["tds_label"]
		rows.append({"seccion": "Propuesta", "propuesta": p["name"],
			"concepto": f"{p['formula_name']} · {p['formula_type']} · {p['fecha'] or ''}",
			"tds_aplicada": tds, "cantidad_kg": p["total_kg"], "n_lotes": p["n_lotes"],
			"cumplimiento": _verdict(p), "nota": p["prediction_note"] or "", "indent": 0, "bold": 1})
		for ln in p["lines"]:
			row = {"seccion": "Lote", "propuesta": p["name"], "concepto": ln["lote"], "tds_aplicada": tds,
				"cantidad_kg": ln["kg"], "pct_mezcla": ln["pct"], "nota": ln["nota"], "indent": 1}
			for h in headline:
				row[h["key"]] = _cell(ln["values"][h["key"]]) if ln["coa"] else None
			rows.append(row)
		total = {"seccion": "TOTAL (puerta)", "propuesta": p["name"], "concepto": "Total ponderado (Simular)",
			"tds_aplicada": tds, "cantidad_kg": p["total_kg"], "nota": _headline_note(p, headline),
			"indent": 1, "bold": 1}
		for h in headline:
			total[h["key"]] = _cell(p["total"][h["key"]])
		rows.append(total)
		for c in p["compliance"]:
			rows.append({"seccion": "Cumplimiento", "propuesta": p["name"],
				"concepto": f"{c['parameter']}" + (f" ({c['uom']})" if c["uom"] else ""),
				"tds_aplicada": tds, "minimo": _fmt_bound(c["min"]), "maximo": _fmt_bound(c["max"]),
				"cumplimiento": "descriptivo — laboratorio" if c["kind"] == "descriptive" else mark(c["ok"]),
				"nota": f"predicho: {c['value']:g}" if isinstance(c["value"], float)
					else f"predicho: {c['value']}" if c["value"] is not None else "predicho: sin dato",
				"indent": 2})

	if data["tds"]:
		b = data["tds"]
		tds_txt = b["name"] if b["status"] == "aprobada" else f"{b['name']} ({b['status']})"
	elif data["proposals"]:
		tds_txt = "por propuesta (filtro vacío: la target_tds de cada una)"
	else:
		tds_txt = data["tds_filter"] or "—"
	props = data["proposals"]
	summary = [
		{"label": "Producto", "value": f"{data['producto']} {data['item_name'] or ''}".strip(), "datatype": "Data"},
		{"label": "TDS", "value": tds_txt, "datatype": "Data"},
		{"label": "Propuestas", "value": len(props), "datatype": "Int"},
		{"label": "Cumplen (TDS aprobada)", "value": sum(1 for p in props if p["overall"] == CUMPLE and not p["borrador"]),
		 "datatype": "Int", "indicator": "Green"},
		{"label": "Cumplen con TDS en borrador", "value": sum(1 for p in props if p["overall"] == CUMPLE and p["borrador"]),
		 "datatype": "Int", "indicator": "Orange"},
	]
	return _columns(headline), rows, None, None, summary
