"""Phase 6D Part E: Secondary KB Replication (E0-STIX-ENT).

Evaluates query hygiene (V0h) and relationship expansion (Vrel) over E0-STIX-ENT
(Enterprise STIX only, 1,698 active objects) across cti-taa (50), cti-ate (60),
and CTI-ATTACK (229) under baselines B2 and B3.

Strictly offline, thread cap 4, one heavy retrieval process at a time.
Strictly descriptive metrics; no causal language.
"""

import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import (
    load_benchmark_dataset,
    load_stix_bundle,
    STIXKnowledgeBase,
)
from src.retriever import HybridSTIXRetriever, Document
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    compute_retrieval_metrics_technique,
    compute_retrieval_metrics_taa_alias_aware,
    normalize_group_name,
)
from src.entity_resolver import CyberEntityResolver
from scripts.run_o1_phase5_benchmark import (
    split_query,
    build_alias_matchers,
    expand_v1h,
    expand_vrel,
)
from scripts.run_vrel_t_extension import (
    build_malware_tech_graph,
    expand_vrel_t,
)


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


def evaluate_dual_attribution(
    docs: List[Document],
    gt_name: str,
    group_alias_map: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    """Evaluate attribution under object-level and text-inclusive rules."""
    raw_gt_norm = normalize_group_name(gt_name)
    all_gt_aliases: Set[str] = {raw_gt_norm}
    target_gid = None

    for gid, gdata in group_alias_map.items():
        canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
        alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == canonical_norm or raw_gt_norm in alias_norms or any(a in raw_gt_norm for a in alias_norms if len(a) > 3):
            target_gid = gid.lower()
            all_gt_aliases.add(target_gid)
            all_gt_aliases.add(canonical_norm)
            all_gt_aliases.update(alias_norms)

    obj_ranks: List[int] = []
    txt_ranks: List[int] = []

    for doc in docs:
        doc_text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        doc_meta = doc.metadata if hasattr(doc, "metadata") else {}
        doc_meta_id = doc_meta.get("mitre_id", "").lower()
        doc_aliases = [normalize_group_name(a) for a in doc_meta.get("aliases", [])]

        is_obj = 0
        if target_gid and (doc_meta_id == target_gid or doc_meta.get("stix_id", "").lower() == target_gid):
            is_obj = 1
        elif doc_meta_id and doc_meta_id in all_gt_aliases:
            is_obj = 1
        elif any(a in all_gt_aliases for a in doc_aliases if a):
            is_obj = 1
        obj_ranks.append(is_obj)

        is_txt = is_obj
        if not is_txt:
            doc_text_norm = normalize_group_name(doc_text)
            for alias in all_gt_aliases:
                if len(alias) >= 4 and alias in doc_text_norm:
                    is_txt = 1
                    break
        txt_ranks.append(is_txt)

    def calc(ranks):
        r10 = 1.0 if any(ranks[:10]) else 0.0
        mrr = 0.0
        for idx, rel in enumerate(ranks):
            if rel:
                mrr = 1.0 / (idx + 1)
                break
        return r10, mrr

    obj_r10, obj_mrr = calc(obj_ranks)
    txt_r10, txt_mrr = calc(txt_ranks)

    return {
        "object_level": {"Recall@10": obj_r10, "MRR": obj_mrr},
        "text_inclusive": {"Recall@10": txt_r10, "MRR": txt_mrr},
    }


def main():
    print("=" * 80)
    print("PHASE 6D PART E: SECONDARY KB REPLICATION (E0-STIX-ENT)")
    print("=" * 80)

    out_dir = REPO_ROOT / "results" / "phase_6d"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_file = REPO_ROOT / ".cache" / "phase_6d_secondary_kb_top10.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    top10_cache: Dict[str, Dict[str, Dict[str, Dict[str, List]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                raw_c = json.load(f)
                for b_k in raw_c:
                    for ds_k in raw_c[b_k]:
                        for a_k in raw_c[b_k][ds_k]:
                            for q_k in raw_c[b_k][ds_k][a_k]:
                                top10_cache[b_k][ds_k][a_k][q_k] = raw_c[b_k][ds_k][a_k][q_k]
            print(f"Loaded existing top10 cache from {cache_file}")
        except Exception as e:
            print(f"Warning: could not load cache: {e}")

    # 1. Load E0-STIX-ENT
    print("Loading E0-STIX-ENT (Enterprise ATT&CK STIX)...")
    stix_ent = load_stix_bundle()
    print(f"Loaded E0-STIX-ENT: {stix_ent.total_objects} active objects.")

    group_alias_map = stix_ent.get_group_alias_map()
    tech_map = stix_ent.get_techniques_map()
    active_tech_ids = set(tech_map.keys())

    from scripts.run_o1_phase5_benchmark import build_stix_indices
    intrusion_sets, software, software_to_groups, software_weights = build_stix_indices(stix_ent)
    matchers = build_alias_matchers(intrusion_sets, software)

    malware_by_id, alias_to_malware, tech_by_id, malware_to_techs = build_malware_tech_graph(stix_ent)

    # Initialize retriever for E0-STIX-ENT
    print("Initializing HybridSTIXRetriever for E0-STIX-ENT (.cache/retriever_index)...")
    retriever = HybridSTIXRetriever(stix_kb=stix_ent, cache_dir=".cache/retriever_index")
    resolver = CyberEntityResolver(stix_kb=stix_ent, min_alias_len=3, random_seed=42)

    # Datasets
    datasets = {
        "cti-taa": load_benchmark_dataset("cti-taa").df,
        "cti-ate": load_benchmark_dataset("cti-ate").df,
        "CTI-ATTACK": load_benchmark_dataset("CTI-ATTACK").df,
    }

    # Store per-query scores: baseline -> dataset -> arm -> metric -> list of floats
    per_query_scores = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    # Evaluation loop
    for b_code, enable_chunking in [("B2", False), ("B3", True)]:
        b_name = "MiniLM-Truncated-256" if not enable_chunking else "MiniLM-MaxSim-Windows"
        print(f"\n{'='*70}")
        print(f"RUNNING BASELINE {b_code}: {b_name} ON E0-STIX-ENT")
        print(f"{'='*70}")

        for ds_name, df in datasets.items():
            print(f"\n--- Dataset: {ds_name} (N={len(df)}) [{b_code}] ---")
            
            for q_idx, row in df.iterrows():
                q_raw = str(row["query"])
                gt = str(row.get("ground_truth", ""))
                _, body, _ = split_query(q_raw)

                # Define arms
                if ds_name == "cti-taa":
                    q_v0 = q_raw
                    q_v0h = body
                    q_v1, _ = resolver.expand_query(q_raw, variant="V1")
                    q_vrel, _ = expand_vrel(body, matchers, intrusion_sets, software_to_groups, software_weights)
                    arms = {
                        "V0": q_v0,
                        "V0h": q_v0h,
                        "V1": q_v1,
                        "Vrel": q_vrel,
                    }
                else:
                    domain = "enterprise-attack"
                    q_v0 = q_raw
                    q_v0h = body
                    q_v1, _ = resolver.expand_query(q_raw, variant="V1")
                    q_vrel, _ = expand_vrel_t(body, domain, alias_to_malware, malware_by_id, tech_by_id, malware_to_techs)
                    arms = {
                        "V0": q_v0,
                        "V0h": q_v0h,
                        "V1": q_v1,
                        "Vrel": q_vrel,
                    }

                q_key = str(q_idx)
                for arm, q_text in arms.items():
                    if q_key in top10_cache[b_code][ds_name][arm]:
                        cached_docs = top10_cache[b_code][ds_name][arm][q_key]
                        docs = [
                            Document(page_content=d["page_content"], metadata=d["metadata"])
                            for d in cached_docs
                        ]
                    else:
                        docs = retriever.retrieve(q_text, top_k=10, enable_query_chunking=enable_chunking)
                        top10_cache[b_code][ds_name][arm][q_key] = [
                            {"page_content": d.page_content, "metadata": d.metadata}
                            for d in docs
                        ]

                    if ds_name == "cti-taa":
                        m_dual = evaluate_dual_attribution(docs, gt, group_alias_map)
                        per_query_scores[b_code][ds_name][arm]["Object_Recall@10"].append(m_dual["object_level"]["Recall@10"])
                        per_query_scores[b_code][ds_name][arm]["Object_MRR"].append(m_dual["object_level"]["MRR"])
                        per_query_scores[b_code][ds_name][arm]["Alias_Recall@10"].append(m_dual["text_inclusive"]["Recall@10"])
                        per_query_scores[b_code][ds_name][arm]["Alias_MRR"].append(m_dual["text_inclusive"]["MRR"])
                    else:
                        m_exact = compute_retrieval_metrics_technique(docs, gt, k_values=[10], subtechnique_parent_credit=False)
                        m_sub = compute_retrieval_metrics_technique(docs, gt, k_values=[10], subtechnique_parent_credit=True)
                        per_query_scores[b_code][ds_name][arm]["Subtech_Recall@10"].append(m_sub["Recall@10"])
                        per_query_scores[b_code][ds_name][arm]["Subtech_MRR"].append(m_sub["MRR"])
                        per_query_scores[b_code][ds_name][arm]["Exact_Recall@10"].append(m_exact["Recall@10"])
                        per_query_scores[b_code][ds_name][arm]["Exact_MRR"].append(m_exact["MRR"])

                if (q_idx + 1) % 25 == 0 or q_idx == len(df) - 1:
                    print(f"  [{b_code} {ds_name}] Processed {q_idx + 1}/{len(df)} queries...", flush=True)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(top10_cache, f)

    # 3. Compute Contrasts and Summary Metrics
    print("\n" + "=" * 80)
    print("E0-STIX-ENT RETRIEVAL CONTRASTS & COMPARISONS")
    print("=" * 80)

    contrasts_list = [
        ("V0h vs V0", "V0", "V0h", "Hygiene effect"),
        ("Vrel vs V1", "V1", "Vrel", "Relationship vs Alias expansion"),
        ("Vrel vs V0h", "V0h", "Vrel", "Relationship over Hygiene"),
        ("V1 vs V0", "V0", "V1", "Alias expansion over Raw"),
    ]

    contrast_records = []
    evaluations_summary = {}

    for b_code in ["B2", "B3"]:
        evaluations_summary[b_code] = {}
        for ds_name in ["cti-taa", "cti-ate", "CTI-ATTACK"]:
            evaluations_summary[b_code][ds_name] = {}
            metric_keys = (
                ["Object_Recall@10", "Alias_Recall@10", "Object_MRR"]
                if ds_name == "cti-taa"
                else ["Subtech_Recall@10", "Exact_Recall@10", "Subtech_MRR"]
            )

            # Store arm means
            arm_means = {}
            for arm in ["V0", "V0h", "V1", "Vrel"]:
                arm_means[arm] = {m: float(np.mean(per_query_scores[b_code][ds_name][arm][m])) for m in metric_keys}
            evaluations_summary[b_code][ds_name]["arm_means"] = arm_means

            # Primary metric for contrast reporting
            primary_met = "Object_Recall@10" if ds_name == "cti-taa" else "Subtech_Recall@10"

            for c_name, ctrl_arm, treat_arm, c_desc in contrasts_list:
                for met in metric_keys:
                    c_vals = per_query_scores[b_code][ds_name][ctrl_arm][met]
                    t_vals = per_query_scores[b_code][ds_name][treat_arm][met]

                    boot = compute_paired_bootstrap_ci(c_vals, t_vals, n_resamples=10000, seed=42)
                    st = compute_exact_sign_test(c_vals, t_vals)

                    rec = {
                        "kb": "E0-STIX-ENT",
                        "baseline": b_code,
                        "dataset": ds_name,
                        "contrast": c_name,
                        "contrast_description": c_desc,
                        "metric": met,
                        "is_primary_metric": (met == primary_met),
                        "control_arm": ctrl_arm,
                        "treatment_arm": treat_arm,
                        "control_mean": boot["mean_before"],
                        "treatment_mean": boot["mean_after"],
                        "delta": boot["mean_delta"],
                        "ci_lower_95": boot["ci_lower"],
                        "ci_upper_95": boot["ci_upper"],
                        "bootstrap_p": boot["p_value"],
                        "wins": st["wins"],
                        "ties": st["ties"],
                        "losses": st["losses"],
                        "exact_sign_p": st["sign_p"],
                    }
                    contrast_records.append(rec)
                    if met == primary_met:
                        sign_ind = "+" if rec["delta"] >= 0 else ""
                        print(
                            f"[{b_code} | {ds_name:<10}] {c_name:<12} ({met}): "
                            f"ctrl={rec['control_mean']:.4f}, treat={rec['treatment_mean']:.4f}, "
                            f"Delta={sign_ind}{rec['delta']:.4f} [95% CI {rec['ci_lower_95']:.4f}, {rec['ci_upper_95']:.4f}], "
                            f"W/T/L={rec['wins']}/{rec['ties']}/{rec['losses']}, p_exact={rec['exact_sign_p']:.4f}"
                        )

    # Save to CSV and JSON
    df_contrasts = pd.DataFrame(contrast_records)
    csv_path = out_dir / "secondary_kb_contrasts.csv"
    json_path = out_dir / "secondary_kb_contrasts.json"
    eval_json_path = out_dir / "secondary_kb_evaluations.json"

    df_contrasts.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(contrast_records, f, indent=2)
    with open(eval_json_path, "w", encoding="utf-8") as f:
        json.dump(evaluations_summary, f, indent=2)

    print(f"\nSaved secondary KB contrasts to {csv_path} and {json_path}")
    print(f"Saved secondary KB evaluation means to {eval_json_path}")


if __name__ == "__main__":
    main()
