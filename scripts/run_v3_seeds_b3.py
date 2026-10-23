"""Part 2.1: Evaluate Variant V3 under Seeds 42, 43, 44 on cti-taa, E0-STIX-ALL, Baseline B3.

Reconciles the discrepancy between grid B3 V3 (0.2000, 0.0830) and checkpoint B3 V3 (0.3200, 0.1054)
by executing strictly with per-query deterministic seeding hash(seed, 'cti-taa', row_idx).
Single process, thread cap 4.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Enforce thread capping and offline mode
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

torch.set_num_threads(4)

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.retriever import HybridSTIXRetriever
from src.entity_resolver import CyberEntityResolver
from src.retrieval_eval import compute_retrieval_metrics_taa_alias_aware


def get_per_query_seed(base_seed: int, dataset: str, row_idx: int) -> int:
    """Deterministic per-query integer seed."""
    key = f"{base_seed}_{dataset}_{row_idx}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16) % (2**31 - 1)


def main():
    print("=" * 75, flush=True)
    print("PART 2.1: RERUN V3 B3 ON CTI-TAA, E0-STIX-ALL (SEEDS 42, 43, 44)", flush=True)
    print("=" * 75, flush=True)

    out_file = REPO_ROOT / "results" / "phase_2" / "v3_seeds_b3_results.json"

    print("Loading STIX Knowledge Base...", flush=True)
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()

    print("Initializing HybridSTIXRetriever for E0-STIX-ALL...", flush=True)
    retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")

    ds_taa = load_benchmark_dataset("cti-taa")
    df_taa = ds_taa.df

    seeds = [42, 43, 44]
    results: Dict[str, Any] = {"baseline": "B3", "dataset": "cti-taa", "corpus": "E0-STIX-ALL", "seeds": {}}

    for seed in seeds:
        print(f"\nEvaluating Seed {seed} on B3 (MaxSim Windows) with per-query seeding...", flush=True)
        t0 = time.time()
        recalls = []
        mrrs = []
        per_query_records = []

        for idx, row in df_taa.iterrows():
            q_seed = get_per_query_seed(seed, "cti-taa", int(idx))
            resolver = CyberEntityResolver(stix_kb=stix_kb, min_alias_len=3, random_seed=q_seed)
            raw_q = str(row["query"])
            gt = str(row.get("ground_truth", ""))

            exp_q, detected = resolver.expand_query(raw_q, variant="V3", max_expansion_tokens=64)
            # Baseline B3: enable_query_chunking=True
            docs = retriever.retrieve(exp_q, top_k=10, enable_query_chunking=True)

            m = compute_retrieval_metrics_taa_alias_aware(docs, gt, group_alias_map=group_alias_map, k_values=[1, 3, 5, 10])
            rec10 = m["Recall@10"]
            mrr = m["MRR"]
            recalls.append(rec10)
            mrrs.append(mrr)
            per_query_records.append({
                "idx": int(idx),
                "query": raw_q,
                "ground_truth": gt,
                "Recall@10": rec10,
                "MRR": mrr,
            })

        elapsed = time.time() - t0
        mean_rec = float(np.mean(recalls))
        mean_mrr = float(np.mean(mrrs))
        print(f"Seed {seed}: Recall@10 = {mean_rec:.4f}, MRR = {mean_mrr:.4f} (elapsed: {elapsed:.1f}s, {elapsed/len(df_taa):.2f}s/q)", flush=True)

        results["seeds"][str(seed)] = {
            "Recall@10": round(mean_rec, 4),
            "MRR": round(mean_mrr, 4),
            "elapsed_seconds": round(elapsed, 2),
            "s_per_query": round(elapsed / len(df_taa), 4),
            "per_query": per_query_records,
        }

    # Aggregate across seeds 42-44
    all_recalls = [v["Recall@10"] for v in results["seeds"].values()]
    all_mrrs = [v["MRR"] for v in results["seeds"].values()]
    results["aggregate"] = {
        "mean_Recall@10": round(float(np.mean(all_recalls)), 4),
        "range_Recall@10": [round(min(all_recalls), 4), round(max(all_recalls), 4)],
        "mean_MRR": round(float(np.mean(all_mrrs)), 4),
        "range_MRR": [round(min(all_mrrs), 4), round(max(all_mrrs), 4)],
    }
    print("\nAggregate across seeds 42-44:", results["aggregate"], flush=True)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved V3 B3 seed sensitivity results to: {out_file}", flush=True)


if __name__ == "__main__":
    main()
