"""Phase 2 Live API Smoke Test Script (Part E).

Evaluates 4 rows of CTI-ATE (queries 0..3) with gemini-3.5-flash-lite:
- Sequential execution (max_workers=1)
- 5.0s request pacing
- Zero client-side retries (max_retries=0)
- Hard budget cap: 70 API calls total
- Halts immediately upon the first HTTP 429
- Evaluates ALL 6 RAGAS metrics:
  1. faithfulness
  2. answer_relevancy
  3. context_recall
  4. context_precision
  5. factual_correctness
  6. noise_sensitivity
- Evaluates offline answer scoring (Part D2) on the same 4 rows for side-by-side comparison
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure ragas compatibility monkeypatch is loaded
import src.ragas_patch

from src.offline_guard import assert_offline_compliant
from src.data_loader import load_benchmark_dataset, load_stix_bundle
from src.retriever import HybridSTIXRetriever
from src.offline_answer_scorer import score_technique_extraction_response
from src.manifest import generate_experiment_manifest


class MonitoredLLMWrapper:
    """Wrapper around LangChain ChatGoogleGenerativeAI to strictly count calls, pace requests, and catch 429s."""

    def __init__(self, base_llm: Any, max_calls: int = 70, pace_seconds: float = 5.0):
        self.base_llm = base_llm
        self.max_calls = max_calls
        self.pace_seconds = pace_seconds
        self.call_count = 0
        self.generation_calls = 0
        self.judge_calls = 0
        self.last_429_headers = None
        self.last_429_error = None
        self.token_usage: List[Dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base_llm, name)

    def _extract_headers(self, e: Exception) -> Dict[str, Any]:
        headers = {}
        for attr in ["response", "raw_response", "http_response"]:
            resp = getattr(e, attr, None)
            if resp is not None and hasattr(resp, "headers"):
                headers.update(dict(resp.headers))
        if not headers and hasattr(e, "headers"):
            headers.update(dict(getattr(e, "headers")))
        return headers

    def _check_and_raise_429(self, e: Exception, method_name: str):
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            self.last_429_error = err_str
            self.last_429_headers = self._extract_headers(e)
            print(f"\n[HTTP 429 ENCOUNTERED in {method_name} at call {self.call_count}]: {err_str}")
            print(f"Captured headers: {self.last_429_headers}")
            raise RuntimeError(f"HTTP_429_RESOURCE_EXHAUSTED: {err_str}") from e
        raise e

    def invoke(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        time.sleep(self.pace_seconds)
        try:
            resp = self.base_llm.invoke(*args, **kwargs)
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                self.token_usage.append(resp.usage_metadata)
            return resp
        except Exception as e:
            self._check_and_raise_429(e, "invoke")

    async def ainvoke(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        await asyncio.sleep(self.pace_seconds)
        try:
            resp = await self.base_llm.ainvoke(*args, **kwargs)
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                self.token_usage.append(resp.usage_metadata)
            return resp
        except Exception as e:
            self._check_and_raise_429(e, "ainvoke")

    def generate(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        time.sleep(self.pace_seconds)
        try:
            return self.base_llm.generate(*args, **kwargs)
        except Exception as e:
            self._check_and_raise_429(e, "generate")

    async def agenerate(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        await asyncio.sleep(self.pace_seconds)
        try:
            return await self.base_llm.agenerate(*args, **kwargs)
        except Exception as e:
            self._check_and_raise_429(e, "agenerate")

    def generate_prompt(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        time.sleep(self.pace_seconds)
        try:
            return self.base_llm.generate_prompt(*args, **kwargs)
        except Exception as e:
            self._check_and_raise_429(e, "generate_prompt")

    async def agenerate_prompt(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        await asyncio.sleep(self.pace_seconds)
        try:
            return await self.base_llm.agenerate_prompt(*args, **kwargs)
        except Exception as e:
            self._check_and_raise_429(e, "agenerate_prompt")


def run_phase2_smoke():
    print("=" * 70)
    print("PHASE 2 LIVE API SMOKE TEST (4 ROWS OF CTI-ATE, 6 RAGAS METRICS)")
    print("=" * 70)

    # 1. Offline guard check
    try:
        assert_offline_compliant("Phase 2 API Smoke Test")
    except RuntimeError as e:
        print(f"\n[OFFLINE GUARD ACTIVE] {e}")
        print("To run Phase 2 smoke test, invoke with OFFLINE_ONLY=false:")
        print("  powershell -Command \"$env:OFFLINE_ONLY='false'; .\\venv\\Scripts\\python scripts/run_phase2_smoke_api.py\"")
        print("=" * 70)
        return

    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY is not set.")
        return

    import tenacity
    from langchain_google_genai import ChatGoogleGenerativeAI
    from ragas import evaluate
    from ragas.run_config import RunConfig
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_recall,
        context_precision,
        FactualCorrectness,
        NoiseSensitivity,
    )
    factual_correctness = FactualCorrectness()
    noise_sensitivity = NoiseSensitivity()
    from datasets import Dataset

    # 2. Setup monitored LLM with gemini-3.5-flash-lite, 0 retries, paced to 12 RPM max
    raw_llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        google_api_key=api_key,
        temperature=0.0,
        max_retries=0,
    )
    raw_llm.async_client._api_client._async_retry = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(1), reraise=True
    )
    raw_llm.client._api_client._async_retry = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(1), reraise=True
    )

    monitored_llm = MonitoredLLMWrapper(raw_llm, max_calls=70, pace_seconds=5.0)

    # 3. Retriever
    print("\nLoading STIX Knowledge Base & Initializing Retriever...")
    kb = load_stix_bundle()
    retriever = HybridSTIXRetriever(stix_kb=kb, enable_query_chunking=True)

    # 4. Load exactly 4 rows of cti-ate (queries 0..3)
    ate = load_benchmark_dataset("cti-ate")
    num_samples = 4
    smoke_samples = []
    for i in range(num_samples):
        smoke_samples.append({
            "idx": i,
            "query": str(ate.df.iloc[i]["query"]),
            "ground_truth": str(ate.df.iloc[i]["ground_truth"]),
        })

    print(f"Loaded {len(smoke_samples)} samples from CTI-ATE (rows 0..3).")

    eval_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }

    generation_records = []
    print("\n--- Generating Threat Analysis Responses with gemini-3.5-flash-lite ---")
    gen_start_time = time.time()
    generation_start_calls = monitored_llm.call_count

    try:
        for s in smoke_samples:
            idx = s["idx"]
            q = s["query"]
            gt = s["ground_truth"]

            t_ret = time.time()
            docs = retriever.retrieve(q, top_k=3)
            ret_lat = time.time() - t_ret
            contexts = [d.page_content for d in docs]
            ctx_text = "\n\n---\n\n".join(contexts)

            prompt = (
                f"You are a cybersecurity expert analyzing cyber threat intelligence.\n"
                f"Context from MITRE ATT&CK:\n{ctx_text}\n\n"
                f"Threat Report / Query: {q}\n\n"
                f"Identify and list all MITRE ATT&CK techniques, tactics, and procedures used in this threat report."
            )

            t_gen = time.time()
            resp = monitored_llm.invoke(prompt)
            gen_lat = time.time() - t_gen

            if isinstance(resp.content, list):
                ans = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in resp.content])
            else:
                ans = str(resp.content)

            eval_data["question"].append(q)
            eval_data["answer"].append(ans)
            eval_data["contexts"].append(contexts)
            eval_data["ground_truth"].append(gt)

            # Offline score immediately
            offline_score = score_technique_extraction_response(ans, gt)

            generation_records.append({
                "row_idx": idx,
                "query": q,
                "ground_truth": gt,
                "answer": ans,
                "retrieval_latency_s": round(ret_lat, 2),
                "generation_latency_s": round(gen_lat, 2),
                "offline_metrics": offline_score,
            })

            print(f"  Row {idx + 1}/4: Generated {len(ans)} chars in {gen_lat:.2f}s | Offline F1: {offline_score['f1']:.4f} (Calls: {monitored_llm.call_count})")

        gen_calls = monitored_llm.call_count - generation_start_calls
        monitored_llm.generation_calls = gen_calls
        print(f"Generation phase complete. Total generation calls: {gen_calls}")

        # 5. Run RAGAS evaluate with all 6 metrics
        print("\n--- Running RAGAS Evaluation (ALL 6 METRICS, max_workers=1) ---")
        judge_start_calls = monitored_llm.call_count
        hf_dataset = Dataset.from_dict(eval_data)
        metrics = [
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision,
            factual_correctness,
            noise_sensitivity,
        ]

        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        ragas_llm = LangchainLLMWrapper(monitored_llm)
        ragas_emb = LangchainEmbeddingsWrapper(retriever.embeddings)

        run_config = RunConfig(max_workers=1, max_retries=0, timeout=180)

        results = evaluate(
            hf_dataset,
            metrics=metrics,
            llm=ragas_llm,
            embeddings=ragas_emb,
            run_config=run_config,
        )

        judge_calls = monitored_llm.call_count - judge_start_calls
        monitored_llm.judge_calls = judge_calls
        total_calls = monitored_llm.call_count

        df_res = results.to_pandas()
        results_dir = Path("results/phase_2")
        results_dir.mkdir(parents=True, exist_ok=True)
        results_csv = results_dir / "ragas_phase2_smoke_results.csv"
        df_res.to_csv(results_csv, index=False)

        print("\n" + "=" * 70)
        print("RAGAS PHASE 2 SMOKE TEST RESULTS (4 ROWS, ALL 6 METRICS)")
        print("=" * 70)
        metric_cols = [
            "faithfulness",
            "answer_relevancy",
            "context_recall",
            "context_precision",
            "factual_correctness",
            "noise_sensitivity",
        ]
        ragas_summary = {}
        for m in metric_cols:
            if m in df_res.columns:
                mean_val = float(df_res[m].mean())
                nan_cnt = int(df_res[m].isna().sum())
                ragas_summary[m] = {"mean": round(mean_val, 4), "nans": nan_cnt}
                print(f"  {m:22s}: Mean = {mean_val:.4f} | NaNs/Failures = {nan_cnt}/4")

        calls_per_row = total_calls / num_samples
        print(f"\nAPI Call Accounting:")
        print(f"  Generation calls: {gen_calls}")
        print(f"  Judge calls:      {judge_calls}")
        print(f"  Total API calls:  {total_calls} / 70 max budget")
        print(f"  Calls per row:    {calls_per_row:.2f} calls/row")

        # Save summary JSON
        summary_out = results_dir / "ragas_phase2_smoke_summary.json"
        with open(summary_out, "w", encoding="utf-8") as f:
            json.dump({
                "model": "gemini-3.5-flash-lite",
                "num_rows": num_samples,
                "total_calls": total_calls,
                "generation_calls": gen_calls,
                "judge_calls": judge_calls,
                "calls_per_row": calls_per_row,
                "ragas_summary": ragas_summary,
                "generation_records": generation_records,
                "token_usage_samples": monitored_llm.token_usage[:4],
            }, f, indent=2)

        # Generate manifest
        manifest_path = generate_experiment_manifest(results_dir, "manifest_phase2_smoke.json")
        print(f"Saved results to {results_csv} and manifest to {manifest_path}")

    except Exception as e:
        print(f"\n[EXECUTION HALTED / ERROR]: {type(e).__name__}: {e}")
        if monitored_llm.last_429_error:
            print(f"Captured HTTP 429 Error: {monitored_llm.last_429_error}")
            print(f"Captured 429 Headers: {monitored_llm.last_429_headers}")
        raise


if __name__ == "__main__":
    run_phase2_smoke()
