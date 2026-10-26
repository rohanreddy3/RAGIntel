import json
from pathlib import Path

p = Path('data/mitre/enterprise-attack.json')
with open(p, 'r', encoding='utf-8') as f:
    bundle = json.load(f)

s9000_all = []
for obj in bundle.get('objects', []):
    for ref in obj.get('external_references', []):
        eid = ref.get('external_id', '')
        if eid.startswith('S90'):
            s9000_all.append((eid, obj.get('name'), obj.get('type'), obj.get('created'), obj.get('modified')))

print(f"Total S90xx objects in enterprise-attack.json: {len(s9000_all)}")
for x in sorted(s9000_all, key=lambda t: t[0])[:20]:
    print(" ", x)
