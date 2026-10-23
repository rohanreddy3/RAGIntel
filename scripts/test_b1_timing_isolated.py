"""Isolated Timing Benchmark for Baseline B1 (Item 7).

Measures on CPU (Python 3.12):
1. Document embedding time for 100 STIX documents.
2. Query encoding and vector retrieval time for 20 queries.
3. Extrapolates total runtime for full E0-STIX-ALL (2,062 documents) and 339 queries.
"""

import json
import os
import sys
import time
from pathlib import Path

def test_b1_timing():
    print("=" * 75)
    print("BASELINE B1 TIMING TEST (100 Documents, 20 Queries on CPU)")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print("=" * 75)

    data_file = Path("scratch/sample_100_docs_20_queries.json")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_texts = data["documents"]
    queries = data["queries"]

    doc_words = [len(t.split()) for t in doc_texts]
    query_words = [len(q.split()) for q in queries]
    print(f"Loaded 100 STIX docs: mean={sum(doc_words)/len(doc_words):.1f} words, max={max(doc_words)} words.")
    print(f"Loaded 20 queries: mean={sum(query_words)/len(query_words):.1f} words, max={max(query_words)} words.")

    candidates = [
        "nomic-ai/nomic-embed-text-v1.5",
        "nomic-ai/modernbert-embed-base",
    ]

    timing_results = {}

    for model_name in candidates:
        print(f"\n--- Testing Candidate: {model_name} ---")
        try:
            from sentence_transformers import SentenceTransformer
            t0 = time.time()
            model = SentenceTransformer(model_name, trust_remote_code=True)
            load_time = time.time() - t0
            print(f"Model loaded in {load_time:.2f} s. Max context: {model.max_seq_length}")

            # Time 100 documents
            print("Encoding 100 documents on CPU...")
            t_docs = time.time()
            doc_embs = model.encode(doc_texts, batch_size=8, show_progress_bar=False)
            doc_time = time.time() - t_docs
            doc_time_per_item = doc_time / 100.0
            print(f"100 documents encoded in {doc_time:.2f} s ({doc_time_per_item:.4f} s/doc)")

            # Time 20 queries
            print("Encoding 20 queries on CPU...")
            t_queries = time.time()
            q_embs = model.encode(queries, batch_size=8, show_progress_bar=False)
            q_time = time.time() - t_queries
            q_time_per_item = q_time / 20.0
            print(f"20 queries encoded in {q_time:.2f} s ({q_time_per_item:.4f} s/query)")

            # Extrapolate for full benchmark
            # Full KB: 2,062 documents. 339 queries
            total_doc_extrap_s = doc_time_per_item * 2062
            total_query_extrap_s = q_time_per_item * 339
            total_projected_s = total_doc_extrap_s + total_query_extrap_s
            total_projected_hours = total_projected_s / 3600.0

            timing_results[model_name] = {
                "status": "success",
                "load_time_s": round(load_time, 2),
                "doc_time_100_s": round(doc_time, 2),
                "doc_time_per_item_s": round(doc_time_per_item, 4),
                "query_time_20_s": round(q_time, 2),
                "query_time_per_item_s": round(q_time_per_item, 4),
                "extrapolated_doc_embed_s": round(total_doc_extrap_s, 2),
                "extrapolated_query_embed_s": round(total_query_extrap_s, 2),
                "total_projected_hours": round(total_projected_hours, 2),
                "meets_2hr_budget": total_projected_hours <= 2.0,
            }
            print(f"Projected total runtime: {total_projected_hours:.2f} hours (Budget <= 2 hours: {total_projected_hours <= 2.0})")

        except Exception as e:
            print(f"FAILED {model_name}: {type(e).__name__}: {e}")
            timing_results[model_name] = {
                "status": "failed",
                "error": f"{type(e).__name__}: {e}",
            }

    out_file = Path("results/phase_2/b1_timing_benchmark.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(timing_results, f, indent=2)
    print(f"\nSaved timing benchmark results to {out_file}")


if __name__ == "__main__":
    test_b1_timing()
