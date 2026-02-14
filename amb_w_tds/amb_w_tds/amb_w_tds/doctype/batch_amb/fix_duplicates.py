import json
import sys

# Read the JSON file
with open('batch_amb.json', 'r') as f:
    data = json.load(f)

if 'fields' not in data:
    print("No 'fields' array found in JSON")
    sys.exit(1)

# Find and remove duplicate planned_qty fields
fields = data['fields']
planned_qty_count = 0
planned_qty_indices = []

# Find all planned_qty fields
for i, field in enumerate(fields):
    if field.get('fieldname') == 'planned_qty':
        planned_qty_count += 1
        planned_qty_indices.append(i)

print(f"Found {planned_qty_count} 'planned_qty' fields at indices: {planned_qty_indices}")

if planned_qty_count > 1:
    # Keep the first one, remove the rest
    print(f"Keeping field at index {planned_qty_indices[0]}, removing duplicates...")
    
    # Remove duplicates (starting from the last to avoid index shifting)
    for idx in reversed(planned_qty_indices[1:]):
        removed_field = fields.pop(idx)
        print(f"Removed duplicate at index {idx}: label='{removed_field.get('label')}'")
    
    # Update the data
    data['fields'] = fields
    
    # Write back to file
    with open('batch_amb.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Fixed! Now only {len([f for f in fields if f.get('fieldname') == 'planned_qty'])} planned_qty field(s)")
    
    # Also check for other potential duplicates
    fieldnames = {}
    duplicates_found = False
    
    for i, field in enumerate(fields):
        fieldname = field.get('fieldname')
        if fieldname:
            if fieldname in fieldnames:
                print(f"WARNING: Duplicate fieldname '{fieldname}' found at positions {fieldnames[fieldname]} and {i+1}")
                duplicates_found = True
            else:
                fieldnames[fieldname] = [i+1]
    
    if not duplicates_found:
        print("No other duplicate fieldnames found.")
else:
    print("No duplicate planned_qty fields found in JSON.")

