
import json
import os

input_file = r'C:\Users\ravi2\.gemini\antigravity\brain\36677ecd-9b96-4863-a859-553d4ca02b78\.system_generated\steps\334\content.md'
output_file = r'd:\geoalloc-env\geoalloc-env\geoaloc\app\data\countries.json'

os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Skip the first few lines which are not JSON
    json_str = "".join(lines[4:])

try:
    data = json.loads(json_str)
    mapping = {}
    for country in data:
        name = country.get('name', {}).get('common')
        latlng = country.get('latlng')
        if name and latlng and len(latlng) == 2:
            mapping[name] = latlng
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
    print(f"Successfully wrote {len(mapping)} countries to {output_file}")
except Exception as e:
    print(f"Error: {e}")
