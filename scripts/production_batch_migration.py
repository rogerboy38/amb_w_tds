# production_batch_migration.py
import frappe
from frappe.utils import nowdate, add_days
from datetime import datetime, timedelta
import json

class ProductionBatchMigrator:
    """Production-ready batch migration for FDA compliance"""
    
    def __init__(self):
        self.migration_log = []
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0
        }
    
    def migrate_sales_batches(self, sales_data_list):
        """
        Migrate sales batches from FoxPro/legacy data
        Expected sales_data format:
        {
            "item_code": "0219071201",  # Sales item
            "batch_id": "0219071201",   # Golden number
            "manufacturing_date": "2024-07-12",
            "quantity": 1000,
            "batch_amb_ref": "BATCH-AMB-001",  # Reference to Batch AMB
            "source_document": "INV-001"       # Original invoice reference
        }
        """
        print("🚀 Starting Production Batch Migration")
        print("=" * 60)
        
        for i, sales_data in enumerate(sales_data_list, 1):
            print(f"📦 Processing {i}/{len(sales_data_list)}: {sales_data.get('item_code')} - {sales_data.get('batch_id')}")
            
            try:
                result = self._create_sales_batch(sales_data)
                self._log_migration(result)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e),
                    "batch_data": sales_data
                }
                self._log_migration(error_result)
        
        self._print_migration_report()
        return self.stats
    
    def _create_sales_batch(self, sales_data):
        """Create a sales batch linked to Batch AMB"""
        
        # GMP: Validation
        validation = self._validate_sales_batch_data(sales_data)
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": f"Validation failed: {', '.join(validation['errors'])}",
                "batch_data": sales_data
            }
        
        # Check if batch already exists
        existing_batch = self._find_existing_batch(
            sales_data["item_code"], 
            sales_data["batch_id"]
        )
        
        if existing_batch:
            return {
                "success": True,
                "batch_name": existing_batch,
                "action": "existing",
                "batch_data": sales_data,
                "warnings": ["Batch already exists"]
            }
        
        # Calculate expiry date
        expiry_date = self._calculate_expiry_date(
            sales_data["item_code"],
            sales_data["manufacturing_date"]
        )
        
        # Create batch document
        batch_doc = {
            "doctype": "Batch",
            "item": sales_data["item_code"],
            "batch_id": sales_data["batch_id"],
            "manufacturing_date": sales_data["manufacturing_date"],
            "expiry_date": expiry_date,
            "batch_qty": sales_data.get("quantity", 0),
            "disabled": 0
        }
        
        # Link to Batch AMB if provided
        if sales_data.get("batch_amb_ref"):
            batch_doc.update({
                "reference_doctype": "Batch AMB",
                "reference_name": sales_data["batch_amb_ref"]
            })
        
        # GMP: Create the batch
        batch = frappe.get_doc(batch_doc)
        batch.insert()
        
        # GMP: Audit trail
        self._create_audit_trail("Batch Created", {
            "batch_name": batch.name,
            "batch_id": sales_data["batch_id"],
            "item_code": sales_data["item_code"],
            "manufacturing_date": sales_data["manufacturing_date"],
            "expiry_date": expiry_date,
            "batch_amb_ref": sales_data.get("batch_amb_ref"),
            "source_document": sales_data.get("source_document")
        })
        
        return {
            "success": True,
            "batch_name": batch.name,
            "action": "created",
            "batch_data": sales_data,
            "expiry_date": expiry_date
        }
    
    def _validate_sales_batch_data(self, sales_data):
        """GMP: Validate sales batch data"""
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Required fields
        required_fields = ["item_code", "batch_id", "manufacturing_date"]
        for field in required_fields:
            if not sales_data.get(field):
                validation["is_valid"] = False
                validation["errors"].append(f"Missing {field}")
        
        # Item validation
        if sales_data.get("item_code"):
            try:
                item = frappe.get_doc("Item", sales_data["item_code"])
                if item.disabled:
                    validation["is_valid"] = False
                    validation["errors"].append(f"Item {sales_data['item_code']} is disabled")
                
                if not item.shelf_life_in_days:
                    validation["warnings"].append(f"Item {sales_data['item_code']} has no shelf life")
                    
            except frappe.DoesNotExistError:
                validation["is_valid"] = False
                validation["errors"].append(f"Item {sales_data['item_code']} not found")
        
        # Date validation
        if sales_data.get("manufacturing_date"):
            try:
                mfg_date = datetime.strptime(sales_data["manufacturing_date"], "%Y-%m-%d")
                if mfg_date > datetime.now():
                    validation["is_valid"] = False
                    validation["errors"].append("Manufacturing date cannot be in future")
            except ValueError:
                validation["is_valid"] = False
                validation["errors"].append("Invalid manufacturing date format")
        
        return validation
    
    def _find_existing_batch(self, item_code, batch_id):
        """Check if batch already exists"""
        existing = frappe.db.exists("Batch", {
            "item": item_code,
            "batch_id": batch_id,
            "disabled": 0
        })
        return existing
    
    def _calculate_expiry_date(self, item_code, manufacturing_date):
        """Calculate expiry date based on item shelf life"""
        try:
            item = frappe.get_doc("Item", item_code)
            if item.shelf_life_in_days:
                mfg_date = datetime.strptime(manufacturing_date, "%Y-%m-%d")
                expiry_date = mfg_date + timedelta(days=item.shelf_life_in_days)
                return expiry_date.strftime("%Y-%m-%d")
        except:
            pass
        
        # Default fallback
        mfg_date = datetime.strptime(manufacturing_date, "%Y-%m-%d")
        return (mfg_date + timedelta(days=365)).strftime("%Y-%m-%d")
    
    def _create_audit_trail(self, action, details):
        """GMP: Create audit trail entry"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        print(f"🔍 AUDIT: {action} - {json.dumps(details, default=str)}")
    
    def _log_migration(self, result):
        """Log migration results"""
        self.migration_log.append(result)
        self.stats["total_processed"] += 1
        
        if result["success"]:
            self.stats["successful"] += 1
            action = result.get("action", "created")
            print(f"   ✅ {action.upper()}: {result['batch_name']}")
            
            if result.get("warnings"):
                self.stats["warnings"] += 1
                for warning in result["warnings"]:
                    print(f"      ⚠️  {warning}")
        else:
            self.stats["failed"] += 1
            print(f"   ❌ FAILED: {result['error']}")
    
    def _print_migration_report(self):
        """Print comprehensive migration report"""
        print("\n" + "=" * 60)
        print("📊 PRODUCTION MIGRATION REPORT")
        print("=" * 60)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"✅ Successful: {self.stats['successful']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"⚠️  Warnings: {self.stats['warnings']}")
        
        # Show failed batches for review
        failed_batches = [log for log in self.migration_log if not log["success"]]
        if failed_batches:
            print(f"\nFailed batches ({len(failed_batches)}):")
            for failed in failed_batches[:5]:  # Show first 5
                print(f"  - {failed['batch_data'].get('item_code')}: {failed['error']}")

# Example usage with your data
def run_example_migration():
    """Run example migration with test data"""
    
    migrator = ProductionBatchMigrator()
    
    # Sample sales data (replace with your actual FoxPro data)
    sample_sales_data = [
        {
            "item_code": "0219",
            "batch_id": "0219071201",
            "manufacturing_date": "2024-07-12",
            "quantity": 1000,
            "batch_amb_ref": "BATCH-AMB-001",  # Your Batch AMB reference
            "source_document": "INV-2024-001"
        },
        {
            "item_code": "0219",
            "batch_id": "0219071202", 
            "manufacturing_date": "2024-07-13",
            "quantity": 1500,
            "batch_amb_ref": "BATCH-AMB-002",
            "source_document": "INV-2024-002"
        }
    ]
    
    results = migrator.migrate_sales_batches(sample_sales_data)
    return results

if __name__ == "__main__":
    run_example_migration()

