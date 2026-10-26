"""Compute Phase 6D API Generation Metrics and Statistical Contrasts.

Evaluates Completed Phase 6D Priority Generation Arms:
- Priority D1: E0'-HD-k200 at B=2000 tokens (cti-ate 60, CTI-ATTACK 229)
- Priority D2a: Hybrid prompt at B*=500 tokens (cti-ate 60, cti-taa 100)
- Priority D3: O2 end-to-end E1h-MIXED + HD preprocessing at B*=500 (cti-ate 60)

Contrasts:
- Compare each new arm against LLM-only (same rows; paired bootstrap 10,000 seed 42 + exact sign test).
- Compare each new arm against matching Phase 6C arm (same rows; paired bootstrap 10,000 seed 42 + exact sign test).
- For cti-taa hybrid: compare Vrel vs V0h under hybrid prompt.

Outputs saved to results/phase_6d/.
"""

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
from scripts.compute_phase6c_metrics import compute_technique_f1, score_group_match

CACHE_DIR = REPO_ROOT / ".cache" / "api_runner"
OUT_DIR = REPO_ROOT / "results" / "phase_6d"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_exact_sign_test(scores_before: List[float], scores_after: List[float]) -> Dict[str, Any]:
    """Compute exact two-sided binomial sign test on discordant pairs."""
    a = np.array(scores_before, dtype=float)
    b = np.array(scores_after, dtype=float)
    valid = (~np.isnan(a)) & (~np.isnan(b))
    a, b = a[valid], b[valid]

    wins = int(np.sum(b > a))
    losses = int(np.sum(b < a))
    ties = int(np.sum(b == a))
    n_discordant = wins + losses

    if n_discordant == 0:
        p_val = 1.0
    else:
        res = binomtest(k=wins, n=n_discordant, p=0.5, alternative="two-sided")
        p_val = float(res.pvalue)

    return {
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "n_discordant": n_discordant,
        "sign_p": round(p_val, 4),
    }


def main():
    print("=" * 80)
    print("PHASE 6D GENERATION METRICS & STATISTICAL CONTRASTS")
    print("=" * 80)

    # 1. Load Datasets
    df_ate = load_benchmark_dataset("cti-ate").df
    df_att = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df

    # 2. Load STIX KB for attribution
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()

    # Helper to load cached answers
    def load_answers(arm: str, ds: str, n: int) -> List[str]:
        answers = []
        for i in range(n):
            cf = CACHE_DIR / f"{arm}_{ds}_row_{i}.json"
            if cf.is_file():
                try:
                    with open(cf, "r", encoding="utf-8") as f:
                        answers.append(json.load(f).get("raw_answer", ""))
                except Exception:
                    answers.append("")
            else:
                answers.append("")
        return answers

    # Score technique extraction
    def score_tech_arm(answers: List[str], df: pd.DataFrame) -> Dict[str, List[float]]:
        scores = {k: [] for k in ["p_strict", "r_strict", "f1_strict", "p_sub", "r_sub", "f1_sub"]}
        for i, row in df.iterrows():
            gt = parse_ground_truth_techniques(str(row["ground_truth"]))
            pred = extract_technique_ids_from_text(answers[i])
            m = compute_technique_f1(pred, gt)
            for k in scores:
                scores[k].append(m[k])
        return scores

    # Score attribution
    def score_taa_arm(answers: List[str], df: pd.DataFrame) -> Dict[str, List[float]]:
        scores = {k: [] for k in ["v1_exact", "v1_alias", "v2_exact", "v2_alias"]}
        for i, row in df.iterrows():
            gt = str(row["ground_truth"])
            m = score_group_match(answers[i], gt, group_alias_map)
            for k in scores:
                scores[k].append(float(m[k]))
        return scores

    # Load frozen Phase 6C baseline per-query scores
    df_p6c = pd.read_csv(REPO_ROOT / "results" / "phase_6c" / "per_query_scores.csv")

    def get_p6c_scores(ds: str, arm: str, metric_keys: List[str]) -> Dict[str, List[float]]:
        sub_df = df_p6c[(df_p6c["dataset"] == ds) & (df_p6c["arm"] == arm)].sort_values("row_idx")
        return {k: sub_df[k].tolist() for k in metric_keys}

    tech_keys = ["p_strict", "r_strict", "f1_strict", "p_sub", "r_sub", "f1_sub"]
    taa_keys = ["v1_exact", "v1_alias", "v2_exact", "v2_alias"]

    scores_llm_ate = get_p6c_scores("cti-ate", "LLM-only", tech_keys)
    scores_llm_att = get_p6c_scores("CTI-ATTACK", "LLM-only", tech_keys)
    scores_llm_taa = get_p6c_scores("cti-taa", "LLM-only", taa_keys)

    scores_p6c_hd_ate = get_p6c_scores("cti-ate", "E0_prime_HD_k200", tech_keys)
    scores_p6c_hd_att = get_p6c_scores("CTI-ATTACK", "E0_prime_HD_k200", tech_keys)
    scores_p6c_v0h_taa = get_p6c_scores("cti-taa", "V0h", taa_keys)
    scores_p6c_vrel_taa = get_p6c_scores("cti-taa", "Vrel", taa_keys)

    all_contrasts = []
    summary_arm_means = {
        "LLM_only_cti-ate": {k: round(float(np.mean(v)), 4) for k, v in scores_llm_ate.items()},
        "LLM_only_CTI-ATTACK": {k: round(float(np.mean(v)), 4) for k, v in scores_llm_att.items()},
        "LLM_only_cti-taa": {k: round(float(np.mean(v)), 4) for k, v in scores_llm_taa.items()},
        "P6C_HD_b500_cti-ate": {k: round(float(np.mean(v)), 4) for k, v in scores_p6c_hd_ate.items()},
        "P6C_HD_b500_CTI-ATTACK": {k: round(float(np.mean(v)), 4) for k, v in scores_p6c_hd_att.items()},
        "P6C_V0h_cti-taa": {k: round(float(np.mean(v)), 4) for k, v in scores_p6c_v0h_taa.items()},
        "P6C_Vrel_cti-taa": {k: round(float(np.mean(v)), 4) for k, v in scores_p6c_vrel_taa.items()},
    }

    # -------------------------------------------------------------------------
    # Arm D1: E0'-HD-k200 at B=2000 (cti-ate 60, CTI-ATTACK 229)
    # -------------------------------------------------------------------------
    ans_d1_ate = load_answers("E0_prime_HD_k200_b2000", "cti-ate", 60)
    ans_d1_att = load_answers("E0_prime_HD_k200_b2000", "CTI-ATTACK", 229)

    scores_d1_ate = score_tech_arm(ans_d1_ate, df_ate)
    scores_d1_att = score_tech_arm(ans_d1_att, df_att)

    summary_arm_means["D1_cti-ate_b2000"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d1_ate.items()}
    summary_arm_means["D1_CTI-ATTACK_b2000"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d1_att.items()}

    def evaluate_contrast(c_name, ds_name, met_name, ctrl_scores, treat_scores, ctrl_label, treat_label, is_prim=True):
        boot = compute_paired_bootstrap_ci(ctrl_scores, treat_scores, n_resamples=10000, seed=42)
        st = compute_exact_sign_test(ctrl_scores, treat_scores)
        rec = {
            "contrast_id": c_name,
            "dataset": ds_name,
            "metric": met_name,
            "is_primary_metric": is_prim,
            "control_arm": ctrl_label,
            "treatment_arm": treat_label,
            "control_mean": boot["mean_before"],
            "treatment_mean": boot["mean_after"],
            "delta": boot["mean_delta"],
            "ci_lower_95": boot["ci_lower"],
            "ci_upper_95": boot["ci_upper"],
            "bootstrap_p": boot["p_value"],
            "wtl": f"{st['wins']}/{st['ties']}/{st['losses']}",
            "exact_sign_p": st["sign_p"],
        }
        all_contrasts.append(rec)
        sign = "+" if rec["delta"] >= 0 else ""
        print(
            f"[{ds_name:<10}] {c_name:<30} ({met_name}): "
            f"ctrl={rec['control_mean']:.4f}, treat={rec['treatment_mean']:.4f}, "
            f"Delta={sign}{rec['delta']:.4f} [{rec['ci_lower_95']:.4f}, {rec['ci_upper_95']:.4f}], "
            f"W/T/L={rec['wtl']}, p_exact={rec['exact_sign_p']:.4f}"
        )

    print("\n--- Priority D1: E0'-HD-k200 at B=2000 Contrasts ---")
    # vs LLM-only
    evaluate_contrast("D1_vs_LLM_only_cti-ate", "cti-ate", "f1_sub", scores_llm_ate["f1_sub"], scores_d1_ate["f1_sub"], "LLM_only", "D1_HD_b2000")
    evaluate_contrast("D1_vs_LLM_only_CTI-ATTACK", "CTI-ATTACK", "f1_sub", scores_llm_att["f1_sub"], scores_d1_att["f1_sub"], "LLM_only", "D1_HD_b2000")
    # vs Phase 6C HD at B=500
    evaluate_contrast("D1_b2000_vs_P6C_b500_cti-ate", "cti-ate", "f1_sub", scores_p6c_hd_ate["f1_sub"], scores_d1_ate["f1_sub"], "HD_b500", "D1_HD_b2000")
    evaluate_contrast("D1_b2000_vs_P6C_b500_CTI-ATTACK", "CTI-ATTACK", "f1_sub", scores_p6c_hd_att["f1_sub"], scores_d1_att["f1_sub"], "HD_b500", "D1_HD_b2000")

    # -------------------------------------------------------------------------
    # Arm D2a: Hybrid prompt at B*=500 (cti-ate 60, cti-taa 100)
    # -------------------------------------------------------------------------
    ans_d2a_ate = load_answers("hybrid_prompt_b500_E0_prime_HD_k200", "cti-ate", 60)
    ans_d2a_v0h = load_answers("hybrid_prompt_b500_V0h", "cti-taa", 50)
    ans_d2a_vrel = load_answers("hybrid_prompt_b500_Vrel", "cti-taa", 50)

    scores_d2a_ate = score_tech_arm(ans_d2a_ate, df_ate)
    scores_d2a_v0h = score_taa_arm(ans_d2a_v0h, df_taa)
    scores_d2a_vrel = score_taa_arm(ans_d2a_vrel, df_taa)

    summary_arm_means["D2a_hybrid_cti-ate"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d2a_ate.items()}
    summary_arm_means["D2a_hybrid_V0h_cti-taa"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d2a_v0h.items()}
    summary_arm_means["D2a_hybrid_Vrel_cti-taa"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d2a_vrel.items()}

    print("\n--- Priority D2a: Hybrid Prompt at B*=500 Contrasts ---")
    # cti-ate vs LLM-only and vs Phase 6C HD
    evaluate_contrast("D2a_hybrid_vs_LLM_cti-ate", "cti-ate", "f1_sub", scores_llm_ate["f1_sub"], scores_d2a_ate["f1_sub"], "LLM_only", "D2a_hybrid")
    evaluate_contrast("D2a_hybrid_vs_P6C_HD_cti-ate", "cti-ate", "f1_sub", scores_p6c_hd_ate["f1_sub"], scores_d2a_ate["f1_sub"], "HD_b500", "D2a_hybrid")

    # cti-taa V0h vs LLM-only and vs Phase 6C V0h
    evaluate_contrast("D2a_hybrid_V0h_vs_LLM_taa", "cti-taa", "v2_alias", scores_llm_taa["v2_alias"], scores_d2a_v0h["v2_alias"], "LLM_only", "D2a_hybrid_V0h")
    evaluate_contrast("D2a_hybrid_V0h_vs_P6C_V0h_taa", "cti-taa", "v2_alias", scores_p6c_v0h_taa["v2_alias"], scores_d2a_v0h["v2_alias"], "P6C_V0h", "D2a_hybrid_V0h")

    # cti-taa Vrel vs LLM-only and vs Phase 6C Vrel
    evaluate_contrast("D2a_hybrid_Vrel_vs_LLM_taa", "cti-taa", "v2_alias", scores_llm_taa["v2_alias"], scores_d2a_vrel["v2_alias"], "LLM_only", "D2a_hybrid_Vrel")
    evaluate_contrast("D2a_hybrid_Vrel_vs_P6C_Vrel_taa", "cti-taa", "v2_alias", scores_p6c_vrel_taa["v2_alias"], scores_d2a_vrel["v2_alias"], "P6C_Vrel", "D2a_hybrid_Vrel")

    # cti-taa Hybrid Vrel vs Hybrid V0h
    evaluate_contrast("D2a_hybrid_Vrel_vs_V0h_taa", "cti-taa", "v2_alias", scores_d2a_v0h["v2_alias"], scores_d2a_vrel["v2_alias"], "D2a_hybrid_V0h", "D2a_hybrid_Vrel")

    # -------------------------------------------------------------------------
    # Arm D3: O2 end to end E1h-MIXED + HD at B*=500 (cti-ate 60, CTI-ATTACK 229)
    # -------------------------------------------------------------------------
    ans_d3_ate = load_answers("E1h_mixed_HD_b500", "cti-ate", 60)
    scores_d3_ate = score_tech_arm(ans_d3_ate, df_ate)
    summary_arm_means["D3_E1h_mixed_HD_cti-ate"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d3_ate.items()}

    print("\n--- Priority D3: O2 end-to-end (E1h-MIXED + HD) on cti-ate ---")
    evaluate_contrast("D3_O2_vs_LLM_cti-ate", "cti-ate", "f1_sub", scores_llm_ate["f1_sub"], scores_d3_ate["f1_sub"], "LLM_only", "D3_O2_E1h_HD")
    evaluate_contrast("D3_O2_vs_P6C_HD_cti-ate", "cti-ate", "f1_sub", scores_p6c_hd_ate["f1_sub"], scores_d3_ate["f1_sub"], "HD_b500", "D3_O2_E1h_HD")

    ans_d3_att = load_answers("E1h_mixed_HD_b500", "CTI-ATTACK", 229)
    if all(len(a) > 0 for a in ans_d3_att):
        scores_d3_att = score_tech_arm(ans_d3_att, df_att)
        summary_arm_means["D3_E1h_mixed_HD_CTI-ATTACK"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d3_att.items()}
        print("\n--- Priority D3: O2 end-to-end (E1h-MIXED + HD) on CTI-ATTACK ---")
        evaluate_contrast("D3_O2_vs_LLM_CTI-ATTACK", "CTI-ATTACK", "f1_sub", scores_llm_att["f1_sub"], scores_d3_att["f1_sub"], "LLM_only", "D3_O2_E1h_HD")
        evaluate_contrast("D3_O2_vs_P6C_HD_CTI-ATTACK", "CTI-ATTACK", "f1_sub", scores_p6c_hd_att["f1_sub"], scores_d3_att["f1_sub"], "HD_b500", "D3_O2_E1h_HD")

    # -------------------------------------------------------------------------
    # Arm D2b: Hybrid prompt at B*=500 on CTI-ATTACK (229)
    # -------------------------------------------------------------------------
    ans_d2b_att = load_answers("hybrid_prompt_b500_E0_prime_HD_k200", "CTI-ATTACK", 229)
    if all(len(a) > 0 for a in ans_d2b_att):
        scores_d2b_att = score_tech_arm(ans_d2b_att, df_att)
        summary_arm_means["D2b_hybrid_CTI-ATTACK"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d2b_att.items()}
        print("\n--- Priority D2b: Hybrid Prompt at B*=500 on CTI-ATTACK ---")
        evaluate_contrast("D2b_hybrid_vs_LLM_CTI-ATTACK", "CTI-ATTACK", "f1_sub", scores_llm_att["f1_sub"], scores_d2b_att["f1_sub"], "LLM_only", "D2b_hybrid")
        evaluate_contrast("D2b_hybrid_vs_P6C_HD_CTI-ATTACK", "CTI-ATTACK", "f1_sub", scores_p6c_hd_att["f1_sub"], scores_d2b_att["f1_sub"], "HD_b500", "D2b_hybrid")

    # -------------------------------------------------------------------------
    # Arm D4: Hybrid prompt at B=2000 on cti-ate (60)
    # -------------------------------------------------------------------------
    ans_d4_ate = load_answers("hybrid_prompt_b2000_E0_prime_HD_k200", "cti-ate", 60)
    if all(len(a) > 0 for a in ans_d4_ate):
        scores_d4_ate = score_tech_arm(ans_d4_ate, df_ate)
        summary_arm_means["D4_hybrid_b2000_cti-ate"] = {k: round(float(np.mean(v)), 4) for k, v in scores_d4_ate.items()}
        print("\n--- Priority D4: Hybrid Prompt at B=2000 on cti-ate ---")
        evaluate_contrast("D4_hybrid_vs_LLM_cti-ate", "cti-ate", "f1_sub", scores_llm_ate["f1_sub"], scores_d4_ate["f1_sub"], "LLM_only", "D4_hybrid_b2000")
        evaluate_contrast("D4_hybrid_vs_P6C_HD_cti-ate", "cti-ate", "f1_sub", scores_p6c_hd_ate["f1_sub"], scores_d4_ate["f1_sub"], "HD_b500", "D4_hybrid_b2000")
        evaluate_contrast("D4_hybrid_vs_D1_b2000_cti-ate", "cti-ate", "f1_sub", scores_d1_ate["f1_sub"], scores_d4_ate["f1_sub"], "D1_HD_b2000", "D4_hybrid_b2000")

    # Save outputs
    df_contrasts = pd.DataFrame(all_contrasts)
    csv_path = OUT_DIR / "generation_contrasts.csv"
    json_path = OUT_DIR / "generation_contrasts.json"
    means_path = OUT_DIR / "generation_arm_means.json"

    df_contrasts.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_contrasts, f, indent=2)
    with open(means_path, "w", encoding="utf-8") as f:
        json.dump(summary_arm_means, f, indent=2)

    print(f"\nSaved generation contrasts to {csv_path} and {json_path}")
    print(f"Saved arm means to {means_path}")



if __name__ == "__main__":
    main()
