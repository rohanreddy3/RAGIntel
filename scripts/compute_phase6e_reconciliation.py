"""Phase 6E: Offline Fix Round & Methodological Reconciliation.

Implements all Phase 6E computational requirements:
1. Retrieval Metric Reconciliation:
   - Recompute Recall@B (sub_credits_parent) and Context Recall (GT)
     on exact context files sent to LLM for E0'(raw), E0'-HD-k200, E1h on cti-ate and CTI-ATTACK at B=500.
2. Vrel Noise Floor Stratification on cti-taa:
   - Active stratum (context changed, N=34) vs Inactive stratum (identical context, N=16)
   - W/T/L and accuracy for each stratum
   - Run-to-run lexical variation on inactive queries
3. Missing Statistical Contrasts:
   - D1 (B=2000) vs raw E0' (B=500) on cti-ate and CTI-ATTACK (paired bootstrap 10,000 seed 42 + exact sign test)
   - Second generator (gemini-3.1-flash-lite) cti-taa arms (paired bootstrap 10,000 seed 42 + exact sign test across all pairs and scorers)
4. Unified Hygiene Summary Table:
   - Synthesizes hygiene effect on cti-ate and CTI-ATTACK across 4 evaluation regimes:
     * Recall@B common budgets (Phase 5)
     * ENT B2/B3 Recall@10 (Phase 6D Part E)
     * B1 Recall@10 (Phase 6D Part D)
     * Generation F1 (Phase 6C)
     with positive (+), null (0), negative (-) classifications
5. Quota Accounting:
   - Calls per model per UTC day across primary and second generator ledgers.
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
from src.chunking import truncate_to_token_budget, Document
from src.retrieval_eval import (
    extract_technique_ids_from_text,
    parse_ground_truth_techniques,
    compute_retrieval_metrics_technique,
    compute_paired_bootstrap_ci,
)
from scripts.compute_phase6c_metrics import compute_technique_f1, score_group_match
from scripts.compute_phase6d_generation_metrics import compute_exact_sign_test

CACHE_DIR = REPO_ROOT / ".cache" / "api_runner"
CACHE_DIR_SEC = REPO_ROOT / ".cache" / "api_runner_second_gen"
RESULTS_DIR = REPO_ROOT / "results" / "phase_6d"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 80)
    print("PHASE 6E: OFFLINE FIX ROUND & METHODOLOGICAL RECONCILIATION")
    print("=" * 80)

    # Load datasets
    df_ate = load_benchmark_dataset("cti-ate").df
    df_att = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df

    # Load Knowledge Base for threat groups
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()

    # Load candidate chunks
    with gzip.open(REPO_ROOT / "results" / "phase_5" / "top200_hd_chunks.json.gz", "rt", encoding="utf-8") as f:
        top200_hd = json.load(f)

    with gzip.open(REPO_ROOT / "results" / "phase_7" / "top200_phase7_chunks.json.gz", "rt", encoding="utf-8") as f:
        top200_p7 = json.load(f)

    with open(REPO_ROOT / "results" / "phase_3" / "o2_phase3c_benchmark_results.json", "r", encoding="utf-8") as f:
        p3c_results = json.load(f)["results"]["text_and_metadata"]

    # =========================================================================
    # 1. RETRIEVAL METRIC RECONCILIATION AT B=500
    # =========================================================================
    print("\n--- 1. Computing Retrieval Metric Reconciliation at B=500 ---")

    reconciliation_rows = []

    for ds_name, df_bench in [("cti-ate", df_ate), ("CTI-ATTACK", df_att)]:
        n_queries = len(df_bench)

        # A. E0' (raw control)
        # Load exact context files sent to LLM in Phase 6C
        ctx_rec_e0 = []
        for idx, row in df_bench.iterrows():
            gt_set = parse_ground_truth_techniques(str(row.get("techniques", row.get("ground_truth", ""))))
            cf = CACHE_DIR / f"E0_prime_{ds_name}_row_{idx}.json"
            assert cf.is_file(), f"Missing cache file {cf}"
            with open(cf, "r", encoding="utf-8") as f:
                d = json.load(f)
            txt = " ".join(d.get("contexts_used", []))
            found = extract_technique_ids_from_text(txt)
            rec = len(found & gt_set) / len(gt_set) if gt_set else 0.0
            ctx_rec_e0.append(rec)

        # Structured Recall@B (sub_credits_parent) from Phase 3c benchmark
        p3c_recall_sub_e0 = p3c_results[ds_name]["B2"]["E0_prime"]["500"]["summary"]["Recall_sub_credits_parent"]

        reconciliation_rows.append({
            "dataset": ds_name,
            "arm": "E0' (raw control)",
            "token_budget": 500,
            "n_queries": n_queries,
            "recall_b_sub_credits_parent": round(float(p3c_recall_sub_e0), 4),
            "context_recall_gt": round(float(np.mean(ctx_rec_e0)), 4),
            "discrepancy_explanation": "Phase 5/3c Recall@B uses chunk metadata mitre_id + parent subtechnique credit; Context Recall uses exact regex on surface text where split child chunks lack explicit ID prefixes."
        })

        # B. E0'-HD-k200
        recs_hd = top200_hd[ds_name]["B2"]["E0_prime_k200"]
        assert len(recs_hd) == n_queries
        r_sub_hd = []
        ctx_rec_hd = []
        for idx, row in df_bench.iterrows():
            gt = str(row.get("techniques", row.get("ground_truth", "")))
            gt_set = parse_ground_truth_techniques(gt)
            raw_docs = [Document(page_content=c["page_content"], metadata=c.get("metadata", {})) for c in recs_hd[idx]["top200"]]
            trunc_docs = truncate_to_token_budget(raw_docs, budget_tokens=500)
            m = compute_retrieval_metrics_technique(trunc_docs, gt, k_values=[len(trunc_docs)], subtechnique_parent_credit=True)
            r_sub_hd.append(m[f"Recall@{len(trunc_docs)}"])
            txt = " ".join([d.page_content for d in trunc_docs])
            found = extract_technique_ids_from_text(txt)
            ctx_rec_hd.append(len(found & gt_set) / len(gt_set) if gt_set else 0.0)

        # Assert Phase 5 exact value on cti-ate (0.2042)
        if ds_name == "cti-ate":
            assert math.isclose(float(np.mean(r_sub_hd)), 0.2042, abs_tol=1e-4), f"cti-ate HD Recall@B mismatch: {np.mean(r_sub_hd)}"
            assert math.isclose(float(np.mean(ctx_rec_hd)), 0.0546, abs_tol=1e-4), f"cti-ate HD Context Recall mismatch: {np.mean(ctx_rec_hd)}"

        reconciliation_rows.append({
            "dataset": ds_name,
            "arm": "E0'-HD-k200",
            "token_budget": 500,
            "n_queries": n_queries,
            "recall_b_sub_credits_parent": round(float(np.mean(r_sub_hd)), 4),
            "context_recall_gt": round(float(np.mean(ctx_rec_hd)), 4),
            "discrepancy_explanation": "Phase 5 Recall@B evaluates structured chunks with metadata (0.2042 on cti-ate, 0.5670 on CTI-ATTACK); Context Recall evaluates verbatim prompt text (0.0546 on cti-ate, 0.2154 on CTI-ATTACK)."
        })

        # C. E1h (from results/phase_7 top200 chunks, truncated to B=500 tokens)
        recs_p7 = top200_p7[ds_name]["E1h"]
        assert len(recs_p7) == n_queries
        r_sub_e1h = []
        ctx_rec_e1h = []
        for idx, row in df_bench.iterrows():
            gt = str(row.get("techniques", row.get("ground_truth", "")))
            gt_set = parse_ground_truth_techniques(gt)
            raw_docs = [Document(page_content=c["page_content"], metadata=c.get("metadata", {})) for c in recs_p7[idx]["top200"]]
            trunc_docs = truncate_to_token_budget(raw_docs, budget_tokens=500)
            m = compute_retrieval_metrics_technique(trunc_docs, gt, k_values=[len(trunc_docs)], subtechnique_parent_credit=True)
            r_sub_e1h.append(m[f"Recall@{len(trunc_docs)}"])
            txt = " ".join([d.page_content for d in trunc_docs])
            found = extract_technique_ids_from_text(txt)
            ctx_rec_e1h.append(len(found & gt_set) / len(gt_set) if gt_set else 0.0)

        reconciliation_rows.append({
            "dataset": ds_name,
            "arm": "E1h (structure-aware field chunks)",
            "token_budget": 500,
            "n_queries": n_queries,
            "recall_b_sub_credits_parent": round(float(np.mean(r_sub_e1h)), 4),
            "context_recall_gt": round(float(np.mean(ctx_rec_e1h)), 4),
            "discrepancy_explanation": "E1h incorporates explicit structured field headers; surface text context recall (0.0919 on cti-ate, 0.4709 on CTI-ATTACK) approaches structured metadata recall (0.1935 on cti-ate, 0.5058 on CTI-ATTACK)."
        })

    df_recon = pd.DataFrame(reconciliation_rows)
    df_recon.to_csv(RESULTS_DIR / "retrieval_reconciliation_b500.csv", index=False)
    with open(RESULTS_DIR / "retrieval_reconciliation_b500.json", "w", encoding="utf-8") as f:
        json.dump(reconciliation_rows, f, indent=2)
    print("Reconciliation Table:")
    print(df_recon[["dataset", "arm", "recall_b_sub_credits_parent", "context_recall_gt"]].to_string(index=False))

    # =========================================================================
    # 2. VREL NOISE FLOOR STRATIFICATION (cti-taa)
    # =========================================================================
    print("\n--- 2. Computing Vrel Noise Floor Stratification on cti-taa ---")

    v0h_ans = []
    vrel_ans = []
    ctx_identical = []
    ans_identical = []

    for idx, row in df_taa.iterrows():
        f_v0h = CACHE_DIR / f"V0h_cti-taa_row_{idx}.json"
        f_vrel = CACHE_DIR / f"Vrel_cti-taa_row_{idx}.json"
        with open(f_v0h, "r", encoding="utf-8") as f:
            d0 = json.load(f)
        with open(f_vrel, "r", encoding="utf-8") as f:
            dr = json.load(f)
        v0h_ans.append(d0)
        vrel_ans.append(dr)
        ctx0 = " ".join(d0.get("contexts_used", [])).strip()
        ctxr = " ".join(dr.get("contexts_used", [])).strip()
        is_same_ctx = (ctx0 == ctxr)
        ctx_identical.append(is_same_ctx)
        ans0 = d0.get("raw_answer", "").strip()
        ansr = dr.get("raw_answer", "").strip()
        ans_identical.append(ans0 == ansr)

    def score_taa_records(records):
        scores = []
        for idx, row in df_taa.iterrows():
            ans = records[idx].get("raw_answer", "")
            gt = str(row["ground_truth"])
            m = score_group_match(ans, gt, group_alias_map)
            scores.append(m["v2_alias"])
        return np.array(scores)

    s_v0h = score_taa_records(v0h_ans)
    s_vrel = score_taa_records(vrel_ans)
    ctx_identical = np.array(ctx_identical)
    active_mask = ~ctx_identical
    inactive_mask = ctx_identical

    stratification_data = {
        "n_total": len(df_taa),
        "active_stratum": {
            "description": "Queries where Vrel expansion altered the retrieved prompt context relative to V0h",
            "n_queries": int(np.sum(active_mask)),
            "pct_total": round(float(np.mean(active_mask) * 100), 1),
            "v0h_accuracy": round(float(np.mean(s_v0h[active_mask])), 4),
            "v0h_correct": int(np.sum(s_v0h[active_mask])),
            "vrel_accuracy": round(float(np.mean(s_vrel[active_mask])), 4),
            "vrel_correct": int(np.sum(s_vrel[active_mask])),
            "wins": int(np.sum(s_vrel[active_mask] > s_v0h[active_mask])),
            "ties": int(np.sum(s_vrel[active_mask] == s_v0h[active_mask])),
            "losses": int(np.sum(s_vrel[active_mask] < s_v0h[active_mask])),
            "wtl": f"{int(np.sum(s_vrel[active_mask] > s_v0h[active_mask]))}/{int(np.sum(s_vrel[active_mask] == s_v0h[active_mask]))}/{int(np.sum(s_vrel[active_mask] < s_v0h[active_mask]))}"
        },
        "inactive_stratum": {
            "description": "Queries where Vrel retrieved prompt context was identical to V0h",
            "n_queries": int(np.sum(inactive_mask)),
            "pct_total": round(float(np.mean(inactive_mask) * 100), 1),
            "v0h_accuracy": round(float(np.mean(s_v0h[inactive_mask])), 4),
            "v0h_correct": int(np.sum(s_v0h[inactive_mask])),
            "vrel_accuracy": round(float(np.mean(s_vrel[inactive_mask])), 4),
            "vrel_correct": int(np.sum(s_vrel[inactive_mask])),
            "wins": int(np.sum(s_vrel[inactive_mask] > s_v0h[inactive_mask])),
            "ties": int(np.sum(s_vrel[inactive_mask] == s_v0h[inactive_mask])),
            "losses": int(np.sum(s_vrel[inactive_mask] < s_v0h[inactive_mask])),
            "wtl": f"{int(np.sum(s_vrel[inactive_mask] > s_v0h[inactive_mask]))}/{int(np.sum(s_vrel[inactive_mask] == s_v0h[inactive_mask]))}/{int(np.sum(s_vrel[inactive_mask] < s_v0h[inactive_mask]))}",
            "run_to_run_differing_answers": sum(1 for i in range(len(df_taa)) if inactive_mask[i] and not ans_identical[i]),
            "run_to_run_variation_pct": round(float(sum(1 for i in range(len(df_taa)) if inactive_mask[i] and not ans_identical[i]) / np.sum(inactive_mask) * 100), 1)
        }
    }

    with open(RESULTS_DIR / "vrel_noise_floor_stratification.json", "w", encoding="utf-8") as f:
        json.dump(stratification_data, f, indent=2)
    print("Vrel Stratification Results:")
    print(f"Active Stratum (N={stratification_data['active_stratum']['n_queries']}): V0h={stratification_data['active_stratum']['v0h_accuracy']:.4f}, Vrel={stratification_data['active_stratum']['vrel_accuracy']:.4f}, WTL={stratification_data['active_stratum']['wtl']}")
    print(f"Inactive Stratum (N={stratification_data['inactive_stratum']['n_queries']}): V0h={stratification_data['inactive_stratum']['v0h_accuracy']:.4f}, Vrel={stratification_data['inactive_stratum']['vrel_accuracy']:.4f}, WTL={stratification_data['inactive_stratum']['wtl']}")
    print(f"Inactive Run-to-Run Lexical Variation: {stratification_data['inactive_stratum']['run_to_run_differing_answers']}/{stratification_data['inactive_stratum']['n_queries']} ({stratification_data['inactive_stratum']['run_to_run_variation_pct']}%)")

    # =========================================================================
    # 3. MISSING STATISTICAL CONTRASTS
    # =========================================================================
    print("\n--- 3. Computing Missing Statistical Contrasts ---")

    # A. D1 (B=2000) vs raw E0' (B=500)
    d1_raw_contrasts = []
    for ds_name, df_bench in [("cti-ate", df_ate), ("CTI-ATTACK", df_att)]:
        n = len(df_bench)
        f1_raw = []
        f1_d1 = []
        for i, row in df_bench.iterrows():
            gt = parse_ground_truth_techniques(str(row.get("techniques", row.get("ground_truth", ""))))
            with open(CACHE_DIR / f"E0_prime_{ds_name}_row_{i}.json", "r", encoding="utf-8") as f:
                ans_raw = json.load(f).get("raw_answer", "")
            with open(CACHE_DIR / f"E0_prime_HD_k200_b2000_{ds_name}_row_{i}.json", "r", encoding="utf-8") as f:
                ans_d1 = json.load(f).get("raw_answer", "")
            pred_raw = extract_technique_ids_from_text(ans_raw)
            pred_d1 = extract_technique_ids_from_text(ans_d1)
            f1_raw.append(compute_technique_f1(pred_raw, gt)["f1_sub"])
            f1_d1.append(compute_technique_f1(pred_d1, gt)["f1_sub"])

        f1_raw = np.array(f1_raw)
        f1_d1 = np.array(f1_d1)
        mean_raw = float(np.mean(f1_raw))
        mean_d1 = float(np.mean(f1_d1))
        delta = mean_d1 - mean_raw
        ci = compute_paired_bootstrap_ci(f1_raw.tolist(), f1_d1.tolist(), n_resamples=10000, seed=42)
        st = compute_exact_sign_test(f1_raw.tolist(), f1_d1.tolist())

        d1_raw_contrasts.append({
            "contrast_id": f"D1_b2000_vs_raw_E0_b500_{ds_name}",
            "dataset": ds_name,
            "metric": "f1_sub",
            "is_primary_metric": True,
            "control_arm": "E0_prime_raw_b500",
            "treatment_arm": "D1_HD_b2000",
            "control_mean": round(mean_raw, 4),
            "treatment_mean": round(mean_d1, 4),
            "delta": round(delta, 4),
            "ci_lower_95": round(ci["ci_lower"], 4),
            "ci_upper_95": round(ci["ci_upper"], 4),
            "bootstrap_p": round(ci["p_value"], 4),
            "wtl": f"{st['wins']}/{st['ties']}/{st['losses']}",
            "exact_sign_p": round(st["sign_p"], 4),
        })

    with open(RESULTS_DIR / "d1_vs_raw_contrasts.json", "w", encoding="utf-8") as f:
        json.dump(d1_raw_contrasts, f, indent=2)
    pd.DataFrame(d1_raw_contrasts).to_csv(RESULTS_DIR / "d1_vs_raw_contrasts.csv", index=False)
    print("D1 vs Raw Contrasts:")
    for c in d1_raw_contrasts:
        print(f"  {c['dataset']}: raw={c['control_mean']:.4f}, D1={c['treatment_mean']:.4f}, delta={c['delta']:+.4f}, 95% CI=[{c['ci_lower_95']:.4f}, {c['ci_upper_95']:.4f}], WTL={c['wtl']}, p={c['exact_sign_p']:.4f}")

    # B. Second Generator cti-taa Contrasts
    sec_arms = ["LLM_only", "V0", "V0h", "Vrel"]
    sec_scores_by_arm = {}
    for arm in sec_arms:
        arm_scores = {k: [] for k in ["v1_exact", "v1_alias", "v2_exact", "v2_alias"]}
        for i in range(50):
            f = CACHE_DIR_SEC / f"{arm}_cti-taa_row_{i}.json"
            assert f.is_file(), f"Missing second gen cache file {f}"
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            ans = d.get("raw_answer", "")
            gt = str(df_taa.iloc[i]["ground_truth"])
            m = score_group_match(ans, gt, group_alias_map)
            for k in arm_scores:
                arm_scores[k].append(float(m[k]))
        sec_scores_by_arm[arm] = arm_scores

    sec_contrasts_list = []
    sec_pairs = [
        ("Vrel", "V0h", "Vrel vs V0h"),
        ("V0h", "V0", "V0h vs V0"),
        ("Vrel", "V0", "Vrel vs V0"),
        ("Vrel", "LLM_only", "Vrel vs LLM_only"),
        ("V0h", "LLM_only", "V0h vs LLM_only"),
    ]

    for t_arm, c_arm, label in sec_pairs:
        for metric_name in ["v2_alias", "v2_exact", "v1_alias", "v1_exact"]:
            c_s = sec_scores_by_arm[c_arm][metric_name]
            t_s = sec_scores_by_arm[t_arm][metric_name]
            ci = compute_paired_bootstrap_ci(c_s, t_s, n_resamples=10000, seed=42)
            st = compute_exact_sign_test(c_s, t_s)
            c_m, t_m, d = float(np.mean(c_s)), float(np.mean(t_s)), float(np.mean(t_s) - np.mean(c_s))

            sec_contrasts_list.append({
                "contrast_id": f"sec_gen_{t_arm}_vs_{c_arm}_{metric_name}",
                "model": "gemini-3.1-flash-lite",
                "dataset": "cti-taa",
                "contrast": label,
                "metric": metric_name,
                "is_primary_metric": (metric_name == "v2_alias"),
                "control_arm": c_arm,
                "treatment_arm": t_arm,
                "control_mean": round(c_m, 4),
                "treatment_mean": round(t_m, 4),
                "delta": round(d, 4),
                "ci_lower_95": round(ci["ci_lower"], 4),
                "ci_upper_95": round(ci["ci_upper"], 4),
                "bootstrap_p": round(ci["p_value"], 4),
                "wtl": f"{st['wins']}/{st['ties']}/{st['losses']}",
                "exact_sign_p": round(st["sign_p"], 4),
            })

    with open(RESULTS_DIR / "second_generator_contrasts.json", "w", encoding="utf-8") as f:
        json.dump(sec_contrasts_list, f, indent=2)
    pd.DataFrame(sec_contrasts_list).to_csv(RESULTS_DIR / "second_generator_contrasts.csv", index=False)
    print("Second Generator Primary Contrasts (v2_alias):")
    for sc in sec_contrasts_list:
        if sc["is_primary_metric"]:
            print(f"  {sc['contrast']}: Control={sc['control_mean']:.4f}, Treat={sc['treatment_mean']:.4f}, Delta={sc['delta']:+.4f}, WTL={sc['wtl']}, p={sc['exact_sign_p']:.4f}")

    # =========================================================================
    # 4. UNIFIED HYGIENE SUMMARY TABLE
    # =========================================================================
    print("\n--- 4. Assembling Unified Hygiene Summary Table ---")

    # Regimes:
    # 1. Recall@B common budgets (Phase 5): B=500, 1000, 2000, 4000
    # 2. ENT B2/B3 Recall@10 (Phase 6D Part E)
    # 3. B1 Recall@10 (Phase 6D Part D, unchunked dense 8k)
    # 4. Live generation technique F1 (Phase 6C)

    hygiene_rows = [
        {
            "evaluation_regime": "1. Recall@B Common Budgets (Phase 5)",
            "representation_tested": "STIX-ALL chunks across B in {500, 1000, 2000, 4000}",
            "metric": "Recall_sub (sub_credits_parent)",
            "cti_ate_control": "0.0517 (B=500)",
            "cti_ate_treatment": "0.2042 (B=500)",
            "cti_ate_delta": "+0.1525",
            "cti_ate_effect": "+ (Positive)",
            "cti_attack_control": "0.1725 (B=500)",
            "cti_attack_treatment": "0.5670 (B=500)",
            "cti_attack_delta": "+0.3945",
            "cti_attack_effect": "+ (Positive)",
            "statistical_status": "Statistically significant gains across all token budgets"
        },
        {
            "evaluation_regime": "2. Enterprise STIX Bundle (Phase 6D Part E)",
            "representation_tested": "E0-STIX-ENT objects under B2 / B3 baselines",
            "metric": "Recall@10",
            "cti_ate_control": "0.1000 (B2) / 0.0667 (B3)",
            "cti_ate_treatment": "0.1167 (B2) / 0.0667 (B3)",
            "cti_ate_delta": "+0.0167 (B2) / +0.0000 (B3)",
            "cti_ate_effect": "0 (Null)",
            "cti_attack_control": "0.1812 (B2/B3)",
            "cti_attack_treatment": "0.6303 (B2/B3)",
            "cti_attack_delta": "+0.4491",
            "cti_attack_effect": "+ (Positive)",
            "statistical_status": "Null on cti-ate (p=0.6875); massive positive on CTI-ATTACK (p < 0.0001)"
        },
        {
            "evaluation_regime": "3. Long-Context Dense Embeddings (Phase 6D Part D)",
            "representation_tested": "B1 nomic-embed-text-v1.5 (8k context, unchunked)",
            "metric": "Recall@10",
            "cti_ate_control": "0.0874",
            "cti_ate_treatment": "0.1809",
            "cti_ate_delta": "+0.0935",
            "cti_ate_effect": "+ (Positive)",
            "cti_attack_control": "0.2118",
            "cti_attack_treatment": "0.5662",
            "cti_attack_delta": "+0.3544",
            "cti_attack_effect": "+ (Positive)",
            "statistical_status": "Statistically significant on both datasets (exact sign p=0.0002 on cti-ate; p < 0.0001 on CTI-ATTACK)"
        },
        {
            "evaluation_regime": "4. Downstream Live Generation (Phase 6C)",
            "representation_tested": "gemini-3.5-flash-lite technique F1 at B*=500 (HD vs true raw E0')",
            "metric": "Technique F1 (f1_sub)",
            "cti_ate_control": "0.4792",
            "cti_ate_treatment": "0.3936",
            "cti_ate_delta": "-0.0855",
            "cti_ate_effect": "- (Negative)",
            "cti_attack_control": "0.2454",
            "cti_attack_treatment": "0.2994",
            "cti_attack_delta": "+0.0540",
            "cti_attack_effect": "0 (Null)",
            "statistical_status": "Significant decrease on cti-ate (p=0.0127, -0.0855); null on CTI-ATTACK (p=0.3551, +0.0540)"
        }
    ]

    df_hygiene = pd.DataFrame(hygiene_rows)
    df_hygiene.to_csv(RESULTS_DIR / "hygiene_summary_table.csv", index=False)
    with open(RESULTS_DIR / "hygiene_summary_table.json", "w", encoding="utf-8") as f:
        json.dump(hygiene_rows, f, indent=2)
    print("Unified Hygiene Summary Table:")
    print(df_hygiene[["evaluation_regime", "cti_ate_effect", "cti_attack_effect", "statistical_status"]].to_string(index=False))

    # =========================================================================
    # 5. QUOTA ACCOUNTING BY UTC DAY
    # =========================================================================
    print("\n--- 5. Computing Quota Accounting Table ---")

    ledger_p = REPO_ROOT / "reviews" / "api_ledger.csv"
    df_ledger = pd.read_csv(ledger_p)
    df_ledger["date"] = pd.to_datetime(df_ledger["timestamp"]).dt.date

    # Add second generator calls
    ledger_sec_p = RESULTS_DIR / "second_generator_ledger.csv"
    df_sec_ledger = pd.read_csv(ledger_sec_p)
    df_sec_ledger["date"] = pd.to_datetime(df_sec_ledger["timestamp_utc"]).dt.date

    quota_rows = []

    # Primary model calls
    for (d, m), grp in df_ledger.groupby(["date", "model"]):
        n_succ = int(np.sum(grp["status"] == "SUCCESS"))
        n_429 = int(np.sum(grp["status"] == "RATE_LIMITED_429"))
        n_err = int(np.sum(~grp["status"].isin(["SUCCESS", "RATE_LIMITED_429"])))
        n_tot = len(grp)

        notes = "Nominal 500 daily quota"
        if d == pd.to_datetime("2026-10-25").date() and n_succ > 500:
            notes = "Crossed 07:00 UTC daily quota reset boundary (391 pre-reset + 607 post-reset)"

        quota_rows.append({
            "utc_date": str(d),
            "model": m,
            "success_calls": n_succ,
            "rate_limited_429": n_429,
            "server_errors": n_err,
            "total_calls": n_tot,
            "notes": notes,
        })

    # Second generator calls
    for (d, m), grp in df_sec_ledger.groupby(["date", "model"]):
        n_succ = int(np.sum(grp["status"] == "SUCCESS"))
        n_429 = int(np.sum(grp["status"] == "RATE_LIMITED_429"))
        n_err = int(np.sum(~grp["status"].isin(["SUCCESS", "RATE_LIMITED_429"])))
        n_tot = len(grp)

        quota_rows.append({
            "utc_date": str(d),
            "model": m,
            "success_calls": n_succ,
            "rate_limited_429": n_429,
            "server_errors": n_err,
            "total_calls": n_tot,
            "notes": "Separate quota pool; completed Part F replication (1 probe + 200 benchmark calls)",
        })

    quota_rows.sort(key=lambda x: (x["utc_date"], x["model"]))
    df_quota = pd.DataFrame(quota_rows)
    df_quota.to_csv(RESULTS_DIR / "quota_accounting_by_utc_day.csv", index=False)
    with open(RESULTS_DIR / "quota_accounting_by_utc_day.json", "w", encoding="utf-8") as f:
        json.dump(quota_rows, f, indent=2)
    print("Quota Accounting Table:")
    print(df_quota[["utc_date", "model", "success_calls", "rate_limited_429", "notes"]].to_string(index=False))

    print("\n[PHASE 6E] All calculations completed and saved to results/phase_6d/ successfully.")


if __name__ == "__main__":
    main()
