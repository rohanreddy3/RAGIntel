"""Run full offline retrieval evaluation (Zero LLM calls).

Evaluates E0-STIX (Control Arm E0' with RAGIntel's 2000/500 char splitter) on:
1. CTI-ATE (60 rows)
2. CTI-ATTACK (229 rows)
3. CTI-TAA (50 rows, alias-aware)

Outputs:
- Recall@1, Recall@3, Recall@5, Recall@10
- Precision@1, Precision@3, Precision@5, Precision@10
- MRR
- nDCG@10
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def evaluate_dataset(
    dataset_key: str,
    df: pd.DataFrame,
    retriever: HybridSTIXRetriever,
    group_alias_map: Dict[str, Dict[str, Any]],
    top_k: int = 10,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    print(f"\n--- Evaluating Retrieval on {dataset_key} ({len(df)} queries) ---")
    results = []
    k_vals = [1, 3, 5, 10]

    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"Evaluating {dataset_key}"):
        query = str(row["query"])
        gt = str(row.get("ground_truth", ""))

        start_t = time.time()
        retrieved_docs = retriever.retrieve(query, top_k=top_k)
        latency_ms = (time.time() - start_t) * 1000

        if dataset_key == "cti-taa":
            metrics = compute_retrieval_metrics_taa_alias_aware(
                retrieved_docs, gt, group_alias_map, k_values=k_vals
            )
        else:
            metrics = compute_retrieval_metrics_technique(
                retrieved_docs, gt, k_values=k_vals
            )

        row_res = {
            "query_idx": idx,
            "query_preview": query[:80] + ("..." if len(query) > 80 else ""),
            "ground_truth": gt,
            "latency_ms": round(latency_ms, 2),
            **metrics,
        }
        results.append(row_res)

    results_df = pd.DataFrame(results)

    # Compute mean summary
    summary = {"num_queries": len(df)}
    for col in results_df.columns:
        if col not in ["query_idx", "query_preview", "ground_truth"]:
            summary[col] = round(float(results_df[col].mean()), 4)

    return results_df, summary


def main():
    results_dir = Path("results/phase_1")
    results_dir.mkdir(parents=True, exist_ok=True)

    print("Loading STIX Knowledge Base...")
    kb = load_stix_bundle()
    group_alias_map = kb.get_group_alias_map()
    print(f"Loaded STIX KB: {kb.total_objects} active objects, {len(group_alias_map)} threat groups with aliases.")

    print("\nInitializing Hybrid STIX Retriever (E0-STIX Baseline)...")
    init_start = time.time()
    retriever = HybridSTIXRetriever(stix_kb=kb)
    print(f"Retriever ready in {time.time() - init_start:.2f}s")

    datasets = load_all_benchmark_datasets()
    all_summaries = {}

    for name, d_info in datasets.items():
        results_df, summary = evaluate_dataset(
            name, d_info.df, retriever, group_alias_map, top_k=10
        )
        all_summaries[name] = summary

        csv_path = results_dir / f"retrieval_metrics_{name.lower().replace('-', '_')}.csv"
        results_df.to_csv(csv_path, index=False)
        print(f"Saved {name} query-level results to {csv_path}")

    # Save summary JSON
    summary_json_path = results_dir / "retrieval_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\nSaved overall summary JSON to {summary_json_path}")

    # Generate Markdown Summary
    md = []
    md.append("# Phase 1 Retrieval Evaluation Summary (E0-STIX / Control Arm E0')\n")
    md.append("Retrieval metrics computed across all 339 benchmark queries without LLM dependency.\n")
    md.append("| Dataset | Queries | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@1 | Precision@5 | Precision@10 | MRR | nDCG@10 | Mean Latency (ms) |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

    for name, s in all_summaries.items():
        md.append(
            f"| **{name}** | {s['num_queries']} | "
            f"{s.get('Recall@1', 0.0):.4f} | {s.get('Recall@3', 0.0):.4f} | {s.get('Recall@5', 0.0):.4f} | {s.get('Recall@10', 0.0):.4f} | "
            f"{s.get('Precision@1', 0.0):.4f} | {s.get('Precision@5', 0.0):.4f} | {s.get('Precision@10', 0.0):.4f} | "
            f"{s.get('MRR', 0.0):.4f} | {s.get('nDCG@10', 0.0):.4f} | {s.get('latency_ms', 0.0):.1f} |"
        )

    summary_md_path = results_dir / "retrieval_summary.md"
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Saved Markdown summary to {summary_md_path}")


if __name__ == "__main__":
    main()
