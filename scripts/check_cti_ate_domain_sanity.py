"""Sanity check for Part C: Domain distribution of cti-ate ground truth.

Checks the share of cti-ate rows whose ground truth IDs fall into the domain
named in the prompt instruction ("MITRE Enterprise" -> enterprise-attack,
"MITRE Mobile" -> mobile-attack).
"""

import json
from pathlib import Path
from collections import defaultdict
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.retrieval_eval import parse_ground_truth_techniques

def run_sanity_check():
    stix_kb = load_stix_all_bundles()
    
    # Map technique ID (and subtechnique) to domain(s)
    tech_to_domains = defaultdict(set)
    for obj in stix_kb.attack_patterns:
        domains = set(obj.get("x_mitre_domains", []))
        ext_refs = obj.get("external_references", [])
        for r in ext_refs:
            src = r.get("source_name", "")
            if src == "mitre-attack":
                domains.add("enterprise-attack")
            elif src == "mitre-mobile-attack":
                domains.add("mobile-attack")
            elif src == "mitre-ics-attack":
                domains.add("ics-attack")
                
            mid = r.get("external_id")
            if mid:
                tech_to_domains[mid].update(domains)
                # Parent technique
                if "." in mid:
                    parent = mid.split(".")[0]
                    tech_to_domains[parent].update(domains)

    df_ate = load_benchmark_dataset("cti-ate").df
    
    total_rows = len(df_ate)
    rows_with_domain = 0
    full_match_rows = 0
    partial_match_rows = 0
    zero_match_rows = 0
    
    total_gt_ids = 0
    matching_gt_ids = 0
    
    domain_counts = defaultdict(int)
    row_details = []
    
    for idx, row in df_ate.iterrows():
        q_raw = str(row["query"])
        gt_raw = str(row["ground_truth"])
        gt_ids = parse_ground_truth_techniques(gt_raw)
        
        # Determine target domain from instruction
        if "MITRE Enterprise" in q_raw:
            target_domain = "enterprise-attack"
        elif "MITRE Mobile" in q_raw:
            target_domain = "mobile-attack"
        else:
            target_domain = "unknown"
            
        domain_counts[target_domain] += 1
        
        if not gt_ids:
            continue
            
        row_matches = 0
        for tid in gt_ids:
            total_gt_ids += 1
            t_domains = tech_to_domains.get(tid, set())
            if not t_domains and "." in tid:
                t_domains = tech_to_domains.get(tid.split(".")[0], set())
            if target_domain in t_domains:
                matching_gt_ids += 1
                row_matches += 1
                
        match_rate = row_matches / len(gt_ids) if gt_ids else 0.0
        if match_rate == 1.0:
            full_match_rows += 1
        elif match_rate > 0.0:
            partial_match_rows += 1
        else:
            zero_match_rows += 1
            
        row_details.append({
            "row_idx": idx,
            "target_domain": target_domain,
            "num_gt_ids": len(gt_ids),
            "matching_gt_ids": row_matches,
            "match_rate": round(match_rate, 4)
        })
        
    row_share_full = full_match_rows / total_rows
    row_share_any = (full_match_rows + partial_match_rows) / total_rows
    id_share = matching_gt_ids / total_gt_ids if total_gt_ids > 0 else 0.0
    
    print("=" * 60)
    print("CTI-ATE DOMAIN SANITY CHECK RESULTS")
    print("=" * 60)
    print(f"Total cti-ate rows: {total_rows}")
    print(f"Domain breakdown: {dict(domain_counts)}")
    print(f"Total GT IDs across rows: {total_gt_ids}")
    print(f"GT IDs matching named domain: {matching_gt_ids} ({id_share * 100:.2f}%)")
    print(f"Rows where 100% of GT IDs match named domain: {full_match_rows}/{total_rows} ({row_share_full * 100:.2f}%)")
    print(f"Rows where >= 1 GT ID matches named domain: {full_match_rows + partial_match_rows}/{total_rows} ({row_share_any * 100:.2f}%)")
    print(f"Rows where 0 GT IDs match named domain: {zero_match_rows}/{total_rows}")

    out_file = REPO_ROOT / "results" / "phase_5" / "cti_ate_domain_sanity.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total_rows": total_rows,
            "domain_breakdown": dict(domain_counts),
            "total_gt_ids": total_gt_ids,
            "matching_gt_ids": matching_gt_ids,
            "gt_id_match_share": round(id_share, 4),
            "rows_100pct_match": full_match_rows,
            "rows_100pct_share": round(row_share_full, 4),
            "rows_any_match": full_match_rows + partial_match_rows,
            "rows_any_share": round(row_share_any, 4),
            "rows_zero_match": zero_match_rows,
            "row_details": row_details
        }, f, indent=2)
    print(f"Saved sanity check to {out_file}")

if __name__ == "__main__":
    run_sanity_check()
