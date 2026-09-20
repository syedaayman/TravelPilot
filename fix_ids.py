import re
import uuid
import sys

filepath = r'c:\Users\DELL\Desktop\TravelPilot\backend\app\db\seed_data.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of IDs.
pattern = r'\"(dest-[^\"]+|place-[^\"]+|hotel-[^\"]+|rest-[^\"]+|trans-opt-[^\"]+|leg-[^\"]+)\"'
matches = re.findall(pattern, content)

unique_ids = sorted(list(set(matches)))

# Generate deterministic UUIDs
id_map = {}
for old_id in unique_ids:
    id_map[old_id] = str(uuid.uuid5(uuid.NAMESPACE_OID, old_id))

# Replace in content
new_content = content
for old_id, new_id in id_map.items():
    new_content = new_content.replace(f'\"{old_id}\"', f'\"{new_id}\"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'Replaced {len(id_map)} unique IDs.')
