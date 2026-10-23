"""Evaluate Variant V3 under multiple random seeds (42, 43, 44, 45, 46) on cti-taa, E0-STIX-ALL, B2 ONLY.
Addresses Phase 2 Amendment Item A4.
Directly reuses Seed 42 from results/phase_2/p1_eval_checkpoint.json (Recall@10=0.3000, MRR=0.0753).
Runs seeds 43, 44, 45, 46 with thread capping (OMP_NUM_THREADS=4, torch.set_num_threads(4)).
Measures elapsed seconds and s/query.
"""

import os
import sys
import time

# Enforce thread capping for cpu_count >= 8 (4 threads per process)
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

torch.set_num_threads(4)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.retriever import HybridSTIXRetriever
from src.entity_resolver import CyberEntityResolver
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    compute_retrieval_metrics_taa_alias_aware,
)


def run_seeds():
    out_dir = REPO_ROOT / "results" / "phase_2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "v3_seeds_b2_results.json"

    print("=" * 70, flush=True)
    print("Running V3 Seed Sensitivity Analysis (Seeds 42, 43, 44, 45, 46) on cti-taa, E0-STIX-ALL, B2", flush=True)
    print(f"Hardware: os.cpu_count() = {os.cpu_count()}, Torch threads = {torch.get_num_threads()}, OMP = {os.environ.get('OMP_NUM_THREADS')}", flush=True)
    print("=" * 70, flush=True)

    # 1. Load Seed 42 directly from checkpoint
    p1_ckpt = REPO_ROOT / "results" / "phase_2" / "p1_eval_checkpoint.json"
    if not p1_ckpt.is_file():
        raise FileNotFoundError(f"Missing {p1_ckpt}")

    with open(p1_ckpt, "r", encoding="utf-8") as f:
        p1_data = json.load(f)

    v3_seed42_records = p1_data["E0-STIX-ALL_B2_V3_cti-taa"]
    seed42_recalls = [float(r["Recall@10"]) for r in v3_seed42_records]
    seed42_mrrs = [float(r["MRR"]) for r in v3_seed42_records]
    mean_rec_42 = float(np.mean(seed42_recalls))
    mean_mrr_42 = float(np.mean(seed42_mrrs))
    print(f"Reused Seed 42 from checkpoint: Recall@10 = {mean_rec_42:.4f}, MRR = {mean_mrr_42:.4f} (50 queries)", flush=True)

    per_seed_scores = {
        42: {
            "Recall@10": round(mean_rec_42, 4),
            "MRR": round(mean_mrr_42, 4),
            "per_query_recall": seed42_recalls,
            "per_query_mrr": seed42_mrrs,
            "elapsed_seconds": None,
            "s_per_query": None,
            "source": "reused_from_p1_eval_checkpoint.json",
        }
    }

    # 2. Setup retriever and data for remaining seeds (43, 44, 45, 46)
    print("\nLoading STIX KB and initializing HybridSTIXRetriever...", flush=True)
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()
    retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")

    ds_taa = load_benchmark_dataset("cti-taa")
    df_taa = ds_taa.df

    # Warmup query
    _ = retriever.retrieve("warmup query", top_k=5, enable_query_chunking=False)

    seeds_to_run = [43, 44, 45, 46]
    seed_timings = {}

    for seed in seeds_to_run:
        print(f"\nEvaluating Seed {seed}...", flush=True)
        resolver = CyberEntityResolver(stix_kb=stix_kb, min_alias_len=3, random_seed=seed)
        seed_recalls = []
        seed_mrrs = []
        seed_records = []

        t0 = time.perf_counter()
        for idx, row in tqdm(df_taa.iterrows(), total=len(df_taa), desc=f"Seed-{seed}"):
            raw_q = str(row["query"])
            gt = str(row.get("ground_truth", ""))

            exp_q, detected = resolver.expand_query(raw_q, variant="V3", max_expansion_tokens=64)
            docs = retriever.retrieve(exp_q, top_k=10, enable_query_chunking=False)
            metrics = compute_retrieval_metrics_taa_alias_aware(
                docs, gt, group_alias_map=group_alias_map, k_values=[1, 3, 5, 10]
            )

            seed_recalls.append(metrics["Recall@10"])
            seed_mrrs.append(metrics["MRR"])
            seed_records.append({
                "idx": idx,
                "Recall@10": metrics["Recall@10"],
                "MRR": metrics["MRR"],
            })
        elapsed = time.perf_counter() - t0
        s_per_query = elapsed / len(df_taa)

        mean_rec = float(np.mean(seed_recalls))
        mean_mrr = float(np.mean(seed_mrrs))
        print(f"Seed {seed}: Recall@10 = {mean_rec:.4f}, MRR = {mean_mrr:.4f} | Time: {elapsed:.2f}s ({s_per_query:.4f} s/query)", flush=True)

        seed_timings[seed] = {
            "elapsed_seconds": round(elapsed, 3),
            "s_per_query": round(s_per_query, 4),
        }

        per_seed_scores[seed] = {
            "Recall@10": round(mean_rec, 4),
            "MRR": round(mean_mrr, 4),
            "per_query_recall": seed_recalls,
            "per_query_mrr": seed_mrrs,
            "elapsed_seconds": round(elapsed, 3),
            "s_per_query": round(s_per_query, 4),
            "source": "measured_online_4threads",
        }

    # Summary across all 5 seeds
    all_seeds = [42, 43, 44, 45, 46]
    all_recalls = [per_seed_scores[s]["Recall@10"] for s in all_seeds]
    all_mrrs = [per_seed_scores[s]["MRR"] for s in all_seeds]

    summary_stats = {
        "hardware": {
            "cpu_count": os.cpu_count(),
            "threads_per_process": 4,
            "torch_threads": torch.get_num_threads(),
        },
        "seeds": all_seeds,
        "timing_measured_seeds": seed_timings,
        "mean_s_per_query_b2_4threads": round(float(np.mean([seed_timings[s]["s_per_query"] for s in seeds_to_run])), 4),
        "Recall@10": {
            "mean": round(float(np.mean(all_recalls)), 4),
            "min": round(float(np.min(all_recalls)), 4),
            "max": round(float(np.max(all_recalls)), 4),
            "range": round(float(np.max(all_recalls) - np.min(all_recalls)), 4),
            "std": round(float(np.std(all_recalls)), 4),
            "per_seed": {str(s): per_seed_scores[s]["Recall@10"] for s in all_seeds},
        },
        "MRR": {
            "mean": round(float(np.mean(all_mrrs)), 4),
            "min": round(float(np.min(all_mrrs)), 4),
            "max": round(float(np.max(all_mrrs)), 4),
            "range": round(float(np.max(all_mrrs) - np.min(all_mrrs)), 4),
            "std": round(float(np.std(all_mrrs)), 4),
            "per_seed": {str(s): per_seed_scores[s]["MRR"] for s in all_seeds},
        },
    }

    # Compute mean per-query scores for V3 across all 5 seeds
    mean_pq_recall_v3 = np.mean([per_seed_scores[s]["per_query_recall"] for s in all_seeds], axis=0)
    mean_pq_mrr_v3 = np.mean([per_seed_scores[s]["per_query_mrr"] for s in all_seeds], axis=0)

    # Load V1 scores from checkpoint
    v1_records = p1_data["E0-STIX-ALL_B2_V1_cti-taa"]
    v1_recalls = np.array([r["Recall@10"] for r in v1_records], dtype=float)
    v1_mrrs = np.array([r["MRR"] for r in v1_records], dtype=float)

    # Contrast V1 vs V3_mean for Recall@10
    ci_rec = compute_paired_bootstrap_ci(v1_recalls, mean_pq_recall_v3, n_resamples=10000, seed=42)
    # Contrast V1 vs V3_mean for MRR
    ci_mrr = compute_paired_bootstrap_ci(v1_mrrs, mean_pq_mrr_v3, n_resamples=10000, seed=42)

    summary_stats["v1_vs_v3_mean_contrasts"] = {
        "Recall@10": ci_rec,
        "MRR": ci_mrr,
    }

    print("\n" + "=" * 70, flush=True)
    print("V3 Seed Sensitivity Summary (5 seeds: 42, 43, 44, 45, 46):", flush=True)
    print(f"Recall@10: mean = {summary_stats['Recall@10']['mean']:.4f}, min = {summary_stats['Recall@10']['min']:.4f}, max = {summary_stats['Recall@10']['max']:.4f}, std = {summary_stats['Recall@10']['std']:.4f}", flush=True)
    print(f"MRR:       mean = {summary_stats['MRR']['mean']:.4f}, min = {summary_stats['MRR']['min']:.4f}, max = {summary_stats['MRR']['max']:.4f}, std = {summary_stats['MRR']['std']:.4f}", flush=True)
    print(f"\nV1 vs V3(mean across 5 seeds):", flush=True)
    print(f"  Recall@10: delta = {ci_rec['mean_delta']:+.4f} [{ci_rec['ci_lower']:+.4f}, {ci_rec['ci_upper']:+.4f}], p = {ci_rec['p_value']:.4f}", flush=True)
    print(f"  MRR:       delta = {ci_mrr['mean_delta']:+.4f} [{ci_mrr['ci_lower']:+.4f}, {ci_mrr['ci_upper']:+.4f}], p = {ci_mrr['p_value']:.4f}", flush=True)
    print("=" * 70, flush=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)

    print(f"\nSaved V3 seed results to {out_file}", flush=True)


if __name__ == "__main__":
    run_seeds()
