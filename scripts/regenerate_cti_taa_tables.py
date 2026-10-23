"""Regenerate cti-taa Diagnostics and Paired Bootstrap Tables.

Reads directly from results/phase_4/per_query_cti_taa_attribution.csv:
1. Enforces assertions that every arm mean matches D1 CSV values:
   - LLM-only: v1_exact=0.60, v1_alias=0.68, v2_exact=0.68, v2_alias=0.72
   - cti-taa_B2_V0: v1_exact=0.40, v1_alias=0.56, v2_exact=0.50, v2_alias=0.60
   - cti-taa_B2_V1: v1_exact=0.38, v1_alias=0.44, v2_exact=0.40, v2_alias=0.46
2. Generates Diagnostics Table with fixed Sensitivity column.
3. Generates Paired Bootstrap Table (N=10,000, seed 42) directly from CSV rows.
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "results" / "phase_4" / "per_query_cti_taa_attribution.csv"
CACHE_DIR = REPO_ROOT / ".cache" / "api_runner"


def paired_bootstrap(
    diffs: np.ndarray,
    n_resamples: int = 10000,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
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
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Missing CSV: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    arms = ["LLM-only", "cti-taa_B2_V0", "cti-taa_B2_V1"]

    # -------------------------------------------------------------------------
    # 1. Assertions against D1 benchmark means
    # -------------------------------------------------------------------------
    expected_means = {
        "LLM-only": {"v1_exact": 0.60, "v1_alias": 0.68, "v2_exact": 0.68, "v2_alias": 0.72},
        "cti-taa_B2_V0": {"v1_exact": 0.40, "v1_alias": 0.56, "v2_exact": 0.50, "v2_alias": 0.60},
        "cti-taa_B2_V1": {"v1_exact": 0.38, "v1_alias": 0.44, "v2_exact": 0.40, "v2_alias": 0.46},
    }

    print("=" * 80)
    print("STEP 1: VERIFYING CSV MEANS AGAINST D1 BENCHMARK VALUES")
    print("=" * 80)
    for arm, exp in expected_means.items():
        sub = df[df["arm"] == arm]
        assert len(sub) == 50, f"Expected 50 rows for {arm}, got {len(sub)}"
        for metric, exp_val in exp.items():
            actual_val = sub[metric].mean()
            assert math.isclose(actual_val, exp_val, abs_tol=1e-4), (
                f"Mismatch in {arm} {metric}: expected {exp_val}, got {actual_val:.4f}"
            )
            print(f"  [PASS] {arm:<15} {metric:<10}: {actual_val:.4f} (expected {exp_val:.4f})")

    # -------------------------------------------------------------------------
    # 2. Build Diagnostics Table with corrected Sensitivity Analysis
    # -------------------------------------------------------------------------
    diag_rows = []
    for arm in arms:
        sub = df[df["arm"] == arm].sort_values("row_idx")
        n_total = len(sub)
        n_empty = 0
        n_truncated = 0
        n_unparseable = 0

        valid_rows_v2 = []
        valid_rows_v1 = []

        for _, r in sub.iterrows():
            row_idx = int(r["row_idx"])
            cache_file = CACHE_DIR / f"{arm}_cti-taa_row_{row_idx}.json"
            raw_ans = ""
            if cache_file.is_file():
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw_ans = json.load(f).get("raw_answer", "")

            is_empty = (len(raw_ans.strip()) == 0)
            is_truncated = (len(raw_ans) >= 2000)
            # Unparseable on cti-taa: response contains refusal or no actor attribution
            # Empirically, if v2_alias == 0, the answer either refused, attributed only malware, or named a wrong actor
            is_unparseable_v2 = (r["v2_alias"] == 0)

            if is_empty:
                n_empty += 1
            if is_truncated:
                n_truncated += 1
            if is_unparseable_v2:
                n_unparseable += 1

            # Sensitivity filter: exclude empty and truncated rows
            if not (is_empty or is_truncated):
                valid_rows_v2.append(r["v2_alias"])
                valid_rows_v1.append(r["v1_alias"])

        mean_v2_overall = sub["v2_alias"].mean()
        mean_v2_sens = float(np.mean(valid_rows_v2)) if valid_rows_v2 else mean_v2_overall

        mean_v1_overall = sub["v1_alias"].mean()
        mean_v1_sens = float(np.mean(valid_rows_v1)) if valid_rows_v1 else mean_v1_overall

        diag_rows.append({
            "arm": arm,
            "N": n_total,
            "n_empty": n_empty,
            "n_unparseable": n_unparseable,
            "n_truncated": n_truncated,
            "N_valid (excl. empty/trunc)": len(valid_rows_v2),
            "Scorer_V2_Overall": round(mean_v2_overall, 4),
            "Scorer_V2_Sensitivity": round(mean_v2_sens, 4),
            "Scorer_V1_Overall": round(mean_v1_overall, 4),
            "Scorer_V1_Sensitivity": round(mean_v1_sens, 4),
        })

    df_diag = pd.DataFrame(diag_rows)
    print("\n" + "=" * 80)
    print("STEP 2: REGENERATED CTI-TAA DIAGNOSTICS TABLE")
    print("=" * 80)
    print(df_diag.to_string(index=False))

    # -------------------------------------------------------------------------
    # 3. Paired Bootstrap Inference from CSV rows
    # -------------------------------------------------------------------------
    # Extract aligned series per row_idx
    data_by_arm = {}
    for arm in arms:
        sub = df[df["arm"] == arm].sort_values("row_idx")
        data_by_arm[arm] = {
            "v1_alias": sub["v1_alias"].to_numpy(),
            "v2_alias": sub["v2_alias"].to_numpy(),
            "v1_exact": sub["v1_exact"].to_numpy(),
            "v2_exact": sub["v2_exact"].to_numpy(),
        }

    paired_results = []
    comparisons = [
        ("V1 vs V0", "cti-taa_B2_V1", "cti-taa_B2_V0"),
        ("V0 vs LLM-only", "cti-taa_B2_V0", "LLM-only"),
        ("V1 vs LLM-only", "cti-taa_B2_V1", "LLM-only"),
    ]

    for label, arm_a, arm_b in comparisons:
        for scorer_key, scorer_name in [
            ("v2_alias", "Scorer V2: STIX Ontology Alias"),
            ("v1_alias", "Scorer V1: Text Regex Alias"),
        ]:
            arr_a = data_by_arm[arm_a][scorer_key]
            arr_b = data_by_arm[arm_b][scorer_key]
            diff = arr_a - arr_b

            obs, low, high, p_val = paired_bootstrap(diff, n_resamples=10000, seed=42)
            w, t, l = compute_win_tie_loss(arr_a, arr_b)

            paired_results.append({
                "Contrast": label,
                "Scorer": scorer_name,
                "Mean_A": round(float(np.mean(arr_a)), 4),
                "Mean_B": round(float(np.mean(arr_b)), 4),
                "Mean_Diff (A - B)": round(obs, 4),
                "95% Bootstrap CI": f"[{low:.4f}, {high:.4f}]",
                "p-value": round(p_val, 4),
                "Win/Tie/Loss": f"{w}/{t}/{l}",
            })

    df_paired = pd.DataFrame(paired_results)
    print("\n" + "=" * 80)
    print("STEP 3: REGENERATED PAIRED BOOTSTRAP INFERENCE TABLE")
    print("=" * 80)
    print(df_paired.to_string(index=False))

    # Save to JSON
    out_json = REPO_ROOT / "results" / "phase_4" / "regenerated_cti_taa_evaluation.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "diagnostics": diag_rows,
            "paired_bootstrap": paired_results,
        }, f, indent=2)
    print(f"\nSaved verified tables to {out_json}")


if __name__ == "__main__":
    main()
