"""
Certification Document DocType Controller

This module manages regulatory certificates and documents including
expiry tracking, renewal notifications, and document verification.
"""

import frappe
import hashlib
import os
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, date_diff, cstr
from frappe import _

class CertificationDocument(Document):
    """
    Certification Document DocType controller.
    
    Manages regulatory certificates, compliance documents, and their
    lifecycle including renewals, verification, and notifications.
    """
    
    def validate(self):
        """Validate certification document before saving."""
        self.validate_dates()
        self.set_defaults()
        
    def before_save(self):
        """Called before saving the document."""
        self.update_status()
        self.calculate_file_hash()
        self.set_system_fields()
        
    def after_insert(self):
        """Called after inserting a new document."""
        self.schedule_renewal_reminders()
        
    def on_update(self):
        """Called after updating the document."""
        self.send_expiry_notifications()
        
    def validate_dates(self):
        """Validate date fields."""
        if self.issue_date and self.expiry_date:
            if self.issue_date >= self.expiry_date:
                frappe.throw(_("Issue date cannot be after expiry date"))
                
        if self.last_renewal_date and self.next_renewal_due:
            if self.last_renewal_date > self.next_renewal_due:
                frappe.throw(_("Last renewal date cannot be after next renewal due date"))
                
    def set_defaults(self):
        """Set default values."""
        if not self.status:
            if self.expiry_date:
                days_to_expiry = date_diff(self.expiry_date, nowdate())
                if days_to_expiry < 0:
                    self.status = "Expired"
                elif days_to_expiry <= 30:
                    self.status = "Expiring Soon"
                else:
                    self.status = "Valid"
            else:
                self.status = "Valid"
                
        if not self.access_level:
            self.access_level = "Internal"
            
        if not self.verification_status:
            self.verification_status = "Pending Verification"
            
        if not self.payment_status:
            self.payment_status = "Paid"
            
        if not self.review_frequency:
            self.review_frequency = "Annual"
            
    def update_status(self):
        """Update status based on expiry date."""
        if self.expiry_date:
            days_to_expiry = date_diff(self.expiry_date, nowdate())
            
            if days_to_expiry < 0:
                self.status = "Expired"
            elif days_to_expiry <= 30:
                self.status = "Expiring Soon"
            elif self.status in ["Expired", "Expiring Soon"]:
                self.status = "Valid"
                
    def calculate_file_hash(self):
        """Calculate and store document hash for integrity verification."""
        if self.document_file and not self.document_hash:
            try:
                file_doc = frappe.get_doc("File", {"file_url": self.document_file})
                file_path = file_doc.get_full_path()
                
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                        self.document_hash = hashlib.md5(file_content).hexdigest()
                        
                    # Set file size
                    self.file_size = f"{os.path.getsize(file_path) / 1024:.1f} KB"
                    
            except Exception as e:
                frappe.log_error(f"Error calculating file hash: {str(e)}")
                
    def set_system_fields(self):
        """Set system tracking fields."""
        if not self.created_by_user:
            self.created_by_user = frappe.session.user
            
        self.last_updated_by = frappe.session.user
        
    def schedule_renewal_reminders(self):
        """Schedule automatic renewal reminder notifications."""
        if self.expiry_date and self.contact_email:
            # Schedule reminders at 90, 30, and 7 days before expiry
            reminder_days = [90, 30, 7]
            
            for days in reminder_days:
                reminder_date = add_days(self.expiry_date, -days)
                if reminder_date >= nowdate():
                    # In a real implementation, this would create scheduled tasks
                    pass
                    
    def send_expiry_notifications(self):
        """Send notifications for expiring certificates."""
        if self.expiry_date and self.contact_email:
            days_to_expiry = date_diff(self.expiry_date, nowdate())
            
            if days_to_expiry in [90, 30, 7, 1] and days_to_expiry > 0:
                try:
                    frappe.sendmail(
                        recipients=[self.contact_email],
                        subject=f"Certificate Expiry Reminder: {self.document_title}",
                        message=f"""
                        <p>Dear {self.primary_contact or 'Sir/Madam'},</p>
                        <p>This is a reminder that the following certificate will expire in {days_to_expiry} days:</p>
                        <ul>
                            <li><strong>Document:</strong> {self.document_title}</li>
                            <li><strong>Certificate Number:</strong> {self.certificate_number or 'N/A'}</li>
                            <li><strong>Expiry Date:</strong> {self.expiry_date}</li>
                            <li><strong>Issuing Authority:</strong> {self.issuing_authority}</li>
                        </ul>
                        <p>Please take necessary action to renew this certificate before expiry.</p>
                        <p>Best regards,<br>Sysmayal Compliance Team</p>
                        """
                    )
                except Exception as e:
                    frappe.log_error(f"Failed to send expiry notification: {str(e)}")
                    
    @frappe.whitelist()
    def verify_document_integrity(self):
        """Verify document integrity using stored hash."""
        if not self.document_file or not self.document_hash:
            return {"status": "error", "message": "No file or hash available for verification"}
            
        try:
            file_doc = frappe.get_doc("File", {"file_url": self.document_file})
            file_path = file_doc.get_full_path()
            
            if not os.path.exists(file_path):
                return {"status": "error", "message": "Document file not found"}
                
            with open(file_path, 'rb') as f:
                current_hash = hashlib.md5(f.read()).hexdigest()
                
            if current_hash == self.document_hash:
                self.verification_status = "Verified"
                self.save()
                return {"status": "success", "message": "Document integrity verified"}
            else:
                self.verification_status = "Verification Failed"
                self.save()
                return {"status": "error", "message": "Document has been modified or corrupted"}
                
        except Exception as e:
            return {"status": "error", "message": f"Verification failed: {str(e)}"}
            
    @frappe.whitelist()
    def renew_certificate(self, new_expiry_date, new_certificate_number=None, renewal_cost=None):
        """Process certificate renewal."""
        self.last_renewal_date = nowdate()
        self.expiry_date = new_expiry_date
        
        if new_certificate_number:
            self.certificate_number = new_certificate_number
            
        if renewal_cost:
            self.renewal_cost = renewal_cost
            
        # Calculate next renewal due date
        if self.review_frequency == "Annual":
            self.next_renewal_due = add_days(new_expiry_date, -90)  # 3 months before
        elif self.review_frequency == "Bi-annual":
            self.next_renewal_due = add_days(new_expiry_date, -60)   # 2 months before
        else:
            self.next_renewal_due = add_days(new_expiry_date, -30)   # 1 month before
            
        self.status = "Valid"
        self.save()
        
        return _("Certificate renewed successfully")
        
    @frappe.whitelist()
    def get_renewal_timeline(self):
        """Get renewal timeline and important dates."""
        timeline = []
        
        if self.issue_date:
            timeline.append({
                "date": self.issue_date,
                "event": "Certificate Issued",
                "status": "completed"
            })
            
        if self.last_renewal_date:
            timeline.append({
                "date": self.last_renewal_date,
                "event": "Last Renewal",
                "status": "completed"
            })
            
        if self.next_renewal_due:
            timeline.append({
                "date": self.next_renewal_due,
                "event": "Renewal Due",
                "status": "upcoming" if self.next_renewal_due > nowdate() else "overdue"
            })
            
        if self.expiry_date:
            timeline.append({
                "date": self.expiry_date,
                "event": "Certificate Expires",
                "status": "upcoming" if self.expiry_date > nowdate() else "expired"
            })
            
        return sorted(timeline, key=lambda x: x["date"])

# Utility functions

@frappe.whitelist()
def get_expiring_certificates(days_ahead=90):
    """Get certificates expiring within specified days."""
    
    expiring_certs = frappe.db.sql("""
        SELECT name, document_title, certificate_number, expiry_date,
               organization, contact_email, status,
               DATEDIFF(expiry_date, CURDATE()) as days_to_expiry
        FROM `tabCertification Document`
        WHERE expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
        AND status != 'Expired'
        ORDER BY expiry_date
    """, (days_ahead,), as_dict=True)
    
    return expiring_certs

@frappe.whitelist()
def get_certificate_dashboard_data():
    """Get dashboard data for certification documents."""
    
    # Status distribution
    status_data = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabCertification Document`
        GROUP BY status
    """, as_dict=True)
    
    # Document type distribution
    type_data = frappe.db.sql("""
        SELECT document_type, COUNT(*) as count
        FROM `tabCertification Document`
        GROUP BY document_type
        ORDER BY count DESC
    """, as_dict=True)
    
    # Monthly expiry forecast
    expiry_forecast = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(expiry_date, '%Y-%m') as month,
            COUNT(*) as expiring_count
        FROM `tabCertification Document`
        WHERE expiry_date >= CURDATE()
        AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """, as_dict=True)
    
    # Cost analysis
    cost_analysis = frappe.db.sql("""
        SELECT 
            SUM(certification_cost) as total_certification_cost,
            SUM(renewal_cost) as total_renewal_cost,
            AVG(certification_cost) as avg_certification_cost,
            COUNT(*) as total_certificates
        FROM `tabCertification Document`
        WHERE certification_cost > 0 OR renewal_cost > 0
    """, as_dict=True)
    
    return {
        "status_distribution": status_data,
        "type_distribution": type_data,
        "expiry_forecast": expiry_forecast,
        "cost_analysis": cost_analysis[0] if cost_analysis else {}
    }

@frappe.whitelist()
def bulk_verify_documents(document_names):
    """Bulk verify multiple documents."""
    
    if isinstance(document_names, str):
        document_names = frappe.parse_json(document_names)
        
    results = []
    
    for doc_name in document_names:
        try:
            doc = frappe.get_doc("Certification Document", doc_name)
            result = doc.verify_document_integrity()
            results.append({
                "document": doc_name,
                "status": result["status"],
                "message": result["message"]
            })
        except Exception as e:
            results.append({
                "document": doc_name,
                "status": "error",
                "message": str(e)
            })
            
    return results

@frappe.whitelist()
def generate_certificate_report(filters=None):
    """Generate comprehensive certificate report."""
    
    conditions = []
    values = []
    
    if filters:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)
            
        if filters.get("status"):
            conditions.append("status = %s")
            values.append(filters["status"])
            
        if filters.get("document_type"):
            conditions.append("document_type = %s")
            values.append(filters["document_type"])
            
        if filters.get("country"):
            conditions.append("country = %s")
            values.append(filters["country"])
            
        if filters.get("organization"):
            conditions.append("organization = %s")
            values.append(filters["organization"])
            
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT 
            name, document_title, document_type, certificate_number,
            status, country, organization, issuing_authority,
            issue_date, expiry_date, next_renewal_due,
            certification_cost, renewal_cost, currency,
            primary_contact, contact_email, verification_status
        FROM `tabCertification Document`
        WHERE {where_clause}
        ORDER BY expiry_date, document_title
    """
    
    certificates = frappe.db.sql(query, values, as_dict=True)
    
    return certificates
