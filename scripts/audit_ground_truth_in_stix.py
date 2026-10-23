"""Audit ground-truth IDs against pinned STIX knowledge base.

Computes:
- Total unique ground-truth IDs per dataset
- Valid active STIX IDs
- Revoked STIX IDs
- Deprecated STIX IDs
- Absent IDs (not in STIX KB)
"""

import json
from pathlib import Path
from collections import defaultdict
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset
from src.retrieval_eval import parse_ground_truth_techniques, normalize_group_name

def audit_ground_truth():
    print("=" * 80)
    print("AUDIT GROUND-TRUTH IDs AGAINST PINNED STIX KB")
    print("=" * 80)

    # 1. Load raw bundles to see ALL objects (active, deprecated, revoked)
    mitre_dir = REPO_ROOT / "data" / "mitre"
    bundle_files = [
        mitre_dir / "enterprise-attack.json",
        mitre_dir / "mobile-attack.json",
        mitre_dir / "ics-attack.json",
    ]

    # Map mitre_id -> status ('active', 'deprecated', 'revoked')
    # and intrusion_set canonical/aliases -> status
    tech_status = {}  # mitre_id -> status
    group_status = {} # normalized name/alias -> status

    for bf in bundle_files:
        if not bf.is_file():
            continue
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
        for obj in data.get("objects", []):
            otype = obj.get("type")
            is_revoked = obj.get("revoked", False)
            is_deprecated = obj.get("x_mitre_deprecated", False)
            if is_revoked:
                status = "revoked"
            elif is_deprecated:
                status = "deprecated"
            else:
                status = "active"

            if otype == "attack-pattern":
                ext_refs = obj.get("external_references", [])
                for r in ext_refs:
                    mid = r.get("external_id")
                    if mid and mid.startswith("T"):
                        # If previously recorded as revoked/deprecated, active takes precedence if any active exists
                        if mid not in tech_status or status == "active":
                            tech_status[mid] = status

            elif otype == "intrusion-set":
                name = obj.get("name", "").strip()
                aliases = set(obj.get("aliases", []))
                if obj.get("x_mitre_aliases"):
                    aliases.update(obj.get("x_mitre_aliases", []))
                aliases.add(name)
                for a in aliases:
                    anorm = normalize_group_name(a)
                    if anorm:
                        if anorm not in group_status or status == "active":
                            group_status[anorm] = status

    results = {}

    # Audit cti-ate (Techniques)
    df_ate = load_benchmark_dataset("cti-ate").df
    ate_gt_all = []
    for gt in df_ate["ground_truth"]:
        ate_gt_all.extend(parse_ground_truth_techniques(str(gt)))
    ate_gt_unique = sorted(list(set(ate_gt_all)))

    ate_counts = defaultdict(int)
    ate_absent_list = []
    ate_dep_list = []
    ate_rev_list = []
    for tid in ate_gt_unique:
        st = tech_status.get(tid, "absent")
        ate_counts[st] += 1
        if st == "absent":
            ate_absent_list.append(tid)
        elif st == "deprecated":
            ate_dep_list.append(tid)
        elif st == "revoked":
            ate_rev_list.append(tid)

    results["cti-ate"] = {
        "total_unique_gt_ids": len(ate_gt_unique),
        "active": ate_counts["active"],
        "deprecated": ate_counts["deprecated"],
        "revoked": ate_counts["revoked"],
        "absent": ate_counts["absent"],
        "deprecated_ids": ate_dep_list,
        "revoked_ids": ate_rev_list,
        "absent_ids": ate_absent_list,
    }

    # Audit CTI-ATTACK (Techniques)
    df_att = load_benchmark_dataset("CTI-ATTACK").df
    att_gt_all = []
    for gt in df_att["ground_truth"]:
        att_gt_all.extend(parse_ground_truth_techniques(str(gt)))
    att_gt_unique = sorted(list(set(att_gt_all)))

    att_counts = defaultdict(int)
    att_absent_list = []
    att_dep_list = []
    att_rev_list = []
    for tid in att_gt_unique:
        st = tech_status.get(tid, "absent")
        att_counts[st] += 1
        if st == "absent":
            att_absent_list.append(tid)
        elif st == "deprecated":
            att_dep_list.append(tid)
        elif st == "revoked":
            att_rev_list.append(tid)

    results["CTI-ATTACK"] = {
        "total_unique_gt_ids": len(att_gt_unique),
        "active": att_counts["active"],
        "deprecated": att_counts["deprecated"],
        "revoked": att_counts["revoked"],
        "absent": att_counts["absent"],
        "deprecated_ids": att_dep_list,
        "revoked_ids": att_rev_list,
        "absent_ids": att_absent_list,
    }

    # Audit cti-taa (Threat Groups)
    df_taa = load_benchmark_dataset("cti-taa").df
    taa_gt_unique = sorted(list(set(str(g).strip() for g in df_taa["ground_truth"])))

    taa_counts = defaultdict(int)
    taa_absent_list = []
    taa_dep_list = []
    taa_rev_list = []

    for g_raw in taa_gt_unique:
        # Check if any token or alias matches group_status
        gnorm = normalize_group_name(g_raw)
        st = group_status.get(gnorm)
        if not st:
            # check subparts for composite strings
            matches = [group_status[a] for a in group_status if len(a) > 3 and a in gnorm]
            if matches:
                st = "active" if "active" in matches else matches[0]
            else:
                st = "absent"
        taa_counts[st] += 1
        if st == "absent":
            taa_absent_list.append(g_raw)
        elif st == "deprecated":
            taa_dep_list.append(g_raw)
        elif st == "revoked":
            taa_rev_list.append(g_raw)

    results["cti-taa"] = {
        "total_unique_gt_strings": len(taa_gt_unique),
        "active": taa_counts["active"],
        "deprecated": taa_counts["deprecated"],
        "revoked": taa_counts["revoked"],
        "absent": taa_counts["absent"],
        "deprecated_strings": taa_dep_list,
        "revoked_strings": taa_rev_list,
        "absent_strings": taa_absent_list,
    }

    print("\nSummary Table:")
    print(f"{'Dataset':<15} {'Total Unique GT':<18} {'Active':<10} {'Deprecated':<12} {'Revoked':<10} {'Absent':<10}")
    print("-" * 75)
    for ds, r in results.items():
        tot = r.get("total_unique_gt_ids", r.get("total_unique_gt_strings"))
        print(f"{ds:<15} {tot:<18} {r['active']:<10} {r['deprecated']:<12} {r['revoked']:<10} {r['absent']:<10}")

    out_file = REPO_ROOT / "results" / "phase_5" / "ground_truth_stix_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved GT STIX status audit to {out_file}")

if __name__ == "__main__":
    audit_ground_truth()
