"""Compute Family P1 Contrasts, Paired Bootstrap CIs, Holm-Bonferroni Correction,
and compile full Phase 2 benchmark results artifact.

Contrasts in Family P1 (cti-taa on E0-STIX-ALL, alpha=0.05):
1. B2 Recall@10 (V1 vs V0)
2. B2 MRR (V1 vs V0)
3. B2 Recall@10 (V1 vs V3)
4. B2 MRR (V1 vs V3)
5. B3 Recall@10 (V1 vs V0)
6. B3 MRR (V1 vs V0)
7. B3 Recall@10 (V1 vs V3)
8. B3 MRR (V1 vs V3)
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

# Ensure repo root on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.retriever import HybridSTIXRetriever
from src.entity_resolver import CyberEntityResolver
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    compute_retrieval_metrics_taa_alias_aware,
)
from src.manifest import generate_experiment_manifest


def holm_bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[Tuple[float, float, bool]]:
    """Holm-Bonferroni step-down procedure."""
    m = len(p_values)
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


def parse_48_cells_from_log(log_path: Path) -> Dict[str, Any]:
    """Parse all 48 cell summaries from task-2841.log."""
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    current_kb = None
    current_baseline = None
    current_variant = None

    evaluations = {
        "E0-STIX-ALL": {"is_primary": True, "total_active_objects": 2062, "baselines": {}},
        "E0-STIX-ENT": {"is_primary": False, "total_active_objects": 1698, "baselines": {}},
    }

    for kb in ["E0-STIX-ALL", "E0-STIX-ENT"]:
        for b in ["B2", "B3"]:
            evaluations[kb]["baselines"][b] = {
                "name": "MiniLM-MaxSim-Windows" if b == "B3" else "MiniLM-Truncated-256",
                "variants": {},
            }
            for v in ["V0", "V1", "V2", "V3"]:
                evaluations[kb]["baselines"][b]["variants"][v] = {}

    for line in lines:
        m_var = re.search(r">>> Running Variant (V[0-3]) under (B[2-3]) on (E0-STIX-[A-Z]+)", line)
        if m_var:
            current_variant = m_var.group(1)
            current_baseline = m_var.group(2)
            current_kb = m_var.group(3)
            continue

        m_res = re.search(
            r"\s*(cti-taa|cti-ate|CTI-ATTACK):\s*Rec@10=([\d\.]+)\s*\|\s*MRR=([\d\.]+)\s*\|\s*Lat\(mean/p95\)=([\d\.]+)/([\d\.]+)ms",
            line,
        )
        if m_res and current_kb and current_baseline and current_variant:
            ds = m_res.group(1)
            rec10 = float(m_res.group(2))
            mrr = float(m_res.group(3))
            lat_mean = float(m_res.group(4))
            lat_p95 = float(m_res.group(5))
            num_q = 50 if ds == "cti-taa" else (60 if ds == "cti-ate" else 229)
            evaluations[current_kb]["baselines"][current_baseline]["variants"][current_variant][ds] = {
                "num_queries": num_q,
                "latency_mean_ms": lat_mean,
                "latency_p95_ms": lat_p95,
                "Recall@10": rec10,
                "MRR": mrr,
            }

    return evaluations


def run_p1_evaluation():
    print("=" * 75, flush=True)
    print("PHASE 2: FAMILY P1 PER-QUERY EVALUATION & BOOTSTRAP SIGNIFICANCE", flush=True)
    print("=" * 75, flush=True)

    results_dir = Path("results/phase_2")
    results_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = results_dir / "p1_eval_checkpoint.json"

    # Check existing checkpoint
    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            per_query_data = json.load(f)
        print(f"Loaded existing checkpoint with keys: {list(per_query_data.keys())}", flush=True)
    else:
        per_query_data = {}

    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()
    retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")
    resolver = CyberEntityResolver(stix_kb=stix_kb, min_alias_len=3, random_seed=42)

    ds_taa = load_benchmark_dataset("cti-taa")
    df_taa = ds_taa.df

    # Evaluate cti-taa on E0-STIX-ALL for B2 and B3 across variants
    for b_code, enable_chunking in [("B2", False), ("B3", True)]:
        for variant in ["V0", "V1", "V2", "V3"]:
            key = f"E0-STIX-ALL_{b_code}_{variant}_cti-taa"
            if key in per_query_data and len(per_query_data[key]) == len(df_taa):
                print(f"Skipping {key} (already evaluated, {len(per_query_data[key])} queries).", flush=True)
                continue

            print(f"\nEvaluating {key} (50 queries)...", flush=True)
            rows = []
            for idx, row in tqdm(df_taa.iterrows(), total=len(df_taa), desc=f"{b_code}-{variant}"):
                raw_q = str(row["query"])
                gt = str(row.get("ground_truth", ""))

                t_res0 = time.time()
                exp_q, detected = resolver.expand_query(raw_q, variant=variant, max_expansion_tokens=64)
                res_ms = (time.time() - t_res0) * 1000

                t_ret0 = time.time()
                docs = retriever.retrieve(exp_q, top_k=10, enable_query_chunking=enable_chunking)
                ret_ms = (time.time() - t_ret0) * 1000

                metrics = compute_retrieval_metrics_taa_alias_aware(
                    docs, gt, k_values=[1, 3, 5, 10], group_alias_map=group_alias_map
                )

                rows.append({
                    "idx": idx,
                    "query": raw_q,
                    "expanded_query": exp_q,
                    "detected_entities": [
                        {
                            "matched_text": getattr(e, "matched_text", str(e)),
                            "canonical_name": getattr(e, "canonical_name", ""),
                            "mitre_id": getattr(e, "mitre_id", ""),
                            "entity_type": getattr(e, "entity_type", ""),
                        }
                        for e in detected
                    ],
                    "ground_truth": gt,
                    "Recall@10": metrics["Recall@10"],
                    "MRR": metrics["MRR"],
                    "retrieved_mitre_ids": [
                        doc.metadata.get("mitre_id", "") for doc in docs if hasattr(doc, "metadata")
                    ],
                    "latency_ms": round(res_ms + ret_ms, 2),
                })

            per_query_data[key] = rows
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(per_query_data, f, indent=2)
            print(f"Saved checkpoint: {key} (Recall@10={np.mean([r['Recall@10'] for r in rows]):.4f}, MRR={np.mean([r['MRR'] for r in rows]):.4f})", flush=True)

    # Compute Family P1 contrasts
    print("\n" + "=" * 75, flush=True)
    print("COMPUTING FAMILY P1 CONTRASTS (10,000 PAIRED BOOTSTRAP RESAMPLES, SEED 42)", flush=True)
    print("=" * 75, flush=True)

    # 8 contrasts:
    # 1. B2 Recall@10 (V1 vs V0)
    # 2. B2 MRR (V1 vs V0)
    # 3. B2 Recall@10 (V1 vs V3)
    # 4. B2 MRR (V1 vs V3)
    # 5. B3 Recall@10 (V1 vs V0)
    # 6. B3 MRR (V1 vs V0)
    # 7. B3 Recall@10 (V1 vs V3)
    # 8. B3 MRR (V1 vs V3)
    contrast_specs = [
        ("B2", "Recall@10", "V1", "V0"),
        ("B2", "MRR", "V1", "V0"),
        ("B2", "Recall@10", "V1", "V3"),
        ("B2", "MRR", "V1", "V3"),
        ("B3", "Recall@10", "V1", "V0"),
        ("B3", "MRR", "V1", "V0"),
        ("B3", "Recall@10", "V1", "V3"),
        ("B3", "MRR", "V1", "V3"),
    ]

    p1_results = []
    raw_p_values = []

    for b_code, metric, arm_after, arm_before in contrast_specs:
        key_after = f"E0-STIX-ALL_{b_code}_{arm_after}_cti-taa"
        key_before = f"E0-STIX-ALL_{b_code}_{arm_before}_cti-taa"

        rows_after = per_query_data[key_after]
        rows_before = per_query_data[key_before]

        scores_after = np.array([r[metric] for r in rows_after], dtype=float)
        scores_before = np.array([r[metric] for r in rows_before], dtype=float)

        diffs = scores_after - scores_before
        wins = int(np.sum(diffs > 1e-4))
        ties = int(np.sum(np.abs(diffs) <= 1e-4))
        losses = int(np.sum(diffs < -1e-4))

        ci_res = compute_paired_bootstrap_ci(scores_before, scores_after, n_resamples=10000, seed=42)
        raw_p_values.append(ci_res["p_value"])

        rec = {
            "baseline": b_code,
            "metric": metric,
            "contrast": f"{arm_after} vs {arm_before}",
            "arm_after": arm_after,
            "arm_before": arm_before,
            "mean_before": round(ci_res["mean_before"], 4),
            "mean_after": round(ci_res["mean_after"], 4),
            "mean_delta": round(ci_res["mean_delta"], 4),
            "ci_lower": round(ci_res["ci_lower"], 4),
            "ci_upper": round(ci_res["ci_upper"], 4),
            "raw_p_value": ci_res["p_value"],
            "wins": wins,
            "ties": ties,
            "losses": losses,
        }
        p1_results.append(rec)

    # Apply Holm-Bonferroni correction
    holm_results = holm_bonferroni_correction(raw_p_values, alpha=0.05)
    for i, rec in enumerate(p1_results):
        raw_p, adj_alpha, is_sig = holm_results[i]
        rec["holm_raw_p"] = raw_p
        rec["holm_adj_alpha"] = adj_alpha
        rec["holm_is_significant"] = is_sig
        print(f"P1 #{i+1} [{rec['baseline']} {rec['metric']} {rec['contrast']}]: delta={rec['mean_delta']:+.4f} [95% CI: {rec['ci_lower']:+.4f}, {rec['ci_upper']:+.4f}] | raw p={raw_p:.4f} vs adj_alpha={adj_alpha:.4f} -> Sig: {is_sig} (W/T/L: {rec['wins']}/{rec['ties']}/{rec['losses']})", flush=True)

    # Helped and Hurt inspection under B3: V1 vs V0
    rows_v0 = per_query_data["E0-STIX-ALL_B3_V0_cti-taa"]
    rows_v1 = per_query_data["E0-STIX-ALL_B3_V1_cti-taa"]
    diff_records = []
    for i in range(len(rows_v0)):
        r0 = rows_v0[i]
        r1 = rows_v1[i]
        delta_rec10 = r1["Recall@10"] - r0["Recall@10"]
        delta_mrr = r1["MRR"] - r0["MRR"]
        diff_records.append({
            "idx": r0["idx"],
            "query": r0["query"],
            "ground_truth": r0["ground_truth"],
            "expanded_query": r1["expanded_query"],
            "detected_entities": r1["detected_entities"],
            "delta_Recall@10": round(delta_rec10, 4),
            "delta_MRR": round(delta_mrr, 4),
            "v0_Recall@10": r0["Recall@10"],
            "v1_Recall@10": r1["Recall@10"],
            "v0_MRR": r0["MRR"],
            "v1_MRR": r1["MRR"],
            "v0_retrieved_ids": r0["retrieved_mitre_ids"],
            "v1_retrieved_ids": r1["retrieved_mitre_ids"],
        })

    # Sort by delta MRR then delta Recall
    sorted_helped = sorted(diff_records, key=lambda x: (x["delta_MRR"], x["delta_Recall@10"]), reverse=True)[:5]
    sorted_hurt = sorted(diff_records, key=lambda x: (x["delta_MRR"], x["delta_Recall@10"]))[:5]

    # Parse 48 cell summaries from task-2841.log
    log_path = Path(r"C:\Users\Akshitha Reddy\.gemini\antigravity-ide\brain\c4a6d059-0f12-4ec3-9728-d6b23631bc4c\.system_generated\tasks\task-2841.log")
    parsed_evals = parse_48_cells_from_log(log_path)

    full_output = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evaluations": parsed_evals,
        "primary_family_p1_contrasts": p1_results,
        "query_case_inspections_b3_v1_vs_v0": {
            "top_5_helped": sorted_helped,
            "top_5_hurt": sorted_hurt,
        },
    }

    out_file = results_dir / "o1_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    manifest_file = generate_experiment_manifest(results_dir, "manifest_phase2_o1.json")
    print(f"\nSaved final benchmark results to {out_file}", flush=True)
    print(f"Generated manifest at {manifest_file}", flush=True)


if __name__ == "__main__":
    run_p1_evaluation()
