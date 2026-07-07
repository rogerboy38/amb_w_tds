"""Selling-edge Pack Plan tests (§1c + 1b-FINAL amendments, 2026-07-06).

Runs against the dev site with SYNTHETIC data only (VABON SYNTH mirror shape:
one SO, two 0402 rows 20/5 kg @ 172.24, mixed pail sizes 25/10 kg). Every test
rolls back — nothing persists.

    bench --site v2.sysmayal.cloud run-tests --app amb_w_tds \
        --module amb_w_tds.tests.test_pack_plan
"""

import unittest

import frappe
from frappe.utils import flt

SYNTH_CUSTOMER = "VABON SYNTH GMBH (TEST)"
ITEM = "0402"
BAG_5KG = "E009"    # 5 kg poly bag  · FG Packaging Materials · tara 0.05
BAG_1KG = "E014"    # 1 kg metallized bag · Raw Materials · tara 0.05
PAIL_25 = "CN025"   # 25 kg pail · Consumables · tara 2.7 (F-8 corrected)
PAIL_10 = "CN010"   # 10 kg pail · Consumables · tara 1.7


def _ensure_customer():
    if not frappe.db.exists("Customer", {"customer_name": SYNTH_CUSTOMER}):
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": SYNTH_CUSTOMER,
            "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
            "territory": frappe.db.get_value("Territory", {"is_group": 0}),
        }).insert(ignore_permissions=True)
    return frappe.db.get_value("Customer", {"customer_name": SYNTH_CUSTOMER})


class TestPackPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.customer = _ensure_customer()

    def tearDown(self):
        frappe.db.rollback()

    # ---- helpers -------------------------------------------------------- #
    def _so(self, rows, plan=None, insert=True):
        doc = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": self.customer,
            "order_type": "Sales",
            "transaction_date": frappe.utils.today(),
            "delivery_date": frappe.utils.today(),
            "company": frappe.db.get_single_value("Global Defaults", "default_company"),
            "items": [{"item_code": ITEM, "qty": q, "rate": 172.24,
                       "delivery_date": frappe.utils.today()} for q in rows],
        })
        for p in plan or []:
            doc.append("custom_pack_plan", p)
        if insert:
            doc.insert(ignore_permissions=True)
        return doc

    def _vabon_plan(self, so):
        """The 2510101 mirror: 4×5 kg bags in a 25 kg pail / 5×1 kg bags in a
        10 kg pail — mixed pail sizes in one order (§1c amendment)."""
        r1, r2 = so.items[0].name, so.items[1].name
        return [
            {"so_item_row": r1, "package_item": BAG_5KG, "units_per_container": 4,
             "unit_net_kg": 5.0, "container_item": PAIL_25, "containers_qty": 1,
             "label_source": "Customer-supplied"},
            {"so_item_row": r2, "package_item": BAG_1KG, "units_per_container": 5,
             "unit_net_kg": 1.0, "container_item": PAIL_10, "containers_qty": 1,
             "label_source": "Customer-supplied"},
        ]

    # ---- computation + F-8 taras ---------------------------------------- #
    def test_group_net_computed_and_taras_fetched_never_typed(self):
        so = self._so([20.0, 5.0])
        for p in self._vabon_plan(so):
            p["unit_tara_kg"] = 99          # typed tara must be overwritten
            p["container_tara_kg"] = 99
            so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        row1, row2 = so.custom_pack_plan
        self.assertEqual(flt(row1.group_net_kg), 20.0)
        self.assertEqual(flt(row2.group_net_kg), 5.0)
        # F-8: taras come from the Item master, whatever was typed
        self.assertEqual(flt(row1.unit_tara_kg), 0.05)
        self.assertEqual(flt(row1.container_tara_kg), 2.7)   # CN025
        self.assertEqual(flt(row2.container_tara_kg), 1.7)   # CN010 — 10 kg pail

    def test_mixed_pail_sizes_in_one_order_allowed(self):
        so = self._so([20.0, 5.0])
        for p in self._vabon_plan(so):
            so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        self.assertEqual({r.container_item for r in so.custom_pack_plan},
                         {PAIL_25, PAIL_10})

    def test_unit_net_is_entered_not_seeded_from_tara(self):
        """weight_per_unit on packaging Items is the TARA — a row without an
        entered net must refuse, never silently become a 0.05 kg row."""
        so = self._so([20.0, 5.0])
        p = self._vabon_plan(so)[0]
        p.pop("unit_net_kg")
        so.append("custom_pack_plan", p)
        with self.assertRaises(frappe.ValidationError):
            so.save(ignore_permissions=True)

    # ---- catalog restriction --------------------------------------------- #
    def test_catalog_restriction_blocks_non_packaging_items(self):
        so = self._so([20.0, 5.0])
        p = self._vabon_plan(so)[0]
        p["package_item"] = ITEM  # the product itself — the classic human error
        so.append("custom_pack_plan", p)
        with self.assertRaises(frappe.ValidationError):
            so.save(ignore_permissions=True)

    # ---- per-SO-row sum validation (1b-FINAL) ----------------------------- #
    def test_per_row_sums_pass_both_rows(self):
        so = self._so([20.0, 5.0], plan=None)
        for p in self._vabon_plan(so):
            so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        so.run_method("before_submit")  # must not raise

    def test_per_row_sum_fails_on_the_off_row(self):
        so = self._so([20.0, 5.0])
        plan = self._vabon_plan(so)
        plan[1]["unit_net_kg"] = 0.9    # row 2 plan: 4.5 kg vs row qty 5 kg
        for p in plan:
            so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            so.run_method("before_submit")

    def test_plan_row_without_so_item_row_blocks_on_multirow_order(self):
        so = self._so([20.0, 5.0])
        plan = self._vabon_plan(so)
        plan[0]["so_item_row"] = ""
        for p in plan:
            so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            so.run_method("before_submit")

    def test_single_row_order_autofills_so_item_row(self):
        so = self._so([25.0])
        so.append("custom_pack_plan", {
            "package_item": BAG_5KG, "units_per_container": 5,
            "unit_net_kg": 5.0, "container_item": PAIL_25, "containers_qty": 1})
        so.save(ignore_permissions=True)
        self.assertEqual(so.custom_pack_plan[0].so_item_row, so.items[0].name)
        so.run_method("before_submit")  # 25 == 25

    # ---- Quotation -> SO copy mapping ------------------------------------- #
    def test_quotation_to_so_copy_carries_so_item_row_association(self):
        q = frappe.get_doc({
            "doctype": "Quotation",
            "quotation_to": "Customer",
            "party_name": self.customer,
            "transaction_date": frappe.utils.today(),
            "company": frappe.db.get_single_value("Global Defaults", "default_company"),
            "items": [{"item_code": ITEM, "qty": 20.0, "rate": 172.24},
                      {"item_code": ITEM, "qty": 5.0, "rate": 172.24}],
        })
        q.append("custom_pack_plan", {
            "so_item_row": "", "package_item": BAG_5KG, "units_per_container": 4,
            "unit_net_kg": 5.0, "container_item": PAIL_25, "containers_qty": 1})
        q.insert(ignore_permissions=True)
        q.custom_pack_plan[0].so_item_row = q.items[0].name
        q.append("custom_pack_plan", {
            "so_item_row": q.items[1].name, "package_item": BAG_1KG,
            "units_per_container": 5, "unit_net_kg": 1.0,
            "container_item": PAIL_10, "containers_qty": 1})
        q.save(ignore_permissions=True)

        # SO mapped from the quotation (rows carry quotation_item back-links)
        so = self._so([20.0, 5.0], insert=False)
        so.items[0].prevdoc_docname = q.name
        so.items[0].quotation_item = q.items[0].name
        so.items[1].prevdoc_docname = q.name
        so.items[1].quotation_item = q.items[1].name
        so.insert(ignore_permissions=True)

        self.assertEqual(len(so.custom_pack_plan), 2)
        self.assertEqual(so.custom_pack_plan[0].so_item_row, so.items[0].name)
        self.assertEqual(so.custom_pack_plan[1].so_item_row, so.items[1].name)
        so.run_method("before_submit")  # copied plan reconciles per row

    def test_copy_never_overwrites_existing_plan(self):
        so = self._so([25.0])
        so.append("custom_pack_plan", {
            "package_item": BAG_5KG, "units_per_container": 5,
            "unit_net_kg": 5.0, "container_item": PAIL_25, "containers_qty": 1})
        so.items[0].prevdoc_docname = "QTN-DOES-NOT-MATTER"
        so.save(ignore_permissions=True)
        self.assertEqual(len(so.custom_pack_plan), 1)

    # ---- single-slot data migration --------------------------------------- #
    def test_single_slot_migration_folds_legacy_fields_into_rows(self):
        from amb_w_tds.selling_edge.pack_plan import migrate_single_slot_data
        so = self._so([25.0])
        frappe.db.set_value("Sales Order", so.name, {
            "custom_tipo_empaque_copy": BAG_5KG,
            "custom_secondary_packaging_copy": PAIL_25,
            "custom_peso_neto": "5",
        }, update_modified=False)
        rep = migrate_single_slot_data(dry_run=1)
        self.assertGreaterEqual(rep["migrated"], 1)
        # dry-run wrote nothing
        so.reload()
        self.assertEqual(len(so.custom_pack_plan), 0)
        rep = migrate_single_slot_data(dry_run=0)
        so.reload()
        self.assertEqual(len(so.custom_pack_plan), 1)
        row = so.custom_pack_plan[0]
        self.assertEqual(row.package_item, BAG_5KG)
        self.assertEqual(row.container_item, PAIL_25)
        self.assertEqual(flt(row.unit_net_kg), 5.0)
        self.assertEqual(row.units_per_container, 5)   # 25 kg / 5 kg
        self.assertEqual(row.so_item_row, so.items[0].name)
