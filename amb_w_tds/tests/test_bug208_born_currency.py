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
_OWNS = False  # True only when this module opened the connection itself
_MADE = []
# Decision 8 (TASKS-268): fixtures this module builds for itself, so it runs on a
# fresh site (CI) as well as on the dev site. Created only when missing; undone in
# tearDownModule. On the dev site (default currency already MXN, Kg items present)
# this changes nothing.
_FIXTURE_ITEM = "_Test AMB Born Currency Item"
_CREATED_ITEM = None
_PREV_CURRENCY = None


def _build_fixtures():
	"""The site default currency is MXN (the collision this file is about) and an
	Item stocked in Kg exists for the sample rows."""
	global _CREATED_ITEM, _PREV_CURRENCY
	_PREV_CURRENCY = frappe.defaults.get_defaults().get("currency")
	if _PREV_CURRENCY != "MXN":
		frappe.db.set_default("currency", "MXN")
	if not frappe.db.get_value("Item", {"stock_uom": "Kg"}, "name"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": _FIXTURE_ITEM,
				"item_name": _FIXTURE_ITEM,
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}),
				"stock_uom": "Kg",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)
		_CREATED_ITEM = _FIXTURE_ITEM


def _undo_fixtures():
	if _CREATED_ITEM and frappe.db.exists("Item", _CREATED_ITEM):
		frappe.delete_doc("Item", _CREATED_ITEM, force=True, ignore_permissions=True)
	if _PREV_CURRENCY == "MXN":
		return
	if _PREV_CURRENCY:
		frappe.db.set_default("currency", _PREV_CURRENCY)
	else:
		frappe.defaults.clear_default("currency", parent="__default")


def setUpModule():
	global _CONNECTED, _OWNS
	if not _HAVE_FRAPPE:
		return
	if getattr(frappe.local, "db", None):
		# Already connected, e.g. under bench run-tests: reuse the runner's
		# connection and never tear it down or commit it.
		_CONNECTED, _OWNS = True, False
		_build_fixtures()
		return
	try:
		frappe.init(site="v2.sysmayal.cloud", sites_path="/home/frappe/frappe-bench/sites")
		frappe.connect()
		frappe.set_user("Administrator")
		_CONNECTED, _OWNS = True, True
	except Exception:
		_CONNECTED = False
		return
	_build_fixtures()


def tearDownModule():
	if not _CONNECTED:
		return
	for name in _MADE:
		try:
			frappe.delete_doc("Sample Request AMB", name, force=True, ignore_permissions=True)
		except Exception:
			pass
	_undo_fixtures()
	if _OWNS:
		# Persist the cleanup and close only a connection this module opened.
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
		frappe.local.form_dict = frappe._dict({"cmd": "frappe.desk.form.save.savedocs"} if desk else {})
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
