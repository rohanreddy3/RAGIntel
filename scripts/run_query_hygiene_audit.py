import json
import re
import sys
from collections import Counter
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.entity_resolver import CyberEntityResolver

def split_query(q: str):
    """Split query into instruction (before marker) and body (after marker)."""
    markers = ["Threat Report:", "**Text:**"]
    found_marker = None
    pos = -1
    for m in markers:
        p = q.find(m)
        if p != -1:
            if pos == -1 or p < pos:
                pos = p
                found_marker = m
                
    if found_marker is None:
        raise ValueError(f"Marker not found in query: {q[:100]}...")
        
    instruction = q[:pos].strip()
    body = q[pos + len(found_marker):].strip()
    return instruction, body, found_marker

def run_query_hygiene_audit():
    print("=" * 80)
    print("PHASE 5 PART A: QUERY HYGIENE AUDIT")
    print("=" * 80)
    
    stix_kb = load_stix_all_bundles()
    resolver = CyberEntityResolver(stix_kb=stix_kb)
    
    datasets = ["cti-ate", "CTI-ATTACK", "cti-taa"]
    
    # Load frozen Phase 4 full-query audit numbers for direct comparison
    frozen_p4_path = REPO_ROOT / "results" / "phase_4" / "detected_examples_audit.json"
    frozen_p4_data = {}
    if frozen_p4_path.is_file():
        with open(frozen_p4_path, "r", encoding="utf-8") as fp:
            frozen_p4_data = json.load(fp)
            
    audit_results = {
        "datasets": {},
        "summary_comparison": {},
        "top20_aliases_body": {},
        "top20_aliases_full": {}
    }
    
    total_queries = 0
    all_body_detections = []
    all_full_detections = []
    
    for ds_name in datasets:
        df = load_benchmark_dataset(ds_name).df
        n_rows = len(df)
        total_queries += n_rows
        
        matches_per_query_body = []
        matches_per_query_full = []
        has_ge1_body = 0
        has_ge1_full = 0
        
        body_alias_counter = Counter()
        full_alias_counter = Counter()
        
        per_query_records = []
        
        for idx, row in df.iterrows():
            q_raw = str(row["query"])
            qid = str(row.get("query_id", ""))
            
            # 1. Assert marker found
            instr, body, marker = split_query(q_raw)
            assert marker in q_raw, f"Marker assertion failed for {ds_name} row {idx}"
            
            # 2. Detect on body
            det_body = resolver.detect_entities(body)
            # 3. Detect on full query
            det_full = resolver.detect_entities(q_raw)
            
            matches_per_query_body.append(len(det_body))
            matches_per_query_full.append(len(det_full))
            
            if len(det_body) >= 1:
                has_ge1_body += 1
            if len(det_full) >= 1:
                has_ge1_full += 1
                
            for d in det_body:
                body_alias_counter[d.matched_text] += 1
                all_body_detections.append(d.matched_text)
                
            for d in det_full:
                full_alias_counter[d.matched_text] += 1
                all_full_detections.append(d.matched_text)
                
            per_query_records.append({
                "row_idx": idx,
                "query_id": qid,
                "marker": marker,
                "instruction_len_chars": len(instr),
                "body_len_chars": len(body),
                "detections_body_count": len(det_body),
                "detections_full_count": len(det_full),
                "body_aliases": [d.matched_text for d in det_body],
                "full_aliases": [d.matched_text for d in det_full]
            })
            
        share_ge1_body = has_ge1_body / n_rows
        share_ge1_full = has_ge1_full / n_rows
        mean_matches_body = float(np.mean(matches_per_query_body))
        mean_matches_full = float(np.mean(matches_per_query_full))
        
        print(f"\n--- {ds_name} (N={n_rows}) ---")
        print(f"  Share with >=1 entity: Body = {share_ge1_body:.4f} ({has_ge1_body}/{n_rows}) vs Full = {share_ge1_full:.4f} ({has_ge1_full}/{n_rows})")
        print(f"  Mean matches per query: Body = {mean_matches_body:.2f} (Total: {sum(matches_per_query_body)}) vs Full = {mean_matches_full:.2f} (Total: {sum(matches_per_query_full)})")
        
        audit_results["datasets"][ds_name] = {
            "n_queries": n_rows,
            "share_ge1_body": round(share_ge1_body, 4),
            "share_ge1_full": round(share_ge1_full, 4),
            "count_ge1_body": has_ge1_body,
            "count_ge1_full": has_ge1_full,
            "mean_matches_body": round(mean_matches_body, 2),
            "mean_matches_full": round(mean_matches_full, 2),
            "total_matches_body": sum(matches_per_query_body),
            "total_matches_full": sum(matches_per_query_full),
            "top10_aliases_body": body_alias_counter.most_common(10),
            "top10_aliases_full": full_alias_counter.most_common(10),
            "queries": per_query_records
        }
        
    # Top 20 aliases across all 339 queries
    total_body_counter = Counter(all_body_detections)
    total_full_counter = Counter(all_full_detections)
    
    top20_body = total_body_counter.most_common(20)
    top20_full = total_full_counter.most_common(20)
    
    audit_results["top20_aliases_body"] = top20_body
    audit_results["top20_aliases_full"] = top20_full
    
    print("\n" + "=" * 60)
    print("TOP 20 DETECTED ALIASES: BODY ONLY vs FULL QUERY")
    print("=" * 60)
    print(f"{'Rank':<5} {'Alias (Body)':<25} {'Count':<8} | {'Alias (Full)':<25} {'Count':<8}")
    print("-" * 70)
    for r in range(20):
        b_name, b_cnt = top20_body[r] if r < len(top20_body) else ("", 0)
        f_name, f_cnt = top20_full[r] if r < len(top20_full) else ("", 0)
        print(f"{r+1:<5} {b_name:<25} {b_cnt:<8} | {f_name:<25} {f_cnt:<8}")
        
    out_path = REPO_ROOT / "results" / "phase_5" / "query_hygiene_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(audit_results, fp, indent=2)
        
    print(f"\nSaved query hygiene audit to {out_path}")

if __name__ == "__main__":
    run_query_hygiene_audit()
