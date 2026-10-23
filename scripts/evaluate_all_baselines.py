"""Complete Baseline Evaluation on E0-STIX-ENT and E0-STIX-ALL (Step 6).

Evaluates:
- Baseline B2: MiniLM truncated to 256 tokens (enable_query_chunking=False)
- Baseline B3: MiniLM + sliding-window MaxSim (enable_query_chunking=True)
Across all 339 queries (CTI-ATE: 60, CTI-ATTACK: 229, CTI-TAA: 50)
On two knowledge bases:
1. E0-STIX-ENT (Enterprise only, 1,698 active objects)
2. E0-STIX-ALL (Enterprise + Mobile + ICS, 2,062 active objects)

Computes:
- Primary: Exact-ID Recall@5, Recall@10, MRR, nDCG@10
- Secondary: Reachable_Recall@10, Reachable_MRR, SubtechCredit_Recall@10, SubtechCredit_MRR
- Paired bootstrap 95% CIs (10,000 resamples, seed 42) for B2 vs B3 delta on Recall@10 and MRR
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.data_loader import (
    load_all_benchmark_datasets,
    load_stix_bundle,
    load_stix_all_bundles,
)
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    compute_retrieval_metrics_taa_alias_aware,
    compute_retrieval_metrics_technique,
)
from src.retriever import HybridSTIXRetriever


def run_baseline_on_kb(
    kb_name: str,
    stix_kb: Any,
    datasets: Dict[str, Any],
) -> Dict[str, Any]:
    print(f"\n{'='*70}\nBUILDING RETRIEVER FOR KB: {kb_name} ({stix_kb.total_objects} objects)\n{'='*70}")
    
    # Use distinct cache dir per KB to avoid cross-contamination
    cache_dir = ".cache/retriever_index" if kb_name == "E0-STIX-ENT" else ".cache/retriever_index_all"
    retriever = HybridSTIXRetriever(stix_kb=stix_kb, enable_query_chunking=False, cache_dir=cache_dir)
    
    tech_map = stix_kb.get_techniques_map()
    active_tech_ids = set(tech_map.keys())
    group_alias_map = stix_kb.get_group_alias_map()
    
    kb_results = {
        "kb_name": kb_name,
        "total_active_objects": stix_kb.total_objects,
        "active_techniques": len(active_tech_ids),
        "active_groups": len(group_alias_map),
        "baselines": {},
    }
    
    # Evaluate B2 (truncated) and B3 (MaxSim)
    for b_code, enable_chunking in [("B2", False), ("B3", True)]:
        b_name = "MiniLM-MaxSim-Windows" if enable_chunking else "MiniLM-Truncated-256"
        print(f"\n--- Running Baseline {b_code}: {b_name} on {kb_name} ---")
        
        b_data = {}
        
        for ds_name in ["cti-ate", "CTI-ATTACK", "cti-taa"]:
            df = datasets[ds_name].df
            print(f"Evaluating {ds_name} ({len(df)} queries)...")
            
            per_query_rows = []
            k_vals = [1, 3, 5, 10]
            
            for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"{ds_name} [{b_code}]"):
                query = str(row["query"])
                gt = str(row.get("ground_truth", ""))
                
                start_t = time.time()
                docs = retriever.retrieve(
                    query, top_k=10, enable_query_chunking=enable_chunking
                )
                lat_ms = (time.time() - start_t) * 1000
                
                row_res = {"idx": idx, "latency_ms": round(lat_ms, 2)}
                
                if ds_name == "cti-taa":
                    metrics = compute_retrieval_metrics_taa_alias_aware(
                        docs, gt, group_alias_map, k_values=k_vals
                    )
                    row_res.update(metrics)
                else:
                    # 1. Exact-ID match (raw)
                    m_exact = compute_retrieval_metrics_technique(docs, gt, k_values=k_vals)
                    # 2. Reachable ceiling (with active STIX IDs)
                    m_reach = compute_retrieval_metrics_technique(
                        docs, gt, k_values=k_vals, reachable_ids=active_tech_ids
                    )
                    # 3. Sub-technique credit (direction: sub_credits_parent)
                    m_subtech = compute_retrieval_metrics_technique(
                        docs, gt, k_values=k_vals, reachable_ids=active_tech_ids, subtechnique_parent_credit=True
                    )
                    
                    row_res["Recall@5"] = m_exact["Recall@5"]
                    row_res["Recall@10"] = m_exact["Recall@10"]
                    row_res["MRR"] = m_exact["MRR"]
                    row_res["nDCG@10"] = m_exact["nDCG@10"]
                    row_res["Reachable_Recall@10"] = m_reach["Reachable_Recall@10"]
                    row_res["Reachable_MRR"] = m_reach["Reachable_MRR"]
                    row_res["SubtechCredit_Recall@10"] = m_subtech["Recall@10"]
                    row_res["SubtechCredit_MRR"] = m_subtech["MRR"]
                    row_res["num_gt"] = m_exact["num_gt"]
                    row_res["num_reachable_gt"] = m_reach.get("num_reachable_gt", 0)
                
                per_query_rows.append(row_res)
            
            df_per_query = pd.DataFrame(per_query_rows)
            
            # Compute macro means
            ds_summary = {
                "num_queries": len(df_per_query),
                "latency_mean_ms": round(float(df_per_query["latency_ms"].mean()), 2),
                "Recall@5": round(float(df_per_query["Recall@5"].mean()), 4),
                "Recall@10": round(float(df_per_query["Recall@10"].mean()), 4),
                "MRR": round(float(df_per_query["MRR"].mean()), 4),
            }
            if "nDCG@10" in df_per_query.columns:
                ds_summary["nDCG@10"] = round(float(df_per_query["nDCG@10"].mean()), 4)
            if "Reachable_Recall@10" in df_per_query.columns:
                # Valid reachable queries only (non-NaN)
                reach_rec = df_per_query["Reachable_Recall@10"].dropna()
                reach_mrr = df_per_query["Reachable_MRR"].dropna()
                ds_summary["Reachable_Recall@10"] = round(float(reach_rec.mean()), 4) if len(reach_rec) > 0 else None
                ds_summary["Reachable_MRR"] = round(float(reach_mrr.mean()), 4) if len(reach_mrr) > 0 else None
                ds_summary["valid_reachable_queries"] = len(reach_rec)
                ds_summary["SubtechCredit_Recall@10"] = round(float(df_per_query["SubtechCredit_Recall@10"].mean()), 4)
                ds_summary["SubtechCredit_MRR"] = round(float(df_per_query["SubtechCredit_MRR"].mean()), 4)
            
            b_data[ds_name] = {
                "summary": ds_summary,
                "per_query": per_query_rows,
            }
            
            print(f"  {ds_name}: Recall@10 = {ds_summary['Recall@10']:.4f} | MRR = {ds_summary['MRR']:.4f}")
            if "Reachable_Recall@10" in ds_summary and ds_summary["Reachable_Recall@10"] is not None:
                print(f"    Reachable_Recall@10 = {ds_summary['Reachable_Recall@10']:.4f} (N={ds_summary['valid_reachable_queries']}) | SubtechCredit_Recall@10 = {ds_summary['SubtechCredit_Recall@10']:.4f}")
        
        kb_results["baselines"][b_code] = b_data
    
    # Compute paired bootstrap 95% CIs (B2 vs B3)
    kb_results["bootstrap_comparisons"] = {}
    for ds_name in ["cti-ate", "CTI-ATTACK", "cti-taa"]:
        b2_rows = kb_results["baselines"]["B2"][ds_name]["per_query"]
        b3_rows = kb_results["baselines"]["B3"][ds_name]["per_query"]
        
        b2_r10 = [r["Recall@10"] for r in b2_rows]
        b3_r10 = [r["Recall@10"] for r in b3_rows]
        b2_mrr = [r["MRR"] for r in b2_rows]
        b3_mrr = [r["MRR"] for r in b3_rows]
        
        ci_r10 = compute_paired_bootstrap_ci(b2_r10, b3_r10, n_resamples=10000, seed=42)
        ci_mrr = compute_paired_bootstrap_ci(b2_mrr, b3_mrr, n_resamples=10000, seed=42)
        
        kb_results["bootstrap_comparisons"][ds_name] = {
            "Recall@10_delta": ci_r10,
            "MRR_delta": ci_mrr,
        }
        print(f"\nPaired Bootstrap (B2 vs B3) on {kb_name} - {ds_name}:")
        print(f"  Recall@10 Delta: {ci_r10['mean_delta']:+.4f} (95% CI [{ci_r10['ci_lower']:+.4f}, {ci_r10['ci_upper']:+.4f}], p={ci_r10['p_value']:.4f})")
        print(f"  MRR Delta      : {ci_mrr['mean_delta']:+.4f} (95% CI [{ci_mrr['ci_lower']:+.4f}, {ci_mrr['ci_upper']:+.4f}], p={ci_mrr['p_value']:.4f})")
    
    return kb_results


def main():
    print("=" * 70)
    print("PHASE 1c: BASELINE EVALUATION (B2 vs B3) ON E0-STIX-ENT AND E0-STIX-ALL")
    print("=" * 70)
    
    datasets = load_all_benchmark_datasets()
    print(f"Loaded datasets: cti-ate ({len(datasets['cti-ate'].df)}), CTI-ATTACK ({len(datasets['CTI-ATTACK'].df)}), cti-taa ({len(datasets['cti-taa'].df)})")
    
    # 1. Run on E0-STIX-ENT
    stix_ent = load_stix_bundle("data/mitre/enterprise-attack.json")
    results_ent = run_baseline_on_kb("E0-STIX-ENT", stix_ent, datasets)
    
    # 2. Run on E0-STIX-ALL
    stix_all = load_stix_all_bundles("data/mitre")
    results_all = run_baseline_on_kb("E0-STIX-ALL", stix_all, datasets)
    
    # Save combined results
    out_dir = Path("results/phase_1")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    combined_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "E0-STIX-ENT": results_ent,
        "E0-STIX-ALL": results_all,
    }
    
    json_path = out_dir / "baseline_evaluation_all.json"
    with open(json_path, "w", encoding="utf-8") as f:
        # Strip large per_query arrays for concise summary
        concise = {
            "timestamp": combined_results["timestamp"],
            "E0-STIX-ENT": {
                "total_active_objects": results_ent["total_active_objects"],
                "B2": {ds: results_ent["baselines"]["B2"][ds]["summary"] for ds in ["cti-ate", "CTI-ATTACK", "cti-taa"]},
                "B3": {ds: results_ent["baselines"]["B3"][ds]["summary"] for ds in ["cti-ate", "CTI-ATTACK", "cti-taa"]},
                "bootstrap_comparisons": results_ent["bootstrap_comparisons"],
            },
            "E0-STIX-ALL": {
                "total_active_objects": results_all["total_active_objects"],
                "B2": {ds: results_all["baselines"]["B2"][ds]["summary"] for ds in ["cti-ate", "CTI-ATTACK", "cti-taa"]},
                "B3": {ds: results_all["baselines"]["B3"][ds]["summary"] for ds in ["cti-ate", "CTI-ATTACK", "cti-taa"]},
                "bootstrap_comparisons": results_all["bootstrap_comparisons"],
            },
        }
        json.dump(concise, f, indent=2)
    
    print(f"\nSaved summary to {json_path}")


if __name__ == "__main__":
    main()
