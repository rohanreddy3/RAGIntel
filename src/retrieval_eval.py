"""Retrieval evaluation metrics module (without any LLM calls).

Computes:
- Precision@K
- Recall@K (Exact ID, Reachable Macro, Reachable Micro, Sub-technique Credit)
- MRR (Mean Reciprocal Rank)
- nDCG@K
- Paired bootstrap 95% confidence intervals (10,000 resamples, seed 42)
for CTI-ATE, CTI-ATTACK (technique IDs), and CTI-TAA (alias-aware threat group matching).
"""

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np


def extract_technique_ids_from_text(text: str) -> Set[str]:
    """Extract all MITRE technique IDs (e.g. T1071, T1071.001) from text."""
    if not text:
        return set()
    matches = re.findall(r"T\d{4}(?:\.\d{3})?", text)
    return set(matches)


def parse_ground_truth_techniques(gt_str: str) -> Set[str]:
    """Parse comma/whitespace-separated technique IDs from ground truth string."""
    return extract_technique_ids_from_text(gt_str)


def compute_retrieval_metrics_technique(
    retrieved_docs: List[Any],
    ground_truth_str: str,
    k_values: List[int] = [1, 3, 5, 10],
    reachable_ids: Optional[Set[str]] = None,
    subtechnique_parent_credit: bool = False,
    subtechnique_direction: str = "sub_credits_parent",
) -> Dict[str, float]:
    """Compute Precision@K, Recall@K, MRR, and nDCG@K for technique extraction.

    Args:
        retrieved_docs: List of retrieved Document objects.
        ground_truth_str: String containing ground truth technique IDs.
        k_values: List of K thresholds.
        reachable_ids: Optional set of STIX active IDs to restrict evaluation to reachable ceiling.
        subtechnique_parent_credit: If True, evaluates sub-technique credit.
        subtechnique_direction: Direction of sub-technique credit:
            - 'sub_credits_parent': Retrieved sub-technique (T1059.001) satisfies parent GT (T1059).
              Retrieved parent does NOT satisfy sub-technique GT.
            - 'bidirectional': Sub-technique satisfies parent AND parent satisfies sub-technique.

    Returns:
        Dict of metrics. When reachable_ids is provided and the query has 0 reachable GT IDs,
        Reachable metrics return float('nan').
    """
    raw_gt_set = parse_ground_truth_techniques(ground_truth_str)
    num_raw_gt = len(raw_gt_set)

    if num_raw_gt == 0:
        res = {f"Precision@{k}": 0.0 for k in k_values}
        res.update({f"Recall@{k}": 0.0 for k in k_values})
        res.update({"MRR": 0.0, "nDCG@10": 0.0, "num_gt": 0, "num_reachable_gt": 0})
        if reachable_ids is not None:
            res.update({f"Reachable_Recall@{k}": float("nan") for k in k_values})
            res.update({"Reachable_MRR": float("nan"), "Reachable_nDCG@10": float("nan")})
        return res

    # Helper function to expand retrieved techniques based on credit direction
    def expand_retrieved_techs(techs: Set[str]) -> Set[str]:
        if not subtechnique_parent_credit:
            return set(techs)
        expanded = set(techs)
        for t in techs:
            if "." in t:
                # Sub-technique credits parent: add parent ID to retrieved set
                expanded.add(t.split(".")[0])
        return expanded

    def expand_gt_techs(techs: Set[str]) -> Set[str]:
        if not subtechnique_parent_credit:
            return set(techs)
        expanded = set(techs)
        if subtechnique_direction == "bidirectional":
            for t in techs:
                if "." in t:
                    expanded.add(t.split(".")[0])
        return expanded

    # 1. Standard evaluation (all GT IDs)
    eval_gt_set = expand_gt_techs(raw_gt_set)

    # Determine binary relevance for each retrieved rank
    relevance_ranks: List[int] = []
    retrieved_techs_by_rank: List[Set[str]] = []

    for doc in retrieved_docs:
        doc_text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        doc_meta_id = doc.metadata.get("mitre_id", "") if hasattr(doc, "metadata") else ""
        doc_techs = extract_technique_ids_from_text(doc_text)
        if doc_meta_id and doc_meta_id.startswith("T"):
            doc_techs.add(doc_meta_id)

        eval_doc_techs = expand_retrieved_techs(doc_techs)
        retrieved_techs_by_rank.append(eval_doc_techs)

        is_rel = 1 if bool(eval_doc_techs & eval_gt_set) else 0
        relevance_ranks.append(is_rel)

    metrics: Dict[str, float] = {
        "num_gt": num_raw_gt,
    }

    # MRR
    mrr = 0.0
    for rank_idx, rel in enumerate(relevance_ranks):
        if rel == 1:
            mrr = 1.0 / (rank_idx + 1)
            break
    metrics["MRR"] = round(mrr, 4)

    # Precision@K, Recall@K, nDCG@K
    for k in k_values:
        sub_rel = relevance_ranks[:k]
        p_at_k = sum(sub_rel) / max(1, k)
        metrics[f"Precision@{k}"] = round(p_at_k, 4)

        covered_gt = set()
        for doc_techs in retrieved_techs_by_rank[:k]:
            covered_gt.update(doc_techs & eval_gt_set)
        # Denominator is original ground truth set size
        r_at_k = len(covered_gt) / num_raw_gt
        metrics[f"Recall@{k}"] = round(r_at_k, 4)
        metrics[f"covered_gt@{k}"] = len(covered_gt)

        # nDCG@K
        dcg = sum((rel / math.log2(i + 2)) for i, rel in enumerate(sub_rel))
        ideal_rels = [1] * min(k, num_raw_gt)
        idcg = sum((1.0 / math.log2(i + 2)) for i in range(len(ideal_rels)))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        metrics[f"nDCG@{k}"] = round(ndcg, 4)

    # 2. Reachable evaluation
    if reachable_ids is not None:
        reach_gt_set = raw_gt_set.intersection(reachable_ids)
        num_reach_gt = len(reach_gt_set)
        metrics["num_reachable_gt"] = num_reach_gt

        if num_reach_gt == 0:
            # Query has zero reachable items in this knowledge base:
            # Unreachable query: recall is mathematically undefined (NaN)
            for k in k_values:
                metrics[f"Reachable_Recall@{k}"] = float("nan")
                metrics[f"covered_reachable_gt@{k}"] = 0
            metrics["Reachable_MRR"] = float("nan")
            metrics["Reachable_nDCG@10"] = float("nan")
        else:
            eval_reach_gt = expand_gt_techs(reach_gt_set)
            reach_rel_ranks = []
            for doc_techs in retrieved_techs_by_rank:
                is_r_rel = 1 if bool(doc_techs & eval_reach_gt) else 0
                reach_rel_ranks.append(is_r_rel)

            reach_mrr = 0.0
            for rank_idx, rel in enumerate(reach_rel_ranks):
                if rel == 1:
                    reach_mrr = 1.0 / (rank_idx + 1)
                    break
            metrics["Reachable_MRR"] = round(reach_mrr, 4)

            for k in k_values:
                sub_r_rel = reach_rel_ranks[:k]
                r_covered = set()
                for doc_techs in retrieved_techs_by_rank[:k]:
                    r_covered.update(doc_techs & eval_reach_gt)
                metrics[f"Reachable_Recall@{k}"] = round(len(r_covered) / num_reach_gt, 4)
                metrics[f"covered_reachable_gt@{k}"] = len(r_covered)

            dcg_r = sum((rel / math.log2(i + 2)) for i, rel in enumerate(reach_rel_ranks[:10]))
            ideal_r = [1] * min(10, num_reach_gt)
            idcg_r = sum((1.0 / math.log2(i + 2)) for i in range(len(ideal_r)))
            metrics["Reachable_nDCG@10"] = round(dcg_r / idcg_r if idcg_r > 0 else 0.0, 4)

    return metrics


def normalize_group_name(name: str) -> str:
    """Normalize threat actor string for matching."""
    s = name.lower()
    s = re.sub(r"\(alias.*?\)", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s.strip()


def compute_retrieval_metrics_taa_alias_aware(
    retrieved_docs: List[Any],
    ground_truth_str: str,
    group_alias_map: Dict[str, Dict[str, Any]],
    k_values: List[int] = [1, 3, 5, 10],
) -> Dict[str, float]:
    """Compute alias-aware Precision@K, Recall@K, MRR, and nDCG@K for CTI-TAA attribution."""
    raw_gt_norm = normalize_group_name(ground_truth_str)
    all_gt_aliases: Set[str] = {raw_gt_norm}

    # Match with STIX group map to expand all known aliases of the ground truth
    for gid, gdata in group_alias_map.items():
        canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
        alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == canonical_norm or raw_gt_norm in alias_norms or any(a in raw_gt_norm for a in alias_norms if len(a) > 3):
            all_gt_aliases.add(gid.lower())
            all_gt_aliases.add(canonical_norm)
            all_gt_aliases.update(alias_norms)

    relevance_ranks: List[int] = []

    for doc in retrieved_docs:
        doc_text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        doc_meta = doc.metadata if hasattr(doc, "metadata") else {}
        doc_meta_id = doc_meta.get("mitre_id", "").lower()
        doc_aliases = [normalize_group_name(a) for a in doc_meta.get("aliases", [])]

        is_rel = 0
        if doc_meta_id and doc_meta_id in all_gt_aliases:
            is_rel = 1
        elif any(a in all_gt_aliases for a in doc_aliases if a):
            is_rel = 1
        else:
            doc_text_norm = normalize_group_name(doc_text)
            for alias in all_gt_aliases:
                if len(alias) >= 4 and alias in doc_text_norm:
                    is_rel = 1
                    break

        relevance_ranks.append(is_rel)

    metrics: Dict[str, float] = {}

    # MRR & first hit rank
    mrr = 0.0
    first_rank = 0
    for rank_idx, rel in enumerate(relevance_ranks):
        if rel == 1:
            mrr = 1.0 / (rank_idx + 1)
            first_rank = rank_idx + 1
            break
    metrics["MRR"] = round(mrr, 4)
    metrics["first_hit_rank"] = float(first_rank)

    # Precision@K, Recall@K, nDCG@K
    for k in k_values:
        sub_rel = relevance_ranks[:k]
        p_at_k = sum(sub_rel) / max(1, k)
        r_at_k = 1.0 if any(sub_rel) else 0.0
        dcg = sum((rel / math.log2(i + 2)) for i, rel in enumerate(sub_rel))
        idcg = 1.0
        ndcg = dcg / idcg

        metrics[f"Precision@{k}"] = round(p_at_k, 4)
        metrics[f"Recall@{k}"] = round(r_at_k, 4)
        metrics[f"nDCG@{k}"] = round(ndcg, 4)

    return metrics


def compute_paired_bootstrap_ci(
    scores_before: List[float],
    scores_after: List[float],
    n_resamples: int = 10000,
    seed: int = 42,
) -> Dict[str, float]:
    """Compute paired bootstrap 95% confidence intervals on delta (After - Before).

    Args:
        scores_before: Per-query metric scores under baseline.
        scores_after: Per-query metric scores under new arm.
        n_resamples: Number of bootstrap resamples (default: 10,000).
        seed: Random seed for reproducibility (default: 42).

    Returns:
        Dict with mean_before, mean_after, mean_delta, ci_lower, ci_upper, p_value.
    """
    a = np.array(scores_before, dtype=float)
    b = np.array(scores_after, dtype=float)

    # Filter out NaNs if any (e.g. unreachable queries)
    valid_mask = (~np.isnan(a)) & (~np.isnan(b))
    a = a[valid_mask]
    b = b[valid_mask]

    n = len(a)
    if n == 0:
        return {
            "mean_before": 0.0,
            "mean_after": 0.0,
            "mean_delta": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "p_value": 1.0,
        }

    deltas = b - a
    observed_mean_delta = float(np.mean(deltas))

    rng = np.random.default_rng(seed)
    boot_indices = rng.integers(0, n, size=(n_resamples, n))
    boot_deltas = np.mean(deltas[boot_indices], axis=1)

    ci_lower = float(np.percentile(boot_deltas, 2.5))
    ci_upper = float(np.percentile(boot_deltas, 97.5))

    # Two-sided empirical p-value for H0: mean delta == 0
    # Center bootstrap distribution around 0
    centered_boot_deltas = boot_deltas - observed_mean_delta
    p_val = float(np.mean(np.abs(centered_boot_deltas) >= np.abs(observed_mean_delta)))

    return {
        "mean_before": round(float(np.mean(a)), 4),
        "mean_after": round(float(np.mean(b)), 4),
        "mean_delta": round(observed_mean_delta, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "p_value": round(p_val, 4),
    }
