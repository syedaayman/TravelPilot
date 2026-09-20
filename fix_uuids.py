import os
import re

files = [
    r'backend\app\services\trip_service.py',
    r'backend\app\services\simulation_service.py',
    r'backend\app\services\disruption_service.py',
    r'backend\app\core\simulation_engine.py',
    r'backend\app\core\disruption_engine.py'
]

pattern = re.compile(r'id=f[\"\'][^\"\']*[\"\']')
pattern2 = re.compile(r'(trip_id|replan_id|simulation_id|disruption_id)\s*=\s*f[\"\'][^\"\']*[\"\']')

for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = pattern.sub('id=str(uuid4())', content)
        new_content = pattern2.sub(r'\1 = str(uuid4())', new_content)
        
        if content != new_content:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Updated {file}')
