"""Optimization 1 (Cyber Entity Resolution) Comprehensive Benchmark (Step C4).

Evaluates query-side entity resolution variants across all 339 queries:
- V0: Baseline (no entity resolution)
- V1: Prepend detected entity aliases (max 64 tokens)
- V2: Prepend canonical name + MITRE ID only
- V3: Random entity ablation control (matched token length, seed 42)

Evaluated across:
- Two Knowledge Bases:
  * Primary: E0-STIX-ALL (Enterprise + Mobile + ICS, 2,062 active objects)
  * Secondary: E0-STIX-ENT (Enterprise only, 1,698 active objects)
- Two Baselines:
  * Baseline B2: MiniLM Truncated (enable_query_chunking=False)
  * Baseline B3: MiniLM MaxSim Windows (enable_query_chunking=True)
- Three Datasets:
  * CTI-TAA: 50 threat actor attribution queries (Primary family P1)
  * CTI-ATE: 60 adversary technique extraction queries (Secondary family S1)
  * CTI-ATTACK: 229 procedural technique queries (Secondary family S1)

Computes:
- Recall@5, Recall@10, MRR, nDCG@10
- Paired bootstrap 95% CIs (10,000 resamples, seed 42)
- Holm step-down adjusted p-values for Family P1 (alpha = 0.05)
- Win / Tie / Loss counts
- Top 5 helped and 5 hurt queries with exact text and retrieved IDs
- Latency overhead per query (mean, p95)
"""

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from src.entity_resolver import CyberEntityResolver
from src.manifest import generate_experiment_manifest


def holm_bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[Tuple[float, float, bool]]:
    """Holm-Bonferroni step-down procedure.
    
    Returns list of (raw_p, adjusted_threshold, is_significant).
    """
    m = len(p_values)
    # Sort indices by p-value
    sorted_indices = sorted(range(m), key=lambda i: p_values[i])
    results = [None] * m

    stopped = False
    for rank, idx in enumerate(sorted_indices):
        raw_p = p_values[idx]
        adj_alpha = alpha / (m - rank)
        if stopped or raw_p > adj_alpha:
            stopped = True
            is_sig = False
        else:
            is_sig = True
        results[idx] = (raw_p, round(adj_alpha, 6), is_sig)

    return results


def run_o1_benchmark():
    print("=" * 75)
    print("PHASE 2: OPTIMIZATION 1 (CYBER ENTITY RESOLUTION) BENCHMARK")
    print("=" * 75)

    datasets = load_all_benchmark_datasets()
    k_vals = [1, 3, 5, 10]

    kb_configs = [
        ("E0-STIX-ALL", load_stix_all_bundles(), ".cache/retriever_index_all", True),
        ("E0-STIX-ENT", load_stix_bundle(), ".cache/retriever_index", False),
    ]

    all_results = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluations": {},
    }

    per_query_archive = {}

    for kb_name, stix_kb, cache_dir, is_primary in kb_configs:
        print(f"\n{'='*75}", flush=True)
        print(f"EVALUATING KB: {kb_name} ({stix_kb.total_objects} active objects) [Primary={is_primary}]", flush=True)
        print(f"{'='*75}", flush=True)

        retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=cache_dir)
        resolver = CyberEntityResolver(stix_kb=stix_kb, min_alias_len=3, random_seed=42)

        tech_map = stix_kb.get_techniques_map()
        active_tech_ids = set(tech_map.keys())
        group_alias_map = stix_kb.get_group_alias_map()

        all_results["evaluations"][kb_name] = {
            "is_primary": is_primary,
            "total_active_objects": stix_kb.total_objects,
            "baselines": {},
        }

        for b_code, enable_chunking in [("B2", False), ("B3", True)]:
            b_name = "MiniLM-MaxSim-Windows" if enable_chunking else "MiniLM-Truncated-256"
            print(f"\n--- Baseline {b_code}: {b_name} on {kb_name} ---", flush=True)

            all_results["evaluations"][kb_name]["baselines"][b_code] = {
                "name": b_name,
                "variants": {},
            }

            for variant in ["V0", "V1", "V2", "V3"]:
                print(f"\n>>> Running Variant {variant} under {b_code} on {kb_name} <<<", flush=True)
                var_data = {}

                for ds_name in ["cti-taa", "cti-ate", "CTI-ATTACK"]:
                    df = datasets[ds_name].df
                    print(f"  Evaluating {ds_name} ({len(df)} queries)...", flush=True)

                    per_query_rows = []
                    latencies = []

                    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"{ds_name} [{b_code}-{variant}]"):
                        raw_query = str(row["query"])
                        gt = str(row.get("ground_truth", ""))

                        t_res_start = time.time()
                        expanded_query, detected_ents = resolver.expand_query(
                            raw_query, variant=variant, max_expansion_tokens=64
                        )
                        res_lat_ms = (time.time() - t_res_start) * 1000

                        t_ret_start = time.time()
                        docs = retriever.retrieve(
                            expanded_query, top_k=10, enable_query_chunking=enable_chunking
                        )
                        ret_lat_ms = (time.time() - t_ret_start) * 1000
                        total_lat_ms = res_lat_ms + ret_lat_ms
                        latencies.append(total_lat_ms)

                        row_res = {
                            "idx": idx,
                            "query": raw_query[:100],
                            "expanded_prefix": expanded_query[:100] if variant != "V0" else "",
                            "num_detected_entities": len(detected_ents),
                            "resolution_latency_ms": round(res_lat_ms, 2),
                            "retrieval_latency_ms": round(ret_lat_ms, 2),
                            "total_latency_ms": round(total_lat_ms, 2),
                            "retrieved_mitre_ids": [d.metadata.get("mitre_id", "") for d in docs],
                        }

                        if ds_name == "cti-taa":
                            m = compute_retrieval_metrics_taa_alias_aware(
                                docs, gt, group_alias_map, k_values=k_vals
                            )
                            row_res.update(m)
                        else:
                            m_exact = compute_retrieval_metrics_technique(docs, gt, k_values=k_vals)
                            m_reach = compute_retrieval_metrics_technique(
                                docs, gt, k_values=k_vals, reachable_ids=active_tech_ids
                            )
                            m_sub = compute_retrieval_metrics_technique(
                                docs, gt, k_values=k_vals, reachable_ids=active_tech_ids, subtechnique_parent_credit=True
                            )
                            row_res["Recall@5"] = m_exact["Recall@5"]
                            row_res["Recall@10"] = m_exact["Recall@10"]
                            row_res["MRR"] = m_exact["MRR"]
                            row_res["nDCG@10"] = m_exact["nDCG@10"]
                            row_res["Reachable_Recall@10"] = m_reach["Reachable_Recall@10"]
                            row_res["Reachable_MRR"] = m_reach["Reachable_MRR"]
                            row_res["SubtechCredit_Recall@10"] = m_sub["Recall@10"]
                            row_res["SubtechCredit_MRR"] = m_sub["MRR"]

                        per_query_rows.append(row_res)

                    df_pq = pd.DataFrame(per_query_rows)
                    key_tag = f"{kb_name}_{b_code}_{variant}_{ds_name}"
                    per_query_archive[key_tag] = per_query_rows

                    summary = {
                        "num_queries": len(df_pq),
                        "latency_mean_ms": round(float(np.mean(latencies)), 2),
                        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 2),
                        "Recall@5": round(float(df_pq["Recall@5"].mean()), 4),
                        "Recall@10": round(float(df_pq["Recall@10"].mean()), 4),
                        "MRR": round(float(df_pq["MRR"].mean()), 4),
                        "nDCG@10": round(float(df_pq["nDCG@10"].mean()), 4),
                    }
                    if "Reachable_Recall@10" in df_pq.columns:
                        reach_r = df_pq["Reachable_Recall@10"].dropna()
                        reach_m = df_pq["Reachable_MRR"].dropna()
                        summary["Reachable_Recall@10"] = round(float(reach_r.mean()), 4) if len(reach_r) > 0 else None
                        summary["Reachable_MRR"] = round(float(reach_m.mean()), 4) if len(reach_m) > 0 else None
                        summary["SubtechCredit_Recall@10"] = round(float(df_pq["SubtechCredit_Recall@10"].mean()), 4)
                        summary["SubtechCredit_MRR"] = round(float(df_pq["SubtechCredit_MRR"].mean()), 4)

                    var_data[ds_name] = summary
                    print(f"    {ds_name}: Rec@10={summary['Recall@10']:.4f} | MRR={summary['MRR']:.4f} | Lat(mean/p95)={summary['latency_mean_ms']}/{summary['latency_p95_ms']}ms", flush=True)

                all_results["evaluations"][kb_name]["baselines"][b_code]["variants"][variant] = var_data

    # Statistical Comparisons (Paired Bootstrap vs V0)
    print("\n" + "=" * 75, flush=True)
    print("COMPUTING STATISTICAL COMPARISONS (10,000 PAIRED BOOTSTRAP RESAMPLES, SEED 42)", flush=True)
    print("=" * 75, flush=True)

    comparisons_out = []
    p1_pvalues = []
    p1_meta = []

    for kb_name in ["E0-STIX-ALL", "E0-STIX-ENT"]:
        for b_code in ["B2", "B3"]:
            for variant in ["V1", "V2", "V3"]:
                for ds_name in ["cti-taa", "cti-ate", "CTI-ATTACK"]:
                    tag_v0 = f"{kb_name}_{b_code}_V0_{ds_name}"
                    tag_vX = f"{kb_name}_{b_code}_{variant}_{ds_name}"

                    rows_v0 = per_query_archive[tag_v0]
                    rows_vX = per_query_archive[tag_vX]

                    for metric in ["Recall@10", "MRR"]:
                        vals_v0 = np.array([r[metric] for r in rows_v0])
                        vals_vX = np.array([r[metric] for r in rows_vX])

                        delta_ci = compute_paired_bootstrap_ci(
                            vals_vX, vals_v0, n_bootstraps=10000, seed=42
                        )

                        # Win / Tie / Loss counts
                        diffs = vals_vX - vals_v0
                        wins = int(np.sum(diffs > 1e-4))
                        ties = int(np.sum(np.abs(diffs) <= 1e-4))
                        losses = int(np.sum(diffs < -1e-4))

                        comp_record = {
                            "kb_name": kb_name,
                            "baseline": b_code,
                            "variant": variant,
                            "dataset": ds_name,
                            "metric": metric,
                            "v0_mean": round(float(np.mean(vals_v0)), 4),
                            "vX_mean": round(float(np.mean(vals_vX)), 4),
                            "mean_delta": delta_ci["mean_delta"],
                            "ci_lower": delta_ci["ci_lower"],
                            "ci_upper": delta_ci["ci_upper"],
                            "p_value": delta_ci["p_value"],
                            "wins": wins,
                            "ties": ties,
                            "losses": losses,
                        }
                        comparisons_out.append(comp_record)

                        # Track Primary Family P1 hypotheses on Primary KB
                        if (
                            kb_name == "E0-STIX-ALL"
                            and variant == "V1"
                            and ds_name == "cti-taa"
                        ):
                            p1_pvalues.append(delta_ci["p_value"])
                            p1_meta.append(comp_record)

    # Apply Holm step-down correction on Family P1
    print("\n--- Applying Holm-Bonferroni Correction on Primary Family P1 ---", flush=True)
    holm_results = holm_bonferroni_correction(p1_pvalues, alpha=0.05)
    for i, meta in enumerate(p1_meta):
        raw_p, adj_alpha, is_sig = holm_results[i]
        meta["holm_raw_p"] = raw_p
        meta["holm_adj_alpha"] = adj_alpha
        meta["holm_is_significant"] = is_sig
        print(f"  P1 {meta['baseline']} {meta['metric']}: delta={meta['mean_delta']:+.4f} | p={raw_p:.4f} vs alpha_adj={adj_alpha:.4f} -> Sig: {is_sig}", flush=True)

    all_results["comparisons"] = comparisons_out
    all_results["primary_family_p1_holm"] = p1_meta

    # Helped / Hurt inspection on Primary Family P1: CTI-TAA V1 vs V0 under B3 on E0-STIX-ALL
    tag_p1_v0 = "E0-STIX-ALL_B3_V0_cti-taa"
    tag_p1_v1 = "E0-STIX-ALL_B3_V1_cti-taa"
    rows_v0 = per_query_archive[tag_p1_v0]
    rows_v1 = per_query_archive[tag_p1_v1]

    diff_records = []
    for i in range(len(rows_v0)):
        r0 = rows_v0[i]
        r1 = rows_v1[i]
        d_rec10 = r1["Recall@10"] - r0["Recall@10"]
        diff_records.append({
            "idx": r0["idx"],
            "query": r0["query"],
            "expanded_prefix": r1["expanded_prefix"],
            "delta_Recall@10": round(d_rec10, 4),
            "v0_Recall@10": r0["Recall@10"],
            "v1_Recall@10": r1["Recall@10"],
            "v0_retrieved_ids": r0["retrieved_mitre_ids"],
            "v1_retrieved_ids": r1["retrieved_mitre_ids"],
        })

    sorted_helped = sorted(diff_records, key=lambda x: x["delta_Recall@10"], reverse=True)[:5]
    sorted_hurt = sorted(diff_records, key=lambda x: x["delta_Recall@10"])[:5]

    all_results["query_case_inspections"] = {
        "top_5_helped": sorted_helped,
        "top_5_hurt": sorted_hurt,
    }

    results_dir = Path("results/phase_2")
    results_dir.mkdir(parents=True, exist_ok=True)
    out_json = results_dir / "o1_benchmark_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    manifest_path = generate_experiment_manifest(results_dir, "manifest_phase2_o1.json")
    print(f"\nSaved complete Phase 2 benchmark results to {out_json}", flush=True)
    print(f"Generated provenance manifest at {manifest_path}", flush=True)


if __name__ == "__main__":
    run_o1_benchmark()
