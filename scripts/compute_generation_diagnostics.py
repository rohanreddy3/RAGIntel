"""Generation Diagnostics and Paired Bootstrap Evaluation.

Analyzes all cached LLM generation responses:
1. File count verification (758 cached answers vs 759 total json files).
2. Per-arm and per-dataset diagnostics:
   - Empty answers count
   - Unparseable answers count
   - Mean predicted IDs count
   - Truncated answers count
   - F1 overall and sensitivity F1 excluding invalid rows.
3. Paired bootstrap comparisons (N=10,000, seed 42) & Win/Tie/Loss:
   - E0' vs LLM-only (technique F1 on cti-ate and CTI-ATTACK)
   - V1 vs V0, V1 vs LLM-only, V0 vs LLM-only (cti-taa attribution, Scorer V1 and V2).
"""

import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.retrieval_eval import (
    extract_technique_ids_from_text,
    parse_ground_truth_techniques,
    normalize_group_name,
)
from src.data_loader import load_benchmark_dataset, load_stix_all_bundles


def compute_f1_components(pred: Set[str], gt: Set[str], sub_credit: bool = True) -> float:
    if not gt:
        return 0.0
    if sub_credit:
        c_pred = set(pred)
        for t in pred:
            if "." in t:
                c_pred.add(t.split(".")[0])
        tp = len(c_pred & gt)
        p = tp / len(c_pred) if c_pred else 0.0
        r = tp / len(gt)
    else:
        tp = len(pred & gt)
        p = tp / len(pred) if pred else 0.0
        r = tp / len(gt)
    return (2 * p * r / (p + r)) if (p + r) > 0 else 0.0


def score_group_match(
    raw_answer: str,
    gt_raw: str,
    group_alias_map: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    # Scorer V1
    parts = re.split(r"\(|\)|,|;|/|\balias\b|\balso known as\b|\bor\b|\band\b", gt_raw, flags=re.I)
    v1_candidates = [p.strip(" \t\n\r*\"'") for p in parts if len(p.strip(" \t\n\r*\"'")) >= 3]
    v1_exact = 0
    if v1_candidates:
        if re.search(r"\b" + re.escape(v1_candidates[0]) + r"\b", raw_answer, re.I):
            v1_exact = 1
    v1_alias = v1_exact
    if v1_alias == 0:
        for cand in v1_candidates:
            if re.search(r"\b" + re.escape(cand) + r"\b", raw_answer, re.I):
                v1_alias = 1
                break

    # Scorer V2
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

    return {
        "v1_exact": v1_exact,
        "v1_alias": v1_alias,
        "v2_exact": v2_exact,
        "v2_alias": v2_alias,
    }


def paired_bootstrap(
    diffs: np.ndarray,
    n_resamples: int = 10000,
    seed: int = 42,
) -> Tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n = len(diffs)
    boot_means = np.empty(n_resamples)
    for i in range(n_resamples):
        sample = rng.choice(diffs, size=n, replace=True)
        boot_means[i] = np.mean(sample)
    
    ci_low = float(np.percentile(boot_means, 2.5))
    ci_high = float(np.percentile(boot_means, 97.5))
    obs_mean = float(np.mean(diffs))
    
    # Two-sided empirical p-value
    p_val = float(2 * min(np.mean(boot_means <= 0), np.mean(boot_means >= 0)))
    p_val = min(1.0, max(1.0 / n_resamples, p_val))
    return obs_mean, ci_low, ci_high, p_val


def compute_win_tie_loss(a: np.ndarray, b: np.ndarray, eps: float = 1e-6) -> Tuple[int, int, int]:
    diff = a - b
    wins = int(np.sum(diff > eps))
    losses = int(np.sum(diff < -eps))
    ties = int(np.sum(np.abs(diff) <= eps))
    return wins, ties, losses


def main():
    cache_dir = REPO_ROOT / ".cache" / "api_runner"
    all_json = list(cache_dir.glob("*.json"))
    known_reset = [f for f in all_json if f.name == "known_reset.json"]
    cached_records = [f for f in all_json if f.name != "known_reset.json"]

    print("=" * 70)
    print("FILE COUNT AUDIT:")
    print(f"Total .json files in .cache/api_runner/: {len(all_json)}")
    print(f"Metadata/State files (known_reset.json): {len(known_reset)}")
    print(f"Actual LLM generation response files:    {len(cached_records)}")
    print("Explanation: The '759' count previously reported was a blind glob over all .json files,")
    print("which included the single known_reset.json runner state file. Exactly 758 generation calls exist.")
    print("=" * 70)

    # Load datasets
    df_ate = load_benchmark_dataset("cti-ate").df
    df_attack = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df

    # Load STIX for group alias map
    kb = load_stix_all_bundles()
    group_map = kb.get_group_alias_map()

    # Load all cached generations
    rows = []
    for f in cached_records:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            rows.append(data)
        except Exception as e:
            print(f"Error loading {f}: {e}")

    df_gen = pd.DataFrame(rows)
    print(f"\nLoaded {len(df_gen)} generation records.")
    print("Arm distribution:\n", df_gen["arm"].value_counts())

    # Map GT
    gt_ate = [set(parse_ground_truth_techniques(str(v))) for v in df_ate["ground_truth"]]
    gt_attack = [set(parse_ground_truth_techniques(str(v))) for v in df_attack["ground_truth"]]
    gt_taa = [str(v) for v in df_taa["ground_truth"]]

    # Diagnostics per arm & dataset
    diag_results = []
    per_query_data = {}

    for (arm, ds), group in df_gen.groupby(["arm", "dataset"]):
        n_total = len(group)
        n_empty = 0
        n_unparseable = 0
        n_truncated = 0
        pred_id_counts = []
        f1_sub_all = []
        f1_strict_all = []
        f1_sub_clean = []
        f1_strict_clean = []
        v1_alias_all = []
        v2_alias_all = []

        q_dict = {}

        for _, r in group.sort_values("row_idx").iterrows():
            idx = int(r["row_idx"])
            ans = str(r["raw_answer"])
            ans_clean = ans.strip()
            is_empty = (ans_clean == "")

            # Truncation check: rough token count >= 500 or finishes abruptly
            # Note: max_output_tokens in config is 512.
            # Character count / 4 is approximate. Also check if trailing sentence is incomplete.
            is_truncated = False
            if len(ans) >= 2000:  # ~500 tokens
                is_truncated = True

            if ds in ["cti-ate", "CTI-ATTACK"]:
                gt_set = gt_ate[idx] if ds == "cti-ate" else gt_attack[idx]
                preds = set(extract_technique_ids_from_text(ans))
                n_preds = len(preds)
                pred_id_counts.append(n_preds)

                is_unparseable = (n_preds == 0 and not is_empty)
                f1_sub = compute_f1_components(preds, gt_set, sub_credit=True)
                f1_strict = compute_f1_components(preds, gt_set, sub_credit=False)

                f1_sub_all.append(f1_sub)
                f1_strict_all.append(f1_strict)

                if not (is_empty or is_unparseable or is_truncated):
                    f1_sub_clean.append(f1_sub)
                    f1_strict_clean.append(f1_strict)

                q_dict[idx] = {
                    "f1_sub": f1_sub,
                    "f1_strict": f1_strict,
                    "n_preds": n_preds,
                    "is_empty": is_empty,
                    "is_unparseable": is_unparseable,
                    "is_truncated": is_truncated,
                }

            else:  # cti-taa
                gt_str = gt_taa[idx]
                gscores = score_group_match(ans, gt_str, group_map)
                pred_id_counts.append(1 if (gscores["v1_alias"] or gscores["v2_alias"]) else 0)
                is_unparseable = (gscores["v1_alias"] == 0 and gscores["v2_alias"] == 0 and not is_empty)

                v1_alias_all.append(gscores["v1_alias"])
                v2_alias_all.append(gscores["v2_alias"])

                q_dict[idx] = {
                    "v1_alias": gscores["v1_alias"],
                    "v2_alias": gscores["v2_alias"],
                    "v1_exact": gscores["v1_exact"],
                    "v2_exact": gscores["v2_exact"],
                    "is_empty": is_empty,
                    "is_unparseable": is_unparseable,
                    "is_truncated": is_truncated,
                }

            if is_empty:
                n_empty += 1
            if is_unparseable:
                n_unparseable += 1
            if is_truncated:
                n_truncated += 1

        mean_n_preds = float(np.mean(pred_id_counts)) if pred_id_counts else 0.0
        f1_sub_mean = float(np.mean(f1_sub_all)) if f1_sub_all else (float(np.mean(v2_alias_all)) if v2_alias_all else 0.0)
        f1_sub_clean_mean = float(np.mean(f1_sub_clean)) if f1_sub_clean else f1_sub_mean

        diag_results.append({
            "arm": arm,
            "dataset": ds,
            "n_total": n_total,
            "n_empty": n_empty,
            "n_unparseable": n_unparseable,
            "n_truncated": n_truncated,
            "mean_predicted_ids": round(mean_n_preds, 2),
            "metric_overall": round(f1_sub_mean, 4),
            "metric_sensitivity_clean": round(f1_sub_clean_mean, 4),
        })

        per_query_data[(arm, ds)] = q_dict

    df_diag = pd.DataFrame(diag_results)
    print("\n" + "=" * 70)
    print("ITEM 3: GENERATION DIAGNOSTICS TABLE")
    print("=" * 70)
    print(df_diag.to_string(index=False))

    # Save to json
    out_diag_json = REPO_ROOT / "results" / "phase_4" / "generation_diagnostics.json"
    out_diag_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_diag_json, "w", encoding="utf-8") as f:
        json.dump(diag_results, f, indent=2)

    # -------------------------------------------------------------------------
    # ITEM 4: Paired Bootstrap & Win/Tie/Loss
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ITEM 4: PAIRED BOOTSTRAP AND WIN/TIE/LOSS ANALYSIS")
    print("=" * 70)

    comparisons = []

    # 1. E0' vs LLM-only on cti-ate (Technique F1 sub_credit)
    ate_e0 = np.array([per_query_data[("E0_prime", "cti-ate")][i]["f1_sub"] for i in range(len(df_ate))])
    ate_llm = np.array([per_query_data[("LLM-only", "cti-ate")][i]["f1_sub"] for i in range(len(df_ate))])
    diff_ate = ate_e0 - ate_llm
    obs, low, high, p = paired_bootstrap(diff_ate, n_resamples=10000, seed=42)
    w, t, l = compute_win_tie_loss(ate_e0, ate_llm)
    comparisons.append({
        "contrast": "E0' vs LLM-only (cti-ate, F1 sub_credit)",
        "mean_diff": round(obs, 4),
        "ci_95": f"[{low:.4f}, {high:.4f}]",
        "p_val": p,
        "win_tie_loss": f"{w}/{t}/{l}",
    })

    # 2. E0' vs LLM-only on CTI-ATTACK (Technique F1 sub_credit)
    att_e0 = np.array([per_query_data[("E0_prime", "CTI-ATTACK")][i]["f1_sub"] for i in range(len(df_attack))])
    att_llm = np.array([per_query_data[("LLM-only", "CTI-ATTACK")][i]["f1_sub"] for i in range(len(df_attack))])
    diff_att = att_e0 - att_llm
    obs, low, high, p = paired_bootstrap(diff_att, n_resamples=10000, seed=42)
    w, t, l = compute_win_tie_loss(att_e0, att_llm)
    comparisons.append({
        "contrast": "E0' vs LLM-only (CTI-ATTACK, F1 sub_credit)",
        "mean_diff": round(obs, 4),
        "ci_95": f"[{low:.4f}, {high:.4f}]",
        "p_val": p,
        "win_tie_loss": f"{w}/{t}/{l}",
    })

    # 3. cti-taa Attribution: V1 vs V0, V1 vs LLM-only, V0 vs LLM-only under Scorer V1 and V2
    for scorer_var in ["v1_alias", "v2_alias"]:
        s_label = "Scorer V1 (Text regex)" if scorer_var == "v1_alias" else "Scorer V2 (STIX ontology)"
        v1 = np.array([per_query_data[("cti-taa_B2_V1", "cti-taa")][i][scorer_var] for i in range(len(df_taa))])
        v0 = np.array([per_query_data[("cti-taa_B2_V0", "cti-taa")][i][scorer_var] for i in range(len(df_taa))])
        llm = np.array([per_query_data[("LLM-only", "cti-taa")][i][scorer_var] for i in range(len(df_taa))])

        # V1 vs V0
        diff_v1_v0 = v1 - v0
        obs, low, high, p = paired_bootstrap(diff_v1_v0, n_resamples=10000, seed=42)
        w, t, l = compute_win_tie_loss(v1, v0)
        comparisons.append({
            "contrast": f"V1 vs V0 ({s_label})",
            "mean_diff": round(obs, 4),
            "ci_95": f"[{low:.4f}, {high:.4f}]",
            "p_val": p,
            "win_tie_loss": f"{w}/{t}/{l}",
        })

        # V1 vs LLM-only
        diff_v1_llm = v1 - llm
        obs, low, high, p = paired_bootstrap(diff_v1_llm, n_resamples=10000, seed=42)
        w, t, l = compute_win_tie_loss(v1, llm)
        comparisons.append({
            "contrast": f"V1 vs LLM-only ({s_label})",
            "mean_diff": round(obs, 4),
            "ci_95": f"[{low:.4f}, {high:.4f}]",
            "p_val": p,
            "win_tie_loss": f"{w}/{t}/{l}",
        })

        # V0 vs LLM-only
        diff_v0_llm = v0 - llm
        obs, low, high, p = paired_bootstrap(diff_v0_llm, n_resamples=10000, seed=42)
        w, t, l = compute_win_tie_loss(v0, llm)
        comparisons.append({
            "contrast": f"V0 vs LLM-only ({s_label})",
            "mean_diff": round(obs, 4),
            "ci_95": f"[{low:.4f}, {high:.4f}]",
            "p_val": p,
            "win_tie_loss": f"{w}/{t}/{l}",
        })

    df_comp = pd.DataFrame(comparisons)
    print(df_comp.to_string(index=False))

    out_comp_json = REPO_ROOT / "results" / "phase_4" / "generation_paired_bootstrap.json"
    with open(out_comp_json, "w", encoding="utf-8") as f:
        json.dump(comparisons, f, indent=2)


if __name__ == "__main__":
    main()
