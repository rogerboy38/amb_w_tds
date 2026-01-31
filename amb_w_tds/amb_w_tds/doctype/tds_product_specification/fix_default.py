import json

with open('tds_product_specification.json', 'r') as f:
    data = json.load(f)

# Find and fix version field
for field in data.get('fields', []):
    if field.get('fieldname') == 'version':
        print(f"Found version field")
        print(f"  Before: default={field.get('default')} (type: {type(field.get('default'))})")
        
        # Fix default to string
        field['default'] = "1.00"
        
        # Also consider making it editable (not read_only) if needed
        # field['read_only'] = 0
        
        print(f"  After: default={field['default']}")
        break

# Write back
with open('tds_product_specification.json', 'w') as f:
    json.dump(data, f, indent=1)

print("✓ Fixed version field default")
