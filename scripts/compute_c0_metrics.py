"""Compute C0 Corpus & Chunk Statistics and determine Primary Budget B*.
"""

import json
from pathlib import Path
import sys
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_stix_all_bundles, load_benchmark_dataset
from src.corpus import build_stix_raw_documents, split_documents_baseline
from src.retriever import HybridSTIXRetriever

REPO_ROOT = Path(__file__).resolve().parent.parent


def count_words(text: str) -> int:
    return len(text.split())


def run_c0():
    print("=" * 70)
    print("Computing C0 Corpus and Chunk Statistics...")
    print("=" * 70)

    kb = load_stix_all_bundles()
    raw_docs = build_stix_raw_documents(kb)
    parent_docs, child_docs = split_documents_baseline(raw_docs)

    type_stats = {}
    for obj_type in ["attack-pattern", "intrusion-set", "malware", "tool"]:
        matching_children = [
            d for d in child_docs
            if d.metadata.get("type") == obj_type
            or (obj_type in ["malware", "tool"] and d.metadata.get("type") in ["malware", "tool", "software"])
        ]
        char_lens = [len(d.page_content) for d in matching_children]
        word_lens = [count_words(d.page_content) for d in matching_children]

        type_stats[obj_type] = {
            "chunk_count": len(matching_children),
            "chars_mean": round(float(np.mean(char_lens)), 1) if char_lens else 0,
            "chars_median": round(float(np.median(char_lens)), 1) if char_lens else 0,
            "tokens_words_mean": round(float(np.mean(word_lens)), 1) if word_lens else 0,
            "tokens_words_median": round(float(np.median(word_lens)), 1) if word_lens else 0,
        }
        print(f"[{obj_type}] Count: {len(matching_children)} | Chars: mean={type_stats[obj_type]['chars_mean']}, median={type_stats[obj_type]['chars_median']} | Tokens(words): mean={type_stats[obj_type]['tokens_words_mean']}, median={type_stats[obj_type]['tokens_words_median']}")

    # 2. Measure top-10 context size on cti-ate (60) and CTI-ATTACK (sample/all) under E0'
    print("\nMeasuring top-10 retrieved context token size for E0' control...")
    retriever = HybridSTIXRetriever(stix_kb=kb, cache_dir=".cache/retriever_index_all")

    ds_ate = load_benchmark_dataset("cti-ate")
    ds_att = load_benchmark_dataset("CTI-ATTACK")

    # Sample representative queries across cti-ate and CTI-ATTACK to establish median top-10 tokens
    context_tokens = []
    # Test all 60 of cti-ate
    for _, row in ds_ate.df.iterrows():
        docs = retriever.dense_retriever.invoke(str(row["query"])) + retriever.bm25_retriever.invoke(str(row["query"]))
        deduped = list({d.page_content: d for d in docs}.values())[:10]
        context_text = "\n".join(d.page_content for d in deduped)
        context_tokens.append(count_words(context_text))

    # Test sample of 60 from CTI-ATTACK
    for _, row in ds_att.df.iloc[:60].iterrows():
        docs = retriever.dense_retriever.invoke(str(row["query"])) + retriever.bm25_retriever.invoke(str(row["query"]))
        deduped = list({d.page_content: d for d in docs}.values())[:10]
        context_text = "\n".join(d.page_content for d in deduped)
        context_tokens.append(count_words(context_text))

    mean_ctx = round(float(np.mean(context_tokens)), 1)
    median_ctx = round(float(np.median(context_tokens)), 1)
    # Round to nearest 50 tokens
    b_star = int(round(median_ctx / 50.0) * 50)
    if b_star == 0:
        b_star = 350

    print(f"\nContext Token Stats (Top-10 Chunks across 120 queries):")
    print(f"  Mean tokens (words): {mean_ctx}")
    print(f"  Median tokens (words): {median_ctx}")
    print(f"  Pre-registered Primary Budget B* = {b_star} tokens (rounded to nearest 50)")

    c0_results = {
        "corpus_stats_by_type": type_stats,
        "top10_context_tokens": {
            "mean": mean_ctx,
            "median": median_ctx,
            "b_star": b_star,
        },
        "secondary_budgets": [500, 1000, 2000, 4000],
    }

    out_file = REPO_ROOT / "results" / "phase_2" / "c0_inspection_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(c0_results, f, indent=2)
    print(f"Saved C0 results to {out_file}")


if __name__ == "__main__":
    run_c0()
