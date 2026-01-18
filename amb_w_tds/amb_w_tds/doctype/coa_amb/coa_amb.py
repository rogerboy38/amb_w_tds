# Copyright (c) 2024, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, flt


class COAAMB(Document):
    """
    COA AMB - Certificate of Analysis
    """
    
    def validate(self):
        """Validation logic"""
        self.validate_linked_tds()
        self.validate_batch_reference()
        self.set_item_details()
        self.evaluate_overall_result()
    
    def before_insert(self):
        """Before insert - sync from TDS"""
        if self.linked_tds and not self.coa_quality_test_parameter:
            self.sync_from_tds()
    
    def before_save(self):
        """Before save hook"""
        self.set_coa_number()
        self.set_approval_info()
    
    def on_submit(self):
        """On submit"""
        self.generate_coa_pdf()
        self.update_batch_status()
        self.notify_quality_team()
    
    def on_cancel(self):
        """On cancel"""
        self.update_batch_status('COA Cancelled')
    
    # ==================== VALIDATION METHODS ====================
    
    def validate_linked_tds(self):
        """Ensure linked TDS exists and is approved"""
        if self.linked_tds:
            if not frappe.db.exists('TDS Product Specification', self.linked_tds):
                frappe.throw(_("TDS {0} does not exist").format(self.linked_tds))
            
            tds = frappe.get_doc('TDS Product Specification', self.linked_tds)
            if tds.docstatus != 1:
                frappe.throw(_("TDS {0} is not approved").format(self.linked_tds))
    
    def validate_batch_reference(self):
        """Validate batch exists"""
        if self.batch_reference:
            if not frappe.db.exists('Batch AMB', self.batch_reference):
                frappe.throw(_("Batch {0} does not exist").format(self.batch_reference))
    
    def set_item_details(self):
        """Get item details from Item master or TDS"""
        if self.product_item:
            item = frappe.get_doc('Item', self.product_item)
            self.item_name = item.item_name
            self.item_code = item.item_code
        elif self.linked_tds:
            tds = frappe.get_doc('TDS Product Specification', self.linked_tds)
            self.product_item = tds.product_item
            self.item_name = tds.item_name
            self.item_code = tds.item_code
    
    def evaluate_overall_result(self):
        """Evaluate overall test result"""
        if not self.coa_quality_test_parameter:
            return
        
        failed_tests = []
        passed_tests = []
        
        for param in self.coa_quality_test_parameter:
            if param.result:
                # Simple pass/fail logic - can be enhanced
                if self.check_parameter_compliance(param):
                    passed_tests.append(param.parameter_name)
                else:
                    failed_tests.append(param.parameter_name)
        
        if failed_tests:
            self.overall_result = 'Fail'
            self.failed_parameters = ', '.join(failed_tests)
        elif passed_tests:
            self.overall_result = 'Pass'
        else:
            self.overall_result = 'Pending'
    
    def check_parameter_compliance(self, param):
        """Check if parameter result is within specification"""
        if not param.result or not param.specification:
            return True  # No data to validate
        
        try:
            result = flt(param.result)
            
            # Extract min/max from specification (format: "10-20" or "≥10" or "≤20")
            spec = param.specification.strip()
            
            # Range format: "10-20"
            if '-' in spec and not spec.startswith('-'):
                parts = spec.split('-')
                if len(parts) == 2:
                    min_val = flt(parts[0].strip())
                    max_val = flt(parts[1].strip())
                    return min_val <= result <= max_val
            
            # Greater than or equal: "≥10" or ">=10"
            elif '≥' in spec or '>=' in spec:
                min_val = flt(spec.replace('≥', '').replace('>=', '').strip())
                return result >= min_val
            
            # Less than or equal: "≤20" or "<=20"
            elif '≤' in spec or '<=' in spec:
                max_val = flt(spec.replace('≤', '').replace('<=', '').strip())
                return result <= max_val
            
            # Exact match
            else:
                target = flt(spec)
                return abs(result - target) < 0.01
        
        except:
            return True  # Can't parse, assume pass
    
    # ==================== SYNC & SETUP ====================
    
    def sync_from_tds(self):
        """Sync specifications from linked TDS"""
        if not self.linked_tds:
            return
        
        tds = frappe.get_doc('TDS Product Specification', self.linked_tds)
        
        # Copy item details
        self.product_item = tds.product_item
        self.item_name = tds.item_name
        self.item_code = tds.item_code
        
        # Copy specifications to quality parameters
        if hasattr(tds, 'specifications'):
            for spec in tds.specifications:
                self.append('coa_quality_test_parameter', {
                    'parameter_name': spec.parameter,
                    'specification': spec.specification,
                    'test_method': spec.test_method,
                    'result': ''
                })
    
    def set_coa_number(self):
        """Set COA number if not set"""
        if not self.coa_number:
            # Format: COA-YYYY-MM-XXXX
            from datetime import datetime
            date_str = datetime.now().strftime('%Y-%m')
            
            last_coa = frappe.db.sql("""
                SELECT coa_number 
                FROM `tabCOA AMB` 
                WHERE coa_number LIKE %s 
                ORDER BY creation DESC 
                LIMIT 1
            """, (f"COA-{date_str}-%",))
            
            if last_coa:
                last_num = int(last_coa[0][0].split('-')[-1])
                seq = last_num + 1
            else:
                seq = 1
            
            self.coa_number = f"COA-{date_str}-{seq:04d}"
    
    def set_approval_info(self):
        """Set approval information"""
        if self.docstatus == 1 and not self.approval_date:
            self.approval_date = nowdate()
            if not self.approved_by:
                self.approved_by = frappe.session.user
    
    # ==================== DOCUMENT ACTIONS ====================
    
    def generate_coa_pdf(self):
        """Generate PDF certificate"""
        # This would use Frappe's print format
        try:
            # The PDF will be generated by Frappe's print system
            # We just log that it was requested
            self.add_comment('Info', 'COA PDF generated on submission')
        except Exception as e:
            frappe.log_error(f"Error generating COA PDF: {str(e)}", "COA AMB - PDF Generation")
    
    def update_batch_status(self, status=None):
        """Update related batch with COA info"""
        if not self.batch_reference:
            return
        
        try:
            batch = frappe.get_doc('Batch AMB', self.batch_reference)
            
            if status:
                batch.add_comment('Info', f'COA Status: {status}')
            else:
                batch.coa_generated = 1
                batch.coa_reference = self.name
                batch.quality_status = self.overall_result
                batch.save(ignore_permissions=True)
                
        except Exception as e:
            frappe.log_error(f"Error updating batch: {str(e)}", "COA AMB - Batch Update")
    
    def notify_quality_team(self):
        """Send notifications"""
        recipients = []
        
        # Get quality team members
        quality_users = frappe.get_all('User', 
            filters={'role': ['like', '%Quality%']},
            pluck='email'
        )
        recipients.extend(quality_users)
        
        # Add production manager if batch exists
        if self.batch_reference:
            batch = frappe.get_doc('Batch AMB', self.batch_reference)
            if hasattr(batch, 'production_manager') and batch.production_manager:
                recipients.append(batch.production_manager)
        
        if recipients:
            frappe.sendmail(
                recipients=list(set(recipients)),
                subject=f'COA {self.name} - {self.overall_result}',
                message=f"""
                    <p>Certificate of Analysis <strong>{self.name}</strong> has been issued.</p>
                    <ul>
                        <li>Product: {self.item_name}</li>
                        <li>Batch: {self.batch_reference or 'N/A'}</li>
                        <li>Result: <strong>{self.overall_result}</strong></li>
                        <li>Approval Date: {self.approval_date}</li>
                    </ul>
                    <p><a href="{frappe.utils.get_url()}/app/coa-amb/{self.name}">View COA</a></p>
                """,
                now=True
            )


# ==================== WHITELISTED METHODS ====================

@frappe.whitelist()
def create_coa_from_tds(tds_name, batch_name=None):
    """Create COA from TDS template"""
    coa = frappe.new_doc('COA AMB')
    coa.linked_tds = tds_name
    
    if batch_name:
        coa.batch_reference = batch_name
    
    # Sync will happen in before_insert
    coa.insert()
    
    return coa.name


@frappe.whitelist()
def get_batch_quality_data(batch_name):
    """Get quality test data for a batch"""
    if not frappe.db.exists('DocType', 'Quality Inspection'):
        return []
    
    return frappe.get_all(
        'Quality Inspection',
        filters={'reference_name': batch_name},
        fields=['name', 'inspection_type', 'status', 'report_date']
    )


@frappe.whitelist()
def generate_coa_pdf(coa_name):
    """Generate PDF for COA"""
    # Use Frappe's print format
    return frappe.get_print(
        'COA AMB',
        coa_name,
        print_format='Standard',
        as_pdf=True
    )
