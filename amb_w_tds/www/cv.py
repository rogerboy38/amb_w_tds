"""Public COA verification endpoint: /cv?t=<token>  (P1.4, T120 §8).

Resolves an opaque per-lot token to the COA's CURRENT shared PDF and 302-redirects to it
(double validation: the scan opens the real document). Fail-safe: if the token is unknown or
no reachable shared PDF exists, render a minimal confirmation page (NOT a data dump) instead of
erroring — the printed PDF in hand stays the source of truth. Guest-accessible.
"""
import frappe

no_cache = 1


def get_context(context):
    token = (frappe.form_dict.get("t") or "").strip()
    coa = None
    if token:
        coa = frappe.db.get_value(
            "COA AMB",
            {"qr_token": token},
            ["name", "coa_number", "item_name", "docstatus"],
            as_dict=True,
        )

    if coa:
        try:
            from amb_w_tds.coa_qr import shared_pdf_url

            url = shared_pdf_url(coa.name)
        except Exception:
            url = None
        if url:
            # 302 (temporary) so the redirect is NEVER cached — the token must always
            # follow the CURRENT shared PDF, which changes when the COA PDF is re-generated.
            frappe.local.flags.redirect_location = url
            raise frappe.Redirect(302)

    # fail-safe confirmation page (minimal metadata only; never errors, never dumps results)
    context.token = token
    context.coa = coa
    context.released = bool(coa) and coa.get("docstatus") == 1
    context.no_cache = 1
    return context
