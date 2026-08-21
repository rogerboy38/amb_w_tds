"""BUG208 D-CCY — the BEHAVIOURAL guard on "born USD".

⭐⭐ WHY THIS FILE EXISTS, AND WHY IT IS NOT IN THE SCHEMA GUARDS.

`sample_request_amb.json` has carried `"currency": {"default": "USD"}` since
2026-04-30. A schema test asserting that key PASSED the whole time — while every
new document was born **MXN**. I read the key and reported "already correct, a
no-op" to the fleet. It was present and UNREACHABLE:

    frappe/model/create_new.py
      :88   user_default = defaults.get(df.fieldname)   # keyed on "currency"
      :95   if user_default ...: return user_default    # ⛔ returns HERE
      :115  return df.default                           # never reached

Global Defaults sets `default_currency = MXN`, which surfaces in
`frappe.defaults` under the key **"currency"** — the same string as the field's
name — so a site-wide default beats the field's own default purely by a name
collision.

⇒ **A declaration is not a behaviour.** The schema guard asserts the key exists;
THIS file asserts what a document actually gets, which is the only thing that
was ever in question. Same shape as the render-precision split: the arithmetic
was right and the page was wrong.

⚠ Needs a bench; skips loudly without one rather than passing.
"""

import unittest

try:
    import frappe
    _HAVE_FRAPPE = True
except Exception:  # pragma: no cover
    _HAVE_FRAPPE = False

_CONNECTED = False
_MADE = []


def setUpModule():
    global _CONNECTED
    if not _HAVE_FRAPPE:
        return
    try:
        frappe.init(site="v2.sysmayal.cloud", sites_path="/home/frappe/frappe-bench/sites")
        frappe.connect()
        frappe.set_user("Administrator")
        _CONNECTED = True
    except Exception:
        _CONNECTED = False


def tearDownModule():
    if not _CONNECTED:
        return
    for name in _MADE:
        try:
            frappe.delete_doc("Sample Request AMB", name, force=True, ignore_permissions=True)
        except Exception:
            pass
    frappe.db.commit()
    frappe.destroy()


@unittest.skipUnless(_HAVE_FRAPPE, "needs a bench")
class TestBornCurrency(unittest.TestCase):

    def setUp(self):
        if not _CONNECTED:
            self.skipTest("frappe present but not connected")

    def _make(self, preset=None):
        item = frappe.db.get_value("Item", {"stock_uom": "Kg"}, "name")
        doc = frappe.new_doc("Sample Request AMB")
        doc.shipment_nature = "Venta"
        doc.request_date = frappe.utils.nowdate()
        doc.commercial_value_usd = 1.00
        if preset is not None:
            doc.currency = preset
        doc.append("samples", {"item": item, "samples_count": 2, "qty_per_sample": 0.02})
        doc.insert(ignore_permissions=True)
        _MADE.append(doc.name)
        return doc

    def test_the_site_really_does_default_to_mxn(self):
        """POSITIVE CONTROL, and the reason the JSON key is not enough. If this
        ever returns USD, the collision is gone and the controller fix below
        becomes belt-and-braces rather than load-bearing — worth knowing."""
        self.assertEqual(frappe.defaults.get_defaults().get("currency"), "MXN")

    def test_a_new_document_is_born_usd_despite_the_site_default(self):
        self.assertEqual(self._make().currency, "USD")

    def test_an_explicitly_blank_currency_becomes_usd(self):
        self.assertEqual(self._make("").currency, "USD")

    def test_a_deliberate_non_usd_choice_survives(self):
        """⭐ THE RULED OVERRIDE. D-CCY keeps the field editable for a genuine
        non-USD export, so the fix must overwrite ONLY the value the site handed
        us — never a value a person chose. Forcing USD unconditionally would
        pass the test above and silently destroy this one."""
        self.assertEqual(self._make("EUR").currency, "EUR")
        self.assertEqual(self._make("CAD").currency, "CAD")

    def test_an_explicit_usd_choice_is_untouched(self):
        self.assertEqual(self._make("USD").currency, "USD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
