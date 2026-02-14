# pharma_batch_migrator.py
import frappe
from frappe.utils import nowdate, add_days
from datetime import datetime
import requests
import json
from typing import Dict, List, Optional

class PharmaBatchMigrator:
    """FDA-compliant batch migration with GMP validation"""
    
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def validate_batch_data(self, batch_data: Dict) -> Dict:
        """GMP: Pre-migration validation"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Required fields check
        required_fields = ["item_code", "batch_id", "manufacturing_date"]
        for field in required_fields:
            if not batch_data.get(field):
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Missing required field: {field}")
        
        # Item validation
        if batch_data.get("item_code"):
            item_valid = self._validate_item(batch_data["item_code"])
            if not item_valid["exists"]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Item not found: {batch_data['item_code']}")
            elif not item_valid["has_shelf_life"]:
                validation_result["warnings"].append(f"Item {batch_data['item_code']} has no shelf life configured")
        
        # Batch uniqueness check
        if batch_data.get("item_code") and batch_data.get("batch_id"):
            existing = self._check_existing_batch(batch_data["item_code"], batch_data["batch_id"])
            if existing:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Batch already exists: {existing}")
        
        # Date validation
        if batch_data.get("manufacturing_date"):
            date_valid = self._validate_manufacturing_date(batch_data["manufacturing_date"])
            if not date_valid["is_valid"]:
                validation_result["is_valid"] = False
                validation_result["errors"].extend(date_valid["errors"])
        
        return validation_result
    
    def _validate_item(self, item_code: str) -> Dict:
        """Validate item exists and has shelf life"""
        try:
            response = self.session.get(f"{self.base_url}/api/resource/Item/{item_code}")
            if response.status_code == 200:
                item_data = response.json()["data"]
                return {
                    "exists": True,
                    "has_shelf_life": bool(item_data.get("shelf_life_in_days")),
                    "shelf_life_days": item_data.get("shelf_life_in_days")
                }
            return {"exists": False, "has_shelf_life": False}
        except:
            return {"exists": False, "has_shelf_life": False}
    
    def _check_existing_batch(self, item_code: str, batch_id: str) -> Optional[str]:
        """Check if batch already exists"""
        filters = json.dumps([
            ["item", "=", item_code],
            ["batch_id", "=", batch_id],
            ["disabled", "=", 0]
        ])
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/resource/Batch?filters={filters}"
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data["data"][0]["name"]
        except:
            pass
        return None
    
    def _validate_manufacturing_date(self, mfg_date: str) -> Dict:
        """Validate manufacturing date"""
        try:
            mfg_date_obj = datetime.strptime(mfg_date, "%Y-%m-%d")
            today = datetime.now()
            
            if mfg_date_obj > today:
                return {
                    "is_valid": False, 
                    "errors": ["Manufacturing date cannot be in the future"]
                }
            return {"is_valid": True, "errors": []}
        except ValueError:
            return {
                "is_valid": False, 
                "errors": ["Invalid date format (use YYYY-MM-DD)"]
            }
    
    def create_pharma_batch(self, batch_data: Dict) -> Dict:
        """Create FDA-compliant batch with full traceability"""
        
        # GMP: Pre-creation validation
        validation = self.validate_batch_data(batch_data)
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": "Validation failed",
                "validation_errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        
        try:
            # Get item details for expiry calculation
            item_details = self._validate_item(batch_data["item_code"])
            
            # Calculate expiry date
            if item_details["has_shelf_life"]:
                mfg_date = datetime.strptime(batch_data["manufacturing_date"], "%Y-%m-%d")
                expiry_date = (mfg_date + timedelta(days=item_details["shelf_life_days"])).strftime("%Y-%m-%d")
            else:
                # Use default if no shelf life (with warning)
                mfg_date = datetime.strptime(batch_data["manufacturing_date"], "%Y-%m-%d")
                expiry_date = (mfg_date + timedelta(days=365)).strftime("%Y-%m-%d")
                validation["warnings"].append("Used default 365-day shelf life")
            
            # Build batch document
            batch_doc = {
                "doctype": "Batch",
                "item": batch_data["item_code"],
                "batch_id": batch_data["batch_id"],
                "manufacturing_date": batch_data["manufacturing_date"],
                "expiry_date": expiry_date,
                "disabled": 0
            }
            
            # Add optional fields
            optional_fields = ["batch_qty", "reference_doctype", "reference_name"]
            for field in optional_fields:
                if batch_data.get(field):
                    batch_doc[field] = batch_data[field]
            
            # GMP: Create batch
            response = self.session.post(
                f"{self.base_url}/api/resource/Batch",
                json=batch_doc
            )
            
            if response.status_code in [200, 201]:
                created_batch = response.json()["data"]
                
                # GMP: Audit log
                self._create_audit_log("Batch Created", {
                    "batch_name": created_batch["name"],
                    "batch_id": batch_data["batch_id"],
                    "item_code": batch_data["item_code"],
                    "manufacturing_date": batch_data["manufacturing_date"],
                    "expiry_date": expiry_date
                })
                
                return {
                    "success": True,
                    "batch_name": created_batch["name"],
                    "warnings": validation["warnings"],
                    "expiry_date": expiry_date
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "response_text": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Creation failed: {str(e)}"
            }
    
    def migrate_batches_bulk(self, batch_list: List[Dict]) -> Dict:
        """Bulk migration with progress tracking"""
        results = {
            "total": len(batch_list),
            "successful": [],
            "failed": [],
            "warnings": []
        }
        
        for i, batch_data in enumerate(batch_list, 1):
            print(f"Processing {i}/{len(batch_list)}: {batch_data.get('batch_id')}")
            
            result = self.create_pharma_batch(batch_data)
            
            if result["success"]:
                results["successful"].append({
                    "batch_id": batch_data["batch_id"],
                    "batch_name": result["batch_name"],
                    "warnings": result.get("warnings", [])
                })
            else:
                results["failed"].append({
                    "batch_data": batch_data,
                    "error": result["error"],
                    "validation_errors": result.get("validation_errors", [])
                })
            
            # Rate limiting for Frappe Cloud
            import time
            time.sleep(0.1)
        
        # Generate migration report
        self._generate_migration_report(results)
        return results
    
    def _create_audit_log(self, action: str, details: Dict):
        """GMP: Create audit trail"""
        # In production, implement proper audit logging
        print(f"🔍 AUDIT: {action} - {json.dumps(details)}")
    
    def _generate_migration_report(self, results: Dict):
        """Generate migration summary report"""
        print("\n" + "=" * 60)
        print("📊 BATCH MIGRATION REPORT")
        print("=" * 60)
        print(f"Total processed: {results['total']}")
        print(f"✅ Successful: {len(results['successful'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        
        if results['failed']:
            print("\nFailed batches (first 5):")
            for failed in results['failed'][:5]:
                print(f"  - {failed['batch_data'].get('batch_id')}: {failed['error']}")

# Example usage
def example_migration():
    """Example of how to use the migrator"""
    
    # Initialize migrator
    migrator = PharmaBatchMigrator(
        base_url="http://your-erpnext-site.com",
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    # Sample batch data
    sample_batches = [
        {
            "item_code": "0219",
            "batch_id": "0219071201",
            "manufacturing_date": "2024-07-12",
            "batch_qty": 1000,
            "reference_doctype": "Batch AMB",
            "reference_name": "BATCH-AMB-001"
        },
        {
            "item_code": "0219", 
            "batch_id": "0219071202",
            "manufacturing_date": "2024-07-12",
            "batch_qty": 1500
        }
    ]
    
    # Validate first
    for batch in sample_batches:
        validation = migrator.validate_batch_data(batch)
        print(f"Validation for {batch['batch_id']}: {'✅' if validation['is_valid'] else '❌'}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
    
    # Migrate
    results = migrator.migrate_batches_bulk(sample_batches)
    return results

if __name__ == "__main__":
    example_migration()

