"""Inspect C0: STIX document construction, chunk token distribution,
and determine the primary matched context budget B* = median token size of E0' top-10 context.
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_stix_all_bundles, load_all_benchmark_datasets
from src.corpus import build_stix_raw_documents, split_documents_baseline
from src.retriever import HybridSTIXRetriever


def count_tokens(text: str) -> int:
    """Standard whitespace word tokenization aligned with thesis token budgeting."""
    return len(text.split())


def main():
    print("=" * 75, flush=True)
    print("C0: STIX DOCUMENTATION & CHUNKING INSPECTION", flush=True)
    print("=" * 75, flush=True)

    stix_kb = load_stix_all_bundles()
    raw_docs = build_stix_raw_documents(stix_kb)
    parent_docs, child_docs = split_documents_baseline(raw_docs)

    print(f"Total raw STIX objects: {len(raw_docs)}", flush=True)
    print(f"Total parent chunks (2000/200): {len(parent_docs)}", flush=True)
    print(f"Total child chunks (500/50):   {len(child_docs)}", flush=True)

    # 1. Distribution by object type for raw docs, parents, and child chunks
    type_stats = {}
    for obj_type in ["attack-pattern", "intrusion-set", "malware", "tool"]:
        raw_t = [d for d in raw_docs if d.metadata.get("type") == obj_type or (obj_type in ["malware", "tool"] and d.metadata.get("type") in ["malware", "tool", "software"])]
        child_t = [d for d in child_docs if d.metadata.get("type") == obj_type or (obj_type in ["malware", "tool"] and d.metadata.get("type") in ["malware", "tool", "software"])]

        raw_lens = [len(d.page_content) for d in raw_t]
        raw_words = [count_tokens(d.page_content) for d in raw_t]
        child_lens = [len(d.page_content) for d in child_t]
        child_words = [count_tokens(d.page_content) for d in child_t]

        type_stats[obj_type] = {
            "raw_count": len(raw_t),
            "child_chunk_count": len(child_t),
            "raw_chars_mean": round(float(np.mean(raw_lens)), 1) if raw_lens else 0,
            "raw_words_mean": round(float(np.mean(raw_words)), 1) if raw_words else 0,
            "child_chars_mean": round(float(np.mean(child_lens)), 1) if child_lens else 0,
            "child_words_mean": round(float(np.mean(child_words)), 1) if child_words else 0,
            "child_words_p50": round(float(np.median(child_words)), 1) if child_words else 0,
            "child_words_p95": round(float(np.percentile(child_words, 95)), 1) if child_words else 0,
        }
        print(f"\n[{obj_type}] Raw count: {len(raw_t)}, Child chunks: {len(child_t)}", flush=True)
        print(f"  Child tokens (words): mean={type_stats[obj_type]['child_words_mean']}, median={type_stats[obj_type]['child_words_p50']}, p95={type_stats[obj_type]['child_words_p95']}", flush=True)

    # 2. Compute median token size of E0' top-10 context across benchmark datasets to determine B*
    print("\n" + "=" * 75, flush=True)
    print("COMPUTING MEDIAN TOP-10 CONTEXT TOKEN SIZE FOR E0' CONTROL TO DETERMINE B*", flush=True)
    print("=" * 75, flush=True)

    retriever = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")
    datasets = load_all_benchmark_datasets()

    # We evaluate E0' top-10 context token size across cti-ate (60) and CTI-ATTACK (229)
    # under baseline B2 (the primary dense+sparse retrieval model)
    context_token_lengths = []
    per_query_top10_tokens = {}

    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        df = datasets[ds_name].df
        ds_lengths = []
        for idx, row in df.iterrows():
            q = str(row["query"])
            docs = retriever.retrieve(q, top_k=10, enable_query_chunking=False)
            # Concatenate top-10 chunk texts
            top10_text = "\n".join(d.page_content for d in docs)
            tok_len = count_tokens(top10_text)
            context_token_lengths.append(tok_len)
            ds_lengths.append(tok_len)

        per_query_top10_tokens[ds_name] = {
            "num_queries": len(df),
            "mean_tokens": round(float(np.mean(ds_lengths)), 1),
            "median_tokens": round(float(np.median(ds_lengths)), 1),
            "p25_tokens": round(float(np.percentile(ds_lengths, 25)), 1),
            "p75_tokens": round(float(np.percentile(ds_lengths, 75)), 1),
            "min_tokens": int(np.min(ds_lengths)),
            "max_tokens": int(np.max(ds_lengths)),
        }
        print(f"[{ds_name}] Top-10 Context Tokens: Mean = {per_query_top10_tokens[ds_name]['mean_tokens']}, Median = {per_query_top10_tokens[ds_name]['median_tokens']}", flush=True)

    overall_median_tokens = int(round(float(np.median(context_token_lengths))))
    overall_mean_tokens = round(float(np.mean(context_token_lengths)), 1)

    print("\n" + "=" * 75, flush=True)
    print(f"OVERALL E0' TOP-10 CONTEXT TOKEN BUDGET:", flush=True)
    print(f"Total queries evaluated (cti-ate + CTI-ATTACK): {len(context_token_lengths)}", flush=True)
    print(f"Mean top-10 tokens:   {overall_mean_tokens}", flush=True)
    print(f"Median top-10 tokens: {overall_median_tokens}", flush=True)
    print(f"DETERMINED PRIMARY BUDGET B* = {overall_median_tokens} tokens", flush=True)
    print("=" * 75, flush=True)

    c0_report = {
        "stix_corpus_chunk_distribution": type_stats,
        "per_dataset_top10_context_tokens": per_query_top10_tokens,
        "overall_mean_tokens": overall_mean_tokens,
        "overall_median_tokens": overall_median_tokens,
        "B_star_tokens": overall_median_tokens,
    }

    out_file = REPO_ROOT / "results" / "phase_2" / "c0_inspection_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(c0_report, f, indent=2)

    print(f"\nSaved C0 inspection report to {out_file}", flush=True)


if __name__ == "__main__":
    main()
