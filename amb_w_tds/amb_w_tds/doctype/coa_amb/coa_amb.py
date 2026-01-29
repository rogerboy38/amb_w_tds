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

    def validate(self):
        """Comprehensive validation logic"""
        super().validate()
        
        # Core validation sequence
        self.validate_linked_tds()
        self.validate_batch_reference()
        self.set_item_details()
        
        # Enhanced test parameter validation
        self.validate_test_parameters()
        self.evaluate_overall_result()
        
        # Additional validations
        self.check_mandatory_tds_link()
        self.validate_signature_on_submit()
        
        # Formula evaluation for parameters
        self.evaluate_formula_parameters()

    def before_insert(self):
        """Before insert - sync from TDS"""
        if self.linked_tds and not self.coa_quality_test_parameter:
            self.sync_from_tds()
        self.set_default_naming_series()

    def before_save(self):
        """Before save hook"""
        self.set_coa_number()
        self.set_approval_info()
        self.calculate_child_table_status()

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
        """Comprehensive validation for quality test parameters"""
        if not self.coa_quality_test_parameter and self.docstatus == 1:
            frappe.throw(_("At least one quality test parameter is required for submission"))
        
        for idx, row in enumerate(self.coa_quality_test_parameter, 1):
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
            if self.docstatus == 1 and not row.result and not row.custom_is_title_row:
                frappe.throw(_(f"Row {idx}: Result is required for parameter '{row.parameter_name}'"))

    def validate_numeric_result(self, row, idx):
        """Validate numeric results against min/max values"""
        try:
            result = flt(row.result)
            
            if row.get('min_value') is not None and result < flt(row.min_value):
                frappe.throw(_(f"Row {idx}: Result {result} is below minimum value {row.min_value} for parameter '{row.parameter_name}'"))
            
            if row.get('max_value') is not None and result > flt(row.max_value):
                frappe.throw(_(f"Row {idx}: Result {result} is above maximum value {row.max_value} for parameter '{row.parameter_name}'"))
                
        except ValueError:
            frappe.throw(_(f"Row {idx}: Invalid numeric result format for parameter '{row.parameter_name}'"))

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
            if param.custom_is_title_row:
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
        """Enhanced parameter compliance checking with multiple formats"""
        if not param.result:
            return False

        try:
            result = flt(param.result)
            
            # Priority 1: Use min/max values if available
            if param.get('min_value') is not None and param.get('max_value') is not None:
                min_val = flt(param.min_value)
                max_val = flt(param.max_value)
                return min_val <= result <= max_val
            
            # Priority 2: Parse specification field
            if param.specification:
                return self.parse_specification_compliance(param.specification, result)
            
            # Priority 3: Formula-based criteria
            if param.formula_based_criteria and param.acceptance_formula:
                allowed_namespaces = {'result': result}
                return frappe.safe_eval(param.acceptance_formula, allowed_namespaces)
            
            return True  # No validation criteria specified
            
        except Exception as e:
            frappe.log_error(f"Error checking compliance for parameter {param.parameter_name}: {str(e)}", "COA Compliance Check")
            return False

    def parse_specification_compliance(self, spec, result):
        """Parse specification string for compliance checking"""
        if not spec:
            return True
            
        spec = cstr(spec).strip()
        
        try:
            # Range format: "10-20", "10 - 20", "10 to 20"
            range_match = re.search(r'([\d\.]+)\s*[-to]+\s*([\d\.]+)', spec, re.IGNORECASE)
            if range_match:
                min_val = flt(range_match.group(1))
                max_val = flt(range_match.group(2))
                return min_val <= result <= max_val
            
            # Greater than or equal: "≥10", ">=10", ">10", "min 10"
            if '≥' in spec or '>=' in spec or ('>' in spec and not '>>' in spec):
                min_val = flt(re.search(r'[\d\.]+', spec.replace('≥', '').replace('>=', '').replace('>', '')).group())
                return result >= min_val
            
            # Less than or equal: "≤20", "<=20", "<20", "max 20"
            if '≤' in spec or '<=' in spec or ('<' in spec and not '<<' in spec):
                max_val = flt(re.search(r'[\d\.]+', spec.replace('≤', '').replace('<=', '').replace('<', '')).group())
                return result <= max_val
            
            # Target value with tolerance: "10 ± 0.5", "10 +/- 0.5"
            tolerance_match = re.search(r'([\d\.]+)\s*[±\+\/-]+\s*([\d\.]+)', spec)
            if tolerance_match:
                target = flt(tolerance_match.group(1))
                tolerance = flt(tolerance_match.group(2))
                return abs(result - target) <= tolerance
            
            # Exact match
            target = flt(spec)
            return abs(result - target) < 0.001
            
        except:
            return True  # Can't parse specification

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

            # Copy specifications to quality parameters
            if hasattr(tds, 'specifications') and tds.specifications:
                for spec in tds.specifications:
                    self.append('coa_quality_test_parameter', {
                        'parameter_name': spec.parameter,
                        'specification': spec.specification,
                        'test_method': spec.test_method,
                        'result': '',
                        'min_value': spec.get('min_value'),
                        'max_value': spec.get('max_value'),
                        'custom_uom': spec.get('custom_uom')
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
                self.coa_number = make_autoname(self.naming_series)
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
            if param.custom_is_title_row:
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
            
        total = len([p for p in self.coa_quality_test_parameter if not p.custom_is_title_row])
        passed = len([p for p in self.coa_quality_test_parameter if p.status == 'Pass'])
        failed = len([p for p in self.coa_quality_test_parameter if p.status == 'Fail'])
        pending = len([p for p in self.coa_quality_test_parameter if p.status == 'Pending'])
        
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
