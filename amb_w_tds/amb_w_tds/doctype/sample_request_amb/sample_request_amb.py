import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SampleRequestAMB(Document):
    
    #: D-CCY: the ruled born-currency for a Sample Request.
    DEFAULT_CURRENCY = "USD"

    def before_insert(self):
        self._apply_default_currency()

    def _apply_default_currency(self):
        """D-CCY — make "born USD" TRUE, because the JSON default cannot be.

        ⛔ THE JSON DEFAULT IS PRESENT AND UNREACHABLE ON THIS SITE. The field
        carries `"default": "USD"` and has since 2026-04-30, yet a new document
        is born **MXN**. Mechanism, read at frappe/model/create_new.py:

            :88   user_default = defaults.get(df.fieldname)   # keyed on "currency"
            :95   if user_default ...: return user_default    # ⛔ returns here
            :115  return df.default                          # never reached

        Global Defaults sets `default_currency = MXN`, which surfaces in
        `frappe.defaults` under the key **"currency"** -- the same string as this
        field's name -- so a site-wide default wins over the field's own default
        purely because the names collide. I previously reported the JSON key as
        "already correct, a no-op"; it is present but INERT, and reporting the
        key instead of the behaviour is what let that stand.

        ⚠ WHY THIS COMPARES AGAINST THE SITE DEFAULT rather than just forcing
        USD: the ruling keeps the field editable for a genuine non-USD export.
        Overwriting unconditionally would discard a deliberate EUR/CAD choice
        made before the first save. Overwriting ONLY the value that the site
        handed us -- the one nobody chose -- honours both halves: the unchosen
        MXN becomes USD, an explicit non-USD choice survives.

        ⛔ NOT a fix for the four existing MXN documents. Those are a ruled,
        enumerated, gated prod write at Node C; this only stops new ones.
        """
        site_default = frappe.defaults.get_defaults().get("currency")
        current = (self.currency or "").strip()

        if not current:
            self.currency = self.DEFAULT_CURRENCY
        elif site_default and current == site_default and current != self.DEFAULT_CURRENCY:
            # the value came from the site, not from a person
            self.currency = self.DEFAULT_CURRENCY

    def before_save(self):
        self.set_customer_name()
        self.update_totals()
        self._assign_control_numbers()
        self._warn_if_no_bags()

    def _warn_if_no_bags(self):
        """BUG208 — warn when the shipment declares a value but counts NO bags.

        Under the ruled contract (V-1) the declared total is the stored
        `commercial_value_usd` scalar, and the per-bag unit is DERIVED as
        total / sum(samples_count). With zero bags there is no divisor, so the
        document prints its total with NO per-bag breakdown at all.

        That is handled safely -- `unit_for()` returns None rather than dividing,
        and the money cells render blank rather than a fabricated $0.00 -- but it
        is handled SILENTLY, and a customs document that declares a value while
        showing no quantity is worth a human glance before it is filed. Two live
        documents are in exactly this state.

        ⚠ A WARNING, NOT A BLOCK. A nominal shipment may legitimately carry no
        counted bags, and throwing here would refuse saves that are correct
        today -- including the existing zero-row documents, which would become
        un-editable. `msgprint` says it out loud and lets the operator decide.
        """
        from amb_w_tds.valuation import total_bags

        if not self.get("samples"):
            bags = 0
        else:
            bags = total_bags(self.get("samples"))

        if bags:
            return

        frappe.msgprint(
            _(
                "No samples counted on this request: the declared value "
                "({0}) will print with no per-unit breakdown. Set "
                "'Number of Samples' on the sample rows if this shipment "
                "carries bags."
            ).format(self.get("commercial_value_usd")),
            title=_("No sample count"),
            indicator="orange",
            alert=True,
        )

    def _assign_control_numbers(self):
        """SR-1 (b): one labelled sample unit = one AMB CONTROL NUMBER, a global
        consecutive serial (FoxPro proto_mues.CONTROL precedent). Assign per samples
        row, fill-forward only -- never reassign an existing number."""
        from frappe.model.naming import make_autoname
        for row in (self.samples or []):
            if not row.get("control_number"):
                row.control_number = make_autoname("AMB-.#####")
    
    def set_customer_name(self):
        if self.customer and not self.customer_name:
            self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name")

    def update_totals(self):
        for row in self.get("samples") or []:
            if row.samples_count and row.qty_per_sample:
                row.total_qty = row.samples_count * row.qty_per_sample
            else:
                row.total_qty = 0
        self._roll_up_shipment_weights()

    def _roll_up_shipment_weights(self):
        """BUG208 D-WEIGHT -- the declared gross is a SERVER rollup of the rows.

        Runs from `before_save`, so it fires on every save: form, API, script or
        import. The previous rollup lived only in `sample_request_amb.js`
        (`amb_wt_rollup`), which fires on form interaction, so
        `computed_gross_kg` was 0/NULL on 14 of 16 live documents while the
        memos printed the MANUAL `gross_weight_kg` instead -- 500 GR declared
        for a 160 GR shipment on one, and on SR-2026-00026 the net typed into
        the gross field (160 GR declared against a true 492 GR).

        ⛔ NEVER DECLARES ZERO FROM AN EMPTY ROLLUP. If the rows carry no
        weights the operator's own figures are left exactly as entered. Writing
        a 0 here would trade an over-declaration for a zero-weight customs
        document, which is worse than the bug -- the failure mode that retired
        the first draft of this criterion.
        """
        rows = self.get("samples") or []
        net = sum(flt(r.get("row_net_weight")) for r in rows)
        tara = sum(flt(r.get("row_tara_weight")) for r in rows)
        gross = sum(flt(r.get("row_gross_weight")) for r in rows)

        if gross > 0:
            self.computed_gross_kg = gross
            # The DECLARED field is what the memos print, so the rollup has to
            # reach it -- computing a correct number into a field nobody prints
            # is the defect this replaces, one layer over.
            self.gross_weight_kg = gross
        if net > 0:
            self.shipment_net_weight = net
        if tara > 0:
            self.shipment_tara_weight = tara

    def validate(self):
        self.validate_batch_consistency()
        self.validate_shipment_values()
        self.validate_shipment_weights()
        self._fill_sample_item_names()
        self._fill_sample_uom()


    def _fill_sample_uom(self):
        """BUG208 D-UOM: a blank row unit is filled from the Item's stock UOM.

        The print formats fell back to a literal "g" when `uom` was empty --
        NULL on 6 of 11 live child rows whose Item is stocked in Kg, so a 1 Kg
        line declared "1.000 g" to customs: a 1000x MASS UNDER-DECLARATION.
        Fixing it here corrects every format at once and, unlike a template
        fallback, leaves the real unit in the data. Only blanks are filled."""
        for row in (self.samples or []):
            if row.item and not (row.get("uom") or "").strip():
                stock_uom = frappe.db.get_value("Item", row.item, "stock_uom")
                if stock_uom:
                    row.uom = stock_uom
    
    def _fill_sample_item_names(self):
        """Backfill each sample row's description from the linked Item.
        Prefers item_name (always populated) over description (empty on some
        prod items). Only fills blanks -- never overwrites. Covers interactive
        and programmatic rows."""
        for row in (self.samples or []):
            if row.item and not (row.description or "").strip():
                name = (frappe.db.get_value("Item", row.item, "item_name")
                        or frappe.db.get_value("Item", row.item, "description"))
                if name:
                    row.description = name

    def validate_batch_consistency(self):
        """Validate that batch data is consistent with fetched values"""
        if self.batch_reference:
            batch = frappe.get_doc("Batch AMB", self.batch_reference)
            
            # Check COA consistency (warning only, not blocking)
            if batch.coa_amb and self.coa_amb and batch.coa_amb != self.coa_amb:
                frappe.msgprint(
                    _("Warning: COA AMB ({0}) differs from Batch ({1})").format(
                        self.coa_amb, batch.coa_amb
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # Check item consistency (warning only, not blocking)
            if batch.item_to_manufacture and self.item and batch.item_to_manufacture != self.item:
                frappe.msgprint(
                    _("Warning: Item ({0}) differs from Batch item ({1})").format(
                        self.item, batch.item_to_manufacture
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # Check Sales Order consistency
            if batch.sales_order_related and self.sales_order_related and batch.sales_order_related != self.sales_order_related:
                frappe.msgprint(
                    _("Warning: Sales Order ({0}) differs from Batch Sales Order ({1})").format(
                        self.sales_order_related, batch.sales_order_related
                    ),
                    alert=True,
                    indicator="orange"
                )
            
            # Auto-set Sales Order if empty
            if batch.sales_order_related and not self.sales_order_related:
                self.sales_order_related = batch.sales_order_related
                frappe.msgprint(
                    _("Sales Order auto-set to: {0}").format(batch.sales_order_related),
                    alert=True,
                    indicator="green"
                )
    
    def validate_shipment_values(self):
        """Validate shipment values for Proforma.

        ⭐ BUG208 T-BUG208-6 -- THE ZERO FIX IS HERE, NOT IN JINJA. The test was
        `if not self.commercial_value_usd`, which is TRUE for a deliberate 0, so
        a Logistics user declaring nothing had it silently rewritten to 1.00 AT
        SAVE, before any template ran. Measured in memory: 0 -> 1.0, None -> 1.0,
        0.50 -> 0.50 (the control). The Jinja `or "1.00"` everyone reached for
        first is DEAD CODE for this field -- it never sees a falsy value,
        because this ran earlier.

        ⭐ Under the ruled model (V-1) this field IS the declared total -- the
        total is pinned to this scalar and does not scale with bags or rows. So
        a silent 0 -> 1.00 is not a rounding nicety: it is the difference
        between declaring nothing and declaring a dollar, on the document that
        goes to customs. `is None` preserves a deliberate zero; a genuinely
        MISSING value still takes the nominal default.
        """
        if self.commercial_value_usd is None:
            self.commercial_value_usd = 1.00

        # Ensure number of packages has a default
        if not self.number_of_packages:
            self.number_of_packages = 1

        # ⛔ The `gross_weight_kg = 0.5` literal that used to live here is GONE.
        # It fabricated a weight on a customs declaration: on SR-2026-00015 it
        # printed 500 GR for a 160 GR shipment. The declared gross now comes
        # from `_roll_up_shipment_weights()`, and when the rows cannot supply
        # one, nothing is invented -- the operator's figure stands.

    def validate_shipment_weights(self):
        """Reject customs weights that print a negative tara (net must not exceed gross)."""
        net = flt(self.shipment_net_weight)
        gross = flt(self.gross_weight_kg)
        if net > 0 and gross > 0 and (net - gross) > 1e-6:
            frappe.throw(_(
                "Shipment Net Weight ({0} Kg) cannot exceed Gross Weight ({1} Kg) - "
                "this prints a negative Tara on the Proforma. Raise Gross Weight to at "
                "least the rolled-up net, or correct the box/bag weights on the rows."
            ).format(net, gross))
    
    def validate_coa_from_batch(self):
        """Ensure COA AMB matches the batch reference (blocking validation)"""
        if self.batch_reference and self.coa_amb:
            batch_coa = frappe.db.get_value("Batch AMB", self.batch_reference, "coa_amb")
            if batch_coa and batch_coa != self.coa_amb:
                frappe.throw(
                    _("COA AMB ({0}) does not match Batch Reference COA ({1})").format(
                        self.coa_amb, batch_coa
                    )
                )
    
    def get_shipment_purpose(self):
        """Get the shipment purpose text for proforma"""
        if self.shipment_nature:
            return self.shipment_nature
        elif self.internal_export_type:
            return self.internal_export_type
        elif self.special_export_type:
            return self.special_export_type
        return "Muestra sin valor comercial"
    
    def get_waybill_display(self):
        """Get waybill number or placeholder"""
        return self.waybill_number or "12 629 A50 04 9499 3785"
