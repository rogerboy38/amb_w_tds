"""BOM Formula "Propuesta" actions (13.10.0): generate + attach the Propuestas de Formulación
PDF and Excel to a proposal, share it (Frappe-native, on the form), and, as a supporting
action, email the files to Dirección; plus what the form may offer the current user.

- Same artifacts as the report: the Excel is the report's own export (`_export_query`),
  the PDF is the Print Format "Propuestas de Formulación", both with the SAME filters
  (the record's product and its Sales Order), so screen = Excel = PDF still holds.
- Permission: exactly what the report itself demands (frappe.desk.query_report.get_report_doc):
  the report's roles AND the "report" right on BOM Formula, plus read on this record.
- Recipients are site configuration: Formulation Settings "Destinatarios de Dirección"
  (a table of Users). Never a parameter of the call, never a literal in code.
- Writes nothing on BOM Formula's fields: it creates two private File attachments and, for
  "Enviar a Dirección", one outgoing email (Email Queue) referencing the record.
"""

import re

import frappe
from frappe import _
from frappe.utils import now_datetime

REPORT = "Propuestas de Formulación"
PRINT_FORMAT = "Propuestas de Formulación"
NO_RECIPIENTS = _("Configure los destinatarios de Dirección en Formulation Settings (\"Destinatarios de Dirección\").")


def _report_allowed() -> bool:
	report = frappe.get_doc("Report", REPORT)
	return bool(report.is_permitted() and frappe.has_permission("BOM Formula", "report"))


def _load(bom_formula):
	doc = frappe.get_doc("BOM Formula", bom_formula)
	doc.check_permission("read")
	if not _report_allowed():
		frappe.throw(_("No tiene acceso al reporte {0}.").format(REPORT), frappe.PermissionError)
	if not doc.product_sku:
		frappe.throw(_("La propuesta no tiene producto (Product SKU)."))
	return doc


def _filters(doc):
	filters = {"producto": doc.product_sku}
	if doc.sales_order:
		filters["sales_order"] = doc.sales_order
	return filters


def _excel(doc) -> bytes:
	"""The report's own Excel export (frappe.desk.query_report._export_query)."""
	from frappe.desk.query_report import _export_query

	form_params = frappe._dict({"report_name": REPORT, "file_format_type": "Excel",
		"filters": _filters(doc), "include_indentation": 1, "ignore_visible_idx": 1})
	_name, _ext, content = _export_query(form_params, frappe._dict(), populate_response=False)
	return content


def _pdf(doc) -> bytes:
	"""The Print Format, requested exactly as the report's "PDF para Dirección" button does."""
	saved = frappe.local.form_dict
	frappe.local.form_dict = frappe._dict({"pedido": doc.sales_order or "", "tds": ""})
	try:
		return frappe.get_print("BOM Formula", doc.name, PRINT_FORMAT, as_pdf=True)
	finally:
		frappe.local.form_dict = saved


def _attach(doc, file_name, content):
	f = frappe.get_doc({"doctype": "File", "file_name": file_name, "attached_to_doctype": "BOM Formula",
		"attached_to_name": doc.name, "is_private": 1, "content": content})
	# the caller's read + report rights were checked in _load; attaching is part of this action
	f.insert(ignore_permissions=True)
	return f


def _stem(doc):
	safe = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{doc.product_sku}-{doc.name}").strip("-")
	return f"Propuestas-{safe}-{now_datetime():%Y%m%d-%H%M%S}"


def _generate(doc):
	stem = _stem(doc)
	pdf = _attach(doc, f"{stem}.pdf", _pdf(doc))
	xlsx = _attach(doc, f"{stem}.xlsx", _excel(doc))
	return {"pdf": pdf.file_url, "excel": xlsx.file_url, "pdf_file": pdf.name, "excel_file": xlsx.name}


def direccion_recipients():
	"""Email addresses of the enabled users in Formulation Settings "Destinatarios de Dirección"."""
	users = [r.user for r in (frappe.get_single("Formulation Settings").get("destinatarios_direccion") or []) if r.user]
	if not users:
		return []
	return [u.email for u in frappe.get_all("User", filters={"name": ("in", users), "enabled": 1},
		fields=["email"], order_by="name asc") if u.email]


@frappe.whitelist()
def propuesta_access(bom_formula):
	"""What the form may offer the current user (buttons are hidden otherwise)."""
	doc = frappe.get_doc("BOM Formula", bom_formula)
	allowed = bool(frappe.has_permission("BOM Formula", "read", doc) and _report_allowed())
	return {"allowed": allowed,
		"recipients_configured": bool(direccion_recipients()) if allowed else False,
		"can_share": bool(frappe.has_permission("BOM Formula", "share", doc))}


@frappe.whitelist(methods=["POST"])
def generate_propuesta_files(bom_formula):
	"""Render the Propuestas PDF + Excel for this record's product and attach both to it."""
	return _generate(_load(bom_formula))


@frappe.whitelist(methods=["POST"])
def email_propuesta_to_direccion(bom_formula):
	"""Attach fresh PDF + Excel and email them to the configured Dirección recipients."""
	doc = _load(bom_formula)
	recipients = direccion_recipients()
	if not recipients:
		frappe.throw(NO_RECIPIENTS, title=_("Sin destinatarios de Dirección"))
	files = _generate(doc)
	pedido = f" · Pedido {doc.sales_order}" if doc.sales_order else ""
	frappe.sendmail(
		recipients=recipients,
		subject=_("Propuesta de formulación — {0} ({1})").format(doc.product_sku, doc.name),
		message=_(
			"<p>Se adjunta la comparación de propuestas de formulación para el producto <b>{0}</b>{1}, "
			"generada desde la propuesta {2}, para la decisión de Dirección:</p>"
			"<ul><li>PDF para revisión y firma (Decisión de Dirección).</li>"
			"<li>Excel con el detalle por lote, el total ponderado y el cumplimiento contra la TDS.</li></ul>"
			"<p>Valores estimados por la puerta (Simular); la liberación requiere el valor medido del lote mezclado.</p>"
		).format(frappe.utils.escape_html(doc.product_sku), frappe.utils.escape_html(pedido),
			frappe.utils.escape_html(doc.name)),
		attachments=[{"fid": files["pdf_file"]}, {"fid": files["excel_file"]}],
		reference_doctype="BOM Formula",
		reference_name=doc.name,
	)
	return {"sent_to": len(recipients), **files}
