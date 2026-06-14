"""P1.4 — COA QR Phase-1 (T120 §8, Hugh-approved): automatic, token→shared-file, fail-safe.

Flow:
  * COA AMB on_submit  -> mint a per-lot OPAQUE token, render the default COA PDF and attach
    it as a SHARED file (is_private=0). Fully automatic; signature-guarded so ANY failure here
    never breaks the submit (the PDF/print is the legal source of truth; the QR is additive).
  * The QR encodes a STABLE token URL ({base}/cv?t=<token>) that REDIRECTS to the *current*
    shared PDF — so the QR survives PDF re-generation and gating can be added later without a
    reprint.
  * Print-time helper coa_qr_img(doc) emits the QR ONLY when a token exists AND a reachable
    SHARED PDF exists — otherwise it returns '' (no QR). Never points a QR at a private/missing
    URL; never raises into the print. Fail-safe per T120 §8.3.

Config: site_config 'coa_qr_base_url' (default below) makes the verification domain a one-line
switch (Daniel decision #2 — id.amb-wellness.com vs erp.sysmayal2.cloud — is non-blocking).
Phase-2 GS1 Digital Link (GTIN+lot) is deferred until GTINs are assigned.
"""
import base64
import io

import frappe

DEFAULT_BASE_URL = "https://erp.sysmayal2.cloud"


def _base_url():
    return (frappe.conf.get("coa_qr_base_url") or DEFAULT_BASE_URL).rstrip("/")


def verify_url(token):
    """Stable per-lot verification URL carried in the QR (redirects to current shared PDF)."""
    return f"{_base_url()}/cv?t={token}"


def get_or_create_token(doc):
    name = doc.get("name") if hasattr(doc, "get") else doc
    token = frappe.db.get_value("COA AMB", name, "qr_token")
    if not token:
        token = frappe.generate_hash(length=22)
        frappe.db.set_value("COA AMB", name, "qr_token", token, update_modified=False)
        if hasattr(doc, "name"):
            doc.qr_token = token
    return token


def shared_pdf_url(coa_name):
    """file_url of the most recent SHARED (is_private=0) PDF attached to this COA, else None."""
    rows = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "COA AMB",
            "attached_to_name": coa_name,
            "is_private": 0,
            "file_url": ["like", "%.pdf"],
        },
        fields=["file_url"],
        order_by="creation desc",
        limit=1,
    )
    return rows[0].file_url if rows else None


def _render_and_attach_shared_pdf(doc):
    from frappe.utils.pdf import get_pdf

    pf = frappe.get_meta("COA AMB").default_print_format or "COA AMB FoxPro"
    html = frappe.get_print("COA AMB", doc.name, print_format=pf)
    # ignore load/media errors so a stray/unresolvable asset URL can never HANG wkhtmltopdf
    # (observed: COA FoxPro triggers a ProtocolUnknownError; default get_pdf would stall).
    pdf = get_pdf(html, options={"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
    fname = "COA-{}.pdf".format(doc.get("coa_number") or doc.name)
    fname = fname.replace("/", "-").replace(" ", "_")
    f = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": fname,
            "attached_to_doctype": "COA AMB",
            "attached_to_name": doc.name,
            "is_private": 0,
            "content": pdf,
        }
    ).insert(ignore_permissions=True)
    return f.file_url


def qr_data_uri(url, box_size=4, ec="Q"):
    """PNG data: URI for the QR at error-correction level Q. Returns '' on any failure."""
    try:
        import qrcode

        levels = {
            "L": qrcode.constants.ERROR_CORRECT_L,
            "M": qrcode.constants.ERROR_CORRECT_M,
            "Q": qrcode.constants.ERROR_CORRECT_Q,
            "H": qrcode.constants.ERROR_CORRECT_H,
        }
        qr = qrcode.QRCode(
            error_correction=levels.get(ec, qrcode.constants.ERROR_CORRECT_Q),
            box_size=box_size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def coa_qr_img(doc):
    """Jinja helper. Full <img> QR tag for the COA, or '' when not safe to emit (fail-safe).

    Emits ONLY when a token exists AND a reachable SHARED PDF exists for this COA — so a scan
    always opens the real document and a QR is never printed pointing at a private/missing URL.
    Never raises into the print.
    """
    try:
        name = doc.get("name") if hasattr(doc, "get") else doc
        if not name:
            return ""
        token = frappe.db.get_value("COA AMB", name, "qr_token")
        if not token:
            return ""
        if not shared_pdf_url(name):
            return ""
        uri = qr_data_uri(verify_url(token))
        if not uri:
            return ""
        # reuse the format's existing .coa-qr slot for placement; inline size guarantees ~28 mm
        return (
            '<img class="coa-qr" alt="COA verification QR" src="{}" '
            'style="width:28mm;height:28mm;image-rendering:pixelated;" />'.format(uri)
        )
    except Exception:
        return ""


def enqueue_attach_shared_pdf(coa_name):
    """Background job: render the default COA PDF and attach it as a shared file. Idempotent."""
    try:
        if shared_pdf_url(coa_name):
            return
        doc = frappe.get_doc("COA AMB", coa_name)
        _render_and_attach_shared_pdf(doc)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "coa_qr.enqueue_attach_shared_pdf")


def on_coa_submit(doc, method=None):
    """COA AMB on_submit: mint token (sync, instant) + ENQUEUE the shared-PDF render.

    Signature-guarded AND non-blocking: the PDF render is pushed to a background worker
    (enqueue_after_commit) so a slow/hanging wkhtmltopdf can never block the submit or gate a
    release (T120 §8.3). The QR simply stays absent until the shared PDF lands (helper is
    defensive). The printed PDF in hand is always the source of truth.
    """
    try:
        get_or_create_token(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "coa_qr.on_coa_submit:token")
    try:
        if not shared_pdf_url(doc.name):
            frappe.enqueue(
                "amb_w_tds.coa_qr.enqueue_attach_shared_pdf",
                queue="short",
                timeout=120,
                enqueue_after_commit=True,
                coa_name=doc.name,
            )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "coa_qr.on_coa_submit:enqueue")
