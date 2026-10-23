"""Phase 5 Addendum Part C: k=200 Candidate Pool Extension for E0' and E0'-TECH.

Addendum Requirement 1:
"Part C budget rule: report AUC only over budgets where the budget is binding for BOTH arms in the
 pair. Also add arms E0'-k200 and E0'-TECH-k200 (re-retrieve with a candidate pool of 200) so they can
 fill 2000 and 4000 tokens; show them next to the k=50 versions. Label cells."

Evaluates:
- Retrievers: E0_prime (E0') and E0_prime_tech (E0'-TECH).
- Candidate pool: k = 200 chunks (dense_k=200, bm25_k=200, rerank top 200).
- Datasets:
  - cti-ate: B2 (no chunking) and B3 (query chunking), 60 queries each.
  - CTI-ATTACK: B2 (no chunking), 229 queries.
- Preprocessing: HD (split_query body-only + cti-ate domain filtering).
- Budget truncation: B in {500, 1000, 2000, 4000} tokens.
- Binding audit: Tracks mean_tokens and mean_chunks to verify budget binding status.
"""

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from flashrank import RerankRequest
from langchain_core.documents import Document

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.chunking import count_tokens, truncate_to_token_budget
from src.retrieval_eval import (
    compute_paired_bootstrap_ci,
    extract_technique_ids_from_text,
    parse_ground_truth_techniques,
)
from src.retriever import HybridSTIXRetriever
from scripts.run_o2_clean_benchmark import (
    split_query,
    build_stix_domain_maps,
    doc_matches_domain,
    compute_context_budget_metrics_technique,
    deserialize_docs,
    BUDGETS,
)

def retrieve_k200(
    retriever: HybridSTIXRetriever,
    query: str,
    top_k: int = 200,
    target_domain: Optional[str] = None,
    enable_chunking: bool = False,
    stix_id_to_domains: Optional[Dict] = None,
    mitre_id_to_domains: Optional[Dict] = None,
) -> List[Document]:
    """Retrieve top_k=200 documents with candidate pool of 200 from dense and BM25."""
    if not enable_chunking:
        windows = [query]
    else:
        windows = retriever._split_query_into_windows(query, max_words=150, overlap=30)

    all_candidate_docs: Dict[str, Document] = {}

    fetch_k = 200
    for win in windows:
        try:
            dense_docs = retriever.vector_store.similarity_search(win, k=fetch_k)
        except Exception:
            dense_docs = retriever.dense_retriever.invoke(win)

        bm25_k_orig = retriever.bm25_retriever.k
        retriever.bm25_retriever.k = fetch_k
        bm25_docs = retriever.bm25_retriever.invoke(win)
        retriever.bm25_retriever.k = bm25_k_orig

        pool = dense_docs + bm25_docs
        for d in pool:
            if target_domain and stix_id_to_domains and mitre_id_to_domains:
                if not doc_matches_domain(d, target_domain, stix_id_to_domains, mitre_id_to_domains):
                    continue
            content = d.page_content if hasattr(d, "page_content") else str(d)
            if content not in all_candidate_docs:
                all_candidate_docs[content] = d

    if not all_candidate_docs:
        return retriever.retrieve(query, top_k=top_k, enable_query_chunking=enable_chunking)

    passages = [
        {"id": idx, "text": doc.page_content, "meta": doc.metadata}
        for idx, doc in enumerate(all_candidate_docs.values())
    ]

    all_reranked = []
    batch_size = 20
    rerank_query = windows[0]
    for i in range(0, len(passages), batch_size):
        batch = passages[i : i + batch_size]
        rerank_req = RerankRequest(query=rerank_query, passages=batch)
        all_reranked.extend(retriever.ranker.rerank(rerank_req))

    all_reranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    final_docs: List[Document] = []
    for r in all_reranked[:top_k]:
        final_docs.append(Document(page_content=r["text"], metadata=r.get("meta", {})))
    return final_docs


def run_k200_extension():
    print("=" * 80)
    print("PHASE 5 ADDENDUM: k=200 CANDIDATE POOL EXTENSION (E0'-k200, E0'-TECH-k200)")
    print("=" * 80)

    stix_kb = load_stix_all_bundles()
    stix_id_to_domains, mitre_id_to_domains = build_stix_domain_maps(stix_kb)

    out_dir = REPO_ROOT / "results" / "phase_5"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\nInitializing retrievers for E0_prime and E0_prime_tech...", flush=True)
    retrievers = {
        "E0_prime_tech_k200": HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_e0_tech"),
        "E0_prime_k200": HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all"),
    }
    print("Retrievers initialized.", flush=True)

    cache_path = out_dir / "top200_hd_chunks.json"
    cache_data: Dict[str, Any] = {}
    if cache_path.exists():
        print(f"Loading existing top200 cache from {cache_path}...", flush=True)
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

    eval_cells = [
        ("cti-ate", "B2", False),
        ("cti-ate", "B3", True),
        ("CTI-ATTACK", "B2", False),
    ]
    arms = ["E0_prime_tech_k200", "E0_prime_k200"]

    for ds_name, baseline, enable_chunking in eval_cells:
        cache_data.setdefault(ds_name, {})
        cache_data[ds_name].setdefault(baseline, {})

        df = load_benchmark_dataset(ds_name).df
        print(f"\nEvaluating k=200 for {ds_name} | {baseline} ({len(df)} queries)...", flush=True)

        for arm in arms:
            if arm in cache_data[ds_name][baseline] and len(cache_data[ds_name][baseline][arm]) == len(df):
                print(f"  Skipping {arm} (already in cache, {len(df)} queries).", flush=True)
                continue

            r = retrievers[arm]
            print(f"  Retrieving {arm} (k=200) under HD preprocessing...", flush=True)
            cell_results = []
            t0 = time.time()

            for idx, row in df.iterrows():
                q_raw = str(row["query"])
                gt = str(row["ground_truth"])
                instr, body, marker = split_query(q_raw)

                target_domain = None
                if ds_name == "cti-ate":
                    if "MITRE Enterprise" in instr:
                        target_domain = "enterprise-attack"
                    elif "MITRE Mobile" in instr:
                        target_domain = "mobile-attack"

                docs = retrieve_k200(
                    retriever=r,
                    query=body,
                    top_k=200,
                    target_domain=target_domain,
                    enable_chunking=enable_chunking,
                    stix_id_to_domains=stix_id_to_domains,
                    mitre_id_to_domains=mitre_id_to_domains,
                )

                cell_results.append({
                    "idx": int(idx),
                    "query_id": str(row["query_id"]),
                    "ground_truth": gt,
                    "target_domain": target_domain,
                    "top200": [
                        {"page_content": d.page_content, "metadata": d.metadata}
                        for d in docs
                    ],
                })

                if (idx + 1) % 25 == 0 or idx == len(df) - 1:
                    print(f"    [{ds_name} {baseline} {arm}] {idx + 1}/{len(df)} queries ({time.time() - t0:.1f}s)...", flush=True)

            cache_data[ds_name][baseline][arm] = cell_results
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

    # Evaluate budget truncation for k=200 arms
    print("\nEvaluating budget truncation across B in {500, 1000, 2000, 4000} for k=200...", flush=True)
    k200_results = defaultdict(lambda: defaultdict(dict))

    for ds_name, baseline, _ in eval_cells:
        for arm in arms:
            records = cache_data[ds_name][baseline][arm]
            arm_budgets = {}

            for b in BUDGETS:
                per_query_b = []
                for q_item in records:
                    idx = q_item["idx"]
                    gt = q_item["ground_truth"]
                    raw_docs = deserialize_docs(q_item["top200"])

                    final_docs = truncate_to_token_budget(raw_docs, budget_tokens=b)
                    m = compute_context_budget_metrics_technique(final_docs, gt, credit_rule="sub_credit")

                    per_query_b.append({
                        "idx": idx,
                        "Recall_sub": float(m["Recall_sub_credits_parent"]),
                        "Recall_strict": float(m["Recall_strict"]),
                        "MRR": float(m["MRR"]),
                        "tokens_used": float(m["tokens_used"]),
                        "num_docs": float(m["num_docs"]),
                    })

                df_b = pd.DataFrame(per_query_b)
                mean_tokens = float(df_b["tokens_used"].mean())
                mean_chunks = float(df_b["num_docs"].mean())
                is_binding = bool(mean_chunks < 195.0 or mean_tokens >= b * 0.95)

                arm_budgets[str(b)] = {
                    "Recall_sub": round(float(df_b["Recall_sub"].mean()), 4),
                    "Recall_strict": round(float(df_b["Recall_strict"].mean()), 4),
                    "MRR": round(float(df_b["MRR"].mean()), 4),
                    "tokens_used": round(mean_tokens, 1),
                    "mean_chunks": round(mean_chunks, 1),
                    "is_binding": is_binding,
                    "binding_status": "Binding" if is_binding else f"Non-binding ({mean_tokens:.1f} < {b} tok)",
                }

            k200_results[ds_name][baseline][arm] = arm_budgets

    out_json = out_dir / "o2_k200_scaling_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(k200_results, f, indent=2)
    print(f"\nSaved k=200 scaling results to {out_json}")

    # Print comparative scaling table
    print("\n" + "=" * 80)
    print("k=200 SCALING SUMMARY")
    print("=" * 80)
    for ds_name, baseline, _ in eval_cells:
        print(f"\n--- {ds_name} | {baseline} ---")
        print(f"{'Arm':<22} {'B=500':<12} {'B=1000':<12} {'B=2000':<15} {'B=4000':<15}")
        print("-" * 75)
        for arm in arms:
            d = k200_results[ds_name][baseline][arm]
            r500 = f"{d['500']['Recall_sub']:.4f} [B]" if d['500']['is_binding'] else f"{d['500']['Recall_sub']:.4f} [C]"
            r1000 = f"{d['1000']['Recall_sub']:.4f} [B]" if d['1000']['is_binding'] else f"{d['1000']['Recall_sub']:.4f} [C]"
            r2000 = f"{d['2000']['Recall_sub']:.4f} [B]" if d['2000']['is_binding'] else f"{d['2000']['Recall_sub']:.4f} [C]"
            r4000 = f"{d['4000']['Recall_sub']:.4f} [B]" if d['4000']['is_binding'] else f"{d['4000']['Recall_sub']:.4f} [C]"
            print(f"{arm:<22} {r500:<12} {r1000:<12} {r2000:<15} {r4000:<15}")

if __name__ == "__main__":
    run_k200_extension()
