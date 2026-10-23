import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def audit_stix_versions():
    mitre_dir = REPO_ROOT / "data" / "mitre"
    bundles = {
        "Enterprise": mitre_dir / "enterprise-attack.json",
        "Mobile": mitre_dir / "mobile-attack.json",
        "ICS": mitre_dir / "ics-attack.json"
    }

    results = {}

    for domain, bpath in bundles.items():
        print(f"\n=================== {domain} ATT&CK ===================")
        with open(bpath, "r", encoding="utf-8") as fp:
            bundle = json.load(fp)

        objects = bundle.get("objects", [])
        
        # Check collection object or attack-pattern metadata
        collection_obj = next((obj for obj in objects if obj.get("type") in ["x-mitre-collection", "attack-pattern"]), None)
        all_collections = [obj for obj in objects if obj.get("type") == "x-mitre-collection"]
        
        spec_versions = set()
        mitre_versions = set()
        modified_dates = []

        for obj in objects:
            if "x_mitre_attack_spec_version" in obj:
                spec_versions.add(obj["x_mitre_attack_spec_version"])
            if "x_mitre_version" in obj and obj.get("type") == "x-mitre-collection":
                mitre_versions.add(obj["x_mitre_version"])
            if obj.get("type") == "x-mitre-collection" and "modified" in obj:
                modified_dates.append(obj["modified"])

        # Count active, revoked, deprecated techniques
        active_parents = 0
        active_subs = 0
        revoked = 0
        deprecated = 0

        for obj in objects:
            if obj.get("type") == "attack-pattern":
                is_revoked = obj.get("revoked", False)
                is_deprecated = obj.get("x_mitre_deprecated", False)
                is_sub = obj.get("x_mitre_is_subtechnique", False)

                if is_revoked:
                    revoked += 1
                elif is_deprecated:
                    deprecated += 1
                else:
                    if is_sub:
                        active_subs += 1
                    else:
                        active_parents += 1

        col_ver = all_collections[0].get("x_mitre_version", "N/A") if all_collections else "N/A"
        col_name = all_collections[0].get("name", "N/A") if all_collections else "N/A"
        col_modified = all_collections[0].get("modified", "N/A") if all_collections else "N/A"

        res = {
            "collection_name": col_name,
            "x_mitre_version": col_ver,
            "x_mitre_attack_spec_version": list(spec_versions),
            "modified": col_modified,
            "active_parents": active_parents,
            "active_subtechniques": active_subs,
            "total_active_techniques": active_parents + active_subs,
            "revoked_techniques": revoked,
            "deprecated_techniques": deprecated
        }
        results[domain] = res

        print(f"Collection Name: {col_name}")
        print(f"x_mitre_version: {col_ver}")
        print(f"Spec Version: {list(spec_versions)}")
        print(f"Modified Date: {col_modified}")
        print(f"Active Parent Techniques: {active_parents}")
        print(f"Active Sub-Techniques: {active_subs}")
        print(f"Total Active Techniques: {active_parents + active_subs}")
        print(f"Revoked Techniques: {revoked}")
        print(f"Deprecated Techniques: {deprecated}")

    out_path = REPO_ROOT / "results" / "phase_4b" / "stix_version_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2)
    print(f"\nSaved audit to {out_path}")

if __name__ == "__main__":
    audit_stix_versions()
