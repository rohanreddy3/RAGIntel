"""Test Candidate Long-Context Embedding Models for Baseline B1 (Part B).

Tests:
1. nomic-ai/nomic-embed-text-v1.5 (8192 context)
2. nomic-ai/modernbert-embed-base (8192 context)
3. Alibaba-NLP/gte-modernbert-base (8192 context)

Evaluates on CPU in Python 3.12:
- Loading model
- Single-pass embedding on 3,000 words
- Memory, speed, dependencies, and error modes
"""

import sys
import time
from typing import Dict, Any


def run_b1_benchmark():
    print("=" * 70)
    print("BASELINE B1 LONG-CONTEXT MODEL TRIAL (Python 3.12 CPU)")
    print(f"Python: {sys.version}")
    print("=" * 70)

    # 3,000-word synthetic threat intelligence text
    base_sentence = "The threat actor utilized PowerShell and command interpreters to execute malicious scripts, establish persistence via registry keys, and exfiltrate sensitive files over encrypted HTTPS channels. "
    synthetic_3000_words = (base_sentence * 150)[:20000]
    word_count = len(synthetic_3000_words.split())
    print(f"Benchmark input text length: {word_count} words ({len(synthetic_3000_words)} chars)")

    candidates = [
        ("nomic-ai/nomic-embed-text-v1.5", {"trust_remote_code": True}),
        ("nomic-ai/modernbert-embed-base", {"trust_remote_code": True}),
        ("Alibaba-NLP/gte-modernbert-base", {"trust_remote_code": True}),
    ]

    results = {}

    for model_name, kwargs in candidates:
        print(f"\n--- Testing Candidate: {model_name} ---")
        t0 = time.time()
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading {model_name}...")
            model = SentenceTransformer(model_name, **kwargs)
            load_time = time.time() - t0
            print(f"Loaded successfully in {load_time:.2f} s. Model max_seq_length: {model.max_seq_length}")

            print(f"Encoding 3,000 words on CPU...")
            t_infer = time.time()
            emb = model.encode([synthetic_3000_words], show_progress_bar=False)
            infer_time = time.time() - t_infer
            print(f"Encoded shape: {emb.shape} in {infer_time:.2f} s")

            results[model_name] = {
                "status": "success",
                "load_time_s": round(load_time, 2),
                "infer_time_s": round(infer_time, 2),
                "max_seq_length": model.max_seq_length,
                "embedding_dim": int(emb.shape[1]),
            }
        except Exception as e:
            elapsed = time.time() - t0
            print(f"FAILED {model_name} after {elapsed:.2f} s: {type(e).__name__}: {e}")
            results[model_name] = {
                "status": "failed",
                "elapsed_s": round(elapsed, 2),
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    print("\n" + "=" * 70)
    print("B1 CANDIDATE TRIAL SUMMARY:")
    for k, v in results.items():
        print(f"  {k}: {v['status']} | {v}")
    print("=" * 70)


if __name__ == "__main__":
    run_b1_benchmark()
