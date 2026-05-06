"""
Migration Script for Container Selection Enhancement - Phase B
Adds new fields to existing Container Selection DocType
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Execute migration for Container Selection enhancement"""
    
    # Add custom fields to existing Container Selection DocType
    add_custom_fields_to_container_selection()
    
    # Update DocType permissions
    update_container_selection_permissions()
    
    # Create new DocTypes
    create_supporting_doctypes()
    
    # Create default plant configurations
    create_default_plant_configs()
    
    # Update existing containers with default values
    update_existing_containers()
    
    print("Container Selection Phase B migration completed successfully!")

def add_custom_fields_to_container_selection():
    """Add new fields to existing Container Selection DocType"""
    
    custom_fields = {
        'Container Selection': [
            # Weight tracking fields
            {
                'fieldname': 'section_break_weights',
                'fieldtype': 'Section Break',
                'label': 'Weight Tracking',
                'insert_after': 'completed_date'
            },
            {
                'fieldname': 'gross_weight',
                'fieldtype': 'Float',
                'label': 'Gross Weight (Kg)',
                'precision': 3,
                'insert_after': 'section_break_weights'
            },
            {
                'fieldname': 'tara_weight',
                'fieldtype': 'Float',
                'label': 'Tara Weight (Kg)',
                'precision': 3,
                'insert_after': 'gross_weight'
            },
            {
                'fieldname': 'net_weight',
                'fieldtype': 'Float',
                'label': 'Net Weight (Kg)',
                'precision': 3,
                'read_only': 1,
                'insert_after': 'tara_weight'
            },
            {
                'fieldname': 'expected_weight',
                'fieldtype': 'Float',
                'label': 'Expected Weight (Kg)',
                'precision': 3,
                'insert_after': 'net_weight'
            },
            {
                'fieldname': 'column_break_weights',
                'fieldtype': 'Column Break',
                'insert_after': 'expected_weight'
            },
            {
                'fieldname': 'weight_variance_percentage',
                'fieldtype': 'Float',
                'label': 'Weight Variance %',
                'precision': 2,
                'read_only': 1,
                'insert_after': 'column_break_weights'
            },
            {
                'fieldname': 'is_within_tolerance',
                'fieldtype': 'Check',
                'label': 'Within 1% Tolerance',
                'read_only': 1,
                'insert_after': 'weight_variance_percentage'
            },
            {
                'fieldname': 'fill_percentage',
                'fieldtype': 'Float',
                'label': 'Fill Percentage %',
                'precision': 2,
                'read_only': 1,
                'insert_after': 'is_within_tolerance'
            },
            {
                'fieldname': 'is_partial_fill',
                'fieldtype': 'Check',
                'label': 'Partial Fill',
                'read_only': 1,
                'insert_after': 'fill_percentage'
            },
            
            # Synchronization fields
            {
                'fieldname': 'section_break_sync',
                'fieldtype': 'Section Break',
                'label': 'Synchronization',
                'insert_after': 'is_partial_fill'
            },
            {
                'fieldname': 'sync_status',
                'fieldtype': 'Select',
                'label': 'Sync Status',
                'options': 'Not_Synced\nPending\nSynced\nError',
                'default': 'Not_Synced',
                'insert_after': 'section_break_sync'
            },
            {
                'fieldname': 'last_synced',
                'fieldtype': 'Datetime',
                'label': 'Last Synced',
                'read_only': 1,
                'insert_after': 'sync_status'
            },
            {
                'fieldname': 'sync_error',
                'fieldtype': 'Text',
                'label': 'Sync Error',
                'read_only': 1,
                'insert_after': 'last_synced'
            },
            {
                'fieldname': 'column_break_sync',
                'fieldtype': 'Column Break',
                'insert_after': 'sync_error'
            },
            {
                'fieldname': 'barcode_scanned_at',
                'fieldtype': 'Datetime',
                'label': 'Barcode Scanned At',
                'read_only': 1,
                'insert_after': 'column_break_sync'
            },
            {
                'fieldname': 'scanned_by',
                'fieldtype': 'Link',
                'label': 'Scanned By',
                'options': 'User',
                'read_only': 1,
                'insert_after': 'barcode_scanned_at'
            },
            {
                'fieldname': 'manual_sync_required',
                'fieldtype': 'Check',
                'label': 'Manual Sync Required',
                'insert_after': 'scanned_by'
            },
            
            # Additional tracking fields
            {
                'fieldname': 'section_break_tracking',
                'fieldtype': 'Section Break',
                'label': 'Additional Tracking',
                'insert_after': 'manual_sync_required'
            },
            {
                'fieldname': 'assigned_operator',
                'fieldtype': 'Link',
                'label': 'Assigned Operator',
                'options': 'User',
                'insert_after': 'section_break_tracking'
            },
            {
                'fieldname': 'quality_check_status',
                'fieldtype': 'Select',
                'label': 'Quality Check Status',
                'options': 'Pending\nPassed\nFailed\nN/A',
                'default': 'Pending',
                'insert_after': 'assigned_operator'
            },
            {
                'fieldname': 'column_break_tracking',
                'fieldtype': 'Column Break',
                'insert_after': 'quality_check_status'
            },
            {
                'fieldname': 'partial_fill_reason',
                'fieldtype': 'Data',
                'label': 'Partial Fill Reason',
                'read_only': 1,
                'insert_after': 'column_break_tracking'
            },
            {
                'fieldname': 'maintenance_notes',
                'fieldtype': 'Text',
                'label': 'Maintenance Notes',
                'insert_after': 'partial_fill_reason'
            }
        ]
    }
    
    create_custom_fields(custom_fields)
    print("Custom fields added to Container Selection DocType")

def update_container_selection_permissions():
    """Update permissions for Container Selection DocType"""
    
    # Add Manufacturing User role if not exists
    roles_to_add = [
        {
            'role': 'Manufacturing User',
            'permlevel': 0,
            'read': 1,
            'write': 1,
            'create': 1,
            'email': 1,
            'print': 1,
            'report': 1
        },
        {
            'role': 'Manufacturing Manager',
            'permlevel': 0,
            'read': 1,
            'write': 1,
            'create': 1,
            'delete': 1,
            'email': 1,
            'print': 1,
            'export': 1,
            'report': 1,
            'share': 1
        }
    ]
    
    doctype = frappe.get_doc('DocType', 'Container Selection')
    
    for role_perm in roles_to_add:
        # Check if permission already exists
        existing_perm = None
        for perm in doctype.permissions:
            if perm.role == role_perm['role'] and perm.permlevel == role_perm['permlevel']:
                existing_perm = perm
                break
        
        if not existing_perm:
            doctype.append('permissions', role_perm)
    
    doctype.save()
    print("Updated Container Selection permissions")

def create_supporting_doctypes():
    """Create new supporting DocTypes if they don't exist"""
    
    # List of DocTypes to create (these should already be created by the integration files)
    doctypes_to_check = [
        'Container Sync Log',
        'Plant Configuration',
        'Container Type Rule',
        'Juice Conversion Config'
    ]
    
    for doctype_name in doctypes_to_check:
        if not frappe.db.exists('DocType', doctype_name):
            print(f"Warning: {doctype_name} DocType not found. Please install from integration files.")
        else:
            print(f"{doctype_name} DocType verified")

def create_default_plant_configs():
    """Create default plant configurations"""
    
    default_plants = [
        {
            'plant_name': 'Juice',
            'plant_code': 'JCE',
            'is_active': 1,
            'min_fill_threshold': 10.0,
            'max_fill_threshold': 95.0,
            'weight_tolerance_percentage': 1.0,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 5,
            'default_tara_weights': '{"220L Barrel": 15.0, "1000L IBC": 45.0, "20L Pail": 2.5}'
        },
        {
            'plant_name': 'Dry',
            'plant_code': 'DRY',
            'is_active': 1,
            'min_fill_threshold': 10.0,
            'max_fill_threshold': 95.0,
            'weight_tolerance_percentage': 1.0,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 5,
            'default_tara_weights': '{"Industrial Bag": 0.5, "20L Pail": 2.5}'
        },
        {
            'plant_name': 'Mix',
            'plant_code': 'MIX',
            'is_active': 1,
            'min_fill_threshold': 10.0,
            'max_fill_threshold': 95.0,
            'weight_tolerance_percentage': 1.0,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 5,
            'default_tara_weights': '{"Industrial Bag": 0.5, "20L Pail": 2.5}'
        },
        {
            'plant_name': 'Lab',
            'plant_code': 'LAB',
            'is_active': 1,
            'min_fill_threshold': 10.0,
            'max_fill_threshold': 95.0,
            'weight_tolerance_percentage': 1.0,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 10,
            'default_tara_weights': '{"20L Pail": 2.5, "Laboratory Bottle": 0.1}'
        }
    ]
    
    for plant_data in default_plants:
        if not frappe.db.exists('Plant Configuration', plant_data['plant_name']):
            try:
                plant_config = frappe.new_doc('Plant Configuration')
                for key, value in plant_data.items():
                    setattr(plant_config, key, value)
                
                plant_config.insert()
                print(f"Created plant configuration for {plant_data['plant_name']}")
            except Exception as e:
                print(f"Error creating plant config for {plant_data['plant_name']}: {str(e)}")
        else:
            print(f"Plant configuration for {plant_data['plant_name']} already exists")

def update_existing_containers():
    """Update existing Container Selection records with default values"""
    
    # Get all existing containers without new fields
    existing_containers = frappe.get_all(
        'Container Selection',
        fields=['name', 'plant', 'container_type'],
        limit=1000
    )
    
    updated_count = 0
    
    for container_info in existing_containers:
        try:
            container = frappe.get_doc('Container Selection', container_info.name)
            
            # Set default values for new fields
            if not hasattr(container, 'sync_status') or not container.sync_status:
                container.sync_status = 'Not_Synced'
            
            if not hasattr(container, 'quality_check_status') or not container.quality_check_status:
                container.quality_check_status = 'Pending'
            
            if not hasattr(container, 'created_by_user') or not container.created_by_user:
                container.created_by_user = container.owner or 'Administrator'
            
            # Auto-calculate tara weight if not set
            if (not hasattr(container, 'tara_weight') or not container.tara_weight) and container.container_type:
                container.set_tara_weight_from_item()
            
            # Calculate weights if gross weight exists
            if hasattr(container, 'gross_weight') and container.gross_weight and container.tara_weight:
                container.calculate_weights()
            
            container.save()
            updated_count += 1
            
        except Exception as e:
            print(f"Error updating container {container_info.name}: {str(e)}")
    
    print(f"Updated {updated_count} existing containers with default values")

def create_container_items():
    """Create standard container items if they don't exist"""
    
    container_items = [
        {
            'item_code': 'E001',
            'item_name': '220L Barrel',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 15.0,
            'description': 'Standard 220 liter barrel for juice storage'
        },
        {
            'item_code': 'E002',
            'item_name': '20L Pail',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 2.5,
            'description': 'Standard 20 liter pail for dry/mix products'
        },
        {
            'item_code': 'E003',
            'item_name': '1000L IBC',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 45.0,
            'description': 'Intermediate Bulk Container 1000L'
        },
        {
            'item_code': 'E004',
            'item_name': 'Industrial Bag',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 0.5,
            'description': 'Industrial grade storage bag for dry products'
        },
        {
            'item_code': 'E005',
            'item_name': 'Laboratory Bottle',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 0.1,
            'description': 'Laboratory sample bottle'
        }
    ]
    
    # Create Containers item group if it doesn't exist
    if not frappe.db.exists('Item Group', 'Containers'):
        item_group = frappe.new_doc('Item Group')
        item_group.item_group_name = 'Containers'
        item_group.parent_item_group = 'All Item Groups'
        item_group.is_group = 0
        item_group.insert()
        print("Created Containers item group")
    
    # Create container items
    created_items = []
    for item_data in container_items:
        if not frappe.db.exists('Item', item_data['item_code']):
            try:
                item = frappe.new_doc('Item')
                for key, value in item_data.items():
                    setattr(item, key, value)
                
                item.insert()
                created_items.append(item_data['item_code'])
                print(f"Created item: {item_data['item_code']} - {item_data['item_name']}")
            except Exception as e:
                print(f"Error creating item {item_data['item_code']}: {str(e)}")
        else:
            print(f"Item {item_data['item_code']} already exists")
    
    return created_items

def verify_migration():
    """Verify that migration completed successfully"""
    
    print("\n=== Migration Verification ===")
    
    # Check custom fields
    container_meta = frappe.get_meta('Container Selection')
    required_fields = ['gross_weight', 'tara_weight', 'net_weight', 'sync_status', 'lifecycle_status']
    
    for field in required_fields:
        if container_meta.get_field(field):
            print(f"✓ Field '{field}' added successfully")
        else:
            print(f"✗ Field '{field}' missing")
    
    # Check DocTypes
    required_doctypes = ['Container Sync Log', 'Plant Configuration', 'Container Type Rule', 'Juice Conversion Config']
    for doctype in required_doctypes:
        if frappe.db.exists('DocType', doctype):
            print(f"✓ DocType '{doctype}' exists")
        else:
            print(f"✗ DocType '{doctype}' missing")
    
    # Check plant configurations
    plant_count = frappe.db.count('Plant Configuration')
    print(f"✓ {plant_count} plant configurations created")
    
    # Check container count
    container_count = frappe.db.count('Container Selection')
    print(f"✓ {container_count} containers available")
    
    print("=== Migration Verification Complete ===\n")

if __name__ == '__main__':
    execute()
    verify_migration()