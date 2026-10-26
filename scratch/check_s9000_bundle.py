import json
import hashlib
from pathlib import Path

p = Path('data/mitre/enterprise-attack.json')
h = hashlib.sha256(p.read_bytes()).hexdigest()
size = p.stat().st_size
print(f"enterprise-attack.json: size={size}, sha256={h}")

with open(p, 'r', encoding='utf-8') as f:
    bundle = json.load(f)

print(f"Total objects in bundle: {len(bundle.get('objects', []))}")
s9000_objs = []
for obj in bundle.get('objects', []):
    ext_refs = obj.get('external_references', [])
    for ref in ext_refs:
        eid = ref.get('external_id', '')
        if eid.startswith('S900'):
            s9000_objs.append((eid, obj.get('name'), obj.get('type'), obj.get('id'), obj.get('created'), obj.get('modified')))

print(f"Found {len(s9000_objs)} S9000 objects directly in enterprise-attack.json:")
for x in s9000_objs[:10]:
    print(" ", x)
