"""BUG208 A4 — standing guards on schema facts the fix silently depends on.

⭐ WHY THIS FILE EXISTS. Two of BUG208's remedies are not code at all; they are
single keys in a DocType JSON:

  * `currency` default = "USD"  -- the whole "born USD" property
  * `shipment_nature` reqd = 1  -- what stops NULL-nature documents recurring

Both are one Customize-Form save, one fixture, or one stale doctype reload away
from vanishing, and NOTHING downstream would complain. The currency one is the
sharper risk: **this site is MXN underneath** -- Global Defaults and all six
Companies are MXN -- so if the USD default is dropped, new Sample Requests do
not fail, they quietly start being born MXN again and print MXN on customs
paperwork. That is the exact shape BUG208 was reported as: a plausible wrong
value that nobody notices.

⚠ These read the SHIPPED APP FILE, not the database. That is deliberate: the
app file is what `migrate` restores from, so it is the thing whose loss is
permanent. A DB-side check is offered separately (`check_live_schema_guards`)
for a deployed tier, because the two can disagree and each answers a different
question.
"""

import json
import os
import unittest

DOCTYPE_JSON = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "amb_w_tds", "doctype",
    "sample_request_amb", "sample_request_amb.json",
))


def _field(fieldname):
    with open(DOCTYPE_JSON, encoding="utf-8") as fh:
        doc = json.load(fh)
    for f in doc["fields"]:
        if f["fieldname"] == fieldname:
            return f
    return None


class TestShippedSchemaGuards(unittest.TestCase):

    def test_the_doctype_file_is_readable_and_populated(self):
        """POSITIVE CONTROL. Without this, a renamed or truncated file would
        make every assertion below fail for the wrong reason -- or, worse, a
        `None` return would be read as 'the guard ran and found nothing'."""
        with open(DOCTYPE_JSON, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertGreater(len(doc["fields"]), 100)
        self.assertIsNotNone(_field("commercial_value_usd"))

    def test_currency_default_is_usd(self):
        """A4 — if this fails, new documents are born MXN and print MXN."""
        fld = _field("currency")
        self.assertIsNotNone(fld, "the currency field itself is gone")
        self.assertEqual(
            fld.get("default"), "USD",
            "currency default lost — new Sample Requests will inherit the "
            "site's MXN default and declare MXN on customs documents",
        )

    def test_shipment_nature_is_required(self):
        """A3 — the field being required is what prevents new NULL-nature docs;
        the Mode-A code default only covers the residual ones."""
        fld = _field("shipment_nature")
        self.assertIsNotNone(fld)
        self.assertTrue(fld.get("reqd"), "shipment_nature is no longer required")

    def test_the_valuation_mode_selector_survives(self):
        fld = _field("custom_valuation_mode")
        self.assertIsNotNone(fld, "the A/B/C selector is gone")
        self.assertEqual(sorted((fld.get("options") or "").split()), ["A", "B", "C"])


def check_live_schema_guards():
    """DB-side twin of the above, for a deployed tier (Node A / Node C).

    Returns a list of failure strings; empty means clean. Deliberately returns
    findings rather than raising, so a deploy check can report ALL of them at
    once instead of stopping at the first.
    """
    import frappe

    problems = []
    checks = [
        ("Sample Request AMB", "currency", "default", "USD"),
        ("Sample Request AMB", "shipment_nature", "reqd", 1),
    ]
    for doctype, fieldname, prop, expected in checks:
        actual = frappe.db.get_value("DocField", {"parent": doctype, "fieldname": fieldname}, prop)
        if str(actual or "") != str(expected):
            problems.append(f"{doctype}.{fieldname}.{prop} = {actual!r}, expected {expected!r}")

    # ⚠ A Property Setter is the usual way one of these dies without the app
    # file changing at all -- Customize Form writes one and migrate keeps it.
    for fieldname in ("currency", "shipment_nature"):
        overrides = frappe.get_all(
            "Property Setter",
            filters={"doc_type": "Sample Request AMB", "field_name": fieldname},
            fields=["name", "property", "value"],
        )
        for o in overrides:
            problems.append(
                f"Property Setter {o.name} overrides {fieldname}.{o.property} = {o.value!r}"
            )
    return problems


if __name__ == "__main__":
    unittest.main(verbosity=2)
