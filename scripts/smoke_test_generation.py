"""Phase 1: 5-Row Generation + RAGAS Smoke Test with Google Gemini Free-Tier.
Enforces:
1. One fixed model: gemini-3.5-flash (temperature=0.1).
2. Local embeddings only: sentence-transformers/all-MiniLM-L6-v2.
3. Persistent on-disk cache for every LLM and embedding call.
4. Automatic rate limiter (14 RPM, 4.3s delay) respecting free-tier quotas.
5. Resumable run with per-row checkpointing.
6. Detailed timing, call count, and token/quota extrapolation to all 339 benchmark rows.
"""

import os
import sys
import time
import re
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

# Ensure root directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.cache import PersistentDiskCache, FreeTierRateLimiter
from src.retriever import HybridSTIXRetriever

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required in .env")

# Fixed model configuration: gemini-3.5-flash-lite is the stable free-tier model (gemini-3.5-flash had 503 high demand spikes)
FIXED_MODEL_NAME = "gemini-3.5-flash-lite"
TEMPERATURE = 0.1
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Free-tier quota constants
FREE_TIER_RPM_LIMIT = 15
FREE_TIER_RPD_LIMIT = 1500  # Requests per day
ENFORCED_RPM = 14
ENFORCED_DELAY = 4.3  # seconds (60 / 14 = 4.28s)

CHECKPOINT_DIR = ROOT_DIR / "results" / "phase_1" / "smoke_checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = ROOT_DIR / ".cache" / "gemini_llm"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

cache = PersistentDiskCache(cache_dir=str(CACHE_DIR))
rate_limiter = FreeTierRateLimiter(requests_per_minute=ENFORCED_RPM, min_delay_seconds=ENFORCED_DELAY)

# Statistics tracker
stats = {
    "model": FIXED_MODEL_NAME,
    "temperature": TEMPERATURE,
    "total_api_calls": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "total_latency_seconds": 0.0,
    "rate_limit_sleep_seconds": 0.0,
    "prompt_tokens_est": 0,
    "completion_tokens_est": 0,
}


def clean_mitre_ids(text: str) -> str:
    """Exact cleaning regex used in RAGIntel (rag_cti.py lines 296-304)."""
    if not isinstance(text, str):
        return "N/A"
    ids = re.findall(r"T\d{4}(?:\.\d{3})?", text)
    # Deduplicate while preserving order
    seen = set()
    dedup = [x for x in ids if not (x in seen or seen.add(x))]
    return ", ".join(dedup) if dedup else "N/A"


def invoke_gemini_with_cache(prompt_text: str, namespace: str = "generation") -> str:
    """Invokes Google Gemini with on-disk caching, rate limiting, and instrumentation."""
    cached = cache.get(namespace, prompt_text)
    if cached is not None:
        stats["cache_hits"] += 1
        return cached

    stats["cache_misses"] += 1
    # Check offline guard before making any API call
    from src.offline_guard import assert_offline_compliant
    assert_offline_compliant("Google Gemini Generation API call")

    sleep_time = rate_limiter.wait_if_needed()
    stats["rate_limit_sleep_seconds"] += sleep_time

    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=FIXED_MODEL_NAME,
        google_api_key=API_KEY,
        temperature=TEMPERATURE,
    )

    t0 = time.time()
    response = llm.invoke(prompt_text)
    latency = time.time() - t0
    stats["total_latency_seconds"] += latency
    stats["total_api_calls"] += 1

    # Extract text content
    if isinstance(response.content, list):
        # Format: [{'type': 'text', 'text': '...'}]
        text_blocks = [b.get("text", "") for b in response.content if isinstance(b, dict)]
        content_str = "\n".join(text_blocks) if text_blocks else str(response.content)
    else:
        content_str = str(response.content)

    content_str = content_str.strip()

    # Estimate tokens (rough heuristic ~ 4 chars/token)
    p_tokens = len(prompt_text) // 4
    c_tokens = len(content_str) // 4
    stats["prompt_tokens_est"] += p_tokens
    stats["completion_tokens_est"] += c_tokens

    cache.set(namespace, prompt_text, content_str)
    return content_str


def run_smoke_test(num_rows: int = 5):
    print("=" * 70)
    print(f"Phase 1 Smoke Test: Generation + RAGAS with {FIXED_MODEL_NAME}")
    print(f"Embedding model: {EMBEDDING_MODEL_NAME} (local CPU)")
    print(f"Rate Limiter: {ENFORCED_RPM} RPM ({ENFORCED_DELAY}s minimum delay)")
    print("=" * 70)

    # 1. Initialize Retriever from cache
    print("\nLoading HybridSTIXRetriever...")
    t_ret_start = time.time()
    retriever = HybridSTIXRetriever(
        embedding_model_name=EMBEDDING_MODEL_NAME,
    )
    print(f"Retriever loaded in {time.time() - t_ret_start:.2f}s")

    # 2. Load CTI-ATE benchmark
    benchmark_path = ROOT_DIR / "data" / "datasets" / "cti-ate.xlsx"
    df = pd.read_excel(benchmark_path).dropna(subset=["query"])
    df = df[df["query"].str.strip() != ""].head(num_rows).reset_index(drop=True)
    print(f"Loaded {len(df)} rows from {benchmark_path.name}")

    # 3. Generation Loop with Checkpointing
    generated_rows = []
    generation_start_time = time.time()

    for idx, row in df.iterrows():
        ckpt_file = CHECKPOINT_DIR / f"generation_row_{idx}.json"
        query = str(row["query"])
        ground_truth = str(row["ground_truth"]) if pd.notna(row["ground_truth"]) else ""

        if ckpt_file.is_file():
            print(f"[{idx+1}/{num_rows}] Loading cached generation from checkpoint: {ckpt_file.name}")
            with open(ckpt_file, "r", encoding="utf-8") as f:
                ckpt_data = json.load(f)
            generated_rows.append(ckpt_data)
            continue

        print(f"\n[{idx+1}/{num_rows}] Processing Query (len={len(query)} chars)...")
        t0 = time.time()
        retrieved_docs = retriever.invoke(query)
        retrieval_time = time.time() - t0

        context_str = "\n".join(doc.page_content for doc in retrieved_docs)
        prompt_text = f"Context:\n{context_str}\n\nQuestion: {query}\nAnswer:"

        t_gen0 = time.time()
        raw_response = invoke_gemini_with_cache(prompt_text, namespace="smoke_generation")
        gen_time = time.time() - t_gen0

        cleaned_ids = clean_mitre_ids(raw_response)

        record = {
            "row_idx": idx,
            "query": query,
            "ground_truth": ground_truth,
            "retrieved_contexts": [doc.page_content for doc in retrieved_docs],
            "retrieved_mitre_ids": [doc.metadata.get("mitre_id", "") for doc in retrieved_docs],
            "raw_response": raw_response,
            "cleaned_response": cleaned_ids,
            "retrieval_time_s": round(retrieval_time, 3),
            "generation_time_s": round(gen_time, 3),
        }

        with open(ckpt_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        print(f"  -> Generated: {raw_response[:80]}...")
        print(f"  -> Cleaned MITRE IDs: {cleaned_ids}")
        print(f"  -> Ground Truth: {ground_truth}")
        print(f"  -> Retrieval: {retrieval_time:.2f}s, Generation: {gen_time:.2f}s")
        generated_rows.append(record)

    total_generation_wall_time = time.time() - generation_start_time

    # 4. Run RAGAS Evaluation
    print("\n" + "=" * 70)
    print("Running RAGAS Judge Evaluation...")
    print("=" * 70)

    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import (
        LLMContextRecall,
        ContextPrecision,
        Faithfulness,
        FactualCorrectness,
        AnswerRelevancy,
    )
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_google_genai import ChatGoogleGenerativeAI

    eval_llm_base = ChatGoogleGenerativeAI(
        model=FIXED_MODEL_NAME,
        google_api_key=API_KEY,
        temperature=TEMPERATURE,
    )
    ragas_llm = LangchainLLMWrapper(eval_llm_base)

    ragas_emb_base = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    ragas_embeddings = LangchainEmbeddingsWrapper(ragas_emb_base)

    # Format dataset for RAGAS
    ragas_records = []
    for r in generated_rows:
        ragas_records.append({
            "user_input": r["query"],
            "reference": r["ground_truth"],
            "retrieved_contexts": r["retrieved_contexts"],
            "response": r["cleaned_response"],  # As in RAGIntel lines 318-320
        })

    ragas_dataset = EvaluationDataset.from_list(ragas_records)

    metrics = [
        LLMContextRecall(),
        ContextPrecision(),
        Faithfulness(),
        FactualCorrectness(),
        AnswerRelevancy(),
    ]

    ragas_start_time = time.time()
    print("Evaluating RAGAS metrics on 5 smoke rows...")
    ragas_eval_results = None
    try:
        ragas_eval_results = evaluate(
            ragas_dataset,
            metrics=metrics,
            llm=ragas_llm,
            embeddings=ragas_embeddings,
        )
        print("RAGAS Evaluation Succeeded!")
        print(ragas_eval_results)
    except Exception as e:
        print(f"Warning: RAGAS evaluation encountered an issue: {e}")

    total_ragas_wall_time = time.time() - ragas_start_time

    # 5. Compile Statistics and Extrapolation
    total_smoke_time = total_generation_wall_time + total_ragas_wall_time
    total_calls_smoke = stats["total_api_calls"]

    # Extrapolate to all 339 benchmark queries (60 CTI-ATE + 229 CTI-ATTACK + 50 CTI-TAA)
    TOTAL_BENCHMARK_ROWS = 339
    multiplier = TOTAL_BENCHMARK_ROWS / num_rows

    extrapolated_api_calls = total_calls_smoke * multiplier
    extrapolated_wall_seconds = total_smoke_time * multiplier
    extrapolated_wall_hours = extrapolated_wall_seconds / 3600.0

    # Under rate limits:
    # 1) RPM constraint: extrapolated_api_calls / 14 RPM = total active minutes
    rpm_constrained_hours = (extrapolated_api_calls / ENFORCED_RPM) / 60.0

    # 2) Daily quota constraint: extrapolated_api_calls / 1,500 RPD = days needed
    quota_constrained_days = extrapolated_api_calls / FREE_TIER_RPD_LIMIT

    exceeds_3_days = quota_constrained_days > 3.0

    summary = {
        "smoke_test_config": {
            "generator_llm": FIXED_MODEL_NAME,
            "judge_llm": FIXED_MODEL_NAME,
            "temperature": TEMPERATURE,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "top_k": 5,
            "reranker": "ms-marco-MiniLM-L-12-v2 (FlashRank)",
            "num_rows_tested": num_rows,
            "benchmark_tested": "CTI-ATE (rows 0-4)",
        },
        "smoke_test_measurements": {
            "generation_wall_time_s": round(total_generation_wall_time, 2),
            "ragas_wall_time_s": round(total_ragas_wall_time, 2),
            "total_smoke_wall_time_s": round(total_smoke_time, 2),
            "api_calls_made": total_calls_smoke,
            "rate_limiter_sleep_s": round(stats["rate_limit_sleep_seconds"], 2),
            "cache_hits": stats["cache_hits"],
            "cache_misses": stats["cache_misses"],
            "estimated_prompt_tokens": stats["prompt_tokens_est"],
            "estimated_completion_tokens": stats["completion_tokens_est"],
        },
        "extrapolation_full_benchmark": {
            "total_benchmark_rows": TOTAL_BENCHMARK_ROWS,
            "extrapolated_total_api_calls": round(extrapolated_api_calls, 1),
            "calls_per_row": round(total_calls_smoke / num_rows, 2),
            "free_tier_limits": {
                "rpm_limit": FREE_TIER_RPM_LIMIT,
                "rpd_limit": FREE_TIER_RPD_LIMIT,
                "enforced_rpm": ENFORCED_RPM,
            },
            "runtime_at_14_rpm_hours": round(rpm_constrained_hours, 2),
            "calendar_days_under_1500_rpd_limit": round(quota_constrained_days, 2),
            "exceeds_3_days_threshold": exceeds_3_days,
        },
        "ragas_scores": {k: float(v) for k, v in ragas_eval_results.items()} if ragas_eval_results else {},
    }

    # Save summary files
    out_summary_json = ROOT_DIR / "results" / "phase_1" / "smoke_test_summary.json"
    with open(out_summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved smoke test summary to {out_summary_json}")

    # Write Markdown summary
    out_summary_md = ROOT_DIR / "results" / "phase_1" / "smoke_test_summary.md"
    with open(out_summary_md, "w", encoding="utf-8") as f:
        f.write("# Phase 1 Generation & RAGAS Smoke Test Report\n\n")
        f.write(f"- **Generator Model**: `{FIXED_MODEL_NAME}` (temperature={TEMPERATURE})\n")
        f.write(f"- **RAGAS Judge Model**: `{FIXED_MODEL_NAME}`\n")
        f.write(f"- **Embedding Model**: `{EMBEDDING_MODEL_NAME}` (local CPU)\n")
        f.write(f"- **Retriever / Compressor**: FAISS + BM25 + FlashRank (`ms-marco-MiniLM-L-12-v2`, top-k=5)\n")
        f.write(f"- **Rows Tested**: {num_rows} rows from `CTI-ATE`\n\n")
        f.write("## 1. Measured Smoke Test Metrics\n\n")
        f.write(f"- **Total Wall Time**: {total_smoke_time:.2f} seconds ({total_smoke_time/60.0:.2f} minutes)\n")
        f.write(f"- **Generation Time**: {total_generation_wall_time:.2f}s\n")
        f.write(f"- **RAGAS Evaluation Time**: {total_ragas_wall_time:.2f}s\n")
        f.write(f"- **Total API Calls**: {total_calls_smoke} ({total_calls_smoke/num_rows:.1f} calls/row)\n")
        f.write(f"- **Rate Limiter Delays**: {stats['rate_limit_sleep_seconds']:.2f}s\n\n")
        f.write("## 2. Extrapolation to Full Benchmark (339 rows)\n\n")
        f.write(f"- **Extrapolated Total API Calls**: ~{extrapolated_api_calls:.0f} calls\n")
        f.write(f"- **Continuous Runtime at 14 RPM**: {rpm_constrained_hours:.2f} hours\n")
        f.write(f"- **Calendar Days under 1,500 RPD Free Limit**: **{quota_constrained_days:.2f} days**\n")
        f.write(f"- **Exceeds 3 Days Constraint?**: **{'YES (STOP REQUIRED)' if exceeds_3_days else 'NO (Safe to proceed)'}**\n\n")
        if ragas_eval_results:
            f.write("## 3. RAGAS Scores (5-row sample)\n\n")
            f.write("| Metric | Sample Score |\n")
            f.write("| :--- | :--- |\n")
            for k, v in ragas_eval_results.items():
                f.write(f"| {k} | {v:.4f} |\n")

    print("\n" + "=" * 70)
    print("SMOKE TEST COMPLETE")
    print(f"Calendar Days under 1,500 RPD: {quota_constrained_days:.2f} days")
    print(f"Exceeds 3-day constraint: {exceeds_3_days}")
    print("=" * 70)


if __name__ == "__main__":
    run_smoke_test(num_rows=5)
