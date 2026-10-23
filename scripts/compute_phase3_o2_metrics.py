"""Phase 3B: Optimization 2 Structure-Aware Chunking Offline Metric Evaluation.

Implements all Phase 3B Part 1 requirements:
1.3: Save ranked top-50 chunk list per query for E0' and E1a (B2 and B3, cti-ate and CTI-ATTACK).
     Compute all budget metrics OFFLINE from these lists (no re-retrieval).
1.4: Metrics at B in {500, 1000, 2000, 4000}, B* = 500:
     - Recall@B over technique IDs credited by chunks inside first B tokens (strict and sub_credits_parent)
     - MRR over chunk rank
     - Distinct technique count in context
     - Tokens used
     E1b: siblings inserted immediately after parent hit, then truncate at B.
     E1c: same number of random siblings (per-query seed).
1.5: Tests:
     (a) E1a and E0' top-10 lists differ on non-trivial fraction of queries.
     (b) Toy case where E1b differs from E1a under budget.
     (c) Recall@B computed strictly from budget-truncated list.
1.6: Print for 5 queries the context list (chunk IDs, field, tokens) of E0', E1a, E1b at B*.
1.7: Family P2 primary confirmatory contrasts (E1b vs E0' at B*, Recall sub_credits_parent, Holm, 10,000 bootstrap, seed 42)
     + exploratory contrast E1a vs E0'.
"""

import copy
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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


def generate_and_save_top50_chunks(
    out_path: Path,
    kb: STIXKnowledgeBase,
    datasets: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """Retrieve and cache top-50 ranked chunks per query for E0' and E1a on B2 and B3."""
    if out_path.is_file():
        print(f"Loading existing top-50 ranked chunk cache from {out_path}...")
        with open(out_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"\nGenerating top-50 ranked chunks for E0' and E1a...")
    r_base = HybridSTIXRetriever(
        stix_kb=kb,
        cache_dir=".cache/retriever_index_all",
        dense_k=60,
        bm25_k=60,
    )
    field_chunks = build_field_chunks_e1a(kb)
    r_field = HybridSTIXRetriever(
        stix_kb=kb,
        cache_dir=".cache/retriever_index_field_chunks",
        custom_documents=field_chunks,
        dense_k=60,
        bm25_k=60,
    )

    top50_data: Dict[str, Any] = {}

    for ds_name, df in datasets.items():
        top50_data[ds_name] = {"B2": {"E0_prime": [], "E1a": []}, "B3": {"E0_prime": [], "E1a": []}}
        baselines = ["B2"] if ds_name == "cti-taa" else ["B2", "B3"]

        for baseline in baselines:
            use_chunking = (baseline == "B3")
            print(f"Retrieving top-50 chunks: {ds_name} | Baseline {baseline} (query_chunking={use_chunking})...")

            for idx, row in df.iterrows():
                if int(idx) % 20 == 0:
                    print(f"  [{ds_name} {baseline}] Processing query {idx}/{len(df)}...")
                query = str(row["query"])
                gt = str(row.get("ground_truth", ""))

                # E0' baseline retrieval
                raw_e0 = r_base.retrieve(query, top_k=50, enable_query_chunking=use_chunking)
                e0_serialized = []
                for r_idx, d in enumerate(raw_e0, start=1):
                    e0_serialized.append({
                        "rank": r_idx,
                        "content": d.page_content,
                        "metadata": d.metadata,
                        "tokens": count_tokens(d.page_content),
                    })
                top50_data[ds_name][baseline]["E0_prime"].append({
                    "idx": int(idx),
                    "query": query,
                    "ground_truth": gt,
                    "top50": e0_serialized,
                })

                # E1a field-chunk retrieval
                raw_e1a = r_field.retrieve(query, top_k=50, enable_query_chunking=use_chunking)
                e1a_serialized = []
                for r_idx, d in enumerate(raw_e1a, start=1):
                    e1a_serialized.append({
                        "rank": r_idx,
                        "content": d.page_content,
                        "metadata": d.metadata,
                        "tokens": count_tokens(d.page_content),
                    })
                top50_data[ds_name][baseline]["E1a"].append({
                    "idx": int(idx),
                    "query": query,
                    "ground_truth": gt,
                    "top50": e1a_serialized,
                })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(top50_data, f, indent=2)
    print(f"Top-50 ranked chunk cache successfully saved to {out_path} ({out_path.stat().st_size} bytes)")
    return top50_data


def deserialize_docs(serialized_list: List[Dict[str, Any]]) -> List[Document]:
    """Convert serialized chunk dicts back to Document objects."""
    docs = []
    for item in serialized_list:
        docs.append(Document(page_content=item["content"], metadata=copy.deepcopy(item.get("metadata", {}))))
    return docs


def compute_context_budget_metrics_technique(
    final_docs: List[Document],
    ground_truth_str: str,
) -> Dict[str, Any]:
    """Compute Recall@B (strict & sub_credits_parent), MRR, distinct technique count, and tokens."""
    gt_set = parse_ground_truth_techniques(ground_truth_str)
    num_gt = len(gt_set)

    tokens_used = sum(count_tokens(d.page_content) for d in final_docs)

    # Collect techniques per chunk
    distinct_techs: Set[str] = set()
    retrieved_techs_by_rank: List[Set[str]] = []

    for doc in final_docs:
        doc_techs = extract_technique_ids_from_text(doc.page_content)
        m_id = doc.metadata.get("mitre_id", "")
        if m_id and m_id.startswith("T"):
            doc_techs.add(m_id)
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

    # 1. Strict Recall (Exact match)
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

    # 3. MRR over chunk rank (first chunk with relevant technique under sub_credits_parent)
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


def evaluate_offline_cells(
    top50_data: Dict[str, Any],
    sa_index: StructureAwareIndex,
    group_alias_map: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute all budget metrics offline across all cells and secondary budgets."""
    results: Dict[str, Any] = {}

    # 1. Primary cells at B* = 500
    # cti-ate and CTI-ATTACK on B2 & B3 for E0', E1a, E1b, E1c
    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        for baseline in ["B2", "B3"]:
            e0_records = top50_data[ds_name][baseline]["E0_prime"]
            e1a_records = top50_data[ds_name][baseline]["E1a"]

            for arm in ["E0_prime", "E1a", "E1b", "E1c"]:
                cell_key = f"{ds_name}_{baseline}_{arm}_B500"
                rec_stricts = []
                rec_subs = []
                mrrs = []
                distinct_counts = []
                tokens_list = []
                per_query = []

                for q_idx in range(len(e0_records)):
                    row_e0 = e0_records[q_idx]
                    row_e1a = e1a_records[q_idx]
                    gt = row_e0["ground_truth"]

                    if arm == "E0_prime":
                        raw_docs = deserialize_docs(row_e0["top50"])
                        final_docs = truncate_to_token_budget(raw_docs, budget_tokens=B_STAR)
                    elif arm == "E1a":
                        raw_docs = deserialize_docs(row_e1a["top50"])
                        final_docs = truncate_to_token_budget(raw_docs, budget_tokens=B_STAR)
                    elif arm == "E1b":
                        raw_docs = deserialize_docs(row_e1a["top50"])
                        final_docs = sa_index.expand_siblings_e1b(raw_docs, budget_tokens=B_STAR)
                    elif arm == "E1c":
                        raw_docs = deserialize_docs(row_e1a["top50"])
                        q_seed = get_per_query_seed(42, ds_name, q_idx)
                        final_docs = sa_index.expand_random_siblings_e1c(
                            raw_docs, budget_tokens=B_STAR, random_seed=q_seed
                        )
                    else:
                        raise ValueError(arm)

                    m = compute_context_budget_metrics_technique(final_docs, gt)
                    rec_stricts.append(m["Recall_strict"])
                    rec_subs.append(m["Recall_sub_credits_parent"])
                    mrrs.append(m["MRR"])
                    distinct_counts.append(m["distinct_techniques"])
                    tokens_list.append(m["tokens_used"])
                    per_query.append({
                        "idx": q_idx,
                        "Recall_strict": m["Recall_strict"],
                        "Recall_sub_credits_parent": m["Recall_sub_credits_parent"],
                        "MRR": m["MRR"],
                        "distinct_techniques": m["distinct_techniques"],
                        "tokens_used": m["tokens_used"],
                        "num_docs": m["num_docs"],
                    })

                results[cell_key] = {
                    "dataset": ds_name,
                    "baseline": baseline,
                    "arm": arm,
                    "budget": B_STAR,
                    "num_queries": len(per_query),
                    "mean_Recall_strict": round(float(np.mean(rec_stricts)), 4),
                    "mean_Recall_sub_credits_parent": round(float(np.mean(rec_subs)), 4),
                    "mean_MRR": round(float(np.mean(mrrs)), 4),
                    "mean_distinct_techniques": round(float(np.mean(distinct_counts)), 2),
                    "mean_tokens_used": round(float(np.mean(tokens_list)), 1),
                    "per_query_Recall_strict": rec_stricts,
                    "per_query_Recall_sub_credits_parent": rec_subs,
                    "per_query_MRR": mrrs,
                    "per_query": per_query,
                }

    # 2. Secondary budgets: cti-ate B2 E1b across B in {1000, 2000, 4000}
    for b in [1000, 2000, 4000]:
        cell_key = f"cti-ate_B2_E1b_B{b}"
        e1a_records = top50_data["cti-ate"]["B2"]["E1a"]
        rec_stricts, rec_subs, mrrs, distinct_counts, tokens_list, per_query = [], [], [], [], [], []

        for q_idx, row_e1a in enumerate(e1a_records):
            gt = row_e1a["ground_truth"]
            raw_docs = deserialize_docs(row_e1a["top50"])
            final_docs = sa_index.expand_siblings_e1b(raw_docs, budget_tokens=b)

            m = compute_context_budget_metrics_technique(final_docs, gt)
            rec_stricts.append(m["Recall_strict"])
            rec_subs.append(m["Recall_sub_credits_parent"])
            mrrs.append(m["MRR"])
            distinct_counts.append(m["distinct_techniques"])
            tokens_list.append(m["tokens_used"])
            per_query.append({"idx": q_idx, **m})

        results[cell_key] = {
            "dataset": "cti-ate",
            "baseline": "B2",
            "arm": "E1b",
            "budget": b,
            "num_queries": len(per_query),
            "mean_Recall_strict": round(float(np.mean(rec_stricts)), 4),
            "mean_Recall_sub_credits_parent": round(float(np.mean(rec_subs)), 4),
            "mean_MRR": round(float(np.mean(mrrs)), 4),
            "mean_distinct_techniques": round(float(np.mean(distinct_counts)), 2),
            "mean_tokens_used": round(float(np.mean(tokens_list)), 1),
            "per_query_Recall_strict": rec_stricts,
            "per_query_Recall_sub_credits_parent": rec_subs,
            "per_query_MRR": mrrs,
        }

    # 3. No-Regression Guard: cti-taa B2 at B* = 500
    if "cti-taa" in top50_data:
        e0_taa = top50_data["cti-taa"]["B2"]["E0_prime"]
        e1a_taa = top50_data["cti-taa"]["B2"]["E1a"]

        for arm in ["E0_prime", "E1b"]:
            cell_key = f"cti-taa_B2_{arm}_B500"
            recalls, mrrs, per_query = [], [], []

            for q_idx in range(len(e0_taa)):
                row_e0 = e0_taa[q_idx]
                row_e1a = e1a_taa[q_idx]
                gt = row_e0["ground_truth"]

                if arm == "E0_prime":
                    raw_docs = deserialize_docs(row_e0["top50"])
                    final_docs = truncate_to_token_budget(raw_docs, budget_tokens=B_STAR)
                else:
                    raw_docs = deserialize_docs(row_e1a["top50"])
                    final_docs = sa_index.expand_siblings_e1b(raw_docs, budget_tokens=B_STAR)

                m = compute_retrieval_metrics_taa_alias_aware(
                    final_docs, gt, group_alias_map=group_alias_map, k_values=[len(final_docs)]
                )
                rec = m.get(f"Recall@{len(final_docs)}", 0.0)
                mrr = m.get("MRR", 0.0)
                recalls.append(rec)
                mrrs.append(mrr)
                per_query.append({"idx": q_idx, "Recall": rec, "MRR": mrr})

            results[cell_key] = {
                "dataset": "cti-taa",
                "baseline": "B2",
                "arm": arm,
                "budget": B_STAR,
                "num_queries": len(per_query),
                "mean_Recall": round(float(np.mean(recalls)), 4),
                "mean_MRR": round(float(np.mean(mrrs)), 4),
                "per_query_Recall": recalls,
                "per_query_MRR": mrrs,
            }

        delta_taa = results["cti-taa_B2_E1b_B500"]["mean_Recall"] - results["cti-taa_B2_E0_prime_B500"]["mean_Recall"]
        results["cti-taa_no_regression_guard"] = {
            "E0_prime_Recall": results["cti-taa_B2_E0_prime_B500"]["mean_Recall"],
            "E1b_Recall": results["cti-taa_B2_E1b_B500"]["mean_Recall"],
            "delta_Recall": round(delta_taa, 4),
            "threshold": -0.05,
            "pass": bool(delta_taa >= -0.05),
        }

    return results


def run_item_1_5_tests(
    top50_data: Dict[str, Any],
    sa_index: StructureAwareIndex,
) -> Dict[str, Any]:
    """Execute the 3 required unit tests: (a), (b), (c)."""
    print("\n" + "=" * 60)
    print("RUNNING ITEM 1.5 TESTS")
    print("=" * 60)

    # Test (a): E1a and E0' top-10 lists must differ on a non-trivial fraction of queries
    e0_ate = top50_data["cti-ate"]["B2"]["E0_prime"]
    e1a_ate = top50_data["cti-ate"]["B2"]["E1a"]
    diff_count = 0
    total_q = len(e0_ate)

    for i in range(total_q):
        e0_top10 = [d["content"] for d in e0_ate[i]["top50"][:10]]
        e1a_top10 = [d["content"] for d in e1a_ate[i]["top50"][:10]]
        if e0_top10 != e1a_top10:
            diff_count += 1

    diff_fraction = diff_count / total_q
    print(f"Test (a): Top-10 difference fraction between E1a and E0' = {diff_fraction:.4f} ({diff_count}/{total_q})")
    assert diff_fraction >= 0.80, f"Expected difference fraction >= 0.80, got {diff_fraction}"

    # Test (b): Toy case where E1b differs from E1a under budget
    # Construct toy seed and sibling chunks
    toy_seed = Document(
        page_content="Technique T9999 Identity: Description of toy attack pattern.",
        metadata={"technique_id": "T9999", "mitre_id": "T9999", "field": "identity_description"}
    )
    toy_sib = Document(
        page_content="Technique T9999 Procedure Examples: Known adversary uses toy attack pattern.",
        metadata={"technique_id": "T9999", "mitre_id": "T9999", "field": "procedure_examples"}
    )
    toy_seed2 = Document(
        page_content="Technique T8888 Identity: Description of unrelated technique.",
        metadata={"technique_id": "T8888", "mitre_id": "T8888", "field": "identity_description"}
    )

    toy_index = StructureAwareIndex([toy_seed, toy_sib, toy_seed2])
    # Under budget B=25 tokens:
    # E1a: [toy_seed, toy_seed2] truncated to 25 tokens
    toy_e1a = truncate_to_token_budget([toy_seed, toy_seed2], budget_tokens=25)
    # E1b: toy_sib inserted immediately after toy_seed, so [toy_seed, toy_sib, toy_seed2] truncated to 25
    toy_e1b = toy_index.expand_siblings_e1b([toy_seed, toy_seed2], budget_tokens=25)

    e1a_contents = [d.page_content for d in toy_e1a]
    e1b_contents = [d.page_content for d in toy_e1b]
    print(f"Test (b): Toy case E1a contents: {len(e1a_contents)} docs | E1b contents: {len(e1b_contents)} docs")
    print(f"          E1a contains T8888: {any('T8888' in c for c in e1a_contents)}")
    print(f"          E1b contains T9999 sibling: {any('Procedure Examples' in c for c in e1b_contents)}")
    assert e1a_contents != e1b_contents, "Toy test failed: E1b and E1a must differ under budget"
    assert any("Procedure Examples" in c for c in e1b_contents), "Toy test failed: sibling not inserted"

    # Test (c): Recall@B is computed strictly from budget-truncated list
    # Construct toy docs where relevant technique appears at rank 3, beyond budget B=15 tokens
    doc_irrel1 = Document(page_content="Word " * 10, metadata={"mitre_id": "T1111"}) # 10 tokens
    doc_irrel2 = Document(page_content="Word " * 10, metadata={"mitre_id": "T2222"}) # 10 tokens
    doc_rel = Document(page_content="Technique T3333 is executed.", metadata={"mitre_id": "T3333"}) # relevant

    gt_toy = "T3333"
    # Full list has recall 1.0
    full_metrics = compute_context_budget_metrics_technique([doc_irrel1, doc_irrel2, doc_rel], gt_toy)
    # Budget-truncated list (B=15 tokens) only keeps doc_irrel1 and part of doc_irrel2; doc_rel is dropped
    trunc_docs = truncate_to_token_budget([doc_irrel1, doc_irrel2, doc_rel], budget_tokens=15)
    trunc_metrics = compute_context_budget_metrics_technique(trunc_docs, gt_toy)

    print(f"Test (c): Full list recall = {full_metrics['Recall_strict']} | Budget-truncated recall = {trunc_metrics['Recall_strict']}")
    assert full_metrics["Recall_strict"] == 1.0, "Full list should find T3333"
    assert trunc_metrics["Recall_strict"] == 0.0, "Budget-truncated list must NOT get credit for dropped chunk"

    print("All 3 Item 1.5 tests PASSED successfully!\n")
    return {
        "test_a_e1a_vs_e0_diff_fraction": diff_fraction,
        "test_b_toy_sibling_insertion_passed": True,
        "test_c_budget_truncation_enforcement_passed": True,
    }


def print_item_1_6_context_cases(
    top50_data: Dict[str, Any],
    sa_index: StructureAwareIndex,
    num_cases: int = 5,
) -> List[Dict[str, Any]]:
    """Print context lists (chunk IDs, field, tokens) for 5 queries of E0', E1a, E1b at B*."""
    print("=" * 80)
    print(f"ITEM 1.6: CONTEXT LIST FOR {num_cases} QUERIES AT B* = {B_STAR}")
    print("=" * 80)

    e0_records = top50_data["cti-ate"]["B2"]["E0_prime"][:num_cases]
    e1a_records = top50_data["cti-ate"]["B2"]["E1a"][:num_cases]
    cases_dump = []

    for idx in range(num_cases):
        q_row = e0_records[idx]
        query_text = q_row["query"]
        gt = q_row["ground_truth"]

        raw_e0 = deserialize_docs(q_row["top50"])
        raw_e1a = deserialize_docs(e1a_records[idx]["top50"])

        docs_e0 = truncate_to_token_budget(raw_e0, budget_tokens=B_STAR)
        docs_e1a = truncate_to_token_budget(raw_e1a, budget_tokens=B_STAR)
        docs_e1b = sa_index.expand_siblings_e1b(raw_e1a, budget_tokens=B_STAR)

        print(f"\n--- Query {idx}: {query_text[:90]}... ---")
        print(f"Ground Truth: {gt}")

        def summarize_context(docs: List[Document], label: str):
            print(f"  [{label}] Total Docs: {len(docs)}, Total Tokens: {sum(count_tokens(d.page_content) for d in docs)}")
            summary_list = []
            cum_tok = 0
            for r, d in enumerate(docs, start=1):
                toks = count_tokens(d.page_content)
                cum_tok += toks
                m_id = d.metadata.get("mitre_id", d.metadata.get("technique_id", "N/A"))
                field = d.metadata.get("field", "baseline_split")
                name = d.metadata.get("name", "Unknown")[:30]
                summary_list.append({
                    "rank": r,
                    "mitre_id": m_id,
                    "field": field,
                    "tokens": toks,
                    "cum_tokens": cum_tok,
                    "name": name,
                })
                print(f"    {r}. ID: {m_id:<10} | Field: {field:<22} | Tokens: {toks:<3} (Cum: {cum_tok:<3}) | {name}")
            return summary_list

        s_e0 = summarize_context(docs_e0, "E0' (Baseline Splitter)")
        s_e1a = summarize_context(docs_e1a, "E1a (Field Chunks)")
        s_e1b = summarize_context(docs_e1b, "E1b (Immediate Sibling Exp.)")

        cases_dump.append({
            "query_idx": idx,
            "query_snippet": query_text[:120],
            "ground_truth": gt,
            "E0_prime": s_e0,
            "E1a": s_e1a,
            "E1b": s_e1b,
        })

    return cases_dump


def compute_family_p2_contrasts(offline_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute Family P2 primary confirmatory contrasts and exploratory E1a vs E0' contrasts."""
    print("\n" + "=" * 80)
    print("FAMILY P2: STRUCTURE-AWARE TECHNIQUE EXTRACTION HYPOTHESIS TESTING")
    print("=" * 80)

    # 4 Pre-registered Primary Confirmatory Contrasts: E1b vs E0' at B* = 500, Recall sub_credits_parent
    primary_contrasts = [
        {
            "id": "H1_cti-ate_B2",
            "dataset": "cti-ate",
            "baseline": "B2",
            "cell_treatment": "cti-ate_B2_E1b_B500",
            "cell_control": "cti-ate_B2_E0_prime_B500",
        },
        {
            "id": "H2_cti-ate_B3",
            "dataset": "cti-ate",
            "baseline": "B3",
            "cell_treatment": "cti-ate_B3_E1b_B500",
            "cell_control": "cti-ate_B3_E0_prime_B500",
        },
        {
            "id": "H3_CTI-ATTACK_B2",
            "dataset": "CTI-ATTACK",
            "baseline": "B2",
            "cell_treatment": "CTI-ATTACK_B2_E1b_B500",
            "cell_control": "CTI-ATTACK_B2_E0_prime_B500",
        },
        {
            "id": "H4_CTI-ATTACK_B3",
            "dataset": "CTI-ATTACK",
            "baseline": "B3",
            "cell_treatment": "CTI-ATTACK_B3_E1b_B500",
            "cell_control": "CTI-ATTACK_B3_E0_prime_B500",
        },
    ]

    contrast_records = []
    for c in primary_contrasts:
        t_res = offline_results[c["cell_treatment"]]
        c_res = offline_results[c["cell_control"]]

        arr_t_rec = np.array(t_res["per_query_Recall_sub_credits_parent"])
        arr_c_rec = np.array(c_res["per_query_Recall_sub_credits_parent"])
        ci_rec = compute_paired_bootstrap_ci(arr_c_rec, arr_t_rec, n_resamples=10000, seed=42)

        arr_t_mrr = np.array(t_res["per_query_MRR"])
        arr_c_mrr = np.array(c_res["per_query_MRR"])
        ci_mrr = compute_paired_bootstrap_ci(arr_c_mrr, arr_t_mrr, n_resamples=10000, seed=42)

        delta_rec = float(t_res["mean_Recall_sub_credits_parent"] - c_res["mean_Recall_sub_credits_parent"])
        delta_mrr = float(t_res["mean_MRR"] - c_res["mean_MRR"])

        contrast_records.append({
            "hypothesis_id": c["id"],
            "type": "primary_confirmatory",
            "dataset": c["dataset"],
            "baseline": c["baseline"],
            "treatment": "E1b",
            "control": "E0_prime",
            "metric": "Recall_sub_credits_parent",
            "treatment_mean": t_res["mean_Recall_sub_credits_parent"],
            "control_mean": c_res["mean_Recall_sub_credits_parent"],
            "delta_recall": round(delta_rec, 4),
            "ci_recall": [ci_rec["ci_lower"], ci_rec["ci_upper"]],
            "raw_p_value": ci_rec["p_value"],
            "treatment_mrr": t_res["mean_MRR"],
            "control_mrr": c_res["mean_MRR"],
            "delta_mrr": round(delta_mrr, 4),
            "ci_mrr": [ci_mrr["ci_lower"], ci_mrr["ci_upper"]],
            "p_value_mrr": ci_mrr["p_value"],
        })

    # Holm-Bonferroni step-down correction over the 4 primary confirmatory tests
    contrast_records.sort(key=lambda x: x["raw_p_value"])
    m = len(contrast_records)
    alpha = 0.05
    for rank, item in enumerate(contrast_records, start=1):
        crit = alpha / (m - rank + 1)
        item["holm_rank"] = rank
        item["holm_critical_value"] = round(crit, 5)
        item["significant_holm"] = bool(item["raw_p_value"] <= crit)

    # Exploratory Contrasts: E1a vs E0' across the same 4 configurations
    exploratory_contrasts = []
    for c in primary_contrasts:
        cell_e1a = c["cell_treatment"].replace("E1b", "E1a")
        cell_e0 = c["cell_control"]

        t_res = offline_results[cell_e1a]
        c_res = offline_results[cell_e0]

        arr_t_rec = np.array(t_res["per_query_Recall_sub_credits_parent"])
        arr_c_rec = np.array(c_res["per_query_Recall_sub_credits_parent"])
        ci_rec = compute_paired_bootstrap_ci(arr_c_rec, arr_t_rec, n_resamples=10000, seed=42)

        arr_t_mrr = np.array(t_res["per_query_MRR"])
        arr_c_mrr = np.array(c_res["per_query_MRR"])
        ci_mrr = compute_paired_bootstrap_ci(arr_c_mrr, arr_t_mrr, n_resamples=10000, seed=42)

        delta_rec = float(t_res["mean_Recall_sub_credits_parent"] - c_res["mean_Recall_sub_credits_parent"])
        delta_mrr = float(t_res["mean_MRR"] - c_res["mean_MRR"])

        exploratory_records = {
            "hypothesis_id": f"Exp_{c['id'].replace('H', 'E1a_vs_E0_')}",
            "type": "exploratory",
            "dataset": c["dataset"],
            "baseline": c["baseline"],
            "treatment": "E1a",
            "control": "E0_prime",
            "metric": "Recall_sub_credits_parent",
            "treatment_mean": t_res["mean_Recall_sub_credits_parent"],
            "control_mean": c_res["mean_Recall_sub_credits_parent"],
            "delta_recall": round(delta_rec, 4),
            "ci_recall": [ci_rec["ci_lower"], ci_rec["ci_upper"]],
            "raw_p_value": ci_rec["p_value"],
            "treatment_mrr": t_res["mean_MRR"],
            "control_mrr": c_res["mean_MRR"],
            "delta_mrr": round(delta_mrr, 4),
            "ci_mrr": [ci_mrr["ci_lower"], ci_mrr["ci_upper"]],
            "p_value_mrr": ci_mrr["p_value"],
        }
        exploratory_contrasts.append(exploratory_records)

    all_contrasts = contrast_records + exploratory_contrasts

    print(f"\n{'Hypothesis':<20} | {'Delta Rec':<10} | {'95% CI':<18} | {'p-val':<8} | {'Holm Crit':<10} | {'Sig':<6}")
    print("-" * 80)
    for c in all_contrasts:
        crit_str = f"{c['holm_critical_value']:.5f}" if "holm_critical_value" in c else "N/A"
        sig_str = str(c.get("significant_holm", "N/A"))
        print(f"{c['hypothesis_id']:<20} | {c['delta_recall']:<+10.4f} | [{c['ci_recall'][0]:+.4f}, {c['ci_recall'][1]:+.4f}] | {c['raw_p_value']:<8.4f} | {crit_str:<10} | {sig_str:<6}")

    return all_contrasts


def main():
    print("=" * 80)
    print("PHASE 3B: O2 STRUCTURE-AWARE CHUNKING BENCHMARK & OFFLINE EVALUATION")
    print(f"Hardware: {os.cpu_count()} CPU cores, Torch threads = {torch.get_num_threads()}")
    print("=" * 80)

    kb = load_stix_all_bundles()
    group_alias_map = kb.get_group_alias_map()
    field_chunks = build_field_chunks_e1a(kb)
    sa_index = StructureAwareIndex(field_chunks)

    ds_ate = load_benchmark_dataset("cti-ate").df
    ds_att = load_benchmark_dataset("CTI-ATTACK").df
    ds_taa = load_benchmark_dataset("cti-taa").df

    datasets = {
        "cti-ate": ds_ate,
        "CTI-ATTACK": ds_att,
        "cti-taa": ds_taa,
    }

    # Step 1: Save / load top-50 ranked chunk lists (Item 1.3)
    top50_path = REPO_ROOT / "results" / "phase_3" / "top50_ranked_chunks.json"
    top50_data = generate_and_save_top50_chunks(top50_path, kb, datasets)

    # Step 2: Compute offline metrics for all cells (Item 1.4)
    print("\nComputing offline metrics across all cells and budgets...")
    offline_results = evaluate_offline_cells(top50_data, sa_index, group_alias_map=group_alias_map)

    # Step 3: Run the 3 Item 1.5 tests (Item 1.5)
    tests_summary = run_item_1_5_tests(top50_data, sa_index)

    # Step 4: Print 5 context cases (Item 1.6)
    cases_dump = print_item_1_6_context_cases(top50_data, sa_index, num_cases=5)

    # Step 5: Compute Family P2 hypothesis contrasts (Item 1.7)
    contrasts_summary = compute_family_p2_contrasts(offline_results)

    # Step 6: Save complete benchmark results
    out_file = REPO_ROOT / "results" / "phase_3" / "o2_benchmark_results.json"
    final_payload = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": {
            "os_cpu_count": os.cpu_count(),
            "torch_threads": torch.get_num_threads(),
        },
        "budget_B_star": B_STAR,
        "secondary_budgets": BUDGETS,
        "cells": offline_results,
        "tests_item_1_5": tests_summary,
        "sample_contexts_item_1_6": cases_dump,
        "family_p2_contrasts": contrasts_summary,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2)
    print(f"\nFinal Phase 3B O2 Benchmark Results saved to {out_file} ({out_file.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
