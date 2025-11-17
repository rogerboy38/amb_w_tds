# Fix the AMB KPI Factors Python controller
import frappe
from frappe.model.document import Document

class AMBKPIFactors(Document):
    """AMB KPI Factors for manufacturing calculations"""
    
    def before_save(self):
        """Set default values if empty"""
        # Only set kpi_name if it exists and is empty
        if hasattr(self, 'kpi_name') and not self.kpi_name:
            self.kpi_name = "Production Efficiency"
        
        # Only set factor_data_year if the field exists and is empty
        if hasattr(self, 'factor_data_year') and not self.factor_data_year:
            self.factor_data_year = "2024"
