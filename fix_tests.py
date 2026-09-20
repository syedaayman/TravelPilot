import os
import re
import uuid

tests_dir = r'c:\Users\DELL\Desktop\TravelPilot\tests'

pattern = r'\"(dest-[^\"]+|place-[^\"]+|hotel-[^\"]+|rest-[^\"]+|trans-[^\"]+|leg-[^\"]+)\"'
pattern2 = r'\'(dest-[^\']+|place-[^\']+|hotel-[^\']+|rest-[^\']+|trans-[^\']+|leg-[^\']+)\''

count = 0
for root, dirs, files in os.walk(tests_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            matches = re.findall(pattern, content) + re.findall(pattern2, content)
            unique_ids = sorted(list(set(matches)))
            if not unique_ids:
                continue
                
            id_map = {}
            for old_id in unique_ids:
                id_map[old_id] = str(uuid.uuid5(uuid.NAMESPACE_OID, old_id))
            
            new_content = content
            for old_id, new_id in id_map.items():
                new_content = new_content.replace(f'\"{old_id}\"', f'\"{new_id}\"')
                new_content = new_content.replace(f'\'{old_id}\'', f'\"{new_id}\"')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            count += len(unique_ids)

print(f'Replaced {count} instances in tests.')
