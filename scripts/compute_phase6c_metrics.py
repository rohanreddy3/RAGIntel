"""Compute Phase 6C Generation Metrics and Statistical Contrasts.

Post-hoc Round 3 (Exploratory):
Evaluates Section 12 Generation Arms:
- E0'-HD-k200 on cti-ate (60) and CTI-ATTACK (229) at B*=500 tokens
- cti-taa V0h (50) and Vrel (50) under baseline B2

Contrasts:
(a) E0'-HD-k200 vs LLM-only (paired bootstrap 10,000, seed 42)
(b) E0'-HD-k200 vs E0' (paired bootstrap 10,000, seed 42)
(c) cti-taa V0h vs LLM-only and vs V0
(d) cti-taa Vrel vs LLM-only and vs V1

Outputs saved to results/phase_6c/.
"""

import gzip
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.retrieval_eval import (
    extract_technique_ids_from_text,
    parse_ground_truth_techniques,
    normalize_group_name,
    compute_paired_bootstrap_ci,
)


def compute_technique_f1(pred_techs: Set[str], gt_techs: Set[str]) -> Dict[str, float]:
    """Compute strict and sub_credit Precision, Recall, and F1."""
    if not gt_techs:
        return {
            "p_strict": 0.0, "r_strict": 0.0, "f1_strict": 0.0,
            "p_sub": 0.0, "r_sub": 0.0, "f1_sub": 0.0,
        }

    # Strict match
    tp_strict = len(pred_techs & gt_techs)
    p_strict = tp_strict / len(pred_techs) if pred_techs else 0.0
    r_strict = tp_strict / len(gt_techs)
    f1_strict = (2 * p_strict * r_strict / (p_strict + r_strict)) if (p_strict + r_strict) > 0 else 0.0

    # Sub-technique credits parent match
    credited_pred = set(pred_techs)
    for t in pred_techs:
        if "." in t:
            credited_pred.add(t.split(".")[0])

    tp_sub = len(credited_pred & gt_techs)
    p_sub = tp_sub / len(credited_pred) if credited_pred else 0.0
    r_sub = tp_sub / len(gt_techs)
    f1_sub = (2 * p_sub * r_sub / (p_sub + r_sub)) if (p_sub + r_sub) > 0 else 0.0

    return {
        "p_strict": round(p_strict, 4),
        "r_strict": round(r_strict, 4),
        "f1_strict": round(f1_strict, 4),
        "p_sub": round(p_sub, 4),
        "r_sub": round(r_sub, 4),
        "f1_sub": round(f1_sub, 4),
    }


def score_group_match(
    raw_answer: str,
    gt_raw: str,
    group_alias_map: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    """Score threat group attribution under both Scorer Variants."""
    # SCORER VARIANT 1: Text-based Parsing from GT String
    parts = re.split(r"\(|\)|,|;|/|\balias\b|\balso known as\b|\bor\b|\band\b", gt_raw, flags=re.I)
    v1_candidates = [p.strip(" \t\n\r*\"'") for p in parts if len(p.strip(" \t\n\r*\"'")) >= 3]

    v1_exact = 0
    if v1_candidates:
        first_cand = v1_candidates[0]
        if re.search(r"\b" + re.escape(first_cand) + r"\b", raw_answer, re.I):
            v1_exact = 1

    v1_alias = v1_exact
    if v1_alias == 0:
        for cand in v1_candidates:
            if re.search(r"\b" + re.escape(cand) + r"\b", raw_answer, re.I):
                v1_alias = 1
                break

    # SCORER VARIANT 2: STIX Knowledge Base Ontology-Expanded
    raw_gt_norm = normalize_group_name(gt_raw)
    gt_canonical_name = None
    gt_canonical_id = None
    all_gt_aliases_text: Set[str] = set()

    for gid, gdata in group_alias_map.items():
        c_norm = normalize_group_name(gdata.get("canonical_name", ""))
        a_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == c_norm or raw_gt_norm in a_norms or any(a in raw_gt_norm for a in a_norms if len(a) > 3):
            gt_canonical_name = gdata.get("canonical_name", "")
            gt_canonical_id = gid
            all_gt_aliases_text.add(gid)
            all_gt_aliases_text.add(gt_canonical_name)
            all_gt_aliases_text.update(gdata.get("aliases", []))
            break

    v2_exact = 0
    if gt_canonical_id and re.search(r"\b" + re.escape(gt_canonical_id) + r"\b", raw_answer, re.I):
        v2_exact = 1
    elif gt_canonical_name and re.search(r"\b" + re.escape(gt_canonical_name) + r"\b", raw_answer, re.I):
        v2_exact = 1
    elif v1_exact == 1:
        v2_exact = 1

    v2_alias = v2_exact
    if v2_alias == 0:
        for alias in all_gt_aliases_text:
            if len(alias) >= 3 and re.search(r"\b" + re.escape(alias) + r"\b", raw_answer, re.I):
                v2_alias = 1
                break
        if v2_alias == 0 and v1_alias == 1:
            v2_alias = 1

    return {
        "v1_exact": v1_exact,
        "v1_alias": v1_alias,
        "v2_exact": v2_exact,
        "v2_alias": v2_alias,
    }


def compute_contrast_stats(
    scores_ctrl: List[float],
    scores_trt: List[float],
    metric_name: str,
    is_binary: bool,
    n_resamples: int = 10000,
    seed: int = 42,
) -> Tuple[Dict[str, Any], np.ndarray]:
    """Compute paired bootstrap CI + empirical p-value + exact sign test."""
    a = np.array(scores_ctrl, dtype=float)
    b = np.array(scores_trt, dtype=float)
    n = len(a)

    deltas = b - a
    mean_ctrl = float(np.mean(a))
    mean_trt = float(np.mean(b))
    obs_delta = float(np.mean(deltas))

    # Wins / Ties / Losses
    wins = int(np.sum(deltas > 1e-9))
    losses = int(np.sum(deltas < -1e-9))
    ties = n - wins - losses
    wtl = f"{wins}/{ties}/{losses}"

    # Bootstrap
    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n, size=(n_resamples, n))
    boot_deltas = np.mean(deltas[boot_idx], axis=1)

    ci_lower = float(np.percentile(boot_deltas, 2.5))
    ci_upper = float(np.percentile(boot_deltas, 97.5))

    centered = boot_deltas - obs_delta
    boot_p = float(np.mean(np.abs(centered) >= np.abs(obs_delta)))

    # Exact sign test on discordant pairs (wins vs losses)
    n_disc = wins + losses
    if n_disc == 0:
        sign_p = 1.0
    else:
        st_res = binomtest(wins, n_disc, p=0.5, alternative="two-sided")
        sign_p = float(st_res.pvalue)

    res = {
        "metric": metric_name,
        "is_binary": is_binary,
        "n_queries": n,
        "mean_control": round(mean_ctrl, 4),
        "mean_treatment": round(mean_trt, 4),
        "mean_delta": round(obs_delta, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "boot_p": round(boot_p, 4),
        "exact_sign_p": round(sign_p, 4),
        "wtl": wtl,
        "n_discordant": n_disc,
    }
    return res, boot_deltas


def main():
    print("=" * 80)
    print("PHASE 6C: EVALUATING GENERATION ARMS AND STATISTICAL CONTRASTS")
    print("=" * 80)

    out_dir = REPO_ROOT / "results" / "phase_6c"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = REPO_ROOT / ".cache" / "api_runner"

    # 1. Load benchmark datasets
    print("Loading benchmark ground truths...")
    df_ate = load_benchmark_dataset("cti-ate").df
    df_att = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df

    # 2. Load STIX knowledge base alias map
    print("Loading STIX Knowledge Base for alias map...")
    kb = load_stix_all_bundles()
    group_alias_map = kb.get_group_alias_map()

    # 3. Load responses from disk cache
    print("Loading cached answers from .cache/api_runner/...")

    def load_answers(arm_prefix: str, ds_name: str, n_rows: int) -> List[Dict[str, Any]]:
        records = []
        for idx in range(n_rows):
            fpath = cache_dir / f"{arm_prefix}_{ds_name}_row_{idx}.json"
            if not fpath.is_file():
                # Check alternative naming
                alt_fpath = cache_dir / f"{arm_prefix}_row_{idx}.json"
                if alt_fpath.is_file():
                    fpath = alt_fpath
                else:
                    raise FileNotFoundError(f"Missing cache file: {fpath}")
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            records.append(data)
        return records

    # cti-ate (60)
    ate_hd = load_answers("E0_prime_HD_k200", "cti-ate", 60)
    ate_e0 = load_answers("E0_prime", "cti-ate", 60)
    ate_llm = load_answers("LLM-only", "cti-ate", 60)

    # CTI-ATTACK (229)
    att_hd = load_answers("E0_prime_HD_k200", "CTI-ATTACK", 229)
    att_e0 = load_answers("E0_prime", "CTI-ATTACK", 229)
    att_llm = load_answers("LLM-only", "CTI-ATTACK", 229)

    # cti-taa (50)
    taa_v0h = load_answers("V0h", "cti-taa", 50)
    taa_vrel = load_answers("Vrel", "cti-taa", 50)
    taa_v0 = load_answers("cti-taa_B2_V0", "cti-taa", 50)
    taa_v1 = load_answers("cti-taa_B2_V1", "cti-taa", 50)
    taa_llm = load_answers("LLM-only", "cti-taa", 50)

    print("All cache files verified and loaded successfully.")

    # 4. Score queries
    per_query_rows = []

    # Helper for technique extraction scoring
    def score_tech_arm(arm_name: str, ds_name: str, df: pd.DataFrame, records: List[Dict[str, Any]]):
        scores_list = []
        for idx, row in df.iterrows():
            rec = records[idx]
            raw_ans = rec.get("raw_answer", "")
            gt_str = str(row.get("techniques", row.get("ground_truth", "")))
            gt_set = parse_ground_truth_techniques(gt_str)
            pred_set = extract_technique_ids_from_text(raw_ans)
            f1_dict = compute_technique_f1(pred_set, gt_set)

            item = {
                "dataset": ds_name,
                "arm": arm_name,
                "row_idx": idx,
                "query": str(row["query"]),
                "num_gt": len(gt_set),
                "num_pred": len(pred_set),
                "pred_techniques": ";".join(sorted(pred_set)),
                "gt_techniques": ";".join(sorted(gt_set)),
                **f1_dict,
                "latency_s": rec.get("latency_s", 0.0),
                "finish_reason": rec.get("finish_reason", ""),
            }
            per_query_rows.append(item)
            scores_list.append(item)
        return scores_list

    ate_hd_scores = score_tech_arm("E0_prime_HD_k200", "cti-ate", df_ate, ate_hd)
    ate_e0_scores = score_tech_arm("E0_prime", "cti-ate", df_ate, ate_e0)
    ate_llm_scores = score_tech_arm("LLM-only", "cti-ate", df_ate, ate_llm)

    att_hd_scores = score_tech_arm("E0_prime_HD_k200", "CTI-ATTACK", df_att, att_hd)
    att_e0_scores = score_tech_arm("E0_prime", "CTI-ATTACK", df_att, att_e0)
    att_llm_scores = score_tech_arm("LLM-only", "CTI-ATTACK", df_att, att_llm)

    # Helper for threat actor attribution scoring
    def score_taa_arm(arm_name: str, df: pd.DataFrame, records: List[Dict[str, Any]]):
        scores_list = []
        for idx, row in df.iterrows():
            rec = records[idx]
            raw_ans = rec.get("raw_answer", "")
            gt_str = str(row.get("group", row.get("ground_truth", "")))
            m_dict = score_group_match(raw_ans, gt_str, group_alias_map)

            item = {
                "dataset": "cti-taa",
                "arm": arm_name,
                "row_idx": idx,
                "query": str(row["query"]),
                "gt_group": gt_str,
                "raw_answer": raw_ans[:200].replace("\n", " "),
                **m_dict,
                "latency_s": rec.get("latency_s", 0.0),
                "finish_reason": rec.get("finish_reason", ""),
            }
            per_query_rows.append(item)
            scores_list.append(item)
        return scores_list

    taa_v0h_scores = score_taa_arm("V0h", df_taa, taa_v0h)
    taa_vrel_scores = score_taa_arm("Vrel", df_taa, taa_vrel)
    taa_v0_scores = score_taa_arm("cti-taa_B2_V0", df_taa, taa_v0)
    taa_v1_scores = score_taa_arm("cti-taa_B2_V1", df_taa, taa_v1)
    taa_llm_scores = score_taa_arm("LLM-only", df_taa, taa_llm)

    # Save per-query CSV
    df_per_query = pd.DataFrame(per_query_rows)
    df_per_query.to_csv(out_dir / "per_query_scores.csv", index=False)
    print(f"Saved per-query scores to {out_dir / 'per_query_scores.csv'}")

    # 5. Compute summary table per arm
    summary_metrics = {
        "cti-ate": {
            "E0_prime_HD_k200": {
                "f1_strict": float(np.mean([s["f1_strict"] for s in ate_hd_scores])),
                "f1_sub": float(np.mean([s["f1_sub"] for s in ate_hd_scores])),
                "p_strict": float(np.mean([s["p_strict"] for s in ate_hd_scores])),
                "r_strict": float(np.mean([s["r_strict"] for s in ate_hd_scores])),
            },
            "E0_prime": {
                "f1_strict": float(np.mean([s["f1_strict"] for s in ate_e0_scores])),
                "f1_sub": float(np.mean([s["f1_sub"] for s in ate_e0_scores])),
                "p_strict": float(np.mean([s["p_strict"] for s in ate_e0_scores])),
                "r_strict": float(np.mean([s["r_strict"] for s in ate_e0_scores])),
            },
            "LLM-only": {
                "f1_strict": float(np.mean([s["f1_strict"] for s in ate_llm_scores])),
                "f1_sub": float(np.mean([s["f1_sub"] for s in ate_llm_scores])),
                "p_strict": float(np.mean([s["p_strict"] for s in ate_llm_scores])),
                "r_strict": float(np.mean([s["r_strict"] for s in ate_llm_scores])),
            },
        },
        "CTI-ATTACK": {
            "E0_prime_HD_k200": {
                "f1_strict": float(np.mean([s["f1_strict"] for s in att_hd_scores])),
                "f1_sub": float(np.mean([s["f1_sub"] for s in att_hd_scores])),
                "p_strict": float(np.mean([s["p_strict"] for s in att_hd_scores])),
                "r_strict": float(np.mean([s["r_strict"] for s in att_hd_scores])),
            },
            "E0_prime": {
                "f1_strict": float(np.mean([s["f1_strict"] for s in att_e0_scores])),
                "f1_sub": float(np.mean([s["f1_sub"] for s in att_e0_scores])),
                "p_strict": float(np.mean([s["p_strict"] for s in att_e0_scores])),
                "r_strict": float(np.mean([s["r_strict"] for s in att_e0_scores])),
            },
            "LLM-only": {
                "f1_strict": float(np.mean([s["f1_strict"] for s in att_llm_scores])),
                "f1_sub": float(np.mean([s["f1_sub"] for s in att_llm_scores])),
                "p_strict": float(np.mean([s["p_strict"] for s in att_llm_scores])),
                "r_strict": float(np.mean([s["r_strict"] for s in att_llm_scores])),
            },
        },
        "cti-taa": {
            "V0h": {
                "v1_exact": float(np.mean([s["v1_exact"] for s in taa_v0h_scores])),
                "v1_alias": float(np.mean([s["v1_alias"] for s in taa_v0h_scores])),
                "v2_exact": float(np.mean([s["v2_exact"] for s in taa_v0h_scores])),
                "v2_alias": float(np.mean([s["v2_alias"] for s in taa_v0h_scores])),
            },
            "Vrel": {
                "v1_exact": float(np.mean([s["v1_exact"] for s in taa_vrel_scores])),
                "v1_alias": float(np.mean([s["v1_alias"] for s in taa_vrel_scores])),
                "v2_exact": float(np.mean([s["v2_exact"] for s in taa_vrel_scores])),
                "v2_alias": float(np.mean([s["v2_alias"] for s in taa_vrel_scores])),
            },
            "cti-taa_B2_V0": {
                "v1_exact": float(np.mean([s["v1_exact"] for s in taa_v0_scores])),
                "v1_alias": float(np.mean([s["v1_alias"] for s in taa_v0_scores])),
                "v2_exact": float(np.mean([s["v2_exact"] for s in taa_v0_scores])),
                "v2_alias": float(np.mean([s["v2_alias"] for s in taa_v0_scores])),
            },
            "cti-taa_B2_V1": {
                "v1_exact": float(np.mean([s["v1_exact"] for s in taa_v1_scores])),
                "v1_alias": float(np.mean([s["v1_alias"] for s in taa_v1_scores])),
                "v2_exact": float(np.mean([s["v2_exact"] for s in taa_v1_scores])),
                "v2_alias": float(np.mean([s["v2_alias"] for s in taa_v1_scores])),
            },
            "LLM-only": {
                "v1_exact": float(np.mean([s["v1_exact"] for s in taa_llm_scores])),
                "v1_alias": float(np.mean([s["v1_alias"] for s in taa_llm_scores])),
                "v2_exact": float(np.mean([s["v2_exact"] for s in taa_llm_scores])),
                "v2_alias": float(np.mean([s["v2_alias"] for s in taa_llm_scores])),
            },
        },
    }

    with open(out_dir / "summary_metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)
    print(f"Saved summary metrics to {out_dir / 'summary_metrics.json'}")

    # 6. Run Declared Statistical Contrasts
    print("\nRunning declared statistical contrasts (10,000 resamples, seed 42)...")
    contrasts_list = []
    boot_distributions = {}

    contrast_definitions = [
        # (a) E0'-HD-k200 vs LLM-only
        {
            "id": "C_HD_vs_LLM_ate",
            "dataset": "cti-ate",
            "contrast": "E0'-HD-k200 vs LLM-only",
            "treatment_scores": ate_hd_scores,
            "control_scores": ate_llm_scores,
            "metrics": [("f1_strict", False), ("f1_sub", False), ("r_strict", False), ("p_strict", False)],
        },
        {
            "id": "C_HD_vs_LLM_att",
            "dataset": "CTI-ATTACK",
            "contrast": "E0'-HD-k200 vs LLM-only",
            "treatment_scores": att_hd_scores,
            "control_scores": att_llm_scores,
            "metrics": [("f1_strict", False), ("f1_sub", False), ("r_strict", False), ("p_strict", False)],
        },
        # (b) E0'-HD-k200 vs E0'
        {
            "id": "C_HD_vs_E0_ate",
            "dataset": "cti-ate",
            "contrast": "E0'-HD-k200 vs E0'",
            "treatment_scores": ate_hd_scores,
            "control_scores": ate_e0_scores,
            "metrics": [("f1_strict", False), ("f1_sub", False), ("r_strict", False), ("p_strict", False)],
        },
        {
            "id": "C_HD_vs_E0_att",
            "dataset": "CTI-ATTACK",
            "contrast": "E0'-HD-k200 vs E0'",
            "treatment_scores": att_hd_scores,
            "control_scores": att_e0_scores,
            "metrics": [("f1_strict", False), ("f1_sub", False), ("r_strict", False), ("p_strict", False)],
        },
        # (c) cti-taa V0h vs LLM-only and vs V0
        {
            "id": "C_V0h_vs_LLM_taa",
            "dataset": "cti-taa",
            "contrast": "V0h vs LLM-only",
            "treatment_scores": taa_v0h_scores,
            "control_scores": taa_llm_scores,
            "metrics": [("v1_exact", True), ("v1_alias", True), ("v2_exact", True), ("v2_alias", True)],
        },
        {
            "id": "C_V0h_vs_V0_taa",
            "dataset": "cti-taa",
            "contrast": "V0h vs V0",
            "treatment_scores": taa_v0h_scores,
            "control_scores": taa_v0_scores,
            "metrics": [("v1_exact", True), ("v1_alias", True), ("v2_exact", True), ("v2_alias", True)],
        },
        # (d) cti-taa Vrel vs LLM-only and vs V1
        {
            "id": "C_Vrel_vs_LLM_taa",
            "dataset": "cti-taa",
            "contrast": "Vrel vs LLM-only",
            "treatment_scores": taa_vrel_scores,
            "control_scores": taa_llm_scores,
            "metrics": [("v1_exact", True), ("v1_alias", True), ("v2_exact", True), ("v2_alias", True)],
        },
        {
            "id": "C_Vrel_vs_V1_taa",
            "dataset": "cti-taa",
            "contrast": "Vrel vs V1",
            "treatment_scores": taa_vrel_scores,
            "control_scores": taa_v1_scores,
            "metrics": [("v1_exact", True), ("v1_alias", True), ("v2_exact", True), ("v2_alias", True)],
        },
    ]

    for cdef in contrast_definitions:
        c_id = cdef["id"]
        ds = cdef["dataset"]
        c_name = cdef["contrast"]
        t_records = cdef["treatment_scores"]
        c_records = cdef["control_scores"]

        for m_name, is_bin in cdef["metrics"]:
            s_t = [float(r[m_name]) for r in t_records]
            s_c = [float(r[m_name]) for r in c_records]
            stats, boot_dist = compute_contrast_stats(
                scores_ctrl=s_c,
                scores_trt=s_t,
                metric_name=m_name,
                is_binary=is_bin,
                n_resamples=10000,
                seed=42,
            )
            stats["contrast_id"] = c_id
            stats["contrast"] = c_name
            stats["dataset"] = ds
            contrasts_list.append(stats)

            # Store bootstrap sample summary (mean, std, 100 quantiles) to keep distribution file lean
            boot_key = f"{c_id}_{m_name}"
            boot_distributions[boot_key] = {
                "observed_delta": stats["mean_delta"],
                "ci_lower": stats["ci_lower"],
                "ci_upper": stats["ci_upper"],
                "quantiles_0_to_100": [float(np.percentile(boot_dist, q)) for q in range(101)],
            }

    df_contrasts = pd.DataFrame(contrasts_list)
    df_contrasts.to_csv(out_dir / "contrasts_table.csv", index=False)
    with open(out_dir / "contrasts_table.json", "w", encoding="utf-8") as f:
        json.dump(contrasts_list, f, indent=2)

    with gzip.open(out_dir / "bootstrap_distributions.json.gz", "wt", encoding="utf-8") as f:
        json.dump(boot_distributions, f, indent=2)

    print(f"Saved contrasts table to {out_dir / 'contrasts_table.csv'} and JSON.")
    print(f"Saved bootstrap distributions to {out_dir / 'bootstrap_distributions.json.gz'}")

    print("\n" + "=" * 80)
    print("PHASE 6C CONTRASTS SUMMARY TABLE:")
    print("=" * 80)
    print(df_contrasts[["dataset", "contrast", "metric", "mean_control", "mean_treatment", "mean_delta", "ci_lower", "ci_upper", "boot_p", "exact_sign_p", "wtl"]].to_string(index=False))


if __name__ == "__main__":
    main()
