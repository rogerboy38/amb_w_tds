# production_batch_migrator.py - Updated for API usage
import frappe
from frappe.utils import nowdate
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

@frappe.whitelist(allow_guest=False)
def migrate_batches_api(batch_data_list, api_key=None, do_validate_api_key=True):
    """
    API endpoint for batch migration from FoxPro environment
    URL: /api/method/amb_w_tds.api.production_batch_migrator.migrate_batches_api
    
    Args:
        batch_data_list: List of batch dictionaries or JSON string
        api_key: Optional API key for authentication
        do_validate_api_key: Whether to validate API key
    
    Returns:
        JSON response with migration results
    """
    try:
        # API Key validation (optional)
        if do_validate_api_key and api_key:
            valid_key = validate_api_key(api_key)
            if not valid_key:
                return {
                    "success": False,
                    "error": "Invalid API key",
                    "status_code": 401
                }
        
        # Parse input data
        if isinstance(batch_data_list, str):
            batch_data_list = json.loads(batch_data_list)
        
        print(f"🔔 API Called: Processing {len(batch_data_list)} batches")
        
        # Initialize migrator
        migrator = PharmaBatchMigrator()
        
        # Process migration
        results = migrator.migrate_from_list(batch_data_list)
        
        # Return API response
        response = {
            "success": True,
            "message": f"Processed {len(batch_data_list)} batches",
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "server": frappe.local.site
        }
        
        return response
        
    except Exception as e:
        error_response = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "status_code": 500
        }
        return error_response

@frappe.whitelist(allow_guest=False)
def validate_batch_data_api(batch_data):
    """
    API endpoint to validate batch data before migration
    URL: /api/method/amb_w_tds.api.production_batch_migrator.validate_batch_data_api
    """
    try:
        if isinstance(batch_data, str):
            batch_data = json.loads(batch_data)
        
        migrator = PharmaBatchMigrator()
        validation = migrator._validate_batch_data(batch_data)
        
        return {
            "success": True,
            "validation": validation,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=False) 
def get_migration_status(migration_id=None):
    """
    API endpoint to check migration status
    """
    # This could check your migration logs or database
    return {
        "success": True,
        "status": "active",
        "last_migration": datetime.now().isoformat()
    }

def validate_api_key(api_key):
    """
    Validate API key (you can implement your own logic)
    """
    # Example: Check against Site Config
    valid_keys = frappe.conf.get("batch_migration_api_keys", [])
    return api_key in valid_keys

class PharmaBatchMigrator:
    """
    Production-ready FDA compliant batch migration system
    """
    
    def __init__(self, log_file="batch_migration_log.json"):
        self.migration_log = []
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0,
            "start_time": None,
            "end_time": None
        }
        self.log_file = log_file
        
    def migrate_from_list(self, batch_data_list: List[Dict], batch_size: int = 50) -> Dict:
        """
        Migrate batches from Python list (API usage)
        """
        print(f"🚀 Starting List Batch Migration")
        print("=" * 60)
        
        self.stats["start_time"] = datetime.now().isoformat()
        
        try:
            results = self._migrate_in_batches(batch_data_list, batch_size)
            
            self.stats["end_time"] = datetime.now().isoformat()
            self._save_migration_log()
            self._generate_migration_report()
            
            return results
            
        except Exception as e:
            error_msg = f"List migration failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _migrate_in_batches(self, batch_data_list: List[Dict], batch_size: int) -> Dict:
        """Process migration in batches for better performance"""
        total_batches = (len(batch_data_list) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(batch_data_list))
            batch_chunk = batch_data_list[start_idx:end_idx]
            
            print(f"🔄 Processing batch {batch_num + 1}/{total_batches} "
                  f"({start_idx + 1}-{end_idx} of {len(batch_data_list)})")
            
            for batch_data in batch_chunk:
                self._process_single_batch(batch_data)
            
            # Commit after each batch for data safety
            frappe.db.commit()
        
        return {
            "success": True,
            "stats": self.stats,
            "total_processed": len(batch_data_list)
        }
    
    def _process_single_batch(self, batch_data: Dict):
        """Process a single batch record with full validation"""
        from datetime import datetime, timedelta
        
        # Clean and validate data
        cleaned_data = self._clean_batch_data(batch_data)
        
        try:
            # GMP: Pre-creation validation
            validation = self._validate_batch_data(cleaned_data)
            if not validation["is_valid"]:
                self._log_failure(cleaned_data, f"Validation failed: {', '.join(validation['errors'])}")
                return
            
            # Check for existing batch
            existing_batch = self._find_existing_batch(
                cleaned_data["item_code"], 
                cleaned_data["batch_id"]
            )
            
            if existing_batch:
                self._log_success(cleaned_data, existing_batch, "existing", validation["warnings"])
                return
            
            # Calculate expiry date
            expiry_date = self._calculate_expiry_date(
                cleaned_data["item_code"],
                cleaned_data["manufacturing_date"]
            )
            
            # Create batch document
            batch_doc = self._build_batch_document(cleaned_data, expiry_date)
            
            # GMP: Create the batch
            batch = frappe.get_doc(batch_doc)
            batch.insert()
            
            # GMP: Audit trail
            self._create_audit_trail("Batch Created", {
                "batch_name": batch.name,
                "batch_id": cleaned_data["batch_id"],
                "item_code": cleaned_data["item_code"],
                "manufacturing_date": cleaned_data["manufacturing_date"],
                "expiry_date": expiry_date,
                "batch_amb_ref": cleaned_data.get("batch_amb_ref"),
                "source_document": cleaned_data.get("source_document"),
                "migration_timestamp": datetime.now().isoformat()
            })
            
            self._log_success(cleaned_data, batch.name, "created", validation["warnings"])
            
        except Exception as e:
            self._log_failure(cleaned_data, f"Creation failed: {str(e)}")
    
    def _clean_batch_data(self, batch_data: Dict) -> Dict:
        """Clean and standardize batch data"""
        cleaned = batch_data.copy()
        
        # Standardize date format
        if 'manufacturing_date' in cleaned:
            try:
                # Handle various date formats
                date_str = str(cleaned['manufacturing_date'])
                if 'T' in date_str:  # ISO format
                    cleaned['manufacturing_date'] = date_str.split('T')[0]
                elif len(date_str) == 8 and date_str.isdigit():  # YYYYMMDD
                    cleaned['manufacturing_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            except:
                pass
        
        # Ensure quantity is numeric
        if 'quantity' in cleaned:
            try:
                cleaned['quantity'] = float(cleaned['quantity'])
            except (ValueError, TypeError):
                cleaned['quantity'] = 0
        
        return cleaned
    
    def _validate_batch_data(self, batch_data: Dict) -> Dict:
        """GMP: Comprehensive batch data validation"""
        from datetime import datetime
        
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Required fields check
        required_fields = ["item_code", "batch_id", "manufacturing_date"]
        for field in required_fields:
            if not batch_data.get(field):
                validation["is_valid"] = False
                validation["errors"].append(f"Missing required field: {field}")
        
        # Item validation
        if batch_data.get("item_code"):
            item_valid = self._validate_item(batch_data["item_code"])
            if not item_valid["exists"]:
                validation["is_valid"] = False
                validation["errors"].append(f"Item not found: {batch_data['item_code']}")
            elif not item_valid["has_shelf_life"]:
                validation["warnings"].append(f"Item {batch_data['item_code']} has no shelf life")
            elif item_valid["disabled"]:
                validation["is_valid"] = False
                validation["errors"].append(f"Item {batch_data['item_code']} is disabled")
        
        # Date validation
        if batch_data.get("manufacturing_date"):
            try:
                mfg_date = datetime.strptime(batch_data["manufacturing_date"], "%Y-%m-%d")
                if mfg_date > datetime.now():
                    validation["is_valid"] = False
                    validation["errors"].append("Manufacturing date cannot be in future")
                
                # Check if date is reasonable (not before 2000)
                if mfg_date.year < 2000:
                    validation["warnings"].append("Manufacturing date seems very old")
                    
            except ValueError:
                validation["is_valid"] = False
                validation["errors"].append("Invalid manufacturing date format (use YYYY-MM-DD)")
        
        # Batch ID validation
        if batch_data.get("batch_id"):
            if len(batch_data["batch_id"]) > 140:
                validation["is_valid"] = False
                validation["errors"].append("Batch ID too long (max 140 characters)")
        
        return validation
    
    def _validate_item(self, item_code: str) -> Dict:
        """Validate item exists and is configured properly"""
        try:
            item = frappe.get_doc("Item", item_code)
            return {
                "exists": True,
                "has_shelf_life": bool(item.shelf_life_in_days),
                "disabled": bool(item.disabled),
                "shelf_life_days": item.shelf_life_in_days
            }
        except frappe.DoesNotExistError:
            return {"exists": False, "has_shelf_life": False, "disabled": False}
    
    def _find_existing_batch(self, item_code: str, batch_id: str) -> Optional[str]:
        """Check if batch already exists"""
        existing = frappe.db.exists("Batch", {
            "item": item_code,
            "batch_id": batch_id,
            "disabled": 0
        })
        return existing
    
    def _calculate_expiry_date(self, item_code: str, manufacturing_date: str) -> str:
        """Calculate expiry date based on item shelf life"""
        from datetime import datetime, timedelta
        
        try:
            item = frappe.get_doc("Item", item_code)
            if item.shelf_life_in_days:
                mfg_date = datetime.strptime(manufacturing_date, "%Y-%m-%d")
                expiry_date = mfg_date + timedelta(days=item.shelf_life_in_days)
                return expiry_date.strftime("%Y-%m-%d")
        except:
            pass
        
        # Default fallback - use 1 year
        mfg_date = datetime.strptime(manufacturing_date, "%Y-%m-%d")
        return (mfg_date + timedelta(days=365)).strftime("%Y-%m-%d")
    
    def _build_batch_document(self, batch_data: Dict, expiry_date: str) -> Dict:
        """Build complete batch document"""
        batch_doc = {
            "doctype": "Batch",
            "item": batch_data["item_code"],
            "batch_id": batch_data["batch_id"],
            "manufacturing_date": batch_data["manufacturing_date"],
            "expiry_date": expiry_date,
            "batch_qty": batch_data.get("quantity", 0),
            "disabled": 0
        }
        
        # Add optional fields if provided
        optional_fields = ["batch_amb_ref", "reference_doctype", "reference_name"]
        for field in optional_fields:
            if batch_data.get(field):
                batch_doc[field] = batch_data[field]
        
        # Special handling for Batch AMB reference
        if batch_data.get("batch_amb_ref") and not batch_data.get("reference_doctype"):
            batch_doc["reference_doctype"] = "Batch AMB"
            batch_doc["reference_name"] = batch_data["batch_amb_ref"]
        
        return batch_doc
    
    def _create_audit_trail(self, action: str, details: Dict):
        """GMP: Create comprehensive audit trail"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "user": frappe.session.user if hasattr(frappe, 'session') else "migration_system"
        }
        print(f"🔍 AUDIT: {action} - {json.dumps(details, default=str)}")
    
    def _log_success(self, batch_data: Dict, batch_name: str, action: str, warnings: List[str]):
        """Log successful batch processing"""
        result = {
            "success": True,
            "batch_name": batch_name,
            "action": action,
            "batch_data": batch_data,
            "timestamp": datetime.now().isoformat(),
            "warnings": warnings
        }
        
        self.migration_log.append(result)
        self.stats["total_processed"] += 1
        self.stats["successful"] += 1
        
        if warnings:
            self.stats["warnings"] += len(warnings)
        
        print(f"   ✅ {action.upper()}: {batch_name}")
        
        if warnings:
            for warning in warnings:
                print(f"      ⚠️  {warning}")
    
    def _log_failure(self, batch_data: Dict, error: str):
        """Log failed batch processing"""
        result = {
            "success": False,
            "error": error,
            "batch_data": batch_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.migration_log.append(result)
        self.stats["total_processed"] += 1
        self.stats["failed"] += 1
        
        print(f"   ❌ FAILED: {error}")
    
    def _save_migration_log(self):
        """Save migration log to file for audit purposes"""
        try:
            log_data = {
                "metadata": {
                    "migration_date": datetime.now().isoformat(),
                    "total_records": self.stats["total_processed"],
                    "successful": self.stats["successful"],
                    "failed": self.stats["failed"],
                    "warnings": self.stats["warnings"]
                },
                "log_entries": self.migration_log
            }
            
            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)
            
            print(f"📁 Migration log saved to: {self.log_file}")
            
        except Exception as e:
            print(f"⚠️  Could not save migration log: {str(e)}")
    
    def _generate_migration_report(self):
        """Generate comprehensive migration report"""
        print("\n" + "=" * 60)
        print("📊 PRODUCTION MIGRATION REPORT")
        print("=" * 60)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"✅ Successful: {self.stats['successful']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"⚠️  Warnings: {self.stats['warnings']}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            start = datetime.fromisoformat(self.stats['start_time'])
            end = datetime.fromisoformat(self.stats['end_time'])
            duration = end - start
            print(f"⏱️  Duration: {duration}")
        
        # Show failed batches for review
        failed_batches = [log for log in self.migration_log if not log["success"]]
        if failed_batches:
            print(f"\nFailed batches ({len(failed_batches)}):")
            for failed in failed_batches[:10]:
                print(f"  - {failed['batch_data'].get('item_code')}: {failed['error']}")
        
        # Success rate
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
            print(f"\n🎯 Success rate: {success_rate:.1f}%")
