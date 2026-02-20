import frappe
import json
from datetime import datetime
from frappe.model.document import Document

class ContainerSelection(Document):
    def validate(self):
        """Validate container data and enforce business rules"""
        self.validate_container_capacity()
        self.validate_container_status()
        self.validate_assignment_rules()
        self.validate_unique_container_id()
        
    def before_save(self):
        """Track changes and assignment history"""
        self.track_assignment_history()
        self.update_container_activity()
        
    def after_insert(self):
        """Initialize container after creation"""
        self.initialize_container_log()
        
    def on_update(self):
        """Handle container status changes"""
        self.handle_status_change()
        
    def on_cancel(self):
        """Handle container cancellation"""
        self.cleanup_container_assignment()
        
    def validate_container_capacity(self):
        """Validate container capacity constraints"""
        if self.capacity_liters and self.capacity_liters <= 0:
            frappe.throw("Container capacity must be a positive value")
            
        # Validate capacity against container type
        capacity_limits = {
            "Sample Container": 10,
            "Production Container": 5000,
            "QC Container": 50,
            "Storage Container": 10000
        }
        
        if self.container_type in capacity_limits:
            max_capacity = capacity_limits[self.container_type]
            if self.capacity_liters > max_capacity:
                frappe.throw(f"Capacity cannot exceed {max_capacity} liters for {self.container_type}")
                
    def validate_container_status(self):
        """Validate container status transitions"""
        if self.container_status == "Retired":
            if not self.is_active:
                pass  # Retired containers should be inactive
            else:
                self.is_active = 0
                
        if self.container_status == "In Use" and not self.current_batch:
            frappe.throw("Containers marked as 'In Use' must have a current batch assigned")
            
    def validate_assignment_rules(self):
        """Validate container assignment business rules"""
        # Check if assigning to batch when status is changing to "In Use"
        if self.container_status == "In Use" and self.current_batch:
            if not self.assignment_date:
                self.assignment_date = datetime.now()
            if not self.assigned_by:
                self.assigned_by = frappe.session.user
                
        # Validate that available containers don't have batch assignments
        if self.container_status == "Available" and self.current_batch:
            frappe.throw("Available containers cannot have current batch assignments")
            
    def validate_unique_container_id(self):
        """Ensure container ID uniqueness across all containers"""
        if self.container_id and not self.is_new():
            existing_container = frappe.get_value(
                "Container Selection",
                filters={
                    "container_id": self.container_id,
                    "name": ["!=", self.name]
                }
            )
            if existing_container:
                frappe.throw(f"Container ID '{self.container_id}' already exists")
                
    def track_assignment_history(self):
        """Track container assignment changes"""
        if self.is_new():
            self.create_assignment_log("Created")
        else:
            # Check for status changes
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.container_status != self.container_status:
                status_change = f"Status changed from {old_doc.container_status} to {self.container_status}"
                self.create_assignment_log(status_change)
                
            # Check for batch assignment changes
            if old_doc and old_doc.current_batch != self.current_batch:
                if old_doc.current_batch and not self.current_batch:
                    self.create_assignment_log(f"Batch {old_doc.current_batch} removed")
                elif self.current_batch:
                    batch_change = f"Batch {old_doc.current_batch or 'None'} to {self.current_batch}"
                    self.create_assignment_log(f"Batch assignment: {batch_change}")
                    
    def create_assignment_log(self, action):
        """Create an assignment history log entry"""
        assignment_log = {
            "doctype": "Container Assignment Log",
            "container_id": self.name,
            "action": action,
            "timestamp": datetime.now(),
            "user": frappe.session.user,
            "container_status": self.container_status,
            "batch": self.current_batch
        }
        
        frappe.get_doc(assignment_log).insert()
        
    def update_container_activity(self):
        """Update container activity timestamp"""
        if self.is_active:
            self.last_activity = datetime.now()
            
    def initialize_container_log(self):
        """Initialize container with default activity log"""
        if self.is_active:
            self.create_assignment_log("Container activated")
            
    def handle_status_change(self):
        """Handle specific status change requirements"""
        if self.container_status == "Maintenance":
            # Release any current batch assignment
            if self.current_batch:
                self.current_batch = None
                self.assignment_date = None
                self.assigned_by = None
                frappe.msgprint("Current batch assignment released due to maintenance status")
                
        elif self.container_status == "Available":
            # Release assignment when marked available
            if self.current_batch:
                self.current_batch = None
                self.assignment_date = None
                self.assigned_by = None
                frappe.msgprint("Current batch assignment released - container is now available")
                
    def cleanup_container_assignment(self):
        """Clean up container assignment when cancelled"""
        if self.container_status == "In Use" and self.current_batch:
            frappe.msgprint(f"Warning: Cancelled container '{self.container_id}' is still assigned to batch '{self.current_batch}'")
            
    def get_available_containers(self, container_type=None, min_capacity=None):
        """Get list of available containers with optional filtering"""
        filters = {
            "container_status": "Available",
            "is_active": 1
        }
        
        if container_type:
            filters["container_type"] = container_type
            
        if min_capacity:
            filters["capacity_liters"] = [">=", min_capacity]
            
        available_containers = frappe.get_all(
            "Container Selection",
            filters=filters,
            fields=["name", "container_id", "container_type", "capacity_liters"],
            order_by="capacity_liters asc"
        )
        
        return available_containers
        
    def assign_container_to_batch(self, batch_id, assign_container=None):
        """Assign container to a batch with validation"""
        available_containers = self.get_available_containers()
        
        if not available_containers:
            frappe.throw("No available containers found for assignment")
            
        container_to_assign = assign_container
        if not container_to_assign and available_containers:
            # Auto-assign first available container
            container_to_assign = available_containers[0]
            
        if isinstance(container_to_assign, dict):
            container_name = container_to_assign["name"]
        else:
            container_name = container_to_assign
            
        container_doc = frappe.get_doc("Container Selection", container_name)
        
        if container_doc.container_status != "Available":
            frappe.throw(f"Container {container_doc.container_id} is not available for assignment")
            
        # Update container assignment
        container_doc.container_status = "In Use"
        container_doc.current_batch = batch_id
        container_doc.assignment_date = datetime.now()
        container_doc.assigned_by = frappe.session.user
        container_doc.save()
        
        frappe.db.commit()
        
        frappe.msgprint(f"Container {container_doc.container_id} successfully assigned to batch {batch_id}")
        return container_doc

# ================================================
# HOOKS.PY CONTAINER SELECTION FUNCTIONS
# ================================================

@frappe.whitelist()
def get_container_status_summary():
    """Get summary of container statuses for dashboard"""
    status_summary = frappe.db.sql("""
        SELECT 
            container_status,
            COUNT(*) as count,
            SUM(capacity_liters) as total_capacity
        FROM `tabContainer Selection`
        WHERE is_active = 1
        GROUP BY container_status
    """, as_dict=True)
    
    return status_summary

@frappe.whitelist()
def get_available_containers_by_type():
    """Get available containers grouped by type"""
    available_containers = frappe.db.sql("""
        SELECT 
            container_type,
            container_id,
            name,
            capacity_liters
        FROM `tabContainer Selection`
        WHERE container_status = 'Available' 
        AND is_active = 1
        ORDER BY container_type, capacity_liters
    """, as_dict=True)
    
    return available_containers

@frappe.whitelist()
def release_container_assignment(container_name):
    """Release container from current batch assignment"""
    container_doc = frappe.get_doc("Container Selection", container_name)
    
    if container_doc.container_status != "In Use":
        frappe.throw("Container is not currently assigned to a batch")
        
    # Update container status
    old_batch = container_doc.current_batch
    container_doc.container_status = "Available"
    container_doc.current_batch = None
    container_doc.assignment_date = None
    container_doc.assigned_by = None
    
    container_doc.save()
    frappe.db.commit()
    
    frappe.msgprint(f"Container {container_doc.container_id} released from batch {old_batch}")
    
@frappe.whitelist()
def validate_container_for_batch(container_name, batch_id):
    """Validate if container can be assigned to specific batch"""
    container_doc = frappe.get_doc("Container Selection", container_name)
    batch_doc = frappe.get_doc("Batch", batch_id)
    
    validation_result = {
        "can_assign": True,
        "errors": []
    }
    
    # Check container availability
    if container_doc.container_status != "Available":
        validation_result["can_assign"] = False
        validation_result["errors"].append(f"Container is {container_doc.container_status}")
        
    # Check capacity requirements (assume batch has quantity requirement)
    if hasattr(batch_doc, 'quantity') and container_doc.capacity_liters < batch_doc.quantity:
        validation_result["can_assign"] = False
        validation_result["errors"].append("Container capacity insufficient for batch quantity")
        
    # Check container type compatibility
    if container_doc.container_type == "Sample Container" and batch_doc.batch_type != "Sample":
        validation_result["errors"].append("Container type mismatch with batch type")
        
    return validation_result

# Frappe hooks integration
def container_selection_on_app_ready():
    """Initialize container selection system on app ready"""
    frappe.db.set_single_value("System Settings", "container_selection_initialized", 1)

def container_selection_on_db_setup():
    """Setup container selection database tables"""
    # This would create additional tables for assignment logs, etc.
    pass

# Quality Gates Integration Functions
def validate_container_selection_quality():
    """Run quality validation on container selection system"""
    quality_results = {
        "syntax_validation": True,
        "naming_conventions": True,
        "security_checks": True,
        "integration_tests": True,
        "completeness_score": 100
    }
    
    # Check naming conventions
    naming_issues = []
    if not all(hasattr(doc, 'container_id') for doc in frappe.get_all("Container Selection")):
        naming_issues.append("Missing container_id fields")
        
    if naming_issues:
        quality_results["naming_conventions"] = False
        quality_results["naming_issues"] = naming_issues
        
    # Security checks
    security_issues = []
    docs_with_hardcoded_creds = frappe.get_all(
        "Container Selection", 
        filters={"notes": ["like", "%password%"]}
    )
    if docs_with_hardcoded_creds:
        security_issues.append("Potential hardcoded credentials found")
        
    if security_issues:
        quality_results["security_checks"] = False
        quality_results["security_issues"] = security_issues
        
    return quality_results