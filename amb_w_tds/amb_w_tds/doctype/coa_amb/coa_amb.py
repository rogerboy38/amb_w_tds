# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, flt, get_url, cstr
import json
import re

class COAAMB(Document):
    """
    COA AMB - Certificate of Analysis with enhanced validation and workflow
    """
    def _is_submit_flow(self):
        """Check if we're in submit flow vs normal edit"""
        return getattr(self, '_action', None) == 'submit'

    def validate(self):
        """Comprehensive validation logic - SKIPS heavy checks for draft"""
        
        # CRITICAL: For draft documents being edited, skip heavy validation to prevent timeout
        # Only run full validation on submit
        if self.docstatus == 0 and not self._is_submit_flow():
            # Lightweight validation for draft editing (saves in <1 second)
            self.validate_linked_tds()
            self.validate_batch_reference()
            self.check_mandatory_tds_link()
            return
        
        # FULL VALIDATION (only on submit)
        # Core validation sequence
        self.validate_linked_tds()
        self.validate_batch_reference()
        
        # Enhanced test parameter validation
        self.validate_test_parameters()
        self.evaluate_overall_result()
        
        # Additional validations
        self.check_mandatory_tds_link()
        self.validate_signature_on_submit()
        
        # Formula evaluation for parameters
        self.evaluate_formula_parameters()

    def before_insert(self):
        """Before insert — sync from TDS.

        Task #46 v3 (2026-05-27): the previous gate `not self.coa_quality_test_parameter`
        let sync_from_tds() be skipped whenever the form-script JS had already pre-populated
        the basic-param table on linked_tds change. That skip meant the preservative branch
        inside sync_from_tds() never ran, so `preservative_system` / `coa_preservatives` stayed
        empty on every COA created through the UI (basic params worked because JS handled them;
        preservatives broke because only this Python path handled them).

        Fix: always run sync_from_tds() when linked_tds is set. The basic-param block inside
        it is dead anyway (`hasattr(tds, 'specifications')` resolves but `tds.specifications`
        is None — the real field is `tds.item_quality_inspection_parameter`), so removing
        the gate doesn't double-add basic rows. The item-details and preservative blocks
        are idempotent (`self.set('coa_preservatives', [])` clears before re-append).
        """
        if self.linked_tds:
            self.sync_from_tds()
        self.set_default_naming_series()

    def before_save(self):
        """Before save hook"""
        self.set_coa_number()
        self.set_approval_info()
        #self.calculate_child_table_status()
        # to be reviewed freezed on save COA AMB document

    def on_submit(self):
        """On submit actions"""
        self.validate_submission_prerequisites()
        self.generate_coa_pdf()
        self.update_batch_status()
        self.notify_quality_team()
        self.create_quality_audit()
        self.update_product_quality_status()

    def on_cancel(self):
        """On cancel actions"""
        self.update_batch_status('COA Cancelled')
        self.revert_product_quality_status()
        frappe.msgprint(_("COA has been cancelled and batch status updated."), alert=True)

    def on_update_after_submit(self):
        """Actions after amending a submitted document"""
        if self.amended_from:
            self.add_comment('Info', f'Amended from {self.amended_from}')

    # ==================== ENHANCED VALIDATION METHODS ====================

    def validate_linked_tds(self):
        """Ensure linked TDS exists and is approved"""
        if self.linked_tds:
            if not frappe.db.exists('TDS Product Specification', self.linked_tds):
                frappe.throw(_("TDS {0} does not exist").format(self.linked_tds))

            tds = frappe.get_doc('TDS Product Specification', self.linked_tds)
            if tds.docstatus != 1:
                frappe.throw(_("TDS {0} is not approved").format(self.linked_tds))
                
            # Additional check for TDS version compatibility
            self.check_tds_version_compatibility(tds)

    def check_tds_version_compatibility(self, tds):
        """Check if TDS version is compatible with COA requirements"""
        if hasattr(tds, 'tds_version') and tds.tds_version:
            # Add version compatibility logic here if needed
            pass

    def validate_batch_reference(self):
        """Validate batch exists and is not closed"""
        if self.batch_reference:
            if not frappe.db.exists('Batch AMB', self.batch_reference):
                frappe.throw(_("Batch {0} does not exist").format(self.batch_reference))
            
            # Check if batch is already closed
            batch = frappe.get_doc('Batch AMB', self.batch_reference)
            if hasattr(batch, 'status') and batch.status == 'Closed':
                frappe.throw(_("Batch {0} is already closed and cannot be used for COA").format(self.batch_reference))

    def validate_test_parameters(self):
        """Comprehensive validation - SKIPS EMPTY ROWS AND TITLE ROWS"""
        if not self.coa_quality_test_parameter and self.docstatus == 1:
            frappe.throw(_("At least one quality test parameter is required for submission"))
    
        for idx, row in enumerate(self.coa_quality_test_parameter, 1):
            # SKIP TITLE ROWS (BUG 117B)
            if self._is_header_row(row):
                continue
            
            # SKIP EMPTY ROWS (BUG 117A) - allow partial saves
            if not row.parameter_name and not row.specification and not row.result:
                continue
                
            # Validate numeric fields
            if row.numeric and row.result:
                self.validate_numeric_result(row, idx)
    
            # Validate formula-based criteria
            if row.formula_based_criteria and row.acceptance_formula:
                self.validate_formula_criteria(row, idx)
    
            # Validate min/max consistency
            if row.get('min_value') is not None and row.get('max_value') is not None:
                if flt(row.min_value) > flt(row.max_value):
                    frappe.throw(_(f"Row {idx}: Minimum value ({row.min_value}) cannot be greater than maximum value ({row.max_value})"))
    
            # Validate mandatory fields for submitted documents
            if self.docstatus == 1 and not row.result:
                param_name = row.parameter_name or row.specification or f"Row {idx}"
                frappe.throw(_(f"Row {idx}: Result is required for parameter '{param_name}'"))


    def validate_numeric_result(self, row, idx):
        """Validate numeric results against the spec (T142: spec text = source of truth)."""
        from amb_w_tds.amb_w_tds.coa_spec_utils import derive_bounds_from_spec, parse_result_value
        result = parse_result_value(row.result)
        if result is None:
            return
        bounds = derive_bounds_from_spec(row.specification)
        if bounds is None:
            lo = flt(row.min_value) if row.get('min_value') else None
            hi = flt(row.max_value) if row.get('max_value') else None
        else:
            lo, hi = bounds
        if lo is not None and result < lo:
            frappe.throw(_(f"Row {idx}: Result {result} is below minimum {lo} for parameter '{row.parameter_name}'"))
        if hi is not None and result > hi:
            frappe.throw(_(f"Row {idx}: Result {result} is above maximum {hi} for parameter '{row.parameter_name}'"))

    def validate_formula_criteria(self, row, idx):
        """Validate formula-based criteria with security measures"""
        if not row.result:
            return
            
        allowed_namespaces = {
            'result': flt(row.result) if row.result else 0,
            'min_value': flt(row.min_value) if row.get('min_value') else None,
            'max_value': flt(row.max_value) if row.get('max_value') else None
        }
        
        try:
            # Use Frappe's safe eval for security
            formula_result = frappe.safe_eval(row.acceptance_formula, allowed_namespaces)
            if not formula_result:
                frappe.throw(_(f"Row {idx}: Formula validation failed for parameter '{row.parameter_name}'"))
        except Exception as e:
            frappe.throw(_(f"Row {idx}: Formula error for parameter '{row.parameter_name}': {str(e)}"))

    def check_mandatory_tds_link(self):
        """Ensure TDS is linked for product-based COAs"""
        if not self.linked_tds and self.product_item and self.docstatus == 0:
            frappe.msgprint(_("Linking a TDS Product Specification is recommended for proper specification mapping"), alert=True)

    def validate_signature_on_submit(self):
        """Validate signature before submission"""
        if self.docstatus == 1 and not self.autorizacion:
            frappe.throw(_("Authorization signature is required before submission"))

    def validate_submission_prerequisites(self):
        """Validate all prerequisites before submission"""
        if not self.coa_quality_test_parameter:
            frappe.throw(_("Cannot submit COA without test parameters"))
        
        if not self.overall_result or self.overall_result == 'Pending':
            frappe.throw(_("Cannot submit COA with pending overall result"))

    # ==================== RESULT EVALUATION METHODS ====================

    def _is_header_row(self, param):
        """Header = explicit flag OR the 'Specification' placeholder acceptance
        (untagged TDS section dividers). Never scored as a test."""
        if param.custom_is_title_row:
            return True
        acc = (param.value or param.specification or "")
        return str(acc).strip().lower() == "specification"

    def evaluate_overall_result(self):
        """Enhanced overall test result evaluation with detailed tracking"""
        if not self.coa_quality_test_parameter:
            self.overall_result = 'No Tests'
            return

        failed_tests = []
        passed_tests = []
        pending_tests = []
        
        total_tests = 0
        tested_tests = 0

        for param in self.coa_quality_test_parameter:
            if self._is_header_row(param):
                param.status = 'Title'
                continue

            total_tests += 1
            
            if not param.result:
                pending_tests.append(param.parameter_name)
                continue
                
            tested_tests += 1
            
            # Check parameter compliance
            is_compliant = self.check_parameter_compliance(param)
            
            if is_compliant:
                passed_tests.append(param.parameter_name)
                param.status = 'Pass'
            else:
                failed_tests.append(param.parameter_name)
                param.status = 'Fail'

        # Calculate percentages
        if total_tests > 0:
            self.pass_percentage = (len(passed_tests) / total_tests) * 100 if tested_tests > 0 else 0
            self.tested_percentage = (tested_tests / total_tests) * 100
        
        # Determine overall result
        if failed_tests:
            self.overall_result = 'Fail'
            self.failed_parameters = ', '.join(failed_tests)
            self.compliance_status = 'Non-Compliant'
        elif pending_tests and not failed_tests and passed_tests:
            self.overall_result = 'Partial'
            self.compliance_status = 'Under Review'
        elif passed_tests and not pending_tests:
            self.overall_result = 'Pass'
            self.compliance_status = 'Compliant'
        else:
            self.overall_result = 'Pending'
            self.compliance_status = 'Pending'

    def check_parameter_compliance(self, param):
        """Compliance via coa_spec_utils -- spec text is source of truth (T142)."""
        if not param.result:
            return False
        try:
            if param.get('formula_based_criteria') and param.get('acceptance_formula'):
                return frappe.safe_eval(param.acceptance_formula, {'result': flt(param.result)})
            from amb_w_tds.amb_w_tds.coa_spec_utils import is_compliant
            _mn = param.get('min_value'); _mx = param.get('max_value')
            _mn = flt(_mn) if _mn else None
            _mx = flt(_mx) if _mx else None
            return is_compliant(param.specification, param.result, _mn, _mx)
        except Exception as e:
            frappe.log_error(f"Error checking compliance for parameter {param.parameter_name}: {str(e)}", "COA Compliance Check")
            return False

    def parse_specification_compliance(self, spec, result):
        """Delegate to coa_spec_utils (T142)."""
        from amb_w_tds.amb_w_tds.coa_spec_utils import is_compliant
        return is_compliant(spec, result)

    def evaluate_formula_parameters(self):
        """Evaluate all formula-based parameters"""
        for param in self.coa_quality_test_parameter:
            if param.formula_based_criteria and param.acceptance_formula and param.result:
                self.validate_formula_criteria_for_row(param)

    def validate_formula_criteria_for_row(self, param):
        """Validate formula for a specific row"""
        try:
            allowed_namespaces = {
                'result': flt(param.result) if param.result else 0,
                'min_value': flt(param.min_value) if param.get('min_value') else None,
                'max_value': flt(param.max_value) if param.get('max_value') else None
            }
            
            formula_result = frappe.safe_eval(param.acceptance_formula, allowed_namespaces)
            if formula_result:
                param.status = 'Pass'
            else:
                param.status = 'Fail'
        except Exception as e:
            frappe.log_error(f"Formula evaluation error for {param.parameter_name}: {str(e)}", "COA Formula Eval")

    # ==================== SYNC & SETUP METHODS ====================

    def sync_from_tds(self):
        """Enhanced sync from linked TDS with better error handling"""
        if not self.linked_tds:
            return

        try:
            tds = frappe.get_doc('TDS Product Specification', self.linked_tds)

            # Copy item details
            self.product_item = tds.product_item
            self.item_name = tds.item_name
            self.item_code = tds.item_code
            
            # Copy additional TDS information
            if hasattr(tds, 'cas_number'):
                self.cas_number = tds.cas_number
            if hasattr(tds, 'inci_name'):
                self.inci_name = tds.inci_name
            if hasattr(tds, 'shelf_life'):
                self.shelf_life = tds.shelf_life
            if hasattr(tds, 'packaging'):
                self.packaging = tds.packaging
            if hasattr(tds, 'storage_and_handling_conditions'):
                self.storage_and_handling_conditions = tds.storage_and_handling_conditions

            # Copy specifications to quality parameters.
            #
            # Note (2026-05-27): this branch is currently DEAD CODE — `tds.specifications`
            # isn't the real TDS child-table fieldname (the real one is
            # `tds.item_quality_inspection_parameter`), so `hasattr(...) and …`
            # evaluates False and the loop never runs. The browser clone path
            # (coa_amb.js → `copy_tds_specifications`) is what populates the table
            # at runtime. Field copies are extended here in parity with the JS path
            # so that if/when the gate is fixed in a future task, the Python path
            # carries the same field set.
            #
            # Task #60 additions (2026-05-28): `custom_method` (Link → Quality Inspection
            # Method) — the source side has this; pre-fix `test_method` was empty post-
            # clone because it was being copied from a non-existent `spec.test_method`.
            # Also propagate `custom_reconstituted_to_05_total_solids_solution`.
            if hasattr(tds, 'specifications') and tds.specifications:
                for spec in tds.specifications:
                    self.append('coa_quality_test_parameter', {
                        'parameter_name': spec.parameter,
                        'specification': spec.specification,
                        'test_method': spec.get('custom_method') or spec.get('test_method'),
                        'custom_method': spec.get('custom_method'),
                        'result': '',
                        'min_value': spec.get('min_value'),
                        'max_value': spec.get('max_value'),
                        'custom_uom': spec.get('custom_uom'),
                        'custom_reconstituted_to_05_total_solids_solution':
                            spec.get('custom_reconstituted_to_05_total_solids_solution') or 0,
                    })

            # Task #46 (2026-05-27) — Clone preservative system + composition from TDS.
            # Mirrors the analysis-table clone above. Read-only on COA side; refresh per
            # COA generation (overwrites any stale prior state).
            #
            # Task #59 follow-up (2026-05-28) — `has_field` guard makes this branch
            # polymorphic across COA AMB (where preservative_system + coa_preservatives
            # are v1 Custom Fields) and clones like COA AMB2 (where those fields are
            # deliberately excluded). On a doctype without the fields, skip cleanly
            # rather than crash with "Field preservative_system not found." which is
            # what Hugh hit creating COA2-26-0002 on 2026-05-28.
            if (self.meta.has_field('preservative_system')
                    and self.meta.has_field('coa_preservatives')):
                self.preservative_system = tds.get('preservative_system')
                self.set('coa_preservatives', [])
                tds_pres = tds.get('tds_preservatives') or []
                for row in tds_pres:
                    self.append('coa_preservatives', {
                        'compound': row.compound,
                        'percentage': row.percentage,
                        'compound_item': row.get('compound_item'),
                        'e_number': row.get('e_number'),
                        'is_override': row.get('is_override') or 0,
                    })

            frappe.msgprint(_("Successfully synced specifications from TDS: {0}").format(self.linked_tds), alert=True)
            
        except Exception as e:
            frappe.log_error(f"Error syncing from TDS {self.linked_tds}: {str(e)}", "COA TDS Sync")
            frappe.throw(_("Error syncing from TDS: {0}").format(str(e)))

    def set_coa_number(self):
        """Set COA number based on naming series"""
        if not self.coa_number and not self.amended_from:
            if self.naming_series:
                # Let Frappe handle the naming based on series
                from frappe.model.naming import make_autoname
                # COA number mirrors the document name (series already applied to name).
                # Off-by-one fix: avoid a second make_autoname() that burned the counter.
                self.coa_number = self.name
            else:
                # Fallback to custom format
                from datetime import datetime
                date_str = datetime.now().strftime('%Y-%m')
                
                last_coa = frappe.db.sql("""
                    SELECT coa_number 
                    FROM `tabCOA AMB` 
                    WHERE coa_number LIKE %s 
                    ORDER BY creation DESC 
                    LIMIT 1
                """, (f"COA-{date_str}-%",))
                
                if last_coa and last_coa[0][0]:
                    last_num = int(last_coa[0][0].split('-')[-1])
                    seq = last_num + 1
                else:
                    seq = 1
                
                self.coa_number = f"COA-{date_str}-{seq:04d}"

    def set_default_naming_series(self):
        """Set default naming series if not set"""
        if not self.naming_series:
            self.naming_series = "COA-.YY.-.####"

    def set_approval_info(self):
        """Set approval information"""
        if self.docstatus == 1 and not self.approval_date:
            self.approval_date = nowdate()
            if not self.approved_by:
                self.approved_by = frappe.session.user

    # ==================== DOCUMENT ACTION METHODS ====================

    def generate_coa_pdf(self):
        """Generate PDF certificate with error handling"""
        try:
            # This would use Frappe's print format system
            # Log the PDF generation request
            self.add_comment('Info', 'COA PDF generation requested on submission')
            
            # In a real implementation, you might trigger an async PDF generation
            # frappe.enqueue('amb_w_tds.amb_w_tds.doctype.coa_amb.coa_amb.generate_coa_pdf_background', 
            #               coa_name=self.name)
            
        except Exception as e:
            frappe.log_error(f"Error generating COA PDF: {str(e)}", "COA AMB - PDF Generation")
            frappe.msgprint(_("PDF generation encountered an error. The COA was still submitted."), alert=True)

    def update_batch_status(self, status=None):
        """Update related batch with COA info"""
        if not self.batch_reference:
            return

        try:
            batch = frappe.get_doc('Batch AMB', self.batch_reference)
            
            if status:
                batch.quality_status = status
                batch.add_comment('Info', f'COA Status: {status} - {self.name}')
            else:
                batch.coa_generated = 1
                batch.coa_reference = self.name
                batch.quality_status = self.overall_result
                batch.last_coa_date = nowdate()
                
                # Add COA details to batch
                if hasattr(batch, 'coa_details'):
                    batch.coa_details = f"""
                        COA: {self.name}
                        Result: {self.overall_result}
                        Approved: {self.approval_date}
                        Approved By: {self.approved_by}
                    """
            
            batch.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error updating batch {self.batch_reference}: {str(e)}", "COA AMB - Batch Update")

    def notify_quality_team(self):
        """Send notifications to relevant teams"""
        recipients = set()
        
        # Get quality team members
        quality_roles = ['Quality Manager', 'Quality Inspector', 'Quality Analyst']
        for role in quality_roles:
            users = frappe.get_all('Has Role', 
                filters={'role': role, 'parenttype': 'User'},
                fields=['parent']
            )
            for user in users:
                email = frappe.db.get_value('User', user.parent, 'email')
                if email:
                    recipients.add(email)
        
        # Add document owner and approver
        if self.owner:
            owner_email = frappe.db.get_value('User', self.owner, 'email')
            if owner_email:
                recipients.add(owner_email)
        
        if self.approved_by:
            recipients.add(self.approved_by)
        
        # Add production manager if batch exists
        if self.batch_reference:
            batch = frappe.get_doc('Batch AMB', self.batch_reference)
            if hasattr(batch, 'production_manager') and batch.production_manager:
                recipients.add(batch.production_manager)
        
        if recipients:
            try:
                frappe.sendmail(
                    recipients=list(recipients),
                    subject=f'COA {self.name} - {self.overall_result}',
                    message=f"""
                        <h3>Certificate of Analysis Notification</h3>
                        <p>A new COA has been issued with the following details:</p>
                        <table border="0" cellspacing="0" cellpadding="5" style="border-collapse: collapse;">
                            <tr><td><strong>COA Number:</strong></td><td>{self.coa_number or self.name}</td></tr>
                            <tr><td><strong>Product:</strong></td><td>{self.item_name} ({self.item_code})</td></tr>
                            <tr><td><strong>Batch:</strong></td><td>{self.batch_reference or 'N/A'}</td></tr>
                            <tr><td><strong>Overall Result:</strong></td><td><strong>{self.overall_result}</strong></td></tr>
                            <tr><td><strong>Compliance Status:</strong></td><td>{self.compliance_status}</td></tr>
                            <tr><td><strong>Approval Date:</strong></td><td>{self.approval_date}</td></tr>
                            <tr><td><strong>Approved By:</strong></td><td>{self.approved_by}</td></tr>
                        </table>
                        <br>
                        <p><a href="{get_url()}/app/coa-amb/{self.name}">View Complete COA</a></p>
                        <p><em>This is an automated notification from the Quality Management System.</em></p>
                    """,
                    now=True,
                    delayed=False
                )
                
                self.add_comment('Email', f'Notification sent to {len(recipients)} recipient(s)')
                
            except Exception as e:
                frappe.log_error(f"Error sending COA notification: {str(e)}", "COA AMB - Notification")

    def create_quality_audit(self):
        """Create audit record for submitted COA"""
        try:
            audit_doc = frappe.get_doc({
                "doctype": "Quality Audit",
                "coa_reference": self.name,
                "product_item": self.product_item,
                "item_name": self.item_name,
                "batch_reference": self.batch_reference,
                "coa_result": self.overall_result,
                "compliance_status": self.compliance_status,
                "status": "Completed",
                "audit_date": nowdate(),
                "audited_by": self.approved_by or frappe.session.user
            })
            audit_doc.insert(ignore_permissions=True)
            
            self.add_comment('Info', f'Quality audit record created: {audit_doc.name}')
            
        except Exception as e:
            frappe.log_error(f"Error creating quality audit: {str(e)}", "COA AMB - Audit Creation")

    def update_product_quality_status(self):
        """Update product master with latest quality status"""
        if not self.product_item:
            return
            
        try:
            # Update item with latest COA information
            frappe.db.set_value('Item', self.product_item, {
                'last_coa_date': nowdate(),
                'last_coa_result': self.overall_result,
                'last_coa_reference': self.name
            })
            
        except Exception as e:
            frappe.log_error(f"Error updating product quality status: {str(e)}", "COA AMB - Product Update")

    def revert_product_quality_status(self):
        """Revert product quality status on COA cancellation"""
        if not self.product_item:
            return
            
        try:
            # Clear COA references from item
            frappe.db.set_value('Item', self.product_item, {
                'last_coa_date': None,
                'last_coa_result': None,
                'last_coa_reference': None
            })
            
        except Exception as e:
            frappe.log_error(f"Error reverting product quality status: {str(e)}", "COA AMB - Product Revert")

    def calculate_child_table_status(self):
        """Calculate and update status for each test parameter"""
        for param in self.coa_quality_test_parameter:
            if self._is_header_row(param):
                param.status = 'Title'
                continue
                
            if not param.result:
                param.status = 'Pending'
                continue
                
            # Check compliance
            is_compliant = self.check_parameter_compliance(param)
            param.status = 'Pass' if is_compliant else 'Fail'

    # ==================== HELPER METHODS ====================

    def get_test_summary(self):
        """Get summary of test results"""
        if not self.coa_quality_test_parameter:
            return {}
            
        non_title = [p for p in self.coa_quality_test_parameter if not self._is_header_row(p)]
        total = len(non_title)
        passed = len([p for p in non_title if p.status == 'Pass'])
        failed = len([p for p in non_title if p.status == 'Fail'])
        pending = len([p for p in non_title if p.status == 'Pending'])
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pending': pending,
            'pass_rate': (passed / total * 100) if total > 0 else 0
        }

# ==================== WHITELISTED METHODS ====================

@frappe.whitelist()
def create_coa_from_tds(tds_name, batch_name=None):
    """Create COA from TDS template"""
    try:
        coa = frappe.new_doc('COA AMB')
        coa.linked_tds = tds_name
        
        if batch_name:
            coa.batch_reference = batch_name
            
        coa.insert()
        
        frappe.msgprint(_("COA created successfully: {0}").format(coa.name), alert=True)
        return coa.name
        
    except Exception as e:
        frappe.log_error(f"Error creating COA from TDS: {str(e)}", "COA Creation")
        frappe.throw(_("Error creating COA: {0}").format(str(e)))

@frappe.whitelist()
def get_batch_quality_data(batch_name):
    """Get quality test data for a batch"""
    if not frappe.db.exists('Batch AMB', batch_name):
        return {"error": "Batch not found"}
    
    try:
        # Get COAs for this batch
        coas = frappe.get_all(
            'COA AMB',
            filters={'batch_reference': batch_name, 'docstatus': 1},
            fields=['name', 'coa_number', 'overall_result', 'approval_date', 'approved_by']
        )
        
        # Get quality inspections if available
        inspections = []
        if frappe.db.exists('DocType', 'Quality Inspection'):
            inspections = frappe.get_all(
                'Quality Inspection',
                filters={'reference_name': batch_name},
                fields=['name', 'inspection_type', 'status', 'report_date', 'inspected_by']
            )
        
        return {
            'coas': coas,
            'inspections': inspections,
            'batch': frappe.get_doc('Batch AMB', batch_name).as_dict()
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting batch quality data: {str(e)}", "Batch Quality Data")
        return {"error": str(e)}

@frappe.whitelist()
def generate_coa_pdf(coa_name):
    """Generate PDF for COA"""
    try:
        return frappe.get_print(
            'COA AMB',
            coa_name,
            print_format='Standard',
            as_pdf=True
        )
    except Exception as e:
        frappe.log_error(f"Error generating COA PDF: {str(e)}", "COA PDF Generation")
        frappe.throw(_("Error generating PDF: {0}").format(str(e)))

@frappe.whitelist()
def fetch_parameter_details(parameter_name):
    """Fetch parameter details from master data"""
    try:
        # Check if parameter exists in master
        if frappe.db.exists('Quality Inspection Parameter', parameter_name):
            param = frappe.get_doc('Quality Inspection Parameter', parameter_name)
            return {
                'specification': param.specification,
                'test_method': param.test_method,
                'uom': param.uom,
                'min_value': param.min_value,
                'max_value': param.max_value
            }
        return {}
        
    except Exception as e:
        frappe.log_error(f"Error fetching parameter details: {str(e)}", "Parameter Details")
        return {}

@frappe.whitelist()
def validate_all_tests(coa_name):
    """Validate all tests in a COA"""
    try:
        coa = frappe.get_doc('COA AMB', coa_name)
        coa.evaluate_overall_result()
        coa.save()
        
        summary = coa.get_test_summary()
        
        return {
            'message': f"Validated {summary['total']} tests: {summary['passed']} passed, {summary['failed']} failed, {summary['pending']} pending",
            'summary': summary
        }
        
    except Exception as e:
        frappe.log_error(f"Error validating tests: {str(e)}", "Test Validation")
        return {"error": str(e)}

@frappe.whitelist()
def duplicate_coa(source_coa, new_batch=None):
    """Duplicate an existing COA for a new batch"""
    try:
        source = frappe.get_doc('COA AMB', source_coa)
        
        # Create new COA
        new_coa = frappe.new_doc('COA AMB')
        
        # Copy basic information
        new_coa.linked_tds = source.linked_tds
        new_coa.product_item = source.product_item
        new_coa.item_name = source.item_name
        new_coa.item_code = source.item_code
        
        # Set new batch if provided
        if new_batch:
            new_coa.batch_reference = new_batch
        
        # Copy test parameters
        for param in source.coa_quality_test_parameter:
            new_coa.append('coa_quality_test_parameter', {
                'parameter_name': param.parameter_name,
                'specification': param.specification,
                'test_method': param.test_method,
                'min_value': param.min_value,
                'max_value': param.max_value,
                'custom_uom': param.custom_uom,
                'numeric': param.numeric,
                'formula_based_criteria': param.formula_based_criteria,
                'acceptance_formula': param.acceptance_formula,
                'parameter_group': param.parameter_group,
                'custom_method': param.custom_method,
                'custom_reconstituted_to_05_total_solids_solution': param.custom_reconstituted_to_05_total_solids_solution,
                'custom_is_title_row': param.custom_is_title_row
            })
        
        new_coa.insert()
        
        return {
            'message': _("COA duplicated successfully"),
            'new_coa': new_coa.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error duplicating COA: {str(e)}", "COA Duplication")
        frappe.throw(_("Error duplicating COA: {0}").format(str(e)))


# ────────────────────────────────────────────────────────────────────────────
# SC4 — Customer-Specific Specification validation hook (wired in hooks.py doc_events)
# ────────────────────────────────────────────────────────────────────────────

def validate_css_on_submit(doc, method=None):
    """On COA AMB submit, cross-reference each measured parameter row against
    approved Customer-Specific Specification records for every customer in custom_coa_customers.

    Behavior controlled by TDS Settings.css_block_on_mismatch (Check):
      0 (default) — warn-only: shows frappe.msgprint for each mismatch
      1           — block:     raises frappe.throw with the full mismatch list

    Skips silently if:
      - No customers in custom_coa_customers (no customer context)
      - No coa_quality_test_parameter rows (no measurements)
      - No matching CSS found for a (param, customer) pair (no expectation to validate against)
    """
    if not doc.get('custom_coa_customers'):
        return

    customers = [c.customer for c in doc.custom_coa_customers if c.customer]
    if not customers:
        return

    errors = []
    warnings = []

    for row in (doc.coa_quality_test_parameter or []):
        param = row.parameter_name
        if not param:
            continue

        for customer in customers:
            css_records = frappe.db.get_list(
                'Customer-Specific Specification',
                filters={
                    'parameter': param,
                    'customer': customer,
                    'status': 'Approved',
                    'is_active': 1,
                    'effective_from': ['<=', frappe.utils.today()],
                },
                fields=[
                    'name', 'value_type', 'value_text', 'value_min', 'value_max',
                    'unit_of_measurement', 'regulatory_reference', 'effective_to',
                ],
                order_by='effective_from DESC',
            )

            for css in css_records:
                if css.get('effective_to') and css['effective_to'] < frappe.utils.today():
                    continue

                if _row_value_matches_css(row, css):
                    continue

                expected = (
                    css.get('value_text')
                    or f"{css.get('value_min')}-{css.get('value_max')}"
                )
                ref = f" [ref: {css['regulatory_reference']}]" if css.get('regulatory_reference') else ''
                msg = _(
                    "Row {idx} (parameter {param!r}, value {val!r}): "
                    "does not match Customer-Specific Specification <a href=\"/app/customer-specific-specification/{css}\">{css}</a> "
                    "for {customer} (expected: {expected}){ref}"
                ).format(
                    idx=row.idx, param=param, val=row.value,
                    css=css['name'], customer=customer, expected=expected, ref=ref,
                )

                if frappe.db.get_single_value('TDS Settings', 'css_block_on_mismatch'):
                    errors.append(msg)
                else:
                    warnings.append(msg)

    if errors:
        frappe.throw('<br>'.join(errors), title=_('CSS Validation Failed'))

    if warnings:
        for w in warnings:
            frappe.msgprint(w, indicator='orange', alert=True, title=_('CSS Warning'))


def _row_value_matches_css(row, css):
    """True if a COA Quality Test Parameter row's value satisfies the CSS expectation."""
    vt = css.get('value_type')

    if vt == 'Choice':
        return (row.value or '').strip().upper() == (css.get('value_text') or '').strip().upper()

    if vt == 'Numeric Range':
        try:
            v = float(row.value)
            vmin = css.get('value_min')
            vmax = css.get('value_max')
            if vmin is None and vmax is None:
                return True
            if vmin is not None and v < vmin:
                return False
            if vmax is not None and v > vmax:
                return False
            return True
        except (ValueError, TypeError):
            return False

    if vt == 'Both':
        return (
            _row_value_matches_css(row, {**css, 'value_type': 'Choice'})
            or _row_value_matches_css(row, {**css, 'value_type': 'Numeric Range'})
        )

    return True
