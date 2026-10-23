"""Comparative Offline Retrieval Evaluation: Truncated Baseline vs Long-Query MaxSim Pooling.

Evaluates all 339 queries across:
1. CTI-ATE (60 rows)
2. CTI-TAA (50 rows)
3. CTI-ATTACK (229 rows)

Computes:
- BEFORE (Standard 256-token truncation)
- AFTER (Long-query sliding-window chunking + MaxSim pooling)
- Evaluates against:
  * All Ground Truth IDs
  * Reachable-Only Ground Truth IDs (in enterprise-attack.json)
  * Sub-technique to Parent Credit
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.data_loader import load_all_benchmark_datasets, load_stix_bundle
from src.retrieval_eval import (
    compute_retrieval_metrics_taa_alias_aware,
    compute_retrieval_metrics_technique,
)
from src.retriever import HybridSTIXRetriever


def evaluate_queries(
    dataset_key: str,
    df: pd.DataFrame,
    retriever: HybridSTIXRetriever,
    group_alias_map: Dict[str, Dict[str, Any]],
    active_tech_ids: Set[str],
    enable_query_chunking: bool,
    top_k: int = 10,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    mode_name = "LongQuery-MaxSim" if enable_query_chunking else "Baseline-Truncated"
    print(f"\n--- Evaluating {dataset_key} ({len(df)} queries) [{mode_name}] ---")
    
    results = []
    k_vals = [1, 3, 5, 10]

    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"{dataset_key} [{mode_name}]"):
        query = str(row["query"])
        gt = str(row.get("ground_truth", ""))

        start_t = time.time()
        retrieved_docs = retriever.retrieve(
            query, top_k=top_k, enable_query_chunking=enable_query_chunking
        )
        latency_ms = (time.time() - start_t) * 1000

        row_res = {
            "query_idx": idx,
            "latency_ms": round(latency_ms, 2),
        }

        if dataset_key == "cti-taa":
            metrics = compute_retrieval_metrics_taa_alias_aware(
                retrieved_docs, gt, group_alias_map, k_values=k_vals
            )
            row_res.update(metrics)
        else:
            # 1. Standard (all GT IDs)
            metrics_all = compute_retrieval_metrics_technique(
                retrieved_docs, gt, k_values=k_vals
            )
            # 2. Reachable only
            metrics_reachable = compute_retrieval_metrics_technique(
                retrieved_docs, gt, k_values=k_vals, reachable_ids=active_tech_ids
            )
            # 3. Subtechnique credit
            metrics_subtech = compute_retrieval_metrics_technique(
                retrieved_docs, gt, k_values=k_vals, reachable_ids=active_tech_ids, subtechnique_parent_credit=True
            )

            for k in [1, 5, 10]:
                row_res[f"Recall@{k}"] = metrics_all[f"Recall@{k}"]
                row_res[f"Precision@{k}"] = metrics_all[f"Precision@{k}"]
                row_res[f"Reachable_Recall@{k}"] = metrics_reachable[f"Recall@{k}"]
                row_res[f"SubtechCredit_Recall@{k}"] = metrics_subtech[f"Recall@{k}"]

            row_res["MRR"] = metrics_all["MRR"]
            row_res["nDCG@10"] = metrics_all["nDCG@10"]
            row_res["Reachable_MRR"] = metrics_reachable["MRR"]
            row_res["Reachable_nDCG@10"] = metrics_reachable["nDCG@10"]
            row_res["SubtechCredit_MRR"] = metrics_subtech["MRR"]
            row_res["SubtechCredit_nDCG@10"] = metrics_subtech["nDCG@10"]

        results.append(row_res)

    results_df = pd.DataFrame(results)

    summary = {"num_queries": len(df)}
    for col in results_df.columns:
        if col not in ["query_idx"]:
            summary[col] = round(float(results_df[col].mean()), 4)

    return results_df, summary


def main():
    results_dir = Path("results/phase_1")
    results_dir.mkdir(parents=True, exist_ok=True)

    print("Loading STIX Knowledge Base...")
    kb = load_stix_bundle()
    group_alias_map = kb.get_group_alias_map()
    tech_map = kb.get_techniques_map()
    active_tech_ids = set(tech_map.keys())
    print(f"Loaded STIX KB: {kb.total_objects} active objects, {len(active_tech_ids)} techniques, {len(group_alias_map)} threat groups.")

    print("\nInitializing Hybrid STIX Retriever...")
    retriever = HybridSTIXRetriever(stix_kb=kb)

    datasets = load_all_benchmark_datasets()

    summary_before = {}
    summary_after = {}

    for mode in [False, True]:
        mode_label = "after_longquery" if mode else "before_truncated"
        mode_dict = summary_after if mode else summary_before

        print(f"\n=======================================================")
        print(f"RUNNING RETRIEVAL EVALUATION: {mode_label.upper()}")
        print(f"=======================================================")

        for name, d_info in datasets.items():
            csv_path = results_dir / f"retrieval_{name.lower().replace('-', '_')}_{mode_label}.csv"
            if csv_path.exists():
                print(f"Found completed results for {name} [{mode_label}], loading from {csv_path}...")
                results_df = pd.read_csv(csv_path)
                summary = {"num_queries": len(results_df)}
                for col in results_df.columns:
                    if col not in ["query_idx"]:
                        summary[col] = round(float(results_df[col].mean()), 4)
            else:
                results_df, summary = evaluate_queries(
                    dataset_key=name,
                    df=d_info.df,
                    retriever=retriever,
                    group_alias_map=group_alias_map,
                    active_tech_ids=active_tech_ids,
                    enable_query_chunking=mode,
                    top_k=10,
                )
                results_df.to_csv(csv_path, index=False)
            mode_dict[name] = summary

    # Save summary JSON files
    with open(results_dir / "retrieval_summary_before.json", "w", encoding="utf-8") as f:
        json.dump(summary_before, f, indent=2)

    with open(results_dir / "retrieval_summary_after_longquery.json", "w", encoding="utf-8") as f:
        json.dump(summary_after, f, indent=2)

    # Generate Markdown Comparison
    md = []
    md.append("# Offline Retrieval Evaluation: Before vs After Long-Query Strategy\n")
    md.append("Comparison of **Baseline (256-token truncation)** vs **Long-Query MaxSim Pooling** across all 339 queries.\n")
    md.append("Zero LLM calls used (offline evaluation).\n\n")

    md.append("### 1. Main Retrieval Metrics Comparison\n")
    md.append("| Dataset | Mode | Queries | Recall@1 | Recall@5 | Recall@10 | MRR | nDCG@10 | Latency (ms) |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for name in datasets.keys():
        b = summary_before[name]
        a = summary_after[name]
        md.append(f"| **{name}** | BEFORE (Truncated) | {b['num_queries']} | {b.get('Recall@1', 0.0):.4f} | {b.get('Recall@5', 0.0):.4f} | {b.get('Recall@10', 0.0):.4f} | {b.get('MRR', 0.0):.4f} | {b.get('nDCG@10', 0.0):.4f} | {b.get('latency_ms', 0.0):.1f} |")
        md.append(f"| **{name}** | AFTER (MaxSim) | {a['num_queries']} | {a.get('Recall@1', 0.0):.4f} | {a.get('Recall@5', 0.0):.4f} | {a.get('Recall@10', 0.0):.4f} | {a.get('MRR', 0.0):.4f} | {a.get('nDCG@10', 0.0):.4f} | {a.get('latency_ms', 0.0):.1f} |")

    md.append("\n### 2. Reachable Ceiling & Sub-technique Credit Breakdown (AFTER: MaxSim)\n")
    md.append("| Dataset | Mode | Raw Recall@10 | Reachable Recall@10 | Subtech-Credit Recall@10 | Raw MRR | Reachable MRR | Subtech MRR |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for name in ["cti-ate", "CTI-ATTACK"]:
        a = summary_after[name]
        md.append(
            f"| **{name}** | AFTER (MaxSim) | "
            f"{a.get('Recall@10', 0.0):.4f} | {a.get('Reachable_Recall@10', 0.0):.4f} | {a.get('SubtechCredit_Recall@10', 0.0):.4f} | "
            f"{a.get('MRR', 0.0):.4f} | {a.get('Reachable_MRR', 0.0):.4f} | {a.get('SubtechCredit_MRR', 0.0):.4f} |"
        )

    comp_md_path = results_dir / "retrieval_comparison_before_after.md"
    with open(comp_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\nSaved Markdown comparison to {comp_md_path}")
    print("Done!")


if __name__ == "__main__":
    main()
