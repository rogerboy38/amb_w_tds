"""
Seed Data for Container Selection Phase B
Creates initial plant configurations, container rules, and sample data
"""

import frappe
import json

def create_seed_data():
    """Create comprehensive seed data for the container management system"""
    
    print("Creating seed data for Container Selection Phase B...")
    
    # Create plant configurations with detailed rules
    create_detailed_plant_configs()
    
    # Create sample container items
    create_container_items()
    
    # Create sample containers for testing
    create_sample_containers()
    
    # Create juice conversion configurations
    create_juice_conversion_configs()
    
    # Create sample sync logs for demonstration
    create_sample_sync_logs()
    
    print("Seed data creation completed successfully!")

def create_detailed_plant_configs():
    """Create detailed plant configurations with container rules"""
    
    plant_configs = [
        {
            'plant_name': 'Juice',
            'plant_code': 'JCE',
            'is_active': 1,
            'location': 'Building A - East Wing',
            'operating_hours': '6:00 AM - 10:00 PM',
            'min_fill_threshold': 10.0,
            'max_fill_threshold': 95.0,
            'weight_tolerance_percentage': 1.0,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 5,
            'default_tara_weights': json.dumps({
                "220L Barrel": 15.0,
                "1000L IBC": 45.0,
                "20L Pail": 2.5
            }),
            'container_rules': [
                {
                    'container_type': '220L Barrel',
                    'capacity': 220.0,
                    'tara_weight': 15.0,
                    'is_reusable': 1,
                    'max_reuse_count': 50,
                    'cleaning_required': 1
                },
                {
                    'container_type': '1000L IBC',
                    'capacity': 1000.0,
                    'tara_weight': 45.0,
                    'is_reusable': 1,
                    'max_reuse_count': 100,
                    'cleaning_required': 1
                }
            ],
            'juice_conversion_rules': [
                {
                    'target_concentration': '30X',
                    'min_brix': 60.0,
                    'max_brix': 70.0,
                    'conversion_factor': 30.0,
                    'yield_percentage': 85.0,
                    'notes': 'Standard 30X concentration for export'
                },
                {
                    'target_concentration': '1X',
                    'min_brix': 10.0,
                    'max_brix': 15.0,
                    'conversion_factor': 1.0,
                    'yield_percentage': 95.0,
                    'notes': 'Ready-to-drink concentration'
                },
                {
                    'target_concentration': '60X',
                    'min_brix': 65.0,
                    'max_brix': 75.0,
                    'conversion_factor': 60.0,
                    'yield_percentage': 80.0,
                    'notes': 'Ultra-concentrated for bulk export'
                }
            ]
        },
        {
            'plant_name': 'Dry',
            'plant_code': 'DRY',
            'is_active': 1,
            'location': 'Building B - West Wing',
            'operating_hours': '7:00 AM - 9:00 PM',
            'min_fill_threshold': 15.0,
            'max_fill_threshold': 98.0,
            'weight_tolerance_percentage': 2.0,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 10,
            'default_tara_weights': json.dumps({
                "Industrial Bag": 0.5,
                "20L Pail": 2.5
            }),
            'container_rules': [
                {
                    'container_type': 'Industrial Bag',
                    'capacity': 25.0,
                    'tara_weight': 0.5,
                    'is_reusable': 0,
                    'max_reuse_count': 1,
                    'cleaning_required': 0
                },
                {
                    'container_type': '20L Pail',
                    'capacity': 20.0,
                    'tara_weight': 2.5,
                    'is_reusable': 1,
                    'max_reuse_count': 20,
                    'cleaning_required': 1
                }
            ]
        },
        {
            'plant_name': 'Mix',
            'plant_code': 'MIX',
            'is_active': 1,
            'location': 'Building C - Central',
            'operating_hours': '6:30 AM - 9:30 PM',
            'min_fill_threshold': 12.0,
            'max_fill_threshold': 96.0,
            'weight_tolerance_percentage': 1.5,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 7,
            'default_tara_weights': json.dumps({
                "Industrial Bag": 0.5,
                "20L Pail": 2.5,
                "50L Drum": 8.0
            }),
            'container_rules': [
                {
                    'container_type': 'Industrial Bag',
                    'capacity': 25.0,
                    'tara_weight': 0.5,
                    'is_reusable': 0,
                    'max_reuse_count': 1,
                    'cleaning_required': 0
                },
                {
                    'container_type': '20L Pail',
                    'capacity': 20.0,
                    'tara_weight': 2.5,
                    'is_reusable': 1,
                    'max_reuse_count': 25,
                    'cleaning_required': 1
                },
                {
                    'container_type': '50L Drum',
                    'capacity': 50.0,
                    'tara_weight': 8.0,
                    'is_reusable': 1,
                    'max_reuse_count': 30,
                    'cleaning_required': 1
                }
            ]
        },
        {
            'plant_name': 'Lab',
            'plant_code': 'LAB',
            'is_active': 1,
            'location': 'Building D - Quality Control',
            'operating_hours': '8:00 AM - 6:00 PM',
            'min_fill_threshold': 5.0,
            'max_fill_threshold': 99.0,
            'weight_tolerance_percentage': 0.5,
            'auto_sync_enabled': 1,
            'sync_interval_minutes': 15,
            'default_tara_weights': json.dumps({
                "Laboratory Bottle": 0.1,
                "20L Pail": 2.5,
                "Sample Vial": 0.05
            }),
            'container_rules': [
                {
                    'container_type': 'Laboratory Bottle',
                    'capacity': 1.0,
                    'tara_weight': 0.1,
                    'is_reusable': 1,
                    'max_reuse_count': 50,
                    'cleaning_required': 1
                },
                {
                    'container_type': '20L Pail',
                    'capacity': 20.0,
                    'tara_weight': 2.5,
                    'is_reusable': 1,
                    'max_reuse_count': 15,
                    'cleaning_required': 1
                },
                {
                    'container_type': 'Sample Vial',
                    'capacity': 0.1,
                    'tara_weight': 0.05,
                    'is_reusable': 1,
                    'max_reuse_count': 100,
                    'cleaning_required': 1
                }
            ]
        }
    ]
    
    for plant_data in plant_configs:
        plant_name = plant_data['plant_name']
        
        if frappe.db.exists('Plant Configuration', plant_name):
            print(f"Plant configuration for {plant_name} already exists, skipping...")
            continue
        
        try:
            # Create plant configuration
            plant_config = frappe.new_doc('Plant Configuration')
            
            # Set basic fields
            for key, value in plant_data.items():
                if key not in ['container_rules', 'juice_conversion_rules']:
                    setattr(plant_config, key, value)
            
            # Add container rules
            for rule_data in plant_data.get('container_rules', []):
                plant_config.append('container_rules', rule_data)
            
            # Add juice conversion rules
            for rule_data in plant_data.get('juice_conversion_rules', []):
                plant_config.append('juice_conversion_rules', rule_data)
            
            plant_config.insert()
            print(f"Created detailed plant configuration for {plant_name}")
            
        except Exception as e:
            print(f"Error creating plant config for {plant_name}: {str(e)}")

def create_container_items():
    """Create comprehensive container item catalog"""
    
    container_items = [
        {
            'item_code': 'CNT-220L-BARREL',
            'item_name': '220L Barrel',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 15.0,
            'standard_rate': 45.00,
            'description': 'Standard 220 liter barrel for juice storage and transportation'
        },
        {
            'item_code': 'CNT-1000L-IBC',
            'item_name': '1000L IBC',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 45.0,
            'standard_rate': 180.00,
            'description': 'Intermediate Bulk Container 1000L for bulk liquid storage'
        },
        {
            'item_code': 'CNT-20L-PAIL',
            'item_name': '20L Pail',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 2.5,
            'standard_rate': 12.00,
            'description': 'Standard 20 liter pail for dry and mix products'
        },
        {
            'item_code': 'CNT-IND-BAG',
            'item_name': 'Industrial Bag',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 0.5,
            'standard_rate': 2.50,
            'description': 'Industrial grade storage bag for dry products, single-use'
        },
        {
            'item_code': 'CNT-50L-DRUM',
            'item_name': '50L Drum',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 8.0,
            'standard_rate': 25.00,
            'description': '50 liter drum for medium volume liquid storage'
        },
        {
            'item_code': 'CNT-LAB-BOTTLE',
            'item_name': 'Laboratory Bottle',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 0.1,
            'standard_rate': 5.00,
            'description': 'Laboratory sample bottle for quality control samples'
        },
        {
            'item_code': 'CNT-SAMPLE-VIAL',
            'item_name': 'Sample Vial',
            'item_group': 'Containers',
            'stock_uom': 'Nos',
            'is_stock_item': 1,
            'maintain_stock': 1,
            'weight_per_unit': 0.05,
            'standard_rate': 1.50,
            'description': 'Small sample vial for micro-sampling and testing'
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
    
    created_items = []
    for item_data in container_items:
        if not frappe.db.exists('Item', item_data['item_code']):
            try:
                item = frappe.new_doc('Item')
                for key, value in item_data.items():
                    setattr(item, key, value)
                
                item.insert()
                created_items.append(item_data['item_code'])
                print(f"Created container item: {item_data['item_code']} - {item_data['item_name']}")
            except Exception as e:
                print(f"Error creating item {item_data['item_code']}: {str(e)}")
        else:
            print(f"Container item {item_data['item_code']} already exists")
    
    return created_items

def create_sample_containers():
    """Create sample container selection records for testing"""
    
    sample_containers = [
        # Juice Plant Containers
        {
            'container_id': 'JCE-BARREL-001',
            'serial_number': 'JCE-220L-20250001',
            'container_type': 'CNT-220L-BARREL',
            'plant': 'Juice',
            'lifecycle_status': 'Available',
            'tara_weight': 15.0,
            'expected_weight': 200.0,
            'quality_check_status': 'Passed'
        },
        {
            'container_id': 'JCE-BARREL-002',
            'serial_number': 'JCE-220L-20250002',
            'container_type': 'CNT-220L-BARREL',
            'plant': 'Juice',
            'lifecycle_status': 'Available',
            'tara_weight': 15.0,
            'expected_weight': 200.0,
            'quality_check_status': 'Passed'
        },
        {
            'container_id': 'JCE-IBC-001',
            'serial_number': 'JCE-1000L-20250001',
            'container_type': 'CNT-1000L-IBC',
            'plant': 'Juice',
            'lifecycle_status': 'Available',
            'tara_weight': 45.0,
            'expected_weight': 950.0,
            'quality_check_status': 'Passed'
        },
        
        # Dry Plant Containers
        {
            'container_id': 'DRY-BAG-001',
            'serial_number': 'DRY-BAG-20250001',
            'container_type': 'CNT-IND-BAG',
            'plant': 'Dry',
            'lifecycle_status': 'Available',
            'tara_weight': 0.5,
            'expected_weight': 24.0,
            'quality_check_status': 'Passed'
        },
        {
            'container_id': 'DRY-PAIL-001',
            'serial_number': 'DRY-20L-20250001',
            'container_type': 'CNT-20L-PAIL',
            'plant': 'Dry',
            'lifecycle_status': 'Available',
            'tara_weight': 2.5,
            'expected_weight': 18.0,
            'quality_check_status': 'Passed'
        },
        
        # Mix Plant Containers
        {
            'container_id': 'MIX-DRUM-001',
            'serial_number': 'MIX-50L-20250001',
            'container_type': 'CNT-50L-DRUM',
            'plant': 'Mix',
            'lifecycle_status': 'Available',
            'tara_weight': 8.0,
            'expected_weight': 45.0,
            'quality_check_status': 'Passed'
        },
        
        # Lab Containers
        {
            'container_id': 'LAB-BOTTLE-001',
            'serial_number': 'LAB-1L-20250001',
            'container_type': 'CNT-LAB-BOTTLE',
            'plant': 'Lab',
            'lifecycle_status': 'Available',
            'tara_weight': 0.1,
            'expected_weight': 0.9,
            'quality_check_status': 'Passed'
        },
        {
            'container_id': 'LAB-VIAL-001',
            'serial_number': 'LAB-VIAL-20250001',
            'container_type': 'CNT-SAMPLE-VIAL',
            'plant': 'Lab',
            'lifecycle_status': 'Available',
            'tara_weight': 0.05,
            'expected_weight': 0.08,
            'quality_check_status': 'Passed'
        },
        
        # Some containers with different statuses for testing
        {
            'container_id': 'JCE-BARREL-003',
            'serial_number': 'JCE-220L-20250003',
            'container_type': 'CNT-220L-BARREL',
            'plant': 'Juice',
            'lifecycle_status': 'In_Use',
            'tara_weight': 15.0,
            'gross_weight': 210.0,
            'net_weight': 195.0,
            'expected_weight': 200.0,
            'weight_variance_percentage': 2.5,
            'is_within_tolerance': 0,
            'quality_check_status': 'Passed',
            'notes': 'Currently in production batch JB-2025-001'
        },
        {
            'container_id': 'DRY-BAG-002',
            'serial_number': 'DRY-BAG-20250002',
            'container_type': 'CNT-IND-BAG',
            'plant': 'Dry',
            'lifecycle_status': 'Completed',
            'tara_weight': 0.5,
            'gross_weight': 24.2,
            'net_weight': 23.7,
            'expected_weight': 24.0,
            'weight_variance_percentage': 1.25,
            'is_within_tolerance': 0,
            'fill_percentage': 94.8,
            'is_partial_fill': 0,
            'quality_check_status': 'Passed'
        }
    ]
    
    created_containers = []
    for container_data in sample_containers:
        if not frappe.db.exists('Container Selection', {'container_id': container_data['container_id']}):
            try:
                container = frappe.new_doc('Container Selection')
                for key, value in container_data.items():
                    setattr(container, key, value)
                
                # Set default values
                container.sync_status = 'Not_Synced'
                container.created_by_user = 'Administrator'
                
                container.insert()
                created_containers.append(container_data['container_id'])
                print(f"Created sample container: {container_data['container_id']}")
            except Exception as e:
                print(f"Error creating container {container_data['container_id']}: {str(e)}")
        else:
            print(f"Container {container_data['container_id']} already exists")
    
    return created_containers

def create_juice_conversion_configs():
    """Create additional juice conversion configurations for different scenarios"""
    
    # This is handled in the plant configurations above
    # But we can add more detailed configurations here if needed
    print("Juice conversion configurations created as part of plant configurations")

def create_sample_sync_logs():
    """Create sample sync logs for demonstration"""
    
    # Get some container names for sync logs
    containers = frappe.get_all('Container Selection', 
                              fields=['name', 'container_id'], 
                              limit=5)
    
    if not containers:
        print("No containers found for creating sample sync logs")
        return
    
    sample_sync_logs = [
        {
            'container_selection': containers[0]['name'],
            'sync_direction': 'CS_to_Batch',
            'sync_status': 'Success',
            'sync_timestamp': '2025-11-01 14:30:00',
            'synced_fields': json.dumps({
                'gross_weight': 210.0,
                'net_weight': 195.0,
                'lifecycle_status': 'In_Use'
            }),
            'sync_result': json.dumps({
                'success': True,
                'message': 'Container successfully synced to Batch AMB'
            })
        },
        {
            'container_selection': containers[1]['name'] if len(containers) > 1 else containers[0]['name'],
            'sync_direction': 'Bidirectional',
            'sync_status': 'Success',
            'sync_timestamp': '2025-11-01 15:45:00',
            'synced_fields': json.dumps({
                'gross_weight': 24.2,
                'net_weight': 23.7,
                'lifecycle_status': 'Completed'
            }),
            'sync_result': json.dumps({
                'success': True,
                'message': 'Bidirectional sync completed successfully'
            })
        }
    ]
    
    created_logs = []
    for log_data in sample_sync_logs:
        try:
            sync_log = frappe.new_doc('Container Sync Log')
            for key, value in log_data.items():
                setattr(sync_log, key, value)
            
            sync_log.insert()
            created_logs.append(sync_log.name)
            print(f"Created sample sync log: {sync_log.name}")
        except Exception as e:
            print(f"Error creating sync log: {str(e)}")
    
    return created_logs

def verify_seed_data():
    """Verify that seed data was created successfully"""
    
    print("\n=== Seed Data Verification ===")
    
    # Check plant configurations
    plant_count = frappe.db.count('Plant Configuration')
    print(f"✓ {plant_count} plant configurations created")
    
    # Check container items
    container_item_count = frappe.db.count('Item', {'item_group': 'Containers'})
    print(f"✓ {container_item_count} container items created")
    
    # Check sample containers
    container_count = frappe.db.count('Container Selection')
    print(f"✓ {container_count} sample containers created")
    
    # Check status distribution
    status_distribution = frappe.db.sql("""
        SELECT lifecycle_status, COUNT(*) as count
        FROM `tabContainer Selection`
        GROUP BY lifecycle_status
    """, as_dict=True)
    
    print("✓ Container status distribution:")
    for status in status_distribution:
        print(f"   - {status.lifecycle_status}: {status.count}")
    
    # Check sync logs
    sync_log_count = frappe.db.count('Container Sync Log')
    print(f"✓ {sync_log_count} sample sync logs created")
    
    print("=== Seed Data Verification Complete ===\n")

if __name__ == '__main__':
    create_seed_data()
    verify_seed_data()