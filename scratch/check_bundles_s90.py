import json
from pathlib import Path

for b_name in ['enterprise-attack.json', 'ics-attack.json', 'mobile-attack.json']:
    p = Path('data/mitre') / b_name
    with open(p, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
    s90 = []
    for obj in bundle.get('objects', []):
        for ref in obj.get('external_references', []):
            eid = ref.get('external_id', '')
            if eid.startswith('S90'):
                s90.append((eid, obj.get('name'), obj.get('type')))
    print(f"{b_name}: {len(s90)} S90xx objects")
