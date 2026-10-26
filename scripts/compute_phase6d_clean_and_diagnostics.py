"""Phase 6D Clean-up and Descriptive Diagnostics.

Tasks:
1. Part A2: Compute missing cti-taa contrasts:
   - Vrel vs V0h across all 4 scorers
   - V0h vs V0 across all 4 scorers
   Using paired bootstrap (10,000 resamples, seed 42) and exact two-sided binomial sign test.
2. Part A3: Apply Holm-Bonferroni step-down correction over the 4 primary generation comparisons:
   - HD vs LLM-only on cti-ate (f1_sub)
   - HD vs LLM-only on CTI-ATTACK (f1_sub)
   - V0h vs LLM-only on cti-taa (v2_alias)
   - Vrel vs V0h on cti-taa (v2_alias)
3. Part C: Descriptive diagnostics across E0'(raw), E0'-HD-k200, E1h, and LLM-only on cti-ate and CTI-ATTACK:
   - Mean predicted technique count
   - Mean distinct IDs and chunks in context (B=500)
   - Context recall (ground-truth techniques present in context)
   - Abstention / empty / truncation counts
   - Per-query Spearman rank correlation between context recall and F1
   - Domain filter verification on Mobile rows of cti-ate
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
from scipy.stats import binomtest, spearmanr

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.chunking import truncate_to_token_budget, Document
from src.retrieval_eval import (
    extract_technique_ids_from_text,
    parse_ground_truth_techniques,
    normalize_group_name,
)
from scripts.compute_phase6c_metrics import score_group_match, compute_contrast_stats, compute_technique_f1


def is_abstention(text: str) -> bool:
    """Check if model answer indicates abstention or inability to find techniques/actors."""
    t = text.lower().strip()
    if not t:
        return True
    patterns = [
        r"\bno\s+(?:mitre\s+)?techniques?\b",
        r"\bcannot\s+(?:determine|identify|attribute)\b",
        r"\bunable\s+to\s+(?:determine|identify|attribute)\b",
        r"\bnone\s+(?:identified|found|applicable)\b",
        r"\bnot\s+enough\s+information\b",
        r"\bno\s+threat\s+(?:actor|group)\b",
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def main():
    print("=" * 80)
    print("PHASE 6D: CLEAN-UP, MISSING CONTRASTS, HOLM CORRECTION & DESCRIPTIVE DIAGNOSTICS")
    print("=" * 80)

    out_dir = REPO_ROOT / "results" / "phase_6d"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = REPO_ROOT / ".cache" / "api_runner"

    # 1. Load benchmark datasets
    df_ate = load_benchmark_dataset("cti-ate").df
    df_att = load_benchmark_dataset("CTI-ATTACK").df
    df_taa = load_benchmark_dataset("cti-taa").df

    # 2. Load Knowledge Base
    kb = load_stix_all_bundles()
    group_alias_map = kb.get_group_alias_map()

    # Load generation answers for cti-taa
    def load_taa_arm(arm_prefix: str) -> List[Dict[str, Any]]:
        records = []
        for idx in range(50):
            fpath = cache_dir / f"{arm_prefix}_cti-taa_row_{idx}.json"
            with open(fpath, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        return records

    taa_v0h = load_taa_arm("V0h")
    taa_vrel = load_taa_arm("Vrel")
    taa_v0 = load_taa_arm("cti-taa_B2_V0")
    taa_llm = load_taa_arm("LLM-only")

    # Score cti-taa
    def score_taa(records: List[Dict[str, Any]]) -> List[Dict[str, int]]:
        res = []
        for idx, row in df_taa.iterrows():
            raw_ans = records[idx].get("raw_answer", "")
            gt_str = str(row.get("group", row.get("ground_truth", "")))
            res.append(score_group_match(raw_ans, gt_str, group_alias_map))
        return res

    s_v0h = score_taa(taa_v0h)
    s_vrel = score_taa(taa_vrel)
    s_v0 = score_taa(taa_v0)
    s_llm = score_taa(taa_llm)

    # =========================================================================
    # Task A2: Add missing contrasts on cti-taa (Vrel vs V0h, V0h vs V0)
    # =========================================================================
    print("\n--- Running Part A2: Missing cti-taa contrasts ---")
    scorers = ["v1_exact", "v1_alias", "v2_exact", "v2_alias"]
    missing_contrasts = []

    pairs = [
        ("Vrel vs V0h", s_v0h, s_vrel, "C_Vrel_vs_V0h_taa"),
        ("V0h vs V0", s_v0, s_v0h, "C_V0h_vs_V0_taa"),
    ]

    for c_name, c_ctrl, c_trt, c_id in pairs:
        for scorer in scorers:
            scores_c = [float(r[scorer]) for r in c_ctrl]
            scores_t = [float(r[scorer]) for r in c_trt]
            stats, _ = compute_contrast_stats(
                scores_ctrl=scores_c,
                scores_trt=scores_t,
                metric_name=scorer,
                is_binary=True,
                n_resamples=10000,
                seed=42,
            )
            stats["contrast_id"] = c_id
            stats["contrast"] = c_name
            stats["dataset"] = "cti-taa"
            missing_contrasts.append(stats)

    df_missing = pd.DataFrame(missing_contrasts)
    df_missing.to_csv(out_dir / "missing_taa_contrasts.csv", index=False)
    with open(out_dir / "missing_taa_contrasts.json", "w", encoding="utf-8") as f:
        json.dump(missing_contrasts, f, indent=2)

    print("Missing cti-taa contrasts table:")
    print(df_missing[["contrast", "metric", "mean_control", "mean_treatment", "mean_delta", "ci_lower", "ci_upper", "boot_p", "exact_sign_p", "wtl"]].to_string(index=False))

    # =========================================================================
    # Task A3: Holm over the 4 primary generation comparisons
    # =========================================================================
    print("\n--- Running Part A3: Holm Step-down over Primary Generation Contrasts ---")
    # Load phase_6c contrasts to get the raw p-values
    with open(REPO_ROOT / "results" / "phase_6c" / "contrasts_table.json", "r", encoding="utf-8") as f:
        p6c_contrasts = json.load(f)

    # 1. HD vs LLM-only on cti-ate (f1_sub)
    c1 = next(c for c in p6c_contrasts if c["contrast_id"] == "C_HD_vs_LLM_ate" and c["metric"] == "f1_sub")
    # 2. HD vs LLM-only on CTI-ATTACK (f1_sub)
    c2 = next(c for c in p6c_contrasts if c["contrast_id"] == "C_HD_vs_LLM_att" and c["metric"] == "f1_sub")
    # 3. V0h vs LLM-only on cti-taa (v2_alias)
    c3 = next(c for c in p6c_contrasts if c["contrast_id"] == "C_V0h_vs_LLM_taa" and c["metric"] == "v2_alias")
    # 4. Vrel vs V0h on cti-taa (v2_alias) from missing_contrasts
    c4 = next(c for c in missing_contrasts if c["contrast_id"] == "C_Vrel_vs_V0h_taa" and c["metric"] == "v2_alias")

    primary_comparisons = [
        {"test_id": "GEN_01", "comparison": "HD vs LLM-only (cti-ate)", "metric": "f1_sub", "mean_delta": c1["mean_delta"], "p_raw": c1["boot_p"], "exact_sign_p": c1["exact_sign_p"], "wtl": c1["wtl"]},
        {"test_id": "GEN_02", "comparison": "HD vs LLM-only (CTI-ATTACK)", "metric": "f1_sub", "mean_delta": c2["mean_delta"], "p_raw": c2["boot_p"], "exact_sign_p": c2["exact_sign_p"], "wtl": c2["wtl"]},
        {"test_id": "GEN_03", "comparison": "V0h vs LLM-only (cti-taa)", "metric": "v2_alias", "mean_delta": c3["mean_delta"], "p_raw": c3["exact_sign_p"], "boot_p": c3["boot_p"], "wtl": c3["wtl"]},
        {"test_id": "GEN_04", "comparison": "Vrel vs V0h (cti-taa)", "metric": "v2_alias", "mean_delta": c4["mean_delta"], "p_raw": c4["exact_sign_p"], "boot_p": c4["boot_p"], "wtl": c4["wtl"]},
    ]

    # Sort by p_raw ascending for Holm correction (M = 4)
    primary_comparisons.sort(key=lambda x: x["p_raw"])
    M = len(primary_comparisons)
    alpha = 0.05
    holm_results = []
    stopped = False

    for rank_idx, comp in enumerate(primary_comparisons):
        k = rank_idx + 1
        holm_thresh = alpha / (M - k + 1)
        raw_p = comp["p_raw"]
        is_sig = False
        if not stopped:
            if raw_p <= holm_thresh:
                is_sig = True
            else:
                stopped = True

        res_entry = {
            "rank": k,
            "test_id": comp["test_id"],
            "comparison": comp["comparison"],
            "metric": comp["metric"],
            "mean_delta": comp["mean_delta"],
            "wtl": comp["wtl"],
            "p_raw": raw_p,
            "holm_threshold": round(holm_thresh, 5),
            "reject_null_holm": is_sig,
            "verdict": "Statistically Significant" if is_sig else "Not Significant",
        }
        holm_results.append(res_entry)

    df_holm = pd.DataFrame(holm_results)
    df_holm.to_csv(out_dir / "holm_primary_generation.csv", index=False)
    with open(out_dir / "holm_primary_generation.json", "w", encoding="utf-8") as f:
        json.dump(holm_results, f, indent=2)

    print("Holm-Bonferroni correction table (M=4, alpha=0.05):")
    print(df_holm[["rank", "test_id", "comparison", "mean_delta", "p_raw", "holm_threshold", "reject_null_holm", "verdict"]].to_string(index=False))

    # =========================================================================
    # Task C: Descriptive Diagnostics for E0'(raw), E0'-HD-k200, E1h, LLM-only
    # =========================================================================
    print("\n--- Running Part C: Descriptive Diagnostics ---")

    # Load top200 phase 7 chunks for E1h
    with gzip.open(REPO_ROOT / "results" / "phase_7" / "top200_phase7_chunks.json.gz", "rt", encoding="utf-8") as f:
        p7_chunks = json.load(f)

    # Load per-query phase 6c scores
    df_p6c_scores = pd.read_csv(REPO_ROOT / "results" / "phase_6c" / "per_query_scores.csv")

    diagnostics_rows = []

    for ds_name, df_bench in [("cti-ate", df_ate), ("CTI-ATTACK", df_att)]:
        n_queries = len(df_bench)

        # 1. LLM-only
        llm_sub = df_p6c_scores[(df_p6c_scores["dataset"] == ds_name) & (df_p6c_scores["arm"] == "LLM-only")]
        pred_counts_llm = [len(str(t).split(";")) if str(t) != "" and str(t) != "nan" else 0 for t in llm_sub["pred_techniques"]]
        empty_llm = sum(1 for p in pred_counts_llm if p == 0)
        trunc_llm = sum(1 for _, r in llm_sub.iterrows() if r["finish_reason"] == "FinishReason.MAX_TOKENS")

        # Load raw answer texts for abstention count
        abstain_llm = 0
        for idx in range(n_queries):
            c_file = cache_dir / f"LLM-only_{ds_name}_row_{idx}.json"
            if c_file.is_file():
                with open(c_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if is_abstention(d.get("raw_answer", "")):
                        abstain_llm += 1

        diagnostics_rows.append({
            "dataset": ds_name,
            "arm": "LLM-only",
            "n_queries": n_queries,
            "mean_pred_tech_count": round(float(np.mean(pred_counts_llm)), 2),
            "mean_distinct_ids_in_ctx": 0.0,
            "mean_chunks_in_ctx": 0.0,
            "mean_context_recall": 0.0,
            "abstention_count": abstain_llm,
            "empty_response_count": empty_llm,
            "truncation_count": trunc_llm,
            "spearman_ctx_rec_vs_f1": "N/A (no context)",
            "spearman_p": "N/A",
        })

        # 2. E0' (raw control)
        e0_sub = df_p6c_scores[(df_p6c_scores["dataset"] == ds_name) & (df_p6c_scores["arm"] == "E0_prime")].sort_values("row_idx")
        pred_counts_e0 = [len(str(t).split(";")) if str(t) != "" and str(t) != "nan" else 0 for t in e0_sub["pred_techniques"]]
        empty_e0 = sum(1 for p in pred_counts_e0 if p == 0)
        trunc_e0 = sum(1 for _, r in e0_sub.iterrows() if r["finish_reason"] == "FinishReason.MAX_TOKENS")

        chunks_per_ctx_e0 = []
        distinct_ids_e0 = []
        ctx_recall_e0 = []
        abstain_e0 = 0

        for idx, row in df_bench.iterrows():
            c_file = cache_dir / f"E0_prime_{ds_name}_row_{idx}.json"
            gt_set = parse_ground_truth_techniques(str(row.get("techniques", row.get("ground_truth", ""))))
            if c_file.is_file():
                with open(c_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if is_abstention(d.get("raw_answer", "")):
                        abstain_e0 += 1
                    ctxs = d.get("contexts_used", [])
                    chunks_per_ctx_e0.append(len(ctxs))
                    all_ctx_text = " ".join(ctxs)
                    ctx_techs = extract_technique_ids_from_text(all_ctx_text)
                    distinct_ids_e0.append(len(ctx_techs))
                    if gt_set:
                        # Ground-truth techniques present in context
                        rec = len(ctx_techs & gt_set) / len(gt_set)
                        ctx_recall_e0.append(rec)
                    else:
                        ctx_recall_e0.append(0.0)
            else:
                chunks_per_ctx_e0.append(0)
                distinct_ids_e0.append(0)
                ctx_recall_e0.append(0.0)

        f1_vals_e0 = list(e0_sub["f1_sub"])
        rho_e0, p_val_e0 = spearmanr(ctx_recall_e0, f1_vals_e0)

        diagnostics_rows.append({
            "dataset": ds_name,
            "arm": "E0' (raw control)",
            "n_queries": n_queries,
            "mean_pred_tech_count": round(float(np.mean(pred_counts_e0)), 2),
            "mean_distinct_ids_in_ctx": round(float(np.mean(distinct_ids_e0)), 2),
            "mean_chunks_in_ctx": round(float(np.mean(chunks_per_ctx_e0)), 2),
            "mean_context_recall": round(float(np.mean(ctx_recall_e0)), 4),
            "abstention_count": abstain_e0,
            "empty_response_count": empty_e0,
            "truncation_count": trunc_e0,
            "spearman_ctx_rec_vs_f1": round(float(rho_e0), 4),
            "spearman_p": round(float(p_val_e0), 4),
        })

        # 3. E0'-HD-k200
        hd_sub = df_p6c_scores[(df_p6c_scores["dataset"] == ds_name) & (df_p6c_scores["arm"] == "E0_prime_HD_k200")].sort_values("row_idx")
        pred_counts_hd = [len(str(t).split(";")) if str(t) != "" and str(t) != "nan" else 0 for t in hd_sub["pred_techniques"]]
        empty_hd = sum(1 for p in pred_counts_hd if p == 0)
        trunc_hd = sum(1 for _, r in hd_sub.iterrows() if r["finish_reason"] == "FinishReason.MAX_TOKENS")

        chunks_per_ctx_hd = []
        distinct_ids_hd = []
        ctx_recall_hd = []
        abstain_hd = 0

        for idx, row in df_bench.iterrows():
            c_file = cache_dir / f"E0_prime_HD_k200_{ds_name}_row_{idx}.json"
            gt_set = parse_ground_truth_techniques(str(row.get("techniques", row.get("ground_truth", ""))))
            if c_file.is_file():
                with open(c_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if is_abstention(d.get("raw_answer", "")):
                        abstain_hd += 1
                    ctxs = d.get("contexts_used", [])
                    chunks_per_ctx_hd.append(len(ctxs))
                    all_ctx_text = " ".join(ctxs)
                    ctx_techs = extract_technique_ids_from_text(all_ctx_text)
                    distinct_ids_hd.append(len(ctx_techs))
                    if gt_set:
                        rec = len(ctx_techs & gt_set) / len(gt_set)
                        ctx_recall_hd.append(rec)
                    else:
                        ctx_recall_hd.append(0.0)
            else:
                chunks_per_ctx_hd.append(0)
                distinct_ids_hd.append(0)
                ctx_recall_hd.append(0.0)

        f1_vals_hd = list(hd_sub["f1_sub"])
        rho_hd, p_val_hd = spearmanr(ctx_recall_hd, f1_vals_hd)

        diagnostics_rows.append({
            "dataset": ds_name,
            "arm": "E0'-HD-k200",
            "n_queries": n_queries,
            "mean_pred_tech_count": round(float(np.mean(pred_counts_hd)), 2),
            "mean_distinct_ids_in_ctx": round(float(np.mean(distinct_ids_hd)), 2),
            "mean_chunks_in_ctx": round(float(np.mean(chunks_per_ctx_hd)), 2),
            "mean_context_recall": round(float(np.mean(ctx_recall_hd)), 4),
            "abstention_count": abstain_hd,
            "empty_response_count": empty_hd,
            "truncation_count": trunc_hd,
            "spearman_ctx_rec_vs_f1": round(float(rho_hd), 4),
            "spearman_p": round(float(p_val_hd), 4),
        })

        # 4. E1h (from results/phase_7 top200 chunks, truncated to B=500 tokens)
        e1h_records = p7_chunks[ds_name]["E1h"]
        chunks_per_ctx_e1h = []
        distinct_ids_e1h = []
        ctx_recall_e1h = []
        pred_counts_e1h = []
        abstain_e1h = 0
        empty_e1h = 0
        trunc_e1h = 0
        f1_vals_e1h = []

        for idx, row in df_bench.iterrows():
            gt_set = parse_ground_truth_techniques(str(row.get("techniques", row.get("ground_truth", ""))))
            raw_top200 = e1h_records[idx]["top200"]
            docs = [Document(page_content=c["page_content"], metadata=c.get("metadata", {})) for c in raw_top200]
            trunc_docs = truncate_to_token_budget(docs, budget_tokens=500)
            chunks_per_ctx_e1h.append(len(trunc_docs))
            ctx_text = " ".join([d.page_content for d in trunc_docs])
            ctx_techs = extract_technique_ids_from_text(ctx_text)
            distinct_ids_e1h.append(len(ctx_techs))
            if gt_set:
                rec = len(ctx_techs & gt_set) / len(gt_set)
                ctx_recall_e1h.append(rec)
            else:
                ctx_recall_e1h.append(0.0)

            c_file = cache_dir / f"E1h_mixed_HD_b500_{ds_name}_row_{idx}.json"
            if c_file.is_file():
                with open(c_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                raw_ans = d.get("raw_answer", "")
                if is_abstention(raw_ans):
                    abstain_e1h += 1
                if d.get("finish_reason") == "FinishReason.MAX_TOKENS":
                    trunc_e1h += 1
                preds = extract_technique_ids_from_text(raw_ans)
                pred_counts_e1h.append(len(preds))
                if len(preds) == 0:
                    empty_e1h += 1
                f1_sub = compute_technique_f1(preds, gt_set)["f1_sub"]
                f1_vals_e1h.append(f1_sub)
            else:
                pred_counts_e1h.append(0)
                f1_vals_e1h.append(0.0)

        rho_e1h, p_val_e1h = spearmanr(ctx_recall_e1h, f1_vals_e1h)

        diagnostics_rows.append({
            "dataset": ds_name,
            "arm": "E1h (B=500 context)",
            "n_queries": n_queries,
            "mean_pred_tech_count": round(float(np.mean(pred_counts_e1h)), 2),
            "mean_distinct_ids_in_ctx": round(float(np.mean(distinct_ids_e1h)), 2),
            "mean_chunks_in_ctx": round(float(np.mean(chunks_per_ctx_e1h)), 2),
            "mean_context_recall": round(float(np.mean(ctx_recall_e1h)), 4),
            "abstention_count": abstain_e1h,
            "empty_response_count": empty_e1h,
            "truncation_count": trunc_e1h,
            "spearman_ctx_rec_vs_f1": round(float(rho_e1h), 4),
            "spearman_p": round(float(p_val_e1h), 4),
        })

    df_diag = pd.DataFrame(diagnostics_rows)
    df_diag.to_csv(out_dir / "diagnostics_generation.csv", index=False)
    with open(out_dir / "diagnostics_generation.json", "w", encoding="utf-8") as f:
        json.dump(diagnostics_rows, f, indent=2)

    print("\nDescriptive Diagnostics Table:")
    print(df_diag.to_string(index=False))

    # =========================================================================
    # Task C Verification: Confirm domain filter is applied to Mobile rows of cti-ate
    # =========================================================================
    print("\n--- Verifying Mobile Domain Filter on cti-ate ---")
    from scripts.run_o2_clean_benchmark import build_stix_domain_maps
    stix_kb_obj = load_stix_all_bundles()
    _, mitre_id_to_domains = build_stix_domain_maps(stix_kb_obj)

    mobile_rows = [idx for idx, row in df_ate.iterrows() if "MITRE Mobile" in str(row["query"])]
    print(f"cti-ate contains {len(mobile_rows)} queries with 'MITRE Mobile' instruction: {mobile_rows}")

    # Check retrieved chunks for these rows in E0_prime_HD_k200
    mobile_filter_details = []
    for idx in mobile_rows:
        row = df_ate.iloc[idx]
        gt_techs = parse_ground_truth_techniques(str(row.get("techniques", row.get("ground_truth", ""))))
        c_file = cache_dir / f"E0_prime_HD_k200_cti-ate_row_{idx}.json"
        if c_file.is_file():
            with open(c_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                ctx_techs = extract_technique_ids_from_text(" ".join(d.get("contexts_used", [])))
                mobile_techs = [t for t in ctx_techs if "mobile-attack" in mitre_id_to_domains.get(t, set())]
                ent_techs = [t for t in ctx_techs if "enterprise-attack" in mitre_id_to_domains.get(t, set()) and "mobile-attack" not in mitre_id_to_domains.get(t, set())]
                mobile_filter_details.append({
                    "row_idx": idx,
                    "gt_techniques": sorted(gt_techs),
                    "retrieved_total": len(ctx_techs),
                    "retrieved_mobile": len(mobile_techs),
                    "retrieved_pure_enterprise": len(ent_techs),
                })
                print(f"Row {idx:2d} (Mobile): GT={sorted(gt_techs)[:3]}, retrieved in context={len(ctx_techs)} (mobile={len(mobile_techs)}, ent={len(ent_techs)})")

    with open(out_dir / "mobile_domain_filter_check.json", "w", encoding="utf-8") as f:
        json.dump(mobile_filter_details, f, indent=2)

    print(f"Mobile domain filter check completed. All {len(mobile_rows)} mobile rows logged to {out_dir / 'mobile_domain_filter_check.json'}.")


if __name__ == "__main__":
    main()

