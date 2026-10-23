import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_stix_all_bundles

bundle_files = [
    REPO_ROOT / "data" / "mitre" / "enterprise-attack.json",
    REPO_ROOT / "data" / "mitre" / "mobile-attack.json",
    REPO_ROOT / "data" / "mitre" / "ics-attack.json",
]

def get_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

print("=" * 80)
print("PART A7: STIX BUNDLE OBJECT COUNTS & RECONCILIATION AUDIT")
print("=" * 80)

domain_stats = {}
all_active_attack_patterns = {}
all_active_intrusion_sets = {}
all_active_malware = {}
all_active_tools = {}

for bf in bundle_files:
    fname = bf.name
    sha = get_sha256(bf)
    with open(bf, "r", encoding="utf-8") as f:
        data = json.load(f)

    # MITRE ATT&CK version from x-mitre-collection or identity or metadata
    objects = data.get("objects", [])
    version = "unknown"
    for o in objects:
        if o.get("type") in ["x-mitre-collection", "marking-definition"]:
            if "x_mitre_version" in o:
                version = f"v{o['x_mitre_version']}"
                break
            if "version" in o:
                version = f"v{o['version']}"
                break
    if version == "unknown":
        # Check first attack-pattern x_mitre_version or modified date
        for o in objects:
            if o.get("type") == "attack-pattern" and "x_mitre_version" in o:
                version = f"ATT&CK (spec {o.get('spec_version', '2.1')}, modified {o.get('modified', '')[:10]})"
                break

    # Count by type
    active_objs = [o for o in objects if not o.get("revoked", False) and not o.get("x_mitre_deprecated", False)]
    active_ap = [o for o in active_objs if o.get("type") == "attack-pattern"]
    active_is = [o for o in active_objs if o.get("type") == "intrusion-set"]
    active_mal = [o for o in active_objs if o.get("type") == "malware"]
    active_tool = [o for o in active_objs if o.get("type") == "tool"]

    parents = [o for o in active_ap if not o.get("x_mitre_is_subtechnique", False)]
    subs = [o for o in active_ap if o.get("x_mitre_is_subtechnique", False)]

    print(f"\nBundle: {fname}")
    print(f"  SHA-256: {sha}")
    print(f"  Version: {version}")
    print(f"  Total raw objects: {len(objects)}")
    print(f"  Active objects: {len(active_objs)}")
    print(f"  Active attack-patterns: {len(active_ap)} (Parents: {len(parents)}, Sub-techniques: {len(subs)})")
    print(f"  Active intrusion-sets: {len(active_is)}")
    print(f"  Active malware: {len(active_mal)}")
    print(f"  Active tools: {len(active_tool)}")

    domain_stats[fname] = {
        "sha256": sha,
        "version": version,
        "total_raw": len(objects),
        "active": len(active_objs),
        "active_ap": len(active_ap),
        "parents": len(parents),
        "subs": len(subs),
        "active_is": len(active_is),
        "active_malware": len(active_mal),
        "active_tools": len(active_tool),
    }

    # Dedup by STIX id across combined bundle
    for o in active_ap:
        all_active_attack_patterns[o["id"]] = o
    for o in active_is:
        all_active_intrusion_sets[o["id"]] = o
    for o in active_mal:
        all_active_malware[o["id"]] = o
    for o in active_tool:
        all_active_tools[o["id"]] = o

print("\n" + "=" * 80)
print("COMBINED DEDUPLICATED E0-STIX-ALL STATS:")
print("=" * 80)
comb_parents = [o for o in all_active_attack_patterns.values() if not o.get("x_mitre_is_subtechnique", False)]
comb_subs = [o for o in all_active_attack_patterns.values() if o.get("x_mitre_is_subtechnique", False)]
total_techniques = len(all_active_attack_patterns)
total_groups = len(all_active_intrusion_sets)
total_malware = len(all_active_malware)
total_tools = len(all_active_tools)
total_software = total_malware + total_tools

print(f"Unique active attack-patterns: {total_techniques}")
print(f"  - Parent techniques: {len(comb_parents)}")
print(f"  - Sub-techniques:    {len(comb_subs)}")
print(f"Unique active intrusion-sets:  {total_groups}")
print(f"Unique active malware:         {total_malware}")
print(f"Unique active tools:           {total_tools}")
print(f"Unique active software:        {total_software}")

total_core_entities = total_techniques + total_groups + total_software
print(f"\nSum: techniques ({total_techniques}) + groups ({total_groups}) + software ({total_software}) = {total_core_entities}")

# Check where 2062 came from in load_stix_all_bundles
from src.data_loader import load_stix_all_bundles
kb = load_stix_all_bundles()
print(f"\nkb.total_objects: {kb.total_objects}")
print(f"len(kb.attack_patterns): {len(kb.attack_patterns)}")
print(f"len(kb.intrusion_sets): {len(kb.intrusion_sets)}")
print(f"len(kb.malware): {len(kb.malware)}")
print(f"len(kb.tools): {len(kb.tools)}")
print(f"Sum of kb lists: {len(kb.attack_patterns) + len(kb.intrusion_sets) + len(kb.malware) + len(kb.tools)}")
