"""Phase 3C: Controls and Corrected Arms Offline Evaluation.

Implements all Part 1 requirements:
1.1: Index composition analysis (E0' vs E1a vs E0'-TECH vs E1-MIXED).
1.2: Technique credit under BOTH rules (Primary: regex+metadata, Secondary: metadata-only).
1.3: New arm E0'-TECH: original splitter on technique objects only (same coverage as E1a).
1.4: New arm E1-MIXED: technique objects field-chunked + other active objects with original splitter.
     E1b-MIXED = E1-MIXED + sibling insertion after parent (technique chunks only).
     E1c-MIXED = random-sibling control (per-query seed).
1.5: Offline evaluation at B in {500, 1000, 2000, 4000} under BOTH credit rules:
     Recall (strict & sub_credit), MRR, distinct techniques, tokens used.
1.6: Pre-registered Family P2' confirmatory tests + exploratory contrasts + Holm correction.
"""

import copy
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Enforce offline mode and thread capping
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

import torch
torch.set_num_threads(4)

from langchain_core.documents import Document

from src.data_loader import (
    load_stix_all_bundles,
    load_benchmark_dataset,
    STIXKnowledgeBase,
)
from src.retriever import HybridSTIXRetriever
from src.corpus import build_stix_raw_documents, split_documents_baseline
from src.chunking import (
    count_tokens,
    build_field_chunks_e1a,
    StructureAwareIndex,
    truncate_to_token_budget,
    extract_parent_technique_id,
)
from src.retrieval_eval import (
    extract_technique_ids_from_text,
    parse_ground_truth_techniques,
    compute_retrieval_metrics_taa_alias_aware,
    compute_paired_bootstrap_ci,
)

B_STAR = 500
BUDGETS = [500, 1000, 2000, 4000]


def get_per_query_seed(base_seed: int, dataset: str, row_idx: int) -> int:
    """Deterministic per-query integer seed."""
    key = f"{base_seed}_{dataset}_{row_idx}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16) % (2**31 - 1)


def build_e0_tech_documents(kb: STIXKnowledgeBase) -> List[Document]:
    """Child documents from baseline splitter applied strictly to attack-pattern objects."""
    raw_docs = build_stix_raw_documents(kb)
    raw_tech = [d for d in raw_docs if d.metadata.get("type") == "attack-pattern"]
    _, child_docs = split_documents_baseline(raw_tech)
    return child_docs


def build_e1_mixed_documents(
    kb: STIXKnowledgeBase,
    e0_child_docs: List[Document],
    field_chunks: List[Document],
) -> List[Document]:
    """Combine technique field chunks with baseline splitter chunks for non-technique objects."""
    # 1. Technique objects chunked by field
    tech_field_chunks = [d for d in field_chunks if d.metadata.get("type") == "attack-pattern"]
    
    # 2. Non-technique objects chunked with baseline splitter
    non_tech_base_chunks = [d for d in e0_child_docs if d.metadata.get("type") != "attack-pattern"]
    
    mixed_docs = tech_field_chunks + non_tech_base_chunks
    return mixed_docs


def expand_siblings_e1b_mixed(
    seed_docs: List[Document],
    tech_sa_index: StructureAwareIndex,
    budget_tokens: int,
) -> List[Document]:
    """E1b-MIXED: Sibling insertion after parent hit for TECHNIQUE chunks only, then truncate at B."""
    expanded: List[Document] = []
    seen_contents: Set[str] = set()
    field_order = {
        "identity_description": 0,
        "procedure_examples": 1,
        "mitigations": 2,
        "detection": 3,
    }

    for seed in seed_docs:
        if seed.page_content not in seen_contents:
            expanded.append(seed)
            seen_contents.add(seed.page_content)

        # Only technique chunks expand siblings
        is_technique = (
            seed.metadata.get("type") == "attack-pattern"
            or str(seed.metadata.get("mitre_id", "")).startswith("T")
        )
        if is_technique:
            siblings = tech_sa_index.get_siblings(seed)
            sorted_sibs = sorted(
                siblings,
                key=lambda d: (
                    field_order.get(d.metadata.get("field", ""), 9),
                    d.metadata.get("mitre_id", ""),
                ),
            )
            for sib in sorted_sibs:
                if sib.page_content not in seen_contents:
                    expanded.append(sib)
                    seen_contents.add(sib.page_content)

    return truncate_to_token_budget(expanded, budget_tokens)


def expand_random_siblings_e1c_mixed(
    seed_docs: List[Document],
    tech_sa_index: StructureAwareIndex,
    budget_tokens: int,
    random_seed: int = 42,
) -> List[Document]:
    """E1c-MIXED: Random-sibling control inserting random unrelated technique siblings."""
    e1b_docs = expand_siblings_e1b_mixed(seed_docs, tech_sa_index, budget_tokens)
    seed_contents = {d.page_content for d in seed_docs}
    target_sibling_count = sum(1 for d in e1b_docs if d.page_content not in seed_contents)

    expanded: List[Document] = []
    seen_contents: Set[str] = set()
    seed_tech_ids = {
        d.metadata.get("technique_id") or extract_parent_technique_id(d.metadata.get("mitre_id", ""))
        for d in seed_docs
    }
    seed_tech_ids = {t for t in seed_tech_ids if t}

    unrelated_chunks = [
        d for d in tech_sa_index.field_chunks
        if d.metadata.get("technique_id") not in seed_tech_ids
    ]
    if not unrelated_chunks:
        unrelated_chunks = tech_sa_index.field_chunks

    rng = np.random.RandomState(random_seed)
    shuffled_indices = rng.permutation(len(unrelated_chunks))
    random_pool = [unrelated_chunks[i] for i in shuffled_indices]
    random_pool_idx = 0

    sibs_inserted = 0
    for seed in seed_docs:
        if seed.page_content not in seen_contents:
            expanded.append(seed)
            seen_contents.add(seed.page_content)

        is_technique = (
            seed.metadata.get("type") == "attack-pattern"
            or str(seed.metadata.get("mitre_id", "")).startswith("T")
        )
        if is_technique:
            while sibs_inserted < target_sibling_count and random_pool_idx < len(random_pool):
                cand = random_pool[random_pool_idx]
                random_pool_idx += 1
                if cand.page_content not in seen_contents:
                    expanded.append(cand)
                    seen_contents.add(cand.page_content)
                    sibs_inserted += 1
                    break

    while sibs_inserted < target_sibling_count and random_pool_idx < len(random_pool):
        cand = random_pool[random_pool_idx]
        random_pool_idx += 1
        if cand.page_content not in seen_contents:
            expanded.append(cand)
            seen_contents.add(cand.page_content)
            sibs_inserted += 1

    return truncate_to_token_budget(expanded, budget_tokens)


def deserialize_docs(serialized_list: List[Dict[str, Any]]) -> List[Document]:
    """Convert serialized chunk dicts back to Document objects."""
    docs = []
    for item in serialized_list:
        docs.append(Document(page_content=item["content"], metadata=copy.deepcopy(item.get("metadata", {}))))
    return docs


def compute_context_budget_metrics_technique(
    final_docs: List[Document],
    ground_truth_str: str,
    credit_rule: str = "text_and_metadata",
) -> Dict[str, Any]:
    """Compute Recall@B (strict & sub_credits_parent), MRR, distinct techniques, and tokens under credit_rule.
    
    credit_rule in {'text_and_metadata', 'metadata_only'}:
    - 'text_and_metadata': regex extraction on chunk text + metadata mitre_id (Primary rule)
    - 'metadata_only': strictly chunk metadata mitre_id or technique_id (Sensitivity rule)
    """
    gt_set = parse_ground_truth_techniques(ground_truth_str)
    num_gt = len(gt_set)
    tokens_used = sum(count_tokens(d.page_content) for d in final_docs)

    distinct_techs: Set[str] = set()
    retrieved_techs_by_rank: List[Set[str]] = []

    for doc in final_docs:
        doc_techs: Set[str] = set()
        m_id = str(doc.metadata.get("mitre_id", "")).strip()
        t_id = str(doc.metadata.get("technique_id", "")).strip()

        if credit_rule == "text_and_metadata":
            # Primary: regex on chunk text + metadata mitre_id if T*
            doc_techs = extract_technique_ids_from_text(doc.page_content)
            if m_id and m_id.startswith("T"):
                doc_techs.add(m_id)
        elif credit_rule == "metadata_only":
            # Secondary: strictly metadata
            if m_id and m_id.startswith("T"):
                doc_techs.add(m_id)
            elif t_id and t_id.startswith("T"):
                doc_techs.add(t_id)
        else:
            raise ValueError(f"Unknown credit_rule: {credit_rule}")

        distinct_techs.update(doc_techs)
        retrieved_techs_by_rank.append(doc_techs)

    if num_gt == 0:
        return {
            "Recall_strict": 0.0,
            "Recall_sub_credits_parent": 0.0,
            "MRR": 0.0,
            "distinct_techniques": len(distinct_techs),
            "tokens_used": tokens_used,
            "num_docs": len(final_docs),
        }

    # 1. Strict Recall
    covered_strict: Set[str] = set()
    for d_techs in retrieved_techs_by_rank:
        covered_strict.update(d_techs & gt_set)
    rec_strict = len(covered_strict) / num_gt

    # 2. Sub-technique credits parent Recall
    credited_techs: Set[str] = set()
    for d_techs in retrieved_techs_by_rank:
        for t in d_techs:
            credited_techs.add(t)
            if "." in t:
                credited_techs.add(t.split(".")[0])
    covered_sub = credited_techs & gt_set
    rec_sub = len(covered_sub) / num_gt

    # 3. MRR over chunk rank
    mrr = 0.0
    for r_idx, d_techs in enumerate(retrieved_techs_by_rank, start=1):
        c_techs = set(d_techs)
        for t in d_techs:
            if "." in t:
                c_techs.add(t.split(".")[0])
        if bool(c_techs & gt_set):
            mrr = 1.0 / r_idx
            break

    return {
        "Recall_strict": round(rec_strict, 4),
        "Recall_sub_credits_parent": round(rec_sub, 4),
        "MRR": round(mrr, 4),
        "distinct_techniques": len(distinct_techs),
        "tokens_used": tokens_used,
        "num_docs": len(final_docs),
    }


def main():
    print("=" * 80, flush=True)
    print("PHASE 3C: CONTROLS AND CORRECTED ARMS BENCHMARK", flush=True)
    print("=" * 80, flush=True)

    t0_all = time.time()

    # Load Knowledge Base and Datasets
    print("Loading STIX Knowledge Base...", flush=True)
    kb = load_stix_all_bundles()
    group_alias_map = kb.get_group_alias_map()

    print("Loading benchmark datasets...", flush=True)
    datasets = {
        "cti-ate": load_benchmark_dataset("cti-ate").df,
        "CTI-ATTACK": load_benchmark_dataset("CTI-ATTACK").df,
        "cti-taa": load_benchmark_dataset("cti-taa").df,
    }
    for name, df in datasets.items():
        print(f"  {name}: {len(df)} queries", flush=True)

    # ---------------------------------------------------------
    # PART 1.1: Index Composition Reporting
    # ---------------------------------------------------------
    print("\n--- Part 1.1: Index Composition Analysis ---", flush=True)
    # Load E0 child docs
    e0_cache_docs = REPO_ROOT / ".cache" / "retriever_index_all" / "child_docs.pkl"
    with open(e0_cache_docs, "rb") as f:
        import pickle
        e0_child_docs = pickle.load(f)

    # Load E1a field chunks
    e1a_cache_docs = REPO_ROOT / ".cache" / "retriever_index_field_chunks" / "child_docs.pkl"
    with open(e1a_cache_docs, "rb") as f:
        field_chunks = pickle.load(f)

    # Build E0'-TECH docs
    e0_tech_docs = build_e0_tech_documents(kb)

    # Build E1-MIXED docs
    e1_mixed_docs = build_e1_mixed_documents(kb, e0_child_docs, field_chunks)

    from collections import Counter
    e0_counts = Counter(d.metadata.get("type") for d in e0_child_docs)
    e1a_counts = Counter(d.metadata.get("type") for d in field_chunks)
    e0_tech_counts = Counter(d.metadata.get("type") for d in e0_tech_docs)
    e1_mixed_counts = Counter(d.metadata.get("type") for d in e1_mixed_docs)

    print(f"E0' Chunks (Total: {len(e0_child_docs)}): {dict(e0_counts)}", flush=True)
    print(f"E1a Field Chunks (Total: {len(field_chunks)}): {dict(e1a_counts)}", flush=True)
    print(f"E0'-TECH Chunks (Total: {len(e0_tech_docs)}): {dict(e0_tech_counts)}", flush=True)
    print(f"E1-MIXED Chunks (Total: {len(e1_mixed_docs)}): {dict(e1_mixed_counts)}", flush=True)

    # Setup StructureAwareIndex for technique field chunks
    tech_field_chunks = [d for d in field_chunks if d.metadata.get("type") == "attack-pattern"]
    tech_sa_index = StructureAwareIndex(tech_field_chunks)
    print(f"StructureAwareIndex initialized with {len(tech_field_chunks)} technique field chunks across {len(tech_sa_index.all_technique_ids)} parent technique IDs.", flush=True)

    # ---------------------------------------------------------
    # PART 1.3 & 1.4: Build Retrievers & Cache Top-50 Chunks
    # ---------------------------------------------------------
    cache_file = REPO_ROOT / "results" / "phase_3" / "top50_phase3c_chunks.json"
    top50_data: Dict[str, Any] = {}
    if cache_file.exists():
        print(f"\nLoading existing Phase 3C top-50 cache from {cache_file}...", flush=True)
        with open(cache_file, "r", encoding="utf-8") as f:
            top50_data = json.load(f)

    # Also load previous Phase 3B top50 for E0' and E1a
    prev_top50_path = REPO_ROOT / "results" / "phase_3" / "top50_ranked_chunks.json"
    prev_top50: Dict[str, Any] = {}
    if prev_top50_path.exists():
        with open(prev_top50_path, "r", encoding="utf-8") as f:
            prev_top50 = json.load(f)

    # Merge E0' and E1a into top50_data if missing
    for ds_name in ["cti-ate", "CTI-ATTACK", "cti-taa"]:
        top50_data.setdefault(ds_name, {})
        for baseline in ["B2", "B3"]:
            top50_data[ds_name].setdefault(baseline, {})
            if ds_name in prev_top50 and baseline in prev_top50[ds_name]:
                for arm_key in ["E0_prime", "E1a"]:
                    if arm_key in prev_top50[ds_name][baseline] and arm_key not in top50_data[ds_name][baseline]:
                        top50_data[ds_name][baseline][arm_key] = prev_top50[ds_name][baseline][arm_key]

    # Initialize retriever for E0'-TECH
    print("\nInitializing HybridSTIXRetriever for E0'-TECH (.cache/retriever_index_e0_tech)...", flush=True)
    r_e0_tech = HybridSTIXRetriever(
        stix_kb=kb,
        cache_dir=".cache/retriever_index_e0_tech",
        custom_documents=e0_tech_docs,
        dense_k=60,
        bm25_k=60,
    )

    # Initialize retriever for E1-MIXED
    print("\nInitializing HybridSTIXRetriever for E1-MIXED (.cache/retriever_index_e1_mixed)...", flush=True)
    r_e1_mixed = HybridSTIXRetriever(
        stix_kb=kb,
        cache_dir=".cache/retriever_index_e1_mixed",
        custom_documents=e1_mixed_docs,
        dense_k=60,
        bm25_k=60,
    )

    # Execute missing retrievals
    # 1. E0'-TECH on cti-ate (B2, B3) and CTI-ATTACK (B2, B3 separately)
    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        df = datasets[ds_name]
        for baseline in ["B2", "B3"]:
            use_chunking = (baseline == "B3")
            if "E0_prime_tech" in top50_data[ds_name][baseline] and len(top50_data[ds_name][baseline]["E0_prime_tech"]) == len(df):
                print(f"Skipping E0'-TECH on {ds_name} {baseline} (already in cache, {len(df)} queries).", flush=True)
                continue

            print(f"\nRetrieving E0'-TECH: {ds_name} | {baseline} ({len(df)} queries, use_chunking={use_chunking})...", flush=True)
            t_cell0 = time.time()
            records = []
            for idx, row in df.iterrows():
                if int(idx) > 0 and int(idx) % 25 == 0:
                    print(f"  [{ds_name} {baseline} E0'-TECH] query {idx}/{len(df)} ({time.time() - t_cell0:.1f}s)...", flush=True)
                query = str(row["query"])
                gt = str(row.get("ground_truth", ""))
                raw_docs = r_e0_tech.retrieve(query, top_k=50, enable_query_chunking=use_chunking)
                docs_ser = [
                    {
                        "rank": r_idx,
                        "content": d.page_content,
                        "metadata": d.metadata,
                        "tokens": count_tokens(d.page_content),
                    }
                    for r_idx, d in enumerate(raw_docs, start=1)
                ]
                records.append({
                    "idx": int(idx),
                    "query": query,
                    "ground_truth": gt,
                    "top50": docs_ser,
                })

            top50_data[ds_name][baseline]["E0_prime_tech"] = records
            # Save incrementally
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(top50_data, f)
            print(f"Completed {ds_name} {baseline} E0'-TECH in {time.time() - t_cell0:.1f}s. Saved to cache.", flush=True)

    # 2. E1-MIXED on cti-ate (B2, B3), CTI-ATTACK (B2, B3), cti-taa (B2, B3)
    for ds_name in ["cti-ate", "CTI-ATTACK", "cti-taa"]:
        df = datasets[ds_name]
        for baseline in ["B2", "B3"]:
            use_chunking = (baseline == "B3")
            if "E1_mixed" in top50_data[ds_name][baseline] and len(top50_data[ds_name][baseline]["E1_mixed"]) == len(df):
                print(f"Skipping E1-MIXED on {ds_name} {baseline} (already in cache, {len(df)} queries).", flush=True)
                continue

            print(f"\nRetrieving E1-MIXED: {ds_name} | {baseline} ({len(df)} queries, use_chunking={use_chunking})...", flush=True)
            t_cell0 = time.time()
            records = []
            for idx, row in df.iterrows():
                if int(idx) > 0 and int(idx) % 25 == 0:
                    print(f"  [{ds_name} {baseline} E1-MIXED] query {idx}/{len(df)} ({time.time() - t_cell0:.1f}s)...", flush=True)
                query = str(row["query"])
                gt = str(row.get("ground_truth", ""))
                raw_docs = r_e1_mixed.retrieve(query, top_k=50, enable_query_chunking=use_chunking)
                docs_ser = [
                    {
                        "rank": r_idx,
                        "content": d.page_content,
                        "metadata": d.metadata,
                        "tokens": count_tokens(d.page_content),
                    }
                    for r_idx, d in enumerate(raw_docs, start=1)
                ]
                records.append({
                    "idx": int(idx),
                    "query": query,
                    "ground_truth": gt,
                    "top50": docs_ser,
                })

            top50_data[ds_name][baseline]["E1_mixed"] = records
            # Save incrementally
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(top50_data, f)
            print(f"Completed {ds_name} {baseline} E1-MIXED in {time.time() - t_cell0:.1f}s. Saved to cache.", flush=True)

    # ---------------------------------------------------------
    # PART 1.5: Offline Metrics Evaluation Across All Arms & Budgets
    # ---------------------------------------------------------
    print("\n--- Part 1.5: Offline Metric Evaluation under Both Credit Rules ---", flush=True)
    all_arms = ["E0_prime", "E0_prime_tech", "E1a", "E1_mixed", "E1b_mixed", "E1c_mixed"]
    credit_rules = ["text_and_metadata", "metadata_only"]

    offline_results: Dict[str, Any] = {}

    for rule in credit_rules:
        offline_results[rule] = {}
        print(f"\n=======================================================", flush=True)
        print(f"EVALUATING CREDIT RULE: {rule.upper()}", flush=True)
        print(f"=======================================================", flush=True)

        for ds_name in ["cti-ate", "CTI-ATTACK", "cti-taa"]:
            offline_results[rule][ds_name] = {}
            for baseline in ["B2", "B3"]:
                offline_results[rule][ds_name][baseline] = {}
                print(f"\n--- {ds_name} | {baseline} [{rule}] ---", flush=True)

                for arm in all_arms:
                    # Skip tech-only on cti-taa
                    if ds_name == "cti-taa" and arm in ["E0_prime_tech", "E1a"]:
                        continue

                    offline_results[rule][ds_name][baseline][arm] = {}

                    for budget in BUDGETS:
                        if arm in ["E0_prime", "E0_prime_tech", "E1a", "E1_mixed"]:
                            source_arm = arm
                        else:
                            source_arm = "E1_mixed"

                        if source_arm not in top50_data[ds_name][baseline] or not top50_data[ds_name][baseline][source_arm]:
                            continue

                        records = top50_data[ds_name][baseline][source_arm]
                        if not records:
                            continue
                        per_query_metrics = []

                        for q_item in records:
                            row_idx = q_item["idx"]
                            raw_docs = deserialize_docs(q_item["top50"])
                            gt = q_item["ground_truth"]

                            # Apply arm transformation
                            if arm in ["E0_prime", "E0_prime_tech", "E1a", "E1_mixed"]:
                                final_docs = truncate_to_token_budget(raw_docs, budget_tokens=budget)
                            elif arm == "E1b_mixed":
                                final_docs = expand_siblings_e1b_mixed(raw_docs, tech_sa_index, budget_tokens=budget)
                            elif arm == "E1c_mixed":
                                q_seed = get_per_query_seed(42, ds_name, row_idx)
                                final_docs = expand_random_siblings_e1c_mixed(
                                    raw_docs, tech_sa_index, budget_tokens=budget, random_seed=q_seed
                                )
                            else:
                                raise ValueError(f"Unknown arm: {arm}")

                            if ds_name == "cti-taa":
                                m = compute_retrieval_metrics_taa_alias_aware(
                                    final_docs, gt, group_alias_map=group_alias_map, k_values=[1, 3, 5, 10]
                                )
                                per_query_metrics.append({
                                    "idx": row_idx,
                                    "Recall@10": m["Recall@10"],
                                    "MRR": m["MRR"],
                                    "tokens_used": sum(count_tokens(d.page_content) for d in final_docs),
                                    "num_docs": len(final_docs),
                                })
                            else:
                                m = compute_context_budget_metrics_technique(
                                    final_docs, gt, credit_rule=rule
                                )
                                per_query_metrics.append({
                                    "idx": row_idx,
                                    "Recall_strict": m["Recall_strict"],
                                    "Recall_sub_credits_parent": m["Recall_sub_credits_parent"],
                                    "MRR": m["MRR"],
                                    "distinct_techniques": m["distinct_techniques"],
                                    "tokens_used": m["tokens_used"],
                                    "num_docs": m["num_docs"],
                                })

                        # Aggregate cell means
                        if not per_query_metrics:
                            continue
                        df_m = pd.DataFrame(per_query_metrics)
                        if ds_name == "cti-taa":
                            cell_summary = {
                                "num_queries": len(df_m),
                                "Recall@10": round(float(df_m["Recall@10"].mean()), 4),
                                "MRR": round(float(df_m["MRR"].mean()), 4),
                                "tokens_used": round(float(df_m["tokens_used"].mean()), 1),
                                "num_docs": round(float(df_m["num_docs"].mean()), 2),
                            }
                        else:
                            cell_summary = {
                                "num_queries": len(df_m),
                                "Recall_strict": round(float(df_m["Recall_strict"].mean()), 4),
                                "Recall_sub_credits_parent": round(float(df_m["Recall_sub_credits_parent"].mean()), 4),
                                "MRR": round(float(df_m["MRR"].mean()), 4),
                                "distinct_techniques": round(float(df_m["distinct_techniques"].mean()), 2),
                                "tokens_used": round(float(df_m["tokens_used"].mean()), 1),
                                "num_docs": round(float(df_m["num_docs"].mean()), 2),
                            }

                        offline_results[rule][ds_name][baseline][arm][str(budget)] = {
                            "summary": cell_summary,
                            "per_query": per_query_metrics,
                        }

                        if budget == 500:
                            if ds_name == "cti-taa":
                                print(f"  {arm:14s} @ B={budget}: Recall@10 = {cell_summary['Recall@10']:.4f}, MRR = {cell_summary['MRR']:.4f}, tokens = {cell_summary['tokens_used']:.1f}", flush=True)
                            else:
                                print(f"  {arm:14s} @ B={budget}: Rec_sub = {cell_summary['Recall_sub_credits_parent']:.4f}, Rec_strict = {cell_summary['Recall_strict']:.4f}, MRR = {cell_summary['MRR']:.4f}, tokens = {cell_summary['tokens_used']:.1f}", flush=True)

    # ---------------------------------------------------------
    # PART 1.6: Pre-Registered Confirmatory Family P2' & Exploratory Tests
    # ---------------------------------------------------------
    print("\n--- Part 1.6: Hypothesis Testing (Family P2' & Exploratory) ---", flush=True)
    tests_summary: Dict[str, Any] = {}

    for rule in credit_rules:
        tests_summary[rule] = {"confirmatory_p2_prime": [], "exploratory": []}
        data_r = offline_results[rule]

        # 1. Family P2' Confirmatory Contrasts: E1b-MIXED vs E0' at B*=500, Recall_sub_credits_parent
        p2_tests = [
            ("P2'_01", "cti-ate", "B2", "E1b_mixed", "E0_prime", "cti-ate B2: E1b-MIXED vs E0'"),
            ("P2'_02", "cti-ate", "B3", "E1b_mixed", "E0_prime", "cti-ate B3: E1b-MIXED vs E0'"),
            ("P2'_03", "CTI-ATTACK", "B2", "E1b_mixed", "E0_prime", "CTI-ATTACK B2: E1b-MIXED vs E0'"),
            ("P2'_04", "CTI-ATTACK", "B3", "E1b_mixed", "E0_prime", "CTI-ATTACK B3: E1b-MIXED vs E0'"),
        ]

        # Check equality of B2 and B3 on CTI-ATTACK
        arr_t_b2 = np.array([q["Recall_sub_credits_parent"] for q in data_r["CTI-ATTACK"]["B2"]["E1b_mixed"]["500"]["per_query"]])
        arr_c_b2 = np.array([q["Recall_sub_credits_parent"] for q in data_r["CTI-ATTACK"]["B2"]["E0_prime"]["500"]["per_query"]])
        arr_t_b3 = np.array([q["Recall_sub_credits_parent"] for q in data_r["CTI-ATTACK"]["B3"]["E1b_mixed"]["500"]["per_query"]])
        arr_c_b3 = np.array([q["Recall_sub_credits_parent"] for q in data_r["CTI-ATTACK"]["B3"]["E0_prime"]["500"]["per_query"]])

        identical_cti_attack = (
            np.array_equal(arr_t_b2, arr_t_b3) and np.array_equal(arr_c_b2, arr_c_b3)
        )
        print(f"[{rule}] CTI-ATTACK B2 and B3 per-query identical: {identical_cti_attack}", flush=True)

        for test_id, ds, base, arm_t, arm_c, desc in p2_tests:
            q_t = data_r[ds][base][arm_t]["500"]["per_query"]
            q_c = data_r[ds][base][arm_c]["500"]["per_query"]
            arr_t = np.array([x["Recall_sub_credits_parent"] for x in q_t])
            arr_c = np.array([x["Recall_sub_credits_parent"] for x in q_c])

            ci = compute_paired_bootstrap_ci(arr_c, arr_t, n_resamples=10000, seed=42)
            tests_summary[rule]["confirmatory_p2_prime"].append({
                "test_id": test_id,
                "dataset": ds,
                "baseline": base,
                "contrast": f"{arm_t} vs {arm_c}",
                "description": desc,
                "metric": "Recall_sub_credits_parent",
                "treatment_mean": round(float(np.mean(arr_t)), 4),
                "control_mean": round(float(np.mean(arr_c)), 4),
                "delta": round(float(ci["mean_delta"]), 4),
                "ci_95": [round(ci["ci_lower"], 4), round(ci["ci_upper"], 4)],
                "raw_p_value": ci["p_value"],
                "identical_to_b2": (test_id == "P2'_04" and identical_cti_attack),
            })

        # Holm-Bonferroni correction over P2' confirmatory tests
        # If CTI-ATTACK B2 and B3 are identical, count as ONE test in Holm
        p2_list = tests_summary[rule]["confirmatory_p2_prime"]
        holm_candidates = [t for t in p2_list if not t.get("identical_to_b2", False)]
        holm_candidates.sort(key=lambda x: x["raw_p_value"])
        m_tests = len(holm_candidates)
        alpha = 0.05
        step_stopped = False
        for r_idx, item in enumerate(holm_candidates, start=1):
            crit = alpha / (m_tests - r_idx + 1)
            item["holm_rank"] = r_idx
            item["holm_critical_value"] = round(crit, 5)
            if not step_stopped and item["raw_p_value"] <= crit:
                item["significant_holm"] = True
            else:
                item["significant_holm"] = False
                step_stopped = True

        # Copy holm results to identical twin if applicable
        for item in p2_list:
            if item.get("identical_to_b2", False):
                b2_twin = next(x for x in p2_list if x["test_id"] == "P2'_03")
                item["holm_rank"] = b2_twin.get("holm_rank")
                item["holm_critical_value"] = b2_twin.get("holm_critical_value")
                item["significant_holm"] = b2_twin.get("significant_holm")

        # No-Regression Guard on cti-taa B2: E1b-MIXED vs E0' (Recall@10)
        taa_t = np.array([x["Recall@10"] for x in data_r["cti-taa"]["B2"]["E1b_mixed"]["500"]["per_query"]])
        taa_c = np.array([x["Recall@10"] for x in data_r["cti-taa"]["B2"]["E0_prime"]["500"]["per_query"]])
        ci_taa = compute_paired_bootstrap_ci(taa_c, taa_t, n_resamples=10000, seed=42)
        guard_passed = (ci_taa["mean_delta"] >= -0.05) and (ci_taa["ci_lower"] >= -0.05)
        tests_summary[rule]["no_regression_guard"] = {
            "dataset": "cti-taa",
            "baseline": "B2",
            "contrast": "E1b_mixed vs E0_prime",
            "metric": "Recall@10",
            "treatment_mean": round(float(np.mean(taa_t)), 4),
            "control_mean": round(float(np.mean(taa_c)), 4),
            "delta": round(float(ci_taa["mean_delta"]), 4),
            "ci_95": [round(ci_taa["ci_lower"], 4), round(ci_taa["ci_upper"], 4)],
            "raw_p_value": ci_taa["p_value"],
            "threshold": -0.05,
            "guard_passed": guard_passed,
        }

        # 2. Exploratory Contrasts
        # (a) E1a vs E0'-TECH on cti-ate (B2, B3) and CTI-ATTACK (B2, B3)
        # (b) E1b-MIXED vs E1-MIXED
        # (c) E1b-MIXED vs E1c-MIXED
        # (d) E1a vs E0'
        exp_specs = [
            ("EXP_01", "cti-ate", "B2", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (cti-ate B2)"),
            ("EXP_02", "cti-ate", "B3", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (cti-ate B3)"),
            ("EXP_03", "CTI-ATTACK", "B2", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (CTI-ATTACK B2)"),
            ("EXP_04", "CTI-ATTACK", "B3", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (CTI-ATTACK B3)"),
            ("EXP_05", "cti-ate", "B2", "E1b_mixed", "E1_mixed", "Sibling Expansion Effect: E1b-MIXED vs E1-MIXED (cti-ate B2)"),
            ("EXP_06", "cti-ate", "B2", "E1b_mixed", "E1c_mixed", "Sibling Specificity: E1b-MIXED vs E1c-MIXED (cti-ate B2)"),
            ("EXP_07", "cti-ate", "B2", "E1a", "E0_prime", "Field vs Baseline Splitter: E1a vs E0' (cti-ate B2)"),
            ("EXP_08", "CTI-ATTACK", "B2", "E1a", "E0_prime", "Field vs Baseline Splitter: E1a vs E0' (CTI-ATTACK B2)"),
        ]

        for test_id, ds, base, arm_t, arm_c, desc in exp_specs:
            q_t = data_r[ds][base][arm_t]["500"]["per_query"]
            q_c = data_r[ds][base][arm_c]["500"]["per_query"]
            arr_t = np.array([x["Recall_sub_credits_parent"] for x in q_t])
            arr_c = np.array([x["Recall_sub_credits_parent"] for x in q_c])
            ci = compute_paired_bootstrap_ci(arr_c, arr_t, n_resamples=10000, seed=42)
            tests_summary[rule]["exploratory"].append({
                "test_id": test_id,
                "dataset": ds,
                "baseline": base,
                "contrast": f"{arm_t} vs {arm_c}",
                "description": desc,
                "metric": "Recall_sub_credits_parent",
                "treatment_mean": round(float(np.mean(arr_t)), 4),
                "control_mean": round(float(np.mean(arr_c)), 4),
                "delta": round(float(ci["mean_delta"]), 4),
                "ci_95": [round(ci["ci_lower"], 4), round(ci["ci_upper"], 4)],
                "raw_p_value": ci["p_value"],
            })

    # Save final structured benchmark results
    final_output = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "budgets": BUDGETS,
            "b_star": B_STAR,
            "arms": all_arms,
            "credit_rules": credit_rules,
            "primary_credit_rule": "text_and_metadata",
            "index_composition": {
                "e0_prime": dict(e0_counts),
                "e1a": dict(e1a_counts),
                "e0_prime_tech": dict(e0_tech_counts),
                "e1_mixed": dict(e1_mixed_counts),
            },
        },
        "results": offline_results,
        "hypothesis_tests": tests_summary,
    }

    out_file = REPO_ROOT / "results" / "phase_3" / "o2_phase3c_benchmark_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    print(f"\n=======================================================", flush=True)
    print(f"PHASE 3C BENCHMARK COMPLETED IN {time.time() - t0_all:.1f}s", flush=True)
    print(f"Results saved to: {out_file} ({out_file.stat().st_size} bytes)", flush=True)
    print(f"=======================================================", flush=True)


if __name__ == "__main__":
    main()
