import frappe
from frappe.model.document import Document

class TDSProductSpecification(Document):
    """TDS Product Specification Doctype"""
    
    pass


@frappe.whitelist()
def generate_tds_pdf(tds_name):
	"""Generate a PDF for a TDS Product Specification via the TDS AMB FoxPro pipeline."""
	try:
		from amb_print.amb_print.api import print_document_pdf
		res = print_document_pdf(
			doctype="TDS Product Specification",
			docname=tds_name,
			print_format="TDS AMB FoxPro",
			save_attachment=1,
			is_private=0,
		)
		return (res or {}).get("file_url")
	except Exception as e:
		frappe.log_error(f"Error generating TDS PDF: {e}", "TDS PDF Generation")
		frappe.throw(_("Error generating TDS PDF: {0}").format(str(e)))
