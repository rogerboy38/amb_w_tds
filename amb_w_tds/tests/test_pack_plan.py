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
            # Mexico-compliance mandatory fields (house bench trait): generic
            # export RFC + tax system, same values the migrated customers carry
            "tax_id": "XAXX010101000",
            "tax_system": "612",
        }).insert(ignore_permissions=True)
    return frappe.db.get_value("Customer", {"customer_name": SYNTH_CUSTOMER})


class TestPackPlan(unittest.TestCase):

    def setUp(self):
        # per-test (not setUpClass): each test ends in rollback, which would
        # erase a class-level customer for the tests after the first
        frappe.set_user("Administrator")
        self.customer = _ensure_customer()
        self._created = []

    def tearDown(self):
        """Rollback + leak-proof sweep: hook-level frappe.db.commit() (house
        controllers self-commit) can punch documents through the rollback.
        Any tracked doc that survived is deleted, then the test FAILS loudly —
        a leak is a real defect to surface, not residue to shrug at."""
        frappe.db.rollback()
        leaked = [(dt, name) for dt, name in self._created
                  if frappe.db.exists(dt, name)]
        for dt, name in leaked:
            doc = frappe.get_doc(dt, name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc(dt, name, force=1, ignore_permissions=True)
        if leaked:
            frappe.db.commit()
            self.fail(f"commit punched through rollback; leaked+cleaned: {leaked}")

    def _track(self, doc):
        self._created.append((doc.doctype, doc.name))
        return doc

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
            self._track(doc)
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

    # ---- F-AUD-1: coverage enforcement (warn now, block later) ------------- #
    def test_uncovered_row_warns_but_submits_in_warn_mode(self):
        so = self._so([20.0, 5.0])
        p = self._vabon_plan(so)[0]        # plan only for row 1
        so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        so.run_method("before_submit")     # warn mode (default): must not raise

    def test_uncovered_row_blocks_in_block_mode(self):
        from unittest.mock import patch as mpatch
        so = self._so([20.0, 5.0])
        p = self._vabon_plan(so)[0]
        so.append("custom_pack_plan", p)
        so.save(ignore_permissions=True)
        with mpatch("amb_w_tds.selling_edge.pack_plan.enforcement_mode",
                    return_value="block"):
            with self.assertRaises(frappe.ValidationError):
                so.run_method("before_submit")

    # ---- F-AUD-2: auto-remap after cancel -> amend -------------------------- #
    def test_amend_remaps_so_item_row_by_idx_and_item_code(self):
        so1 = self._so([20.0, 5.0])
        for p in self._vabon_plan(so1):
            so1.append("custom_pack_plan", p)
        so1.save(ignore_permissions=True)
        old_r1, old_r2 = so1.items[0].name, so1.items[1].name
        so1.submit()
        so1.cancel()   # amended_from must reference a cancelled doc

        so2 = self._so([20.0, 5.0], insert=False)
        so2.amended_from = so1.name
        for p in self._vabon_plan(so1):     # plan rows still carry OLD names
            so2.append("custom_pack_plan", dict(p, so_item_row=(
                old_r1 if p["so_item_row"] == so1.items[0].name else old_r2)))
        self._track(so2.insert(ignore_permissions=True) or so2)
        self.assertEqual(so2.custom_pack_plan[0].so_item_row, so2.items[0].name)
        self.assertEqual(so2.custom_pack_plan[1].so_item_row, so2.items[1].name)
        so2.run_method("before_submit")     # remapped plan reconciles per row

    def test_amend_never_guesses_unresolvable_rows(self):
        so1 = self._so([20.0, 5.0])
        so1.submit()
        so1.cancel()   # amended_from must reference a cancelled doc
        so2 = self._so([20.0, 5.0], insert=False)
        so2.amended_from = so1.name
        p = self._vabon_plan(so2)[0]
        p["so_item_row"] = "row-name-that-never-existed"
        so2.append("custom_pack_plan", p)
        self._track(so2.insert(ignore_permissions=True) or so2)  # saves with a WARNING, no guess
        self.assertEqual(so2.custom_pack_plan[0].so_item_row,
                         "row-name-that-never-existed")
        with self.assertRaises(frappe.ValidationError):
            so2.run_method("before_submit")  # hard gate stays at submit

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
        self._track(q.insert(ignore_permissions=True) or q)
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
        self._track(so.insert(ignore_permissions=True) or so)

        # F-AUD-3: NO silent auto-pull on insert…
        self.assertEqual(len(so.custom_pack_plan), 0)
        # …the EXPLICIT fetch action does the copy
        from amb_w_tds.selling_edge.pack_plan import fetch_pack_plan_from_quotation
        result = fetch_pack_plan_from_quotation(so.name)
        self.assertEqual(result["fetched"], 2)
        so.reload()
        self.assertEqual(len(so.custom_pack_plan), 2)
        self.assertEqual(so.custom_pack_plan[0].so_item_row, so.items[0].name)
        self.assertEqual(so.custom_pack_plan[1].so_item_row, so.items[1].name)
        so.run_method("before_submit")  # copied plan reconciles per row

    def test_copy_never_overwrites_existing_plan(self):
        q = frappe.get_doc({
            "doctype": "Quotation",
            "quotation_to": "Customer",
            "party_name": self.customer,
            "transaction_date": frappe.utils.today(),
            "company": frappe.db.get_single_value("Global Defaults", "default_company"),
            "items": [{"item_code": ITEM, "qty": 25.0, "rate": 172.24}],
        })
        q.append("custom_pack_plan", {
            "package_item": BAG_1KG, "units_per_container": 25,
            "unit_net_kg": 1.0, "container_item": PAIL_10, "containers_qty": 1})
        self._track(q.insert(ignore_permissions=True) or q)

        so = self._so([25.0], insert=False)
        so.append("custom_pack_plan", {
            "package_item": BAG_5KG, "units_per_container": 5,
            "unit_net_kg": 5.0, "container_item": PAIL_25, "containers_qty": 1})
        so.items[0].prevdoc_docname = q.name
        so.items[0].quotation_item = q.items[0].name
        self._track(so.insert(ignore_permissions=True) or so)
        # the SO's own plan stands — nothing was pulled in on insert…
        self.assertEqual(len(so.custom_pack_plan), 1)
        self.assertEqual(so.custom_pack_plan[0].package_item, BAG_5KG)
        # …and the explicit fetch REFUSES to overwrite an existing plan
        from amb_w_tds.selling_edge.pack_plan import fetch_pack_plan_from_quotation
        with self.assertRaises(frappe.ValidationError):
            fetch_pack_plan_from_quotation(so.name)

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
