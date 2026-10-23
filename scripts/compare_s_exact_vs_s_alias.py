"""Compare S_exact vs S_alias on CTI-TAA (Part D1).

For CTI-TAA (50 queries), computes retrieval metrics under:
1. S_exact: strictly requires the canonical name or canonical MITRE ID in the retrieved doc
2. S_alias: credits any valid STIX alias or canonical name

Evaluates on:
- E0-STIX-ALL (primary KB) and E0-STIX-ENT (secondary KB)
- Baseline B2 (Truncated) and Baseline B3 (MaxSim)

Outputs comparison table and exact gap (S_alias - S_exact).
"""

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_stix_bundle, load_stix_all_bundles
from src.retriever import HybridSTIXRetriever
from src.retrieval_eval import normalize_group_name


def evaluate_s_exact_vs_s_alias_single_query(
    docs: List[Any],
    gt_raw: str,
    group_alias_map: Dict[str, Dict[str, Any]],
    k_values: List[int] = [1, 3, 5, 10],
) -> Dict[str, float]:
    """Compute S_exact and S_alias metrics for a single query."""
    raw_gt_norm = normalize_group_name(gt_raw)

    # 1. Identify ground-truth canonical entity
    gt_canonical_norm = None
    gt_canonical_id = None
    all_gt_aliases: Set[str] = {raw_gt_norm}

    for gid, gdata in group_alias_map.items():
        canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
        alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == canonical_norm or raw_gt_norm in alias_norms or any(a in raw_gt_norm for a in alias_norms if len(a) > 3):
            gt_canonical_norm = canonical_norm
            gt_canonical_id = gid.lower()
            all_gt_aliases.add(gid.lower())
            all_gt_aliases.add(canonical_norm)
            all_gt_aliases.update(alias_norms)
            break

    if not gt_canonical_norm:
        gt_canonical_norm = raw_gt_norm

    # 2. Score each retrieved doc
    rel_ranks_exact = []
    rel_ranks_alias = []

    for doc in docs:
        doc_text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        doc_meta = doc.metadata if hasattr(doc, "metadata") else {}
        doc_mid = doc_meta.get("mitre_id", "").lower()
        doc_name_norm = normalize_group_name(doc_meta.get("name", ""))
        doc_aliases = [normalize_group_name(a) for a in doc_meta.get("aliases", [])]

        # S_exact: requires canonical ID or canonical name
        is_rel_exact = 0
        if gt_canonical_id and doc_mid == gt_canonical_id:
            is_rel_exact = 1
        elif doc_name_norm and doc_name_norm == gt_canonical_norm:
            is_rel_exact = 1
        elif re.search(r"\b" + re.escape(gt_canonical_norm) + r"\b", normalize_group_name(doc_text)):
            is_rel_exact = 1

        # S_alias: credits any known STIX alias
        is_rel_alias = 0
        if is_rel_exact == 1:
            is_rel_alias = 1
        elif doc_mid and doc_mid in all_gt_aliases:
            is_rel_alias = 1
        elif any(a in all_gt_aliases for a in doc_aliases if a):
            is_rel_alias = 1
        else:
            doc_text_norm = normalize_group_name(doc_text)
            for alias in all_gt_aliases:
                if len(alias) >= 4 and alias in doc_text_norm:
                    is_rel_alias = 1
                    break

        rel_ranks_exact.append(is_rel_exact)
        rel_ranks_alias.append(is_rel_alias)

    mrr_exact = 0.0
    for r_idx, rel in enumerate(rel_ranks_exact):
        if rel == 1:
            mrr_exact = 1.0 / (r_idx + 1)
            break

    mrr_alias = 0.0
    for r_idx, rel in enumerate(rel_ranks_alias):
        if rel == 1:
            mrr_alias = 1.0 / (r_idx + 1)
            break

    res = {
        "S_exact_MRR": mrr_exact,
        "S_alias_MRR": mrr_alias,
    }
    for k in k_values:
        res[f"S_exact_Recall@{k}"] = 1.0 if any(rel_ranks_exact[:k]) else 0.0
        res[f"S_alias_Recall@{k}"] = 1.0 if any(rel_ranks_alias[:k]) else 0.0

    return res


def run_s_exact_vs_alias_comparison():
    print("=" * 70)
    print("PART D1: S_EXACT VS S_ALIAS COMPARISON ON CTI-TAA")
    print("=" * 70)

    df_taa = pd.read_excel("data/datasets/cti-taa.xlsx")
    results = {}

    kb_configs = [
        ("E0-STIX-ALL", load_stix_all_bundles(), ".cache/retriever_index_all"),
        ("E0-STIX-ENT", load_stix_bundle(), ".cache/retriever_index"),
    ]

    for kb_name, kb, cache_dir in kb_configs:
        print(f"\n--- Loading Retriever for {kb_name} ---")
        retriever = HybridSTIXRetriever(stix_kb=kb, cache_dir=cache_dir)
        group_alias_map = kb.get_group_alias_map()

        results[kb_name] = {}

        for b_code, enable_chunking in [("B2", False), ("B3", True)]:
            mode_label = "B3_MaxSim" if enable_chunking else "B2_Truncated"
            print(f"Evaluating {kb_name} under {mode_label}...")

            query_scores = []
            for idx, row in df_taa.iterrows():
                q = str(row["query"])
                gt = str(row["ground_truth"])
                docs = retriever.retrieve(q, top_k=10, enable_query_chunking=enable_chunking)
                m = evaluate_s_exact_vs_s_alias_single_query(docs, gt, group_alias_map)
                query_scores.append(m)

            df_scores = pd.DataFrame(query_scores)
            summary = {}
            for col in df_scores.columns:
                summary[col] = round(float(df_scores[col].mean()), 4)

            # Compute gaps
            summary["Recall@5_Gap"] = round(summary["S_alias_Recall@5"] - summary["S_exact_Recall@5"], 4)
            summary["Recall@10_Gap"] = round(summary["S_alias_Recall@10"] - summary["S_exact_Recall@10"], 4)
            summary["MRR_Gap"] = round(summary["S_alias_MRR"] - summary["S_exact_MRR"], 4)

            results[kb_name][b_code] = summary
            print(f"  {mode_label}: S_exact Rec@10={summary['S_exact_Recall@10']:.4f} | S_alias Rec@10={summary['S_alias_Recall@10']:.4f} | Gap={summary['Recall@10_Gap']:+.4f}")

    out_file = Path("results/phase_2/s_exact_vs_alias_comparison.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved S_exact vs S_alias results to {out_file}")


if __name__ == "__main__":
    run_s_exact_vs_alias_comparison()
