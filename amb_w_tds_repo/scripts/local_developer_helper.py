#!/usr/bin/env python3
"""
Local Frappe File Deployment Helper
For when you're running Frappe locally
"""

import os
import shutil
import sys
from pathlib import Path

# Fixed file location (our working copy)
FIXED_FILE = "/workspace/user_input_files/batch_amb_extracted/batch_amb/batch_amb_FIXED.py"

def find_frappe_directory():
    """Find local Frappe bench directory"""
    print("🔍 Searching for Frappe bench directory...")
    
    search_paths = [
        Path.home() / "frappe-bench",
        Path.home() / "bench",
        Path("/opt/frappe/bench"),
        Path("./bench"),
        Path("bench")
    ]
    
    found_paths = []
    for path in search_paths:
        if path.exists() and (path / "config").exists():
            print(f"✅ Found Frappe bench at: {path}")
            found_paths.append(path)
    
    return found_paths

def check_batch_amb_file(frappe_path):
    """Check if batch_amb.py exists and show its status"""
    print(f"\n📁 Checking batch_amb.py in {frappe_path}")
    
    batch_amb_path = frappe_path / "apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"
    
    if not batch_amb_path.exists():
        print(f"❌ batch_amb.py NOT FOUND at: {batch_amb_path}")
        return False
    
    # Get file stats
    stat = batch_amb_path.stat()
    line_count = sum(1 for _ in open(batch_amb_path, 'r', encoding='utf-8'))
    
    print(f"📊 File Status:")
    print(f"   Location: {batch_amb_path}")
    print(f"   Size: {stat.st_size:,} bytes")
    print(f"   Lines: {line_count}")
    print(f"   Modified: {stat.st_mtime}")
    
    # Check for our fixes
    content = batch_amb_path.read_text()
    
    has_planned_qty_fix = "planned_qty or batch.batch_quantity" in content
    has_sales_order_fix = "sales_order = batch.sales_order_related" in content
    
    print(f"🔍 Fix Verification:")
    print(f"   ✅ Planned Qty Fix: {'FOUND' if has_planned_qty_fix else 'MISSING'}")
    print(f"   ✅ Sales Order Fix: {'FOUND' if has_sales_order_fix else 'MISSING'}")
    
    if has_planned_qty_fix and has_sales_order_fix:
        print("🎉 ALL FIXES ARE PRESENT!")
        return True
    else:
        print("⚠️  FIXES ARE MISSING - DEPLOYING NEW FILE")
        return False

def deploy_fixed_file(frappe_path):
    """Deploy our fixed file to local Frappe"""
    print(f"\n🚀 Deploying fixed file to local Frappe...")
    
    batch_amb_path = frappe_path / "apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/batch_amb/batch_amb.py"
    
    try:
        # Create backup
        backup_path = batch_amb_path.with_suffix('.py.backup')
        if batch_amb_path.exists():
            shutil.copy2(batch_amb_path, backup_path)
            print(f"📋 Backup created: {backup_path}")
        
        # Copy fixed file
        shutil.copy2(FIXED_FILE, batch_amb_path)
        
        # Verify deployment
        new_line_count = sum(1 for _ in open(batch_amb_path, 'r', encoding='utf-8'))
        print(f"✅ File deployed successfully!")
        print(f"   New line count: {new_line_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

def main():
    """Main function"""
    print("🏠 LOCAL FRAPPE DEPLOYMENT HELPER")
    print("=" * 50)
    
    # Check if fixed file exists
    if not Path(FIXED_FILE).exists():
        print(f"❌ Fixed file not found at: {FIXED_FILE}")
        return False
    
    print(f"✅ Found fixed file: {FIXED_FILE}")
    
    # Find Frappe directories
    frappe_paths = find_frappe_directory()
    
    if not frappe_paths:
        print("❌ No Frappe bench directories found!")
        print("Please check your installation or run from your Frappe directory")
        return False
    
    # Process each Frappe installation
    for frappe_path in frappe_paths:
        print(f"\n{'='*50}")
        print(f"Processing: {frappe_path}")
        print(f"{'='*50}")
        
        # Check current file status
        fixes_present = check_batch_amb_file(frappe_path)
        
        if not fixes_present:
            # Deploy our fixes
            if deploy_fixed_file(frappe_path):
                print(f"\n🎉 DEPLOYMENT COMPLETE!")
                print(f"📝 Next steps:")
                print(f"   1. cd {frappe_path}")
                print(f"   2. bench restart")
                print(f"   3. Clear browser cache")
                print(f"   4. Test Create BOM widget")
            else:
                print(f"\n❌ Deployment failed!")
                return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n✅ ALL SET! Ready to test Create BOM widget")
    else:
        print(f"\n❌ Please check the output above for errors")
    sys.exit(0 if success else 1)
