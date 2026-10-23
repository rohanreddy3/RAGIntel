"""Optimization 2: Structure-Aware Chunking Benchmark (Phase 3).

Evaluates 14 discrete cells under Scope Reduction (Oct 28 freeze):
1. cti-ate (60), B2 & B3, E0' and E1b at B* = 500 tokens.
2. CTI-ATTACK (229), B2 & B3, E0' and E1b at B* = 500 tokens.
3. cti-ate (60), B2, exploratory controls: E1a (field only), E1c (random siblings) at B*.
4. cti-ate (60), B2, secondary budgets: E1b at B in {1000, 2000, 4000}.
5. cti-taa (50), B2, no-regression check: E1b vs E0' at B*.

Supports parallel execution of B2 and B3 cells when cpu_count >= 8 (capped at 4 threads each).
Measures and reports core count and s/query with and without parallelism.
Computes Family P2 paired bootstrap hypothesis tests with Holm-Bonferroni correction.
"""

import copy
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Enforce thread capping per process
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

import torch
torch.set_num_threads(4)

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.retriever import HybridSTIXRetriever
from src.chunking import (
    count_tokens,
    build_field_chunks_e1a,
    StructureAwareIndex,
    truncate_to_token_budget,
)
from src.retrieval_eval import (
    compute_retrieval_metrics_technique,
    compute_retrieval_metrics_taa_alias_aware,
    compute_paired_bootstrap_ci,
)

B_STAR = 500


def evaluate_single_cell(
    cell_name: str,
    dataset_name: str,
    baseline: str,  # "B2" or "B3"
    arm: str,        # "E0_prime", "E1a", "E1b", "E1c"
    budget: int,
    retriever: HybridSTIXRetriever,
    sa_index: StructureAwareIndex,
    df: pd.DataFrame,
    group_alias_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate one benchmark cell on dataset df."""
    use_chunking = (baseline == "B3")
    recalls = []
    mrrs = []
    per_query_records = []

    t0 = time.perf_counter()
    for idx, row in df.iterrows():
        raw_q = str(row["query"])
        gt = str(row.get("ground_truth", ""))

        # 1. Retrieve initial candidate chunks from corpus
        # retrieve returns top-15 chunks from hybrid retriever
        raw_retrieved = retriever.retrieve(raw_q, top_k=15, enable_query_chunking=use_chunking)

        # 2. Apply Structure-Aware Chunking arm logic
        if arm == "E0_prime":
            # Baseline splitter chunks, truncated to budget
            final_docs = truncate_to_token_budget(raw_retrieved, budget_tokens=budget)
        elif arm == "E1a":
            # Field chunks without sibling expansion, truncated to budget
            final_docs = truncate_to_token_budget(raw_retrieved, budget_tokens=budget)
        elif arm == "E1b":
            # Field chunks + Sibling expansion by technique_id under budget
            final_docs = sa_index.expand_siblings_e1b(raw_retrieved, budget_tokens=budget)
        elif arm == "E1c":
            # Field chunks + Random sibling control under budget (seed 42)
            final_docs = sa_index.expand_random_siblings_e1c(raw_retrieved, budget_tokens=budget, random_seed=42)
        else:
            raise ValueError(f"Unknown arm: {arm}")

        # 3. Compute metrics
        if dataset_name == "cti-taa":
            metrics = compute_retrieval_metrics_taa_alias_aware(
                final_docs, gt, group_alias_map=group_alias_map, k_values=[1, 3, 5, 10]
            )
        else:
            metrics = compute_retrieval_metrics_technique(
                final_docs,
                gt,
                k_values=[1, 3, 5, 10],
                subtechnique_parent_credit=True,
                subtechnique_direction="sub_credits_parent",
            )

        rec10 = metrics.get("Recall@10", 0.0)
        mrr = metrics.get("MRR", 0.0)
        recalls.append(rec10)
        mrrs.append(mrr)
        per_query_records.append({
            "idx": idx,
            "Recall@10": rec10,
            "MRR": mrr,
            "num_docs": len(final_docs),
            "tokens": sum(count_tokens(d.page_content) for d in final_docs),
        })

    elapsed = time.perf_counter() - t0
    s_per_query = elapsed / len(df) if len(df) > 0 else 0.0

    mean_rec = float(np.mean(recalls))
    mean_mrr = float(np.mean(mrrs))

    return {
        "cell_name": cell_name,
        "dataset": dataset_name,
        "baseline": baseline,
        "arm": arm,
        "budget": budget,
        "num_queries": len(df),
        "Recall@10": round(mean_rec, 4),
        "MRR": round(mean_mrr, 4),
        "elapsed_seconds": round(elapsed, 2),
        "s_per_query": round(s_per_query, 4),
        "per_query_recall": recalls,
        "per_query_mrr": mrrs,
        "per_query_records": per_query_records,
    }


def main():
    print("=" * 80)
    print("PHASE 3 OPTIMIZATION 2 (STRUCTURE-AWARE CHUNKING) BENCHMARK")
    print("Scope Reduction (Oct 28 Freeze): 14 Discrete Benchmark Cells")
    print(f"Hardware: os.cpu_count() = {os.cpu_count()}, Torch threads = {torch.get_num_threads()}")
    print("=" * 80)

    out_dir = REPO_ROOT / "results" / "phase_3"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "o2_benchmark_results.json"

    # Execution Table & Runtime Estimates
    cells_plan = [
        {"cell": "C01", "dataset": "cti-ate", "baseline": "B2", "arm": "E0_prime", "budget": B_STAR, "queries": 60, "est_s": "45s"},
        {"cell": "C02", "dataset": "cti-ate", "baseline": "B2", "arm": "E1b",      "budget": B_STAR, "queries": 60, "est_s": "45s"},
        {"cell": "C03", "dataset": "cti-ate", "baseline": "B3", "arm": "E0_prime", "budget": B_STAR, "queries": 60, "est_s": "60s"},
        {"cell": "C04", "dataset": "cti-ate", "baseline": "B3", "arm": "E1b",      "budget": B_STAR, "queries": 60, "est_s": "60s"},
        {"cell": "C05", "dataset": "CTI-ATTACK", "baseline": "B2", "arm": "E0_prime", "budget": B_STAR, "queries": 229, "est_s": "150s"},
        {"cell": "C06", "dataset": "CTI-ATTACK", "baseline": "B2", "arm": "E1b",      "budget": B_STAR, "queries": 229, "est_s": "150s"},
        {"cell": "C07", "dataset": "CTI-ATTACK", "baseline": "B3", "arm": "E0_prime", "budget": B_STAR, "queries": 229, "est_s": "210s"},
        {"cell": "C08", "dataset": "CTI-ATTACK", "baseline": "B3", "arm": "E1b",      "budget": B_STAR, "queries": 229, "est_s": "210s"},
        {"cell": "C09", "dataset": "cti-ate", "baseline": "B2", "arm": "E1a",      "budget": B_STAR, "queries": 60, "est_s": "45s"},
        {"cell": "C10", "dataset": "cti-ate", "baseline": "B2", "arm": "E1c",      "budget": B_STAR, "queries": 60, "est_s": "45s"},
        {"cell": "C11", "dataset": "cti-ate", "baseline": "B2", "arm": "E1b",      "budget": 1000,   "queries": 60, "est_s": "45s"},
        {"cell": "C12", "dataset": "cti-ate", "baseline": "B2", "arm": "E1b",      "budget": 2000,   "queries": 60, "est_s": "45s"},
        {"cell": "C13", "dataset": "cti-ate", "baseline": "B2", "arm": "E1b",      "budget": 4000,   "queries": 60, "est_s": "45s"},
        {"cell": "C14", "dataset": "cti-taa", "baseline": "B2", "arm": "E1b_vs_E0", "budget": B_STAR, "queries": 50, "est_s": "50s"},
    ]

    print("\nPlanned 14 Benchmark Cells:")
    print(f"{'Cell':<5} | {'Dataset':<11} | {'Base':<4} | {'Arm':<10} | {'Budget':<6} | {'Queries':<7} | {'Est. Time':<9}")
    print("-" * 65)
    for c in cells_plan:
        print(f"{c['cell']:<5} | {c['dataset']:<11} | {c['baseline']:<4} | {c['arm']:<10} | {c['budget']:<6} | {c['queries']:<7} | {c['est_s']:<9}")

    print("\nLoading Knowledge Base and Indexing...")
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()
    retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")

    print("Building Structure-Aware Field Chunks (E1a)...")
    field_chunks = build_field_chunks_e1a(stix_kb)
    sa_index = StructureAwareIndex(field_chunks)
    print(f"StructureAwareIndex ready: {len(field_chunks)} chunks across {len(sa_index.all_technique_ids)} techniques.")

    # Load datasets
    ds_ate = load_benchmark_dataset("cti-ate").df
    ds_att = load_benchmark_dataset("CTI-ATTACK").df
    ds_taa = load_benchmark_dataset("cti-taa").df

    results = {}
    timing_report = {
        "hardware": {
            "os_cpu_count": os.cpu_count(),
            "torch_threads": torch.get_num_threads(),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "4"),
        },
        "cells": {},
    }

    # 1. Order 1: cti-ate B2 and B3 for E0' and E1b
    print("\n" + "=" * 60)
    print("ORDER 1: cti-ate (B2 & B3 for E0' and E1b at B*)")
    print("=" * 60)

    # Measure cell C01 sequentially (without parallelism)
    res_c01 = evaluate_single_cell("C01_cti-ate_B2_E0prime", "cti-ate", "B2", "E0_prime", B_STAR, retriever, sa_index, ds_ate)
    results["C01"] = res_c01
    timing_report["cells"]["C01_sequential"] = {
        "s_per_query": res_c01["s_per_query"],
        "elapsed_seconds": res_c01["elapsed_seconds"],
    }
    print(f"C01 (Sequential): Recall@10={res_c01['Recall@10']}, MRR={res_c01['MRR']} | {res_c01['s_per_query']} s/query")

    res_c02 = evaluate_single_cell("C02_cti-ate_B2_E1b", "cti-ate", "B2", "E1b", B_STAR, retriever, sa_index, ds_ate)
    results["C02"] = res_c02
    print(f"C02: Recall@10={res_c02['Recall@10']}, MRR={res_c02['MRR']} | {res_c02['s_per_query']} s/query")

    res_c03 = evaluate_single_cell("C03_cti-ate_B3_E0prime", "cti-ate", "B3", "E0_prime", B_STAR, retriever, sa_index, ds_ate)
    results["C03"] = res_c03
    print(f"C03: Recall@10={res_c03['Recall@10']}, MRR={res_c03['MRR']} | {res_c03['s_per_query']} s/query")

    res_c04 = evaluate_single_cell("C04_cti-ate_B3_E1b", "cti-ate", "B3", "E1b", B_STAR, retriever, sa_index, ds_ate)
    results["C04"] = res_c04
    print(f"C04: Recall@10={res_c04['Recall@10']}, MRR={res_c04['MRR']} | {res_c04['s_per_query']} s/query")

    # 2. Order 2: CTI-ATTACK B2 and B3 for E0' and E1b
    print("\n" + "=" * 60)
    print("ORDER 2: CTI-ATTACK (B2 & B3 for E0' and E1b at B*)")
    print("=" * 60)

    res_c05 = evaluate_single_cell("C05_CTI-ATTACK_B2_E0prime", "CTI-ATTACK", "B2", "E0_prime", B_STAR, retriever, sa_index, ds_att)
    results["C05"] = res_c05
    print(f"C05: Recall@10={res_c05['Recall@10']}, MRR={res_c05['MRR']} | {res_c05['s_per_query']} s/query")

    res_c06 = evaluate_single_cell("C06_CTI-ATTACK_B2_E1b", "CTI-ATTACK", "B2", "E1b", B_STAR, retriever, sa_index, ds_att)
    results["C06"] = res_c06
    print(f"C06: Recall@10={res_c06['Recall@10']}, MRR={res_c06['MRR']} | {res_c06['s_per_query']} s/query")

    res_c07 = evaluate_single_cell("C07_CTI-ATTACK_B3_E0prime", "CTI-ATTACK", "B3", "E0_prime", B_STAR, retriever, sa_index, ds_att)
    results["C07"] = res_c07
    print(f"C07: Recall@10={res_c07['Recall@10']}, MRR={res_c07['MRR']} | {res_c07['s_per_query']} s/query")

    res_c08 = evaluate_single_cell("C08_CTI-ATTACK_B3_E1b", "CTI-ATTACK", "B3", "E1b", B_STAR, retriever, sa_index, ds_att)
    results["C08"] = res_c08
    print(f"C08: Recall@10={res_c08['Recall@10']}, MRR={res_c08['MRR']} | {res_c08['s_per_query']} s/query")

    # 3. Order 3: Exploratory controls & Secondary Budgets
    print("\n" + "=" * 60)
    print("ORDER 3: Exploratory Controls & Secondary Budgets (cti-ate)")
    print("=" * 60)

    res_c09 = evaluate_single_cell("C09_cti-ate_B2_E1a", "cti-ate", "B2", "E1a", B_STAR, retriever, sa_index, ds_ate)
    results["C09"] = res_c09
    print(f"C09 (E1a field chunks): Recall@10={res_c09['Recall@10']}, MRR={res_c09['MRR']}")

    res_c10 = evaluate_single_cell("C10_cti-ate_B2_E1c", "cti-ate", "B2", "E1c", B_STAR, retriever, sa_index, ds_ate)
    results["C10"] = res_c10
    print(f"C10 (E1c random control): Recall@10={res_c10['Recall@10']}, MRR={res_c10['MRR']}")

    res_c11 = evaluate_single_cell("C11_cti-ate_B2_E1b_B1000", "cti-ate", "B2", "E1b", 1000, retriever, sa_index, ds_ate)
    results["C11"] = res_c11
    print(f"C11 (B=1000): Recall@10={res_c11['Recall@10']}, MRR={res_c11['MRR']}")

    res_c12 = evaluate_single_cell("C12_cti-ate_B2_E1b_B2000", "cti-ate", "B2", "E1b", 2000, retriever, sa_index, ds_ate)
    results["C12"] = res_c12
    print(f"C12 (B=2000): Recall@10={res_c12['Recall@10']}, MRR={res_c12['MRR']}")

    res_c13 = evaluate_single_cell("C13_cti-ate_B2_E1b_B4000", "cti-ate", "B2", "E1b", 4000, retriever, sa_index, ds_ate)
    results["C13"] = res_c13
    print(f"C13 (B=4000): Recall@10={res_c13['Recall@10']}, MRR={res_c13['MRR']}")

    # 4. Order 4: cti-taa No-Regression Check
    print("\n" + "=" * 60)
    print("ORDER 4: cti-taa No-Regression Check (B2, B*)")
    print("=" * 60)

    res_taa_e0 = evaluate_single_cell("C14a_cti-taa_B2_E0prime", "cti-taa", "B2", "E0_prime", B_STAR, retriever, sa_index, ds_taa, group_alias_map)
    res_taa_e1b = evaluate_single_cell("C14b_cti-taa_B2_E1b", "cti-taa", "B2", "E1b", B_STAR, retriever, sa_index, ds_taa, group_alias_map)
    delta_taa = res_taa_e1b["Recall@10"] - res_taa_e0["Recall@10"]
    delta_mrr = res_taa_e1b["MRR"] - res_taa_e0["MRR"]
    no_regression_pass = (delta_taa >= -0.05)

    results["C14"] = {
        "E0_prime": res_taa_e0,
        "E1b": res_taa_e1b,
        "delta_Recall@10": round(delta_taa, 4),
        "delta_MRR": round(delta_mrr, 4),
        "threshold": -0.05,
        "no_regression_pass": no_regression_pass,
    }
    print(f"cti-taa E0': Recall@10={res_taa_e0['Recall@10']}, MRR={res_taa_e0['MRR']}")
    print(f"cti-taa E1b: Recall@10={res_taa_e1b['Recall@10']}, MRR={res_taa_e1b['MRR']}")
    print(f"Delta Recall@10: {delta_taa:+.4f} (>= -0.05: {no_regression_pass})")

    # 5. Compute Family P2 Primary Confirmatory Hypothesis Contrasts
    print("\n" + "=" * 60)
    print("FAMILY P2 PRIMARY CONFIRMATORY CONTRASTS (Holm-Bonferroni)")
    print("=" * 60)

    contrasts = [
        ("H1_cti-ate_B2", res_c02["per_query_recall"], res_c01["per_query_recall"], res_c02["per_query_mrr"], res_c01["per_query_mrr"]),
        ("H2_cti-ate_B3", res_c04["per_query_recall"], res_c03["per_query_recall"], res_c04["per_query_mrr"], res_c03["per_query_mrr"]),
        ("H3_CTI-ATTACK_B2", res_c06["per_query_recall"], res_c05["per_query_recall"], res_c06["per_query_mrr"], res_c05["per_query_mrr"]),
        ("H4_CTI-ATTACK_B3", res_c08["per_query_recall"], res_c07["per_query_recall"], res_c08["per_query_mrr"], res_c07["per_query_mrr"]),
    ]

    p2_results = []
    for h_name, rec_e1b, rec_e0, mrr_e1b, mrr_e0 in contrasts:
        ci_rec = compute_paired_bootstrap_ci(np.array(rec_e1b), np.array(rec_e0), n_resamples=10000, seed=42)
        ci_mrr = compute_paired_bootstrap_ci(np.array(mrr_e1b), np.array(mrr_e0), n_resamples=10000, seed=42)
        p2_results.append({
            "hypothesis": h_name,
            "raw_p_value": ci_rec["p_value"],
            "mean_delta_recall": ci_rec["mean_delta"],
            "ci_recall": [ci_rec["ci_lower"], ci_rec["ci_upper"]],
            "mean_delta_mrr": ci_mrr["mean_delta"],
            "ci_mrr": [ci_mrr["ci_lower"], ci_mrr["ci_upper"]],
            "p_value_mrr": ci_mrr["p_value"],
        })

    # Sort by p-value ascending for Holm-Bonferroni step-down correction
    p2_results.sort(key=lambda x: x["raw_p_value"])
    m = len(p2_results)  # 4
    alpha = 0.05
    for rank, item in enumerate(p2_results, start=1):
        crit = alpha / (m - rank + 1)
        item["holm_rank"] = rank
        item["holm_critical_value"] = round(crit, 5)
        item["significant_holm"] = bool(item["raw_p_value"] <= crit)
        print(f"[{item['hypothesis']}] Delta Recall={item['mean_delta_recall']:+.4f} [{item['ci_recall'][0]:+.4f}, {item['ci_recall'][1]:+.4f}] | raw p={item['raw_p_value']:.4f} vs Holm crit={crit:.5f} -> Sig: {item['significant_holm']}")

    benchmark_summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware_and_parallelism": timing_report,
        "primary_budget_B_star": B_STAR,
        "cells": results,
        "family_p2_contrasts": p2_results,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2)

    print(f"\nAll 14 cells completed! Results saved to {out_file}")


if __name__ == "__main__":
    main()
