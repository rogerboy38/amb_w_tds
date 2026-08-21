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

    def _make(self, preset=None, desk=False):
        # ⚠ E2 and E6 must be asserted TOGETHER: a fix satisfying born-USD alone
        # can silently destroy the override, and vice versa.
        frappe.local.form_dict = frappe._dict(
            {"cmd": "frappe.desk.form.save.savedocs"} if desk else {}
        )
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


class TestE6FormPathOverride(unittest.TestCase):
    """E6 — on the DESK path the form has already defaulted to USD, so any other
    value was typed by a person and must survive.

    ⭐ MXN is the case that matters: it is the site default, so value-equality
    alone cannot distinguish it from "nobody chose anything" — and it is exactly
    what a Mexican company might declare on a domestic shipment. The form
    default removes the need to guess instead of documenting the guess.
    """

    def setUp(self):
        if not _CONNECTED:
            self.skipTest("frappe present but not connected")

    _make = TestBornCurrency._make

    def test_an_explicit_mxn_survives_a_desk_save(self):
        self.assertEqual(self._make("MXN", desk=True).currency, "MXN")

    def test_other_explicit_choices_survive_a_desk_save(self):
        self.assertEqual(self._make("EUR", desk=True).currency, "EUR")
        self.assertEqual(self._make("USD", desk=True).currency, "USD")

    def test_the_api_path_still_corrects_the_site_default(self):
        """E8 must not be traded away to close E6 — the paths are asserted
        together so neither fix can quietly undo the other."""
        self.assertEqual(self._make("MXN", desk=False).currency, "USD")
        self.assertEqual(self._make(None, desk=False).currency, "USD")

    def test_the_api_path_still_preserves_a_deliberate_non_default(self):
        self.assertEqual(self._make("EUR", desk=False).currency, "EUR")

    def test_the_desk_detector_fails_closed(self):
        """⚠ Any doubt returns False, keeping the override. A wrong False costs
        an explicit MXN on a non-form path; a wrong True re-opens E8 silently."""
        from amb_w_tds.amb_w_tds.doctype.sample_request_amb.sample_request_amb import SampleRequestAMB
        frappe.local.form_dict = frappe._dict({})
        self.assertFalse(SampleRequestAMB._came_from_the_desk_form())
        frappe.local.form_dict = frappe._dict({"cmd": "something.else"})
        self.assertFalse(SampleRequestAMB._came_from_the_desk_form())


if __name__ == "__main__":
    unittest.main(verbosity=2)


@unittest.skipUnless(_HAVE_FRAPPE, "needs a bench")
class TestE6DetectorDependencyIsPinned(unittest.TestCase):
    """OPEN #11 — the E6 detector keys on an INTERNAL frappe RPC string.

    `_came_from_the_desk_form()` compares `form_dict.cmd` against
    "frappe.desk.form.save.savedocs". That is frappe's own desk-save endpoint,
    not a public contract: if an upgrade renames or re-routes it, the detector
    starts returning False for real desk saves and **E6 silently reverts to the
    old value-equality guess** — an operator's explicit MXN would quietly begin
    being overwritten again, with every test still green, because the fallback
    is the behaviour those tests were written against.

    ⭐ THE FAILURE IS SILENT BY DESIGN (the detector fails closed on purpose),
    which is exactly why the DEPENDENCY needs its own alarm. A fail-closed
    default protects correctness at the cost of hiding its own trigger.

    These tests fail LOUDLY on a frappe upgrade that moves the marker, naming
    what to re-check rather than leaving a behaviour change to be discovered on
    a customs document.
    """

    MARKER = "frappe.desk.form.save.savedocs"

    def setUp(self):
        if not _CONNECTED:
            self.skipTest("frappe present but not connected")

    def test_the_endpoint_the_marker_names_still_exists(self):
        import importlib
        module_path, _, attr = self.MARKER.rpartition(".")
        module = importlib.import_module(module_path)
        self.assertTrue(
            hasattr(module, attr),
            f"{self.MARKER} is gone (frappe {frappe.__version__}) — the E6 desk "
            f"detector will now fail closed on EVERY save and an explicit MXN "
            f"will be silently overwritten again. Re-derive the desk-save marker.",
        )

    def test_the_endpoint_is_still_whitelisted_as_an_rpc(self):
        """Existing is not enough: it has to be the thing the desk actually
        CALLS, or `form_dict.cmd` will never carry this string."""
        import importlib
        module_path, _, attr = self.MARKER.rpartition(".")
        fn = getattr(importlib.import_module(module_path), attr)
        self.assertTrue(
            getattr(fn, "__func__", fn) in frappe.whitelisted,
            f"{self.MARKER} exists but is no longer a whitelisted RPC — the desk "
            f"is reaching Save by some other route, so cmd will not match.",
        )

    def test_the_controller_and_this_test_name_the_same_marker(self):
        """⚠ Pins the string in ONE place. If the controller's marker is edited
        without this test, the alarm would guard a string nobody uses — a guard
        watching the wrong door is worse than no guard."""
        import inspect
        from amb_w_tds.amb_w_tds.doctype.sample_request_amb.sample_request_amb import SampleRequestAMB
        src = inspect.getsource(SampleRequestAMB._came_from_the_desk_form)
        self.assertIn(self.MARKER, src)
