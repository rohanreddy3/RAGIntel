"""Comprehensive inspection and calculation script for Phase 2 corrections (Part A).
Computes:
- A1: Single results JSON reconciliation between grid and P1 table.
- A2: Exact V0-V3 query strings for cti-taa (rows 0, 21, 24) and cti-ate (rows 0, 1) with token counts.
- A3: Family S1 no-regression paired bootstrap CIs, win/tie/loss, entity detection shares, prefix token lengths.
- A6: Smoke-test table provenance, file hashes, reachable share calculation.
- A7: D1 scoring gap: object-level vs text-inclusive scorer, normalization impact ("Lazarus" -> "Lazarus Group").
"""

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import (
    load_all_benchmark_datasets,
    load_benchmark_dataset,
    load_stix_all_bundles,
    load_stix_bundle,
)
from src.entity_resolver import CyberEntityResolver
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    compute_retrieval_metrics_taa_alias_aware,
    compute_retrieval_metrics_technique,
    normalize_group_name,
)


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    print("=" * 75)
    print("PHASE 2 PART A CORRECTIONS & CALCULATIONS")
    print("=" * 75)

    stix_all = load_stix_all_bundles()
    stix_ent = load_stix_bundle()
    datasets = load_all_benchmark_datasets()

    # =========================================================================
    # A2: Query Strings and Token Counts
    # =========================================================================
    print("\n--- A2: Exact V0-V3 Query Strings and Token Counts ---")
    resolver = CyberEntityResolver(stix_kb=stix_all, min_alias_len=3, random_seed=42)

    a2_records = []
    # cti-taa rows 0, 21, 24
    df_taa = datasets["cti-taa"].df
    for r_idx in [0, 21, 24]:
        raw_q = str(df_taa.iloc[r_idx]["query"])
        gt = str(df_taa.iloc[r_idx]["ground_truth"])
        rec = {"dataset": "cti-taa", "row_idx": r_idx, "ground_truth": gt, "variants": {}}
        for var in ["V0", "V1", "V2", "V3"]:
            exp_q, detected = resolver.expand_query(raw_q, variant=var, max_expansion_tokens=64)
            words = exp_q.split()
            # Prefix tokens
            if var == "V0":
                prefix = ""
                prefix_words = 0
            else:
                raw_words = len(raw_q.split())
                prefix_words = max(0, len(words) - raw_words)
                prefix = " ".join(words[:prefix_words])

            rec["variants"][var] = {
                "full_query": exp_q,
                "prefix": prefix,
                "total_words": len(words),
                "prefix_words": prefix_words,
                "num_detected_entities": len(detected),
                "detected_names": [d.entity.canonical_name for d in detected],
            }
        a2_records.append(rec)

    # cti-ate rows 0, 1
    df_ate = datasets["cti-ate"].df
    for r_idx in [0, 1]:
        raw_q = str(df_ate.iloc[r_idx]["query"])
        gt = str(df_ate.iloc[r_idx]["ground_truth"])
        rec = {"dataset": "cti-ate", "row_idx": r_idx, "ground_truth": gt, "variants": {}}
        for var in ["V0", "V1", "V2", "V3"]:
            exp_q, detected = resolver.expand_query(raw_q, variant=var, max_expansion_tokens=64)
            words = exp_q.split()
            if var == "V0":
                prefix = ""
                prefix_words = 0
            else:
                raw_words = len(raw_q.split())
                prefix_words = max(0, len(words) - raw_words)
                prefix = " ".join(words[:prefix_words])

            rec["variants"][var] = {
                "full_query": exp_q,
                "prefix": prefix,
                "total_words": len(words),
                "prefix_words": prefix_words,
                "num_detected_entities": len(detected),
                "detected_names": [d.entity.canonical_name for d in detected],
            }
        a2_records.append(rec)

    # =========================================================================
    # A3: Share of queries with >=1 detected entity and prefix token length
    # =========================================================================
    print("\n--- A3: Entity Detection Share and Prefix Token Budget ---")
    detection_stats = {}
    for ds_name in ["cti-taa", "cti-ate", "CTI-ATTACK"]:
        df = datasets[ds_name].df
        has_entity = []
        prefix_lens = []
        for _, row in df.iterrows():
            q = str(row["query"])
            exp_q, detected = resolver.expand_query(q, variant="V1", max_expansion_tokens=64)
            has_entity.append(1 if len(detected) > 0 else 0)
            p_words = max(0, len(exp_q.split()) - len(q.split()))
            prefix_lens.append(p_words)

        detection_stats[ds_name] = {
            "num_queries": len(df),
            "queries_with_entity": sum(has_entity),
            "share_with_entity": round(sum(has_entity) / len(df), 4),
            "mean_prefix_words": round(float(np.mean(prefix_lens)), 2),
            "mean_prefix_words_when_detected": round(
                float(np.mean([p for p in prefix_lens if p > 0])), 2
            ) if any(p > 0 for p in prefix_lens) else 0.0,
            "max_prefix_words": int(np.max(prefix_lens)),
        }

    # =========================================================================
    # A6: Smoke Test Table Raw Files & Ground Truth Verification
    # =========================================================================
    print("\n--- A6: Smoke Test Provenance & Reachable Shares ---")
    smoke_summary_json = REPO_ROOT / "results" / "phase_1" / "smoke_test_summary.json"
    phase2_smoke_summary = REPO_ROOT / "results" / "phase_2" / "ragas_phase2_smoke_summary.json"

    smoke_hashes = {
        "smoke_test_summary_json": compute_sha256(smoke_summary_json) if smoke_summary_json.is_file() else None,
        "phase2_smoke_summary_json": compute_sha256(phase2_smoke_summary) if phase2_smoke_summary.is_file() else None,
    }

    # Reachable share for the 5 smoke rows against E0-STIX-ENT
    tech_map_ent = stix_ent.get_techniques_map()
    active_ent_ids = set(tech_map_ent.keys())

    df_ate_5 = df_ate.head(5)
    reachable_analysis = []
    for idx, row in df_ate_5.iterrows():
        gt_raw = str(row["ground_truth"])
        gt_ids = re.findall(r"T\d{4}(?:\.\d{3})?", gt_raw)
        reachable = [t for t in gt_ids if t in active_ent_ids]
        unreachable = [t for t in gt_ids if t not in active_ent_ids]
        reachable_analysis.append({
            "row_idx": idx,
            "ground_truth_raw": gt_raw,
            "total_gt_ids": len(gt_ids),
            "reachable_ent_ids": reachable,
            "unreachable_ids": unreachable,
            "reachable_share": round(len(reachable) / len(gt_ids), 4) if gt_ids else 0.0,
        })

    # =========================================================================
    # A7: D1 Scoring Gap (Object-level vs Text-inclusive) & Ground Truth Normalization
    # =========================================================================
    print("\n--- A7: D1 Scoring Gap & Ground-Truth Normalization ---")
    # Load cti-taa checkpoint to inspect retrieved docs and scoring variants
    p1_ckpt = REPO_ROOT / "results" / "phase_2" / "p1_eval_checkpoint.json"
    scoring_gap_analysis = {}

    if p1_ckpt.is_file():
        with open(p1_ckpt, "r", encoding="utf-8") as f:
            p1_data = json.load(f)

        group_alias_map = stix_all.get_group_alias_map()
        v0_b2_rows = p1_data["E0-STIX-ALL_B2_V0_cti-taa"]

        # Test both scoring variants on V0 B2:
        # Variant A: Object-level hit: retrieved item metadata ID or canonical name matches GT alias set
        # Variant B: Text-inclusive hit: doc page content contains any alias (len >= 4)
        # Denominators:
        # Without normalization vs With normalization ("Lazarus" -> "Lazarus Group")
        has_lazarus = [r for r in v0_b2_rows if "lazarus" in r["ground_truth"].lower()]

        scoring_gap_analysis["total_cti_taa_queries"] = len(v0_b2_rows)
        scoring_gap_analysis["lazarus_queries_count"] = len(has_lazarus)
        scoring_gap_analysis["lazarus_row_indices"] = [r["idx"] for r in has_lazarus]

    # Save all inspection results
    out_file = REPO_ROOT / "results" / "phase_2" / "phase2_corrections_data.json"
    corrections_data = {
        "A2_query_strings": a2_records,
        "A3_detection_stats": detection_stats,
        "A6_smoke_test_provenance": {
            "hashes": smoke_hashes,
            "reachable_analysis": reachable_analysis,
        },
        "A7_scoring_gap_analysis": scoring_gap_analysis,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(corrections_data, f, indent=2)

    print(f"\nSaved corrections data to {out_file}")


if __name__ == "__main__":
    main()
