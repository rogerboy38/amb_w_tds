import frappe
from frappe.model.document import Document


class TDSProductSpecification(Document):
    """TDS Product Specification Doctype"""

    def before_submit(self):
        """T142-B: numeric-spec gate, runs when the TDS is approved (submitted).

        For every Item Quality Inspection Parameter row flagged ``numeric``:
          * skip rows whose acceptance text (``value``) is blank (lenient on draft),
          * derive (lo, hi) bounds from the acceptance text via coa_spec_utils,
          * if the text cannot be parsed, collect it and block the approval,
          * otherwise re-sync the stored ``min_value`` / ``max_value`` to match the
            spec text -- writing ONLY the defined bound so an unbounded side is not
            forced to 0.0 (the Float column is NOT NULL). This corrects baked ranges
            such as "20 -25%" that were previously mis-stored as 10/15.

        Defense-in-depth on top of the COA validator, which already treats the
        acceptance text as the source of truth.
        """
        from amb_w_tds.amb_w_tds.coa_spec_utils import derive_bounds_from_spec

        issues = []
        for idx, row in enumerate(
            self.get("item_quality_inspection_parameter") or [], start=1
        ):
            if not row.get("numeric"):
                continue
            spec_text = (row.get("value") or "").strip()
            if not spec_text:
                continue
            bounds = derive_bounds_from_spec(spec_text)
            if bounds is None:
                label = row.get("specification") or "parameter"
                issues.append(
                    "Row {0} ({1}): numeric acceptance '{2}' could not be parsed "
                    "into a range.".format(idx, label, spec_text)
                )
                continue
            lo, hi = bounds
            if lo is not None:
                row.min_value = lo
            if hi is not None:
                row.max_value = hi

        if issues:
            frappe.throw(
                "Cannot approve this TDS — fix the numeric acceptance "
                "specifications first:<br>" + "<br>".join(issues),
                title="Invalid numeric specification",
            )
