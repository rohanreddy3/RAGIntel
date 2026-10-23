"""Phase 5 Part C: Optimization 2 Clean Comparisons Benchmark (O2 HD Preprocessing).

Evaluates:
- Preprocessing HD:
  - Query body text only (split_query).
  - For cti-ate: domain filter derived from instruction text ("MITRE Enterprise" vs "MITRE Mobile").
  - For CTI-ATTACK: no domain filter (all STIX objects eligible).
- Comparison: Raw (frozen Phase 3C) preprocessing without domain filter.
- Arms: E0'-TECH, E1a, E0', E1-MIXED. (No sibling arms).
- Token Budgets: B in {500, 1000, 2000, 4000}.
- Family P4: 6 confirmatory contrasts evaluated on Mean Recall@B across binding budgets:
  1. E1a vs E0'-TECH on cti-ate B2
  2. E1-MIXED vs E0' on cti-ate B2
  3. E1a vs E0'-TECH on cti-ate B3
  4. E1-MIXED vs E0' on cti-ate B3
  5. E1a vs E0'-TECH on CTI-ATTACK (B2)
  6. E1-MIXED vs E0' on CTI-ATTACK (B2)
  Multiplicity control: Holm-Bonferroni step-down (M=6, alpha=0.05).
  Paired bootstrap: N=10,000, seed 42.
- Hygiene Effect Alone:
  E0' HD vs E0' raw on cti-ate and CTI-ATTACK.
- Sanity Check:
  Share of cti-ate rows whose ground truth IDs fall into named domain.
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

def compute_context_budget_metrics_technique(
    final_docs: List[Document],
    ground_truth_str: str,
    credit_rule: str = "text_and_metadata",
) -> Dict[str, Any]:
    """Compute Recall@B (strict & sub_credits_parent), MRR, distinct techniques, and tokens."""
    gt_set = parse_ground_truth_techniques(ground_truth_str)
    num_gt = len(gt_set)
    tokens_used = sum(count_tokens(d.page_content) for d in final_docs)

    distinct_techs: Set[str] = set()
    retrieved_techs_by_rank: List[Set[str]] = []

    for doc in final_docs:
        doc_techs: Set[str] = set()
        m_id = str(doc.metadata.get("mitre_id", "")).strip()
        t_id = str(doc.metadata.get("technique_id", "")).strip()

        if credit_rule == "text_and_metadata" or credit_rule == "sub_credit":
            doc_techs = extract_technique_ids_from_text(doc.page_content)
            if m_id and m_id.startswith("T"):
                doc_techs.add(m_id)
        elif credit_rule == "metadata_only":
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

BUDGETS = [500, 1000, 2000, 4000]

# Binding budgets per dataset
BINDING_BUDGETS = {
    "cti-ate": [500, 1000, 2000],
    "CTI-ATTACK": [500, 1000],
}


def split_query(q: str):
    markers = ["Threat Report:", "**Text:**"]
    pos = -1
    found_marker = None
    for m in markers:
        p = q.find(m)
        if p != -1:
            if pos == -1 or p < pos:
                pos = p
                found_marker = m
    if found_marker is None:
        raise ValueError(f"Marker not found in query: {q[:100]}...")
    instruction = q[:pos].strip()
    body = q[pos + len(found_marker):].strip()
    return instruction, body, found_marker


def build_stix_domain_maps(stix_kb):
    """Map STIX ID and MITRE ID to associated ATT&CK domain(s)."""
    stix_id_to_domains = defaultdict(set)
    mitre_id_to_domains = defaultdict(set)

    for obj in stix_kb.attack_patterns:
        sid = obj.get("id")
        domains = set(obj.get("x_mitre_domains", []))
        ext_refs = obj.get("external_references", [])
        for r in ext_refs:
            src = r.get("source_name", "")
            if src == "mitre-attack":
                domains.add("enterprise-attack")
            elif src == "mitre-mobile-attack":
                domains.add("mobile-attack")
            elif src == "mitre-ics-attack":
                domains.add("ics-attack")

            mid = r.get("external_id")
            if mid:
                mitre_id_to_domains[mid].update(domains)
                if "." in mid:
                    mitre_id_to_domains[mid.split(".")[0]].update(domains)

        if sid:
            stix_id_to_domains[sid].update(domains)

    return stix_id_to_domains, mitre_id_to_domains


def doc_matches_domain(doc: Document, target_domain: Optional[str], stix_id_to_domains, mitre_id_to_domains) -> bool:
    """Return True if doc belongs to target_domain, or if target_domain is None."""
    if target_domain is None:
        return True

    meta = doc.metadata if hasattr(doc, "metadata") else {}
    sid = meta.get("stix_id", "")
    mid = meta.get("mitre_id", "")

    doc_domains = set()
    if sid and sid in stix_id_to_domains:
        doc_domains.update(stix_id_to_domains[sid])
    if mid and mid in mitre_id_to_domains:
        doc_domains.update(mitre_id_to_domains[mid])
    if "." in mid and mid.split(".")[0] in mitre_id_to_domains:
        doc_domains.update(mitre_id_to_domains[mid.split(".")[0]])

    return target_domain in doc_domains


def retrieve_with_domain_filter(
    retriever: HybridSTIXRetriever,
    query: str,
    top_k: int = 50,
    target_domain: Optional[str] = None,
    enable_chunking: bool = False,
    stix_id_to_domains: Optional[Dict] = None,
    mitre_id_to_domains: Optional[Dict] = None,
) -> List[Document]:
    """Retrieve top_k documents with optional candidate domain filtering before reranking."""
    from flashrank import RerankRequest

    if not enable_chunking:
        windows = [query]
    else:
        windows = retriever._split_query_into_windows(query, max_words=150, overlap=30)

    all_candidate_docs: Dict[str, Document] = {}

    for win in windows:
        # If domain filter is active, fetch broader candidate pool (k=150) so domain filtering doesn't starve candidates
        fetch_k = 150 if target_domain else retriever.dense_k
        try:
            dense_docs = retriever.vector_store.similarity_search(win, k=fetch_k)
        except Exception:
            dense_docs = retriever.dense_retriever.invoke(win)

        bm25_k_orig = retriever.bm25_retriever.k
        if target_domain:
            retriever.bm25_retriever.k = 150
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
        # Fallback if domain filter was overly restrictive: return unfiltered top candidates
        return retriever.retrieve(query, top_k=top_k, enable_query_chunking=enable_chunking)

    passages = [
        {"id": idx, "text": doc.page_content, "meta": doc.metadata}
        for idx, doc in enumerate(all_candidate_docs.values())
    ]

    all_reranked = []
    batch_size = 20
    # Use first window for reranking context
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


def deserialize_docs(doc_list: List[Dict[str, Any]]) -> List[Document]:
    """Deserialize dict documents from JSON cache."""
    return [
        Document(page_content=d.get("page_content", d.get("content", "")), metadata=d.get("metadata", {}))
        for d in doc_list
    ]


def run_o2_benchmark():
    print("=" * 80)
    print("PHASE 5 PART C: O2 CLEAN COMPARISONS BENCHMARK (HD PREPROCESSING)")
    print("=" * 80)

    stix_kb = load_stix_all_bundles()
    stix_id_to_domains, mitre_id_to_domains = build_stix_domain_maps(stix_kb)

    out_dir = REPO_ROOT / "results" / "phase_5"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize retrievers from existing .cache indices
    print("\nInitializing retrievers from .cache indices...", flush=True)
    retrievers = {
        "E0_prime_tech": HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_e0_tech"),
        "E1a": HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_field_chunks"),
        "E0_prime": HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all"),
        "E1_mixed": HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_e1_mixed"),
    }
    print("All 4 retrievers initialized.", flush=True)

    # 2. Load frozen Raw top50 results for comparison
    frozen_top50_path = REPO_ROOT / "results" / "phase_3" / "top50_phase3c_chunks.json"
    with open(frozen_top50_path, "r", encoding="utf-8") as f:
        frozen_top50 = json.load(f)

    # Storage for HD top50 chunks
    hd_top50_path = out_dir / "top50_hd_chunks.json"
    hd_top50: Dict[str, Any] = {}
    if hd_top50_path.exists():
        print(f"Loading existing HD top50 cache from {hd_top50_path}...", flush=True)
        with open(hd_top50_path, "r", encoding="utf-8") as f:
            hd_top50 = json.load(f)

    # Datasets and baselines to evaluate
    eval_cells = [
        ("cti-ate", "B2", False),
        ("cti-ate", "B3", True),
        ("CTI-ATTACK", "B2", False),
    ]

    arms = ["E0_prime_tech", "E1a", "E0_prime", "E1_mixed"]

    # 3. Compute HD top50 chunks
    for ds_name, baseline, enable_chunking in eval_cells:
        hd_top50.setdefault(ds_name, {})
        hd_top50[ds_name].setdefault(baseline, {})

        df = load_benchmark_dataset(ds_name).df
        print(f"\n=======================================================", flush=True)
        print(f"EVALUATING HD RETRIEVAL: {ds_name} | {baseline} ({len(df)} queries)", flush=True)
        print(f"=======================================================", flush=True)

        for arm in arms:
            if arm in hd_top50[ds_name][baseline] and len(hd_top50[ds_name][baseline][arm]) == len(df):
                print(f"  Skipping {arm} (already in cache, {len(df)} queries).", flush=True)
                continue

            r = retrievers[arm]
            print(f"  Retrieving {arm} under HD preprocessing...", flush=True)
            cell_results = []
            t0 = time.time()

            for idx, row in df.iterrows():
                q_raw = str(row["query"])
                gt = str(row["ground_truth"])
                instr, body, marker = split_query(q_raw)

                # Determine target domain for cti-ate
                target_domain = None
                if ds_name == "cti-ate":
                    if "MITRE Enterprise" in instr:
                        target_domain = "enterprise-attack"
                    elif "MITRE Mobile" in instr:
                        target_domain = "mobile-attack"

                # Preprocessing HD: body-only query + domain filter
                docs = retrieve_with_domain_filter(
                    retriever=r,
                    query=body,
                    top_k=50,
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
                    "top50": [
                        {"page_content": d.page_content, "metadata": d.metadata}
                        for d in docs
                    ],
                })

                if (idx + 1) % 25 == 0 or idx == len(df) - 1:
                    print(f"    [{ds_name} {baseline} {arm}] {idx + 1}/{len(df)} queries ({time.time() - t0:.1f}s)...", flush=True)

            hd_top50[ds_name][baseline][arm] = cell_results

            # Save checkpoint
            with open(hd_top50_path, "w", encoding="utf-8") as f:
                json.dump(hd_top50, f, indent=2)

    # 4. Evaluate budget truncation & metrics for both HD and Raw
    print("\n" + "=" * 80)
    print("EVALUATING BUDGET TRUNCATION & METRICS (HD vs Raw)")
    print("=" * 80)

    # Results structure:
    # results[prep][ds_name][baseline][arm][budget] -> {"per_query": [...], "mean_recall": float, ...}
    eval_results = {"HD": defaultdict(lambda: defaultdict(dict)), "Raw": defaultdict(lambda: defaultdict(dict))}

    for prep, top50_source in [("HD", hd_top50), ("Raw", frozen_top50)]:
        for ds_name, baseline, _ in eval_cells:
            b_list = BINDING_BUDGETS[ds_name]
            for arm in arms:
                records = top50_source[ds_name][baseline][arm]
                arm_budgets = {}

                # Track per-query metrics for binding budget average
                per_query_binding_recalls = defaultdict(list)

                for b in BUDGETS:
                    per_query_b = []
                    for q_item in records:
                        idx = q_item["idx"]
                        gt = q_item["ground_truth"]
                        raw_docs = deserialize_docs(q_item["top50"])

                        final_docs = truncate_to_token_budget(raw_docs, budget_tokens=b)
                        m = compute_context_budget_metrics_technique(final_docs, gt, credit_rule="sub_credit")

                        rec_sub = float(m["Recall_sub_credits_parent"])
                        rec_strict = float(m["Recall_strict"])
                        mrr = float(m["MRR"])
                        tokens_used = float(m["tokens_used"])

                        per_query_b.append({
                            "idx": idx,
                            "Recall_sub": rec_sub,
                            "Recall_strict": rec_strict,
                            "MRR": mrr,
                            "tokens_used": tokens_used,
                        })

                        if b in b_list:
                            per_query_binding_recalls[idx].append(rec_sub)

                    df_b = pd.DataFrame(per_query_b)
                    arm_budgets[str(b)] = {
                        "Recall_sub": round(float(df_b["Recall_sub"].mean()), 4),
                        "Recall_strict": round(float(df_b["Recall_strict"].mean()), 4),
                        "MRR": round(float(df_b["MRR"].mean()), 4),
                        "tokens_used": round(float(df_b["tokens_used"].mean()), 1),
                        "per_query": per_query_b,
                    }

                # Compute mean binding recall per query
                binding_means = [
                    float(np.mean(per_query_binding_recalls[q_item["idx"]]))
                    for q_item in records
                ]

                arm_budgets["binding_mean"] = {
                    "mean_recall": round(float(np.mean(binding_means)), 4),
                    "binding_budgets": b_list,
                    "per_query_binding_means": binding_means,
                }

                eval_results[prep][ds_name][baseline][arm] = arm_budgets

    # 5. Print 4-Budget Scaling Tables
    print("\n" + "=" * 80)
    print("4-BUDGET SCALING TABLES: Recall@B (sub_credit)")
    print("=" * 80)

    for prep in ["HD", "Raw"]:
        print(f"\n--- Preprocessing: {prep} ---")
        for ds_name, baseline, _ in eval_cells:
            print(f"\nDataset: {ds_name} | Baseline: {baseline}")
            print(f"{'Arm':<15} {'B=500':<10} {'B=1000':<10} {'B=2000':<10} {'B=4000':<10} {'Binding Mean':<12}")
            print("-" * 65)
            for arm in arms:
                data = eval_results[prep][ds_name][baseline][arm]
                r500 = data["500"]["Recall_sub"]
                r1000 = data["1000"]["Recall_sub"]
                r2000 = data["2000"]["Recall_sub"]
                r4000 = data["4000"]["Recall_sub"]
                bmean = data["binding_mean"]["mean_recall"]
                print(f"{arm:<15} {r500:<10.4f} {r1000:<10.4f} {r2000:<10.4f} {r4000:<10.4f} {bmean:<12.4f}")

    # 6. Statistical Contrasts: Family P4 (6 tests, Holm-Bonferroni step-down)
    print("\n" + "=" * 80)
    print("FAMILY P4 CONFIRMATORY CONTRASTS (6 tests on Mean Binding Recall, Holm step-down)")
    print("=" * 80)

    p4_specs = [
        ("P4_01", "cti-ate", "B2", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (cti-ate B2)"),
        ("P4_02", "cti-ate", "B2", "E1_mixed", "E0_prime", "STIX-ALL Architecture: E1-MIXED vs E0' (cti-ate B2)"),
        ("P4_03", "cti-ate", "B3", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (cti-ate B3)"),
        ("P4_04", "cti-ate", "B3", "E1_mixed", "E0_prime", "STIX-ALL Architecture: E1-MIXED vs E0' (cti-ate B3)"),
        ("P4_05", "CTI-ATTACK", "B2", "E1a", "E0_prime_tech", "Field Chunking Alone: E1a vs E0'-TECH (CTI-ATTACK B2)"),
        ("P4_06", "CTI-ATTACK", "B2", "E1_mixed", "E0_prime", "STIX-ALL Architecture: E1-MIXED vs E0' (CTI-ATTACK B2)"),
    ]

    p4_results = []
    for test_id, ds_name, baseline, t_arm, c_arm, desc in p4_specs:
        t_vals = eval_results["HD"][ds_name][baseline][t_arm]["binding_mean"]["per_query_binding_means"]
        c_vals = eval_results["HD"][ds_name][baseline][c_arm]["binding_mean"]["per_query_binding_means"]

        mean_t = float(np.mean(t_vals))
        mean_c = float(np.mean(c_vals))
        delta = mean_t - mean_c

        boot_res = compute_paired_bootstrap_ci(c_vals, t_vals, n_resamples=10000, seed=42)
        ci_l, ci_h, p_val = boot_res["ci_lower"], boot_res["ci_upper"], boot_res["p_value"]

        diffs = [t - c for t, c in zip(t_vals, c_vals)]
        wins = sum(1 for d in diffs if d > 1e-9)
        ties = sum(1 for d in diffs if abs(d) <= 1e-9)
        losses = sum(1 for d in diffs if d < -1e-9)

        p4_results.append({
            "test_id": test_id,
            "dataset": ds_name,
            "baseline": baseline,
            "treatment": t_arm,
            "control": c_arm,
            "description": desc,
            "treatment_mean": round(mean_t, 4),
            "control_mean": round(mean_c, 4),
            "delta": round(delta, 4),
            "ci_95": [round(ci_l, 4), round(ci_h, 4)],
            "raw_p": round(p_val, 4),
            "wtl": f"{wins}/{ties}/{losses}",
            "sum_diffs": round(sum(diffs), 4),
        })

    # Apply Holm step-down across the 6 tests
    p4_results.sort(key=lambda x: x["raw_p"])
    M = len(p4_results)
    sig_active = True
    print(f"\n--- Holm-Bonferroni Step-Down (M={M}, alpha=0.05) ---")
    for rank, c in enumerate(p4_results, 1):
        alpha_k = 0.05 / (M - rank + 1)
        p = c["raw_p"]
        if sig_active and p <= alpha_k:
            decision = "Significant decrease" if c["delta"] < 0 else "Significant increase"
        else:
            sig_active = False
            decision = "Not significant"

        c["holm_rank"] = rank
        c["holm_alpha"] = round(alpha_k, 5)
        c["decision"] = decision
        p_str = "< 0.0001" if p == 0.0 else f"{p:.4f}"
        print(f"Rank {rank}: {c['test_id']} ({c['description']}): Delta={c['delta']:+.4f}, p={p_str}, alpha_k={alpha_k:.5f} -> {decision}")

    # 7. Hygiene Effect Alone: E0' HD vs E0' Raw
    print("\n" + "=" * 80)
    print("HYGIENE EFFECT ALONE: E0' under HD vs E0' under Raw")
    print("=" * 80)

    hygiene_results = []
    for ds_name, baseline, _ in eval_cells:
        hd_vals = eval_results["HD"][ds_name][baseline]["E0_prime"]["binding_mean"]["per_query_binding_means"]
        raw_vals = eval_results["Raw"][ds_name][baseline]["E0_prime"]["binding_mean"]["per_query_binding_means"]

        mean_hd = float(np.mean(hd_vals))
        mean_raw = float(np.mean(raw_vals))
        delta = mean_hd - mean_raw

        boot_res = compute_paired_bootstrap_ci(raw_vals, hd_vals, n_resamples=10000, seed=42)
        ci_l, ci_h, p_val = boot_res["ci_lower"], boot_res["ci_upper"], boot_res["p_value"]
        diffs = [h - r for h, r in zip(hd_vals, raw_vals)]
        wins = sum(1 for d in diffs if d > 1e-9)
        ties = sum(1 for d in diffs if abs(d) <= 1e-9)
        losses = sum(1 for d in diffs if d < -1e-9)

        p_str = "< 0.0001" if p_val == 0.0 else f"{p_val:.4f}"
        print(f"{ds_name} {baseline}: HD={mean_hd:.4f}, Raw={mean_raw:.4f}, Delta={delta:+.4f} (95% CI [{ci_l:+.4f}, {ci_h:+.4f}], p={p_str}, W/T/L: {wins}/{ties}/{losses})")

        hygiene_results.append({
            "dataset": ds_name,
            "baseline": baseline,
            "mean_hd": round(mean_hd, 4),
            "mean_raw": round(mean_raw, 4),
            "delta": round(delta, 4),
            "ci_95": [round(ci_l, 4), round(ci_h, 4)],
            "raw_p": round(p_val, 4),
            "wtl": f"{wins}/{ties}/{losses}",
        })

    # Save all results to results/phase_5/o2_phase5_benchmark_results.json
    out_json = out_dir / "o2_phase5_benchmark_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "eval_results": {
                prep: {
                    ds: {
                        b: {
                            arm: {
                                k: v for k, v in eval_results[prep][ds][b][arm].items() if k != "per_query"
                            }
                            for arm in eval_results[prep][ds][b]
                        }
                        for b in eval_results[prep][ds]
                    }
                    for ds in eval_results[prep]
                }
                for prep in eval_results
            },
            "family_p4_contrasts": p4_results,
            "hygiene_effect": hygiene_results,
        }, f, indent=2)
    print(f"\nSaved O2 benchmark results to {out_json}")


if __name__ == "__main__":
    run_o2_benchmark()
