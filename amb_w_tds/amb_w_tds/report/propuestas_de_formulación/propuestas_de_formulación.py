# Script Report "Propuestas de Formulación" -- the grid / Excel surface.
# All logic lives in amb_w_tds.formulation.propuestas (shared with the PDF Print Format).

import frappe

from amb_w_tds.formulation.propuestas import HEADLINE, build, mark


def _fmt_bound(v):
	return "" if v is None else f"{v:g}"


def _columns(headline):
	cols = [
		{"fieldname": "seccion", "label": "Sección", "fieldtype": "Data", "width": 150},
		{"fieldname": "propuesta", "label": "Propuesta", "fieldtype": "Link", "options": "BOM Formula", "width": 170},
		{"fieldname": "concepto", "label": "Lote / Parámetro", "fieldtype": "Data", "width": 220},
		{"fieldname": "cantidad_kg", "label": "Cantidad (kg)", "fieldtype": "Float", "precision": 3, "width": 110},
	]
	for h in headline:
		label = f"{h['label']} ({h['uom']})" if h["uom"] else h["label"]
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
	return "" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = build(filters.get("producto"), sales_order=filters.get("sales_order"), tds=filters.get("tds"))
	headline = data["headline"]
	rows = []

	# 1. Comparativo para decisión: one row per proposal
	for p in data["proposals"]:
		row = {"seccion": "Comparativo", "propuesta": p["name"], "concepto": p["formula_name"],
			"cantidad_kg": p["total_kg"], "cumplimiento": p["overall"], "n_lotes": p["n_lotes"],
			"nota": "; ".join(p["notes"]), "indent": 0}
		for h in headline:
			row[h["key"]] = _cell(p["total"][h["key"]])
		rows.append(row)

	# 2. Per proposal: lot lines, the gate's TOTAL, the compliance per TDS parameter
	for p in data["proposals"]:
		rows.append({"seccion": "Propuesta", "propuesta": p["name"],
			"concepto": f"{p['formula_name']} · {p['formula_type']} · {p['fecha'] or ''}",
			"cantidad_kg": p["total_kg"], "n_lotes": p["n_lotes"], "cumplimiento": p["overall"],
			"nota": p["prediction_note"] or "", "indent": 0, "bold": 1})
		for ln in p["lines"]:
			row = {"seccion": "Lote", "propuesta": p["name"], "concepto": ln["lote"], "cantidad_kg": ln["kg"],
				"pct_mezcla": ln["pct"], "nota": ln["nota"], "indent": 1}
			for h in headline:
				row[h["key"]] = _cell(ln["values"][h["key"]]) if ln["coa"] else ""
			rows.append(row)
		total = {"seccion": "TOTAL (puerta)", "propuesta": p["name"], "concepto": "Total ponderado (Simular)",
			"cantidad_kg": p["total_kg"], "indent": 1, "bold": 1}
		for h in headline:
			total[h["key"]] = _cell(p["total"][h["key"]])
		rows.append(total)
		for c in p["compliance"]:
			rows.append({"seccion": "Cumplimiento", "propuesta": p["name"],
				"concepto": f"{c['parameter']}" + (f" ({c['uom']})" if c["uom"] else ""),
				"minimo": _fmt_bound(c["min"]), "maximo": _fmt_bound(c["max"]),
				"cumplimiento": "descriptivo — laboratorio" if c["kind"] == "descriptive" else mark(c["ok"]),
				"nota": f"predicho: {_cell(c['value'])}" if c["value"] is not None else "predicho: sin dato",
				"indent": 2})

	if data["tds"]:
		tds_txt = data["tds"]["name"]
	else:
		tds_txt = "sin TDS: valores predichos sin límites ni cumplimiento"
	summary = [
		{"label": "Producto", "value": f"{data['producto']} {data['item_name'] or ''}".strip(), "datatype": "Data"},
		{"label": "TDS", "value": tds_txt, "datatype": "Data"},
		{"label": "Propuestas", "value": len(data["proposals"]), "datatype": "Int"},
		{"label": "Cumplen", "value": sum(1 for p in data["proposals"] if p["overall"] == "CUMPLE"), "datatype": "Int",
		 "indicator": "Green"},
	]
	return _columns(headline), rows, None, None, summary
