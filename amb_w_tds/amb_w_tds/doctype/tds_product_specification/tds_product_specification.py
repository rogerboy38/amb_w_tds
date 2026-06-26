import frappe
from frappe import _
from frappe.model.document import Document

class TDSProductSpecification(Document):
    """TDS Product Specification Doctype"""
    
    pass


@frappe.whitelist()
def generate_tds_pdf(tds_name, attach_to_doctype=None, attach_to_name=None):
	"""Generate a PDF for a TDS Product Specification via the TDS AMB FoxPro pipeline.
	#37: when called from a Sample Request, also attach the PDF to that SR."""
	try:
		from amb_print.amb_print.api import print_document_pdf
		from amb_w_tds.amb_w_tds.doctype.coa_amb.coa_amb import _attach_file_url_to
		res = print_document_pdf(
			doctype="TDS Product Specification",
			docname=tds_name,
			print_format="TDS AMB FoxPro",
			save_attachment=1,
			is_private=0,
		)
		file_url = (res or {}).get("file_url")
		_attach_file_url_to(file_url, attach_to_doctype, attach_to_name)
		return file_url
	except Exception as e:
		frappe.log_error(f"Error generating TDS PDF: {e}", "TDS PDF Generation")
		frappe.throw(_("Error generating TDS PDF: {0}").format(str(e)))
