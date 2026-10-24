"""Phase 7: Optimization 2 Redesign Benchmark & Statistical Contrasts.

Evaluates redesigned structure-aware chunking variants:
- E1h:
  - Header prepending: "[<technique_id> <name> | <tactics>]"
  - 150-token sentence-boundary splitting with header repeated on every split chunk
  - Indexing the same four fields as E1a (identity_description, procedure_examples, mitigations, detection)
  - Evaluated on technique corpus (E1h) and mixed corpus (E1h-MIXED)
- E1h-div:
  - E1h with diversity-constrained packing: at most 2 chunks per technique ID kept in the packed context
- Candidate pool: k = 200 chunks (dense_k=200, bm25_k=200, rerank top 200 via FlashRank)
- Preprocessing: body-only queries (hygiene), domain routing for cti-ate
- Token budgets: B in {500, 1000, 2000, 4000} tokens

Contrasts (Family P7, Holm M=4):
- P7_01: E1h vs E0'-TECH-k200 on cti-ate (Mean Recall@B over B in {500, 1000}, sub-credit)
- P7_02: E1h-div vs E0'-TECH-k200 on cti-ate (Mean Recall@B over B in {500, 1000}, sub-credit)
- P7_03: E1h vs E0'-TECH-k200 on CTI-ATTACK (Mean Recall@B over B in {500, 1000}, sub-credit)
- P7_04: E1h-div vs E0'-TECH-k200 on CTI-ATTACK (Mean Recall@B over B in {500, 1000}, sub-credit)
- Paired bootstrap: 10,000 resamples, seed 42
- Multiplicity control: Holm-Bonferroni step-down (M=4, alpha=0.05)
"""

import copy
import json
import os
import pickle
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from flashrank import RerankRequest
from langchain_core.documents import Document
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.chunking import count_tokens, truncate_to_token_budget, extract_parent_technique_id
from src.retriever import HybridSTIXRetriever
from scripts.run_o2_clean_benchmark import (
    split_query,
    build_stix_domain_maps,
    doc_matches_domain,
    compute_context_budget_metrics_technique,
    deserialize_docs,
    BUDGETS,
)

BUDGETS_EVAL = [500, 1000, 2000, 4000]
PRIMARY_BUDGETS = [500, 1000]


def split_into_sentence_units(text: str) -> List[str]:
    """Split text into sentence-like segments respecting boundaries, newlines, and list items."""
    lines = text.split("\n")
    units = []
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        # Split sentence boundaries: . ! ? followed by whitespace and capital letter / number
        sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", line_s)
        for s in sents:
            s_strip = s.strip()
            if s_strip:
                units.append(s_strip)
    return units


def build_e1h_documents(field_docs: List[Document], max_tokens: int = 150) -> List[Document]:
    """Build E1h documents from E1a field chunks.
    
    1. Prepend header '[<technique_id> <name> | <tactics>]' to every chunk.
    2. Cap each chunk at 150 tokens (split at sentence boundaries; header repeated).
    """
    e1h_docs: List[Document] = []

    for d in field_docs:
        mitre_id = str(d.metadata.get("mitre_id", "")).strip()
        name = str(d.metadata.get("name", "")).strip()
        tactics = d.metadata.get("tactics", [])
        tactics_str = ", ".join(tactics) if tactics else "none"
        header = f"[{mitre_id} {name} | {tactics_str}]"
        header_tokens = count_tokens(header)
        available_body_tokens = max(10, max_tokens - header_tokens)

        units = split_into_sentence_units(d.page_content)

        current_units: List[str] = []
        current_tokens = 0
        sub_idx = 0

        for u in units:
            u_tokens = count_tokens(u)

            # If a single sentence unit exceeds available_body_tokens, split by word tokens
            if u_tokens > available_body_tokens:
                if current_units:
                    chunk_text = header + "\n" + " ".join(current_units)
                    meta = copy.deepcopy(d.metadata)
                    meta["sub_idx"] = sub_idx
                    meta["chunk_tokens"] = count_tokens(chunk_text)
                    e1h_docs.append(Document(page_content=chunk_text, metadata=meta))
                    sub_idx += 1
                    current_units = []
                    current_tokens = 0

                words = u.split()
                sub_start = 0
                while sub_start < len(words):
                    sub_words = words[sub_start : sub_start + available_body_tokens]
                    chunk_text = header + "\n" + " ".join(sub_words)
                    meta = copy.deepcopy(d.metadata)
                    meta["sub_idx"] = sub_idx
                    meta["chunk_tokens"] = count_tokens(chunk_text)
                    e1h_docs.append(Document(page_content=chunk_text, metadata=meta))
                    sub_idx += 1
                    sub_start += available_body_tokens
                continue

            if current_tokens + u_tokens <= available_body_tokens:
                current_units.append(u)
                current_tokens += u_tokens
            else:
                chunk_text = header + "\n" + " ".join(current_units)
                meta = copy.deepcopy(d.metadata)
                meta["sub_idx"] = sub_idx
                meta["chunk_tokens"] = count_tokens(chunk_text)
                e1h_docs.append(Document(page_content=chunk_text, metadata=meta))
                sub_idx += 1
                current_units = [u]
                current_tokens = u_tokens

        if current_units:
            chunk_text = header + "\n" + " ".join(current_units)
            meta = copy.deepcopy(d.metadata)
            meta["sub_idx"] = sub_idx
            meta["chunk_tokens"] = count_tokens(chunk_text)
            e1h_docs.append(Document(page_content=chunk_text, metadata=meta))

    return e1h_docs


def retrieve_k200_candidates(
    retriever: HybridSTIXRetriever,
    query: str,
    top_k: int = 200,
    target_domain: Optional[str] = None,
    stix_id_to_domains: Optional[Dict] = None,
    mitre_id_to_domains: Optional[Dict] = None,
) -> List[Document]:
    """Retrieve top_k=200 documents with candidate pool of 200 from dense and BM25."""
    fetch_k = 200
    try:
        dense_docs = retriever.vector_store.similarity_search(query, k=fetch_k)
    except Exception:
        dense_docs = retriever.dense_retriever.invoke(query)

    bm25_k_orig = retriever.bm25_retriever.k
    retriever.bm25_retriever.k = fetch_k
    bm25_docs = retriever.bm25_retriever.invoke(query)
    retriever.bm25_retriever.k = bm25_k_orig

    all_candidate_docs: Dict[str, Document] = {}
    pool = dense_docs + bm25_docs

    for d in pool:
        if target_domain and stix_id_to_domains and mitre_id_to_domains:
            if not doc_matches_domain(d, target_domain, stix_id_to_domains, mitre_id_to_domains):
                continue
        content = d.page_content if hasattr(d, "page_content") else str(d)
        if content not in all_candidate_docs:
            all_candidate_docs[content] = d

    if not all_candidate_docs:
        return retriever.retrieve(query, top_k=top_k, enable_query_chunking=False)

    passages = [
        {"id": idx, "text": doc.page_content, "meta": doc.metadata}
        for idx, doc in enumerate(all_candidate_docs.values())
    ]

    all_reranked = []
    batch_size = 20
    for i in range(0, len(passages), batch_size):
        batch = passages[i : i + batch_size]
        rerank_req = RerankRequest(query=query, passages=batch)
        all_reranked.extend(retriever.ranker.rerank(rerank_req))

    all_reranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    final_docs: List[Document] = []
    for r in all_reranked[:top_k]:
        final_docs.append(Document(page_content=r["text"], metadata=r.get("meta", {})))
    return final_docs


def filter_diversity_e1h(docs: List[Document], max_per_tech: int = 2) -> List[Document]:
    """Filter candidate documents to retain at most max_per_tech chunks per technique ID."""
    seen_counts: Dict[str, int] = defaultdict(int)
    diversified: List[Document] = []

    for d in docs:
        tech_id = d.metadata.get("technique_id") or extract_parent_technique_id(d.metadata.get("mitre_id", ""))
        if not tech_id:
            tech_id = d.metadata.get("stix_id", str(id(d)))
        if seen_counts[tech_id] < max_per_tech:
            diversified.append(d)
            seen_counts[tech_id] += 1

    return diversified


def compute_paired_bootstrap(
    diffs: np.ndarray,
    n_resamples: int = 10000,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
    """Paired bootstrap computing mean diff, 95% CI [lower, upper], and empirical p-value."""
    n = len(diffs)
    observed_mean = float(np.mean(diffs))
    rng = np.random.RandomState(seed)

    boot_indices = rng.randint(0, n, size=(n_resamples, n))
    boot_means = np.mean(diffs[boot_indices], axis=1)

    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))

    # Two-sided empirical p-value
    if observed_mean >= 0:
        p_val = 2.0 * float(np.mean(boot_means <= 0))
    else:
        p_val = 2.0 * float(np.mean(boot_means >= 0))
    p_val = min(1.0, max(1.0 / n_resamples, p_val))

    return observed_mean, ci_lower, ci_upper, p_val


def run_phase7_benchmark():
    print("=" * 80)
    print("PHASE 7: OPTIMIZATION 2 REDESIGN BENCHMARK (E1h & E1h-div)")
    print("=" * 80)

    stix_kb = load_stix_all_bundles()
    stix_id_to_domains, mitre_id_to_domains = build_stix_domain_maps(stix_kb)

    out_dir = REPO_ROOT / "results" / "phase_7"
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build E1h documents
    print("\n[Step 1] Loading E1a field chunks to construct E1h...", flush=True)
    e1a_cache_docs = REPO_ROOT / ".cache" / "retriever_index_field_chunks" / "child_docs.pkl"
    with open(e1a_cache_docs, "rb") as f:
        e1a_field_docs = pickle.load(f)

    tech_field_docs = [d for d in e1a_field_docs if d.metadata.get("type") == "attack-pattern"]
    print(f"Loaded {len(tech_field_docs)} technique field chunks from E1a.", flush=True)

    e1h_docs = build_e1h_documents(tech_field_docs, max_tokens=150)
    print(f"Constructed {len(e1h_docs)} E1h documents (capped at 150 tokens with repeated headers).", flush=True)

    # E1h-MIXED documents
    e0_cache_docs = REPO_ROOT / ".cache" / "retriever_index_all" / "child_docs.pkl"
    with open(e0_cache_docs, "rb") as f:
        e0_child_docs = pickle.load(f)
    non_tech_base_docs = [d for d in e0_child_docs if d.metadata.get("type") != "attack-pattern"]
    e1h_mixed_docs = e1h_docs + non_tech_base_docs
    print(f"Constructed {len(e1h_mixed_docs)} E1h-MIXED documents ({len(e1h_docs)} tech + {len(non_tech_base_docs)} non-tech).", flush=True)

    # 2. Initialize Retrievers
    print("\n[Step 2] Initializing retrievers for E1h and E1h-MIXED...", flush=True)
    retriever_e1h = HybridSTIXRetriever(
        stix_kb=stix_kb,
        cache_dir=".cache/retriever_index_e1h",
        custom_documents=e1h_docs,
        dense_k=200,
        bm25_k=200,
    )
    retriever_e1h_mixed = HybridSTIXRetriever(
        stix_kb=stix_kb,
        cache_dir=".cache/retriever_index_e1h_mixed",
        custom_documents=e1h_mixed_docs,
        dense_k=200,
        bm25_k=200,
    )
    print("Retrievers ready.", flush=True)

    # 3. Candidate Retrieval (k=200)
    cache_file = out_dir / "top200_phase7_chunks.json"
    top200_cache: Dict[str, Any] = {}
    if cache_file.is_file():
        print(f"Loading existing Phase 7 retrieval cache from {cache_file}...", flush=True)
        with open(cache_file, "r", encoding="utf-8") as f:
            top200_cache = json.load(f)

    datasets = ["cti-ate", "CTI-ATTACK"]
    retriever_arms = {
        "E1h": retriever_e1h,
        "E1h_MIXED": retriever_e1h_mixed,
    }

    print("\n[Step 3] Retrieving k=200 candidate pools under query hygiene...", flush=True)
    for ds_name in datasets:
        top200_cache.setdefault(ds_name, {})
        df = load_benchmark_dataset(ds_name).df

        for arm_name, r in retriever_arms.items():
            if arm_name in top200_cache[ds_name] and len(top200_cache[ds_name][arm_name]) == len(df):
                print(f"  [{ds_name} {arm_name}] Already in cache ({len(df)} queries).", flush=True)
                continue

            print(f"  [{ds_name} {arm_name}] Retrieving {len(df)} queries...", flush=True)
            cell_records = []
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

                docs = retrieve_k200_candidates(
                    retriever=r,
                    query=body,
                    top_k=200,
                    target_domain=target_domain,
                    stix_id_to_domains=stix_id_to_domains,
                    mitre_id_to_domains=mitre_id_to_domains,
                )

                cell_records.append({
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
                    print(f"    {idx + 1}/{len(df)} completed ({time.time() - t0:.1f}s)...", flush=True)

            top200_cache[ds_name][arm_name] = cell_records
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(top200_cache, f, indent=2)

    # 4. Context Budget Evaluation & Diversity Packing
    print("\n[Step 4] Evaluating budget truncation across B in {500, 1000, 2000, 4000}...", flush=True)
    eval_arms = ["E1h", "E1h_div", "E1h_MIXED", "E1h_MIXED_div"]
    scaling_results = defaultdict(lambda: defaultdict(dict))
    per_query_results = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    for ds_name in datasets:
        for arm in eval_arms:
            is_div = arm.endswith("_div")
            base_arm = arm.replace("_div", "")
            raw_records = top200_cache[ds_name][base_arm]

            arm_budgets = {}

            for b in BUDGETS_EVAL:
                per_q_b = []
                for q_item in raw_records:
                    idx = q_item["idx"]
                    gt = q_item["ground_truth"]
                    raw_docs = deserialize_docs(q_item["top200"])

                    if is_div:
                        candidate_docs = filter_diversity_e1h(raw_docs, max_per_tech=2)
                    else:
                        candidate_docs = raw_docs

                    final_docs = truncate_to_token_budget(candidate_docs, budget_tokens=b)
                    m = compute_context_budget_metrics_technique(final_docs, gt, credit_rule="sub_credit")

                    rec = {
                        "idx": idx,
                        "Recall_sub": float(m["Recall_sub_credits_parent"]),
                        "Recall_strict": float(m["Recall_strict"]),
                        "MRR": float(m["MRR"]),
                        "tokens_used": float(m["tokens_used"]),
                        "num_docs": float(m["num_docs"]),
                    }
                    per_q_b.append(rec)
                    per_query_results[ds_name][arm][str(b)][idx] = rec

                df_b = pd.DataFrame(per_q_b)
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

            scaling_results[ds_name][arm] = arm_budgets

    # 5. Load Phase 5 Baselines for Contrast & 4-Budget Scaling Table
    print("\n[Step 5] Loading Phase 5 baselines for contrasts and ladder table...", flush=True)
    p5_k200_path = REPO_ROOT / "results" / "phase_5" / "top200_hd_chunks.json"
    with open(p5_k200_path, "r", encoding="utf-8") as f:
        p5_d200 = json.load(f)

    p5_k50_path = REPO_ROOT / "results" / "phase_5" / "top50_hd_chunks.json"
    with open(p5_k50_path, "r", encoding="utf-8") as f:
        p5_d50 = json.load(f)

    # Evaluate Phase 5 arms across budgets for clean alignment
    p5_per_query = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    p5_scaling = defaultdict(lambda: defaultdict(dict))

    p5_arms = [
        ("E0_prime_k200", p5_d200),
        ("E0_prime_tech_k200", p5_d200),
        ("E1a", p5_d50),
        ("E1_mixed", p5_d50),
    ]

    for ds_name in datasets:
        for arm_key, src in p5_arms:
            records = src[ds_name]["B2"][arm_key]
            arm_budgets = {}

            for b in BUDGETS_EVAL:
                per_q_b = []
                for q_item in records:
                    idx = q_item["idx"]
                    gt = q_item["ground_truth"]
                    raw_docs = deserialize_docs(q_item.get("top200", q_item.get("top50", [])))
                    final_docs = truncate_to_token_budget(raw_docs, budget_tokens=b)
                    m = compute_context_budget_metrics_technique(final_docs, gt, credit_rule="sub_credit")

                    rec = {
                        "idx": idx,
                        "Recall_sub": float(m["Recall_sub_credits_parent"]),
                        "Recall_strict": float(m["Recall_strict"]),
                        "MRR": float(m["MRR"]),
                        "tokens_used": float(m["tokens_used"]),
                        "num_docs": float(m["num_docs"]),
                    }
                    per_q_b.append(rec)
                    p5_per_query[ds_name][arm_key][str(b)][idx] = rec

                df_b = pd.DataFrame(per_q_b)
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

            p5_scaling[ds_name][arm_key] = arm_budgets

    # 6. Evaluate Family P7 Contrasts (Holm M=4)
    print("\n[Step 6] Evaluating Family P7 contrasts (Mean Recall@B over {500, 1000}, sub-credit)...", flush=True)
    contrasts_decl = [
        {"id": "P7_01", "dataset": "cti-ate", "treatment": "E1h", "control": "E0_prime_tech_k200"},
        {"id": "P7_02", "dataset": "cti-ate", "treatment": "E1h_div", "control": "E0_prime_tech_k200"},
        {"id": "P7_03", "dataset": "CTI-ATTACK", "treatment": "E1h", "control": "E0_prime_tech_k200"},
        {"id": "P7_04", "dataset": "CTI-ATTACK", "treatment": "E1h_div", "control": "E0_prime_tech_k200"},
    ]

    contrast_results = []

    for c in contrasts_decl:
        ds = c["dataset"]
        treat_name = c["treatment"]
        ctrl_name = c["control"]

        df_ds = load_benchmark_dataset(ds).df
        n_queries = len(df_ds)

        # Compute per-query mean Recall@B over {500, 1000}
        treat_means = []
        ctrl_means = []

        for idx in range(n_queries):
            t_vals = [
                per_query_results[ds][treat_name][str(b)][idx]["Recall_sub"]
                for b in PRIMARY_BUDGETS
            ]
            c_vals = [
                p5_per_query[ds][ctrl_name][str(b)][idx]["Recall_sub"]
                for b in PRIMARY_BUDGETS
            ]
            treat_means.append(np.mean(t_vals))
            ctrl_means.append(np.mean(c_vals))

        treat_arr = np.array(treat_means)
        ctrl_arr = np.array(ctrl_means)
        diff_arr = treat_arr - ctrl_arr

        # Wins / Ties / Losses
        wins = int(np.sum(diff_arr > 1e-6))
        losses = int(np.sum(diff_arr < -1e-6))
        ties = int(np.sum(np.abs(diff_arr) <= 1e-6))

        # Paired bootstrap
        diff_mean, ci_low, ci_high, boot_pval = compute_paired_bootstrap(
            diff_arr, n_resamples=10000, seed=42
        )

        # Exact two-sided binomial sign test on discordant pairs
        n_discordant = wins + losses
        if n_discordant > 0:
            res_sign = stats.binomtest(wins, n_discordant, p=0.5, alternative="two-sided")
            sign_pval = float(res_sign.pvalue)
        else:
            sign_pval = 1.0

        contrast_results.append({
            "contrast_id": c["id"],
            "dataset": ds,
            "treatment": treat_name,
            "control": "E0'-TECH-k200",
            "metric": "Mean Recall@{500,1000} (sub-credit)",
            "n_queries": n_queries,
            "control_mean": round(float(np.mean(ctrl_arr)), 4),
            "treatment_mean": round(float(np.mean(treat_arr)), 4),
            "delta": round(diff_mean, 4),
            "ci_95_low": round(ci_low, 4),
            "ci_95_high": round(ci_high, 4),
            "bootstrap_pval": round(boot_pval, 5),
            "exact_sign_pval": round(sign_pval, 5),
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "wtl_str": f"{wins}/{ties}/{losses}",
        })

    # Apply Holm step-down correction across M=4
    contrast_results.sort(key=lambda x: x["bootstrap_pval"])
    m_tests = len(contrast_results)
    for rank, cr in enumerate(contrast_results):
        k_rank = rank + 1
        holm_alpha = 0.05 / (m_tests - k_rank + 1)
        cr["holm_alpha"] = round(holm_alpha, 4)
        cr["is_significant_holm"] = bool(cr["bootstrap_pval"] < holm_alpha)
        cr["verdict"] = "Significant Improvement" if cr["is_significant_holm"] and cr["delta"] > 0 else (
            "Significant Deficit" if cr["is_significant_holm"] and cr["delta"] < 0 else "Neutral / Not Significant"
        )

    # Sort back by contrast_id
    contrast_results.sort(key=lambda x: x["contrast_id"])

    df_p7 = pd.DataFrame(contrast_results)
    p7_csv = assets_dir / "table_p7_contrasts.csv"
    df_p7.to_csv(p7_csv, index=False)
    print(f"Saved P7 contrasts table to {p7_csv}")

    # 7. Construct Full 4-Budget Scaling Table
    print("\n[Step 7] Constructing full 4-budget scaling table...", flush=True)
    scaling_rows = []

    all_display_arms = [
        ("E0'-k200 (Phase 5)", "E0_prime_k200", p5_scaling),
        ("E0'-TECH-k200 (Control)", "E0_prime_tech_k200", p5_scaling),
        ("E1a (Phase 5)", "E1a", p5_scaling),
        ("E1-MIXED (Phase 5)", "E1_mixed", p5_scaling),
        ("E1h (Phase 7)", "E1h", scaling_results),
        ("E1h-div (Phase 7)", "E1h_div", scaling_results),
        ("E1h-MIXED (Phase 7)", "E1h_MIXED", scaling_results),
        ("E1h-MIXED-div (Phase 7)", "E1h_MIXED_div", scaling_results),
    ]

    for ds_name in datasets:
        for arm_label, arm_key, src_dict in all_display_arms:
            d = src_dict[ds_name][arm_key]
            row_dict = {
                "dataset": ds_name,
                "arm": arm_label,
            }
            for b in BUDGETS_EVAL:
                rec_sub = d[str(b)]["Recall_sub"]
                is_bind = d[str(b)]["is_binding"]
                flag = "[B]" if is_bind else "[C]"
                row_dict[f"B={b}"] = f"{rec_sub:.4f} {flag}"
                row_dict[f"B={b}_raw"] = rec_sub
                row_dict[f"B={b}_binding"] = is_bind

            # Mean across 500 & 1000
            m_500_1000 = (row_dict["B=500_raw"] + row_dict["B=1000_raw"]) / 2.0
            row_dict["Mean_Recall@500_1000"] = round(m_500_1000, 4)

            scaling_rows.append(row_dict)

    df_scaling = pd.DataFrame(scaling_rows)
    scaling_csv = assets_dir / "table_o2_4budget_scaling.csv"
    df_scaling.to_csv(scaling_csv, index=False)
    print(f"Saved 4-budget scaling table to {scaling_csv}")

    # Save detailed JSON summary
    out_json = out_dir / "phase7_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "family_P7_contrasts": contrast_results,
            "scaling_results_phase7": scaling_results,
            "scaling_results_phase5_baseline": p5_scaling,
        }, f, indent=2)
    print(f"Saved Phase 7 results JSON to {out_json}")

    print("\n" + "=" * 80)
    print("FAMILY P7 CONTRASTS SUMMARY")
    print("=" * 80)
    print(df_p7[["contrast_id", "dataset", "treatment", "control", "treatment_mean", "control_mean", "delta", "ci_95_low", "ci_95_high", "bootstrap_pval", "wtl_str", "verdict"]].to_string(index=False))

    print("\n" + "=" * 80)
    print("4-BUDGET SCALING COMPARISON")
    print("=" * 80)
    print(df_scaling[["dataset", "arm", "B=500", "B=1000", "B=2000", "B=4000", "Mean_Recall@500_1000"]].to_string(index=False))


if __name__ == "__main__":
    run_phase7_benchmark()
