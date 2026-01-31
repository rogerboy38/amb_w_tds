import frappe
from frappe.model.document import Document

class TDSProductSpecification(Document):
    def validate(self):
        self.validate_version_control()
        # Add any other validation methods here if they exist
    
    def validate_version_control(self):
        """
        Validate version control with safe handling for missing 'version' field
        """
        try:
            # Safely check if version field exists
            if hasattr(self, 'version'):
                if not self.version:
                    # Your existing logic for when version is empty
                    self.handle_empty_version()
                else:
                    # Your existing logic for when version has value
                    self.handle_existing_version()
            else:
                # Version field doesn't exist in the schema
                # Log this for debugging and continue without validation
                frappe.log_error(
                    message="'version' field not found in TDS Product Specification schema",
                    title="Schema Validation Warning"
                )
                
                # Option 1: Skip validation silently (for production)
                # pass
                
                # Option 2: Show a warning (for development/admin users)
                if frappe.session.user == "Administrator":
                    frappe.msgprint(
                        "Version field not found in schema. Please add 'version' field to TDS Product Specification doctype.",
                        alert=True,
                        indicator="orange"
                    )
                
                # Option 3: Create a temporary version field to prevent errors
                self.version = self.get_default_version()
                
        except AttributeError as e:
            # Catch any other attribute errors
            frappe.log_error(
                message=f"Error in validate_version_control: {str(e)}",
                title="TDS Product Specification Validation Error"
            )
            # Set a default version to prevent save failures
            self.version = self.get_default_version()
        except Exception as e:
            # Catch any other exceptions
            frappe.log_error(
                message=f"Unexpected error in validate_version_control: {str(e)}",
                title="TDS Product Specification Validation Error"
            )
            # Continue without breaking
            pass
    
    def handle_empty_version(self):
        """
        Your existing logic when version is empty
        Based on the traceback, this should be your original logic
        """
        # This is where your original code goes
        # Example:
        if not self.version and self.is_new():
            self.version = "1.0"
        elif not self.version:
            # Generate version based on tds_sequence or other fields
            self.generate_version()
    
    def handle_existing_version(self):
        """
        Your existing logic when version has a value
        """
        # This is where your version validation/update logic goes
        # Example:
        if self.has_value_changed("tds_sequence") or self.has_value_changed("approval_date"):
            self.update_version()
    
    def get_default_version(self):
        """
        Generate a default version if field doesn't exist
        """
        # You can customize this based on your needs
        if hasattr(self, 'tds_version') and self.tds_version:
            return self.tds_version
        elif hasattr(self, 'tds_sequence') and self.tds_sequence:
            return f"V{self.tds_sequence}"
        else:
            return "1.0"
    
    def generate_version(self):
        """
        Generate version based on existing data
        """
        # Your version generation logic here
        # Example:
        if hasattr(self, 'tds_sequence') and self.tds_sequence:
            self.version = f"V{self.tds_sequence}"
        else:
            self.version = "1.0"
    
    def update_version(self):
        """
        Update version when certain fields change
        """
        # Your version update logic here
        # Example:
        if hasattr(self, 'tds_sequence'):
            self.version = f"V{self.tds_sequence}"
