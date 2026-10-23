"""Deferred RAGAS Smoke Test Script (Step 8: Baseline Lock + Smoke Test).

Evaluates 5 rows of CTI-ATE using gemini-3.5-flash-lite:
- Best available retriever: HybridSTIXRetriever(enable_query_chunking=True)
- Max 40 calls total
- Intercepts and halts at the first HTTP 429 (captures headers, no retry loop)
- Tracks exact calls made per metric, NaN/parse failures, measured calls per row
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

# Ensure ragas compatibility monkeypatch is active
import src

from src.offline_guard import assert_offline_compliant
from src.data_loader import load_benchmark_dataset, load_stix_bundle
from src.retriever import HybridSTIXRetriever


class MonitoredLLMWrapper:
    """Wrapper around LangChain ChatGoogleGenerativeAI to strictly count calls, pace requests, and catch 429s."""

    def __init__(self, base_llm: Any, max_calls: int = 40, pace_seconds: float = 5.0):
        self.base_llm = base_llm
        self.max_calls = max_calls
        self.pace_seconds = pace_seconds
        self.call_count = 0
        self.generation_calls = 0
        self.judge_calls = 0
        self.last_429_headers = None
        self.last_429_error = None
        self.failing_outputs: List[Dict[str, Any]] = []

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
            return self.base_llm.invoke(*args, **kwargs)
        except Exception as e:
            self._check_and_raise_429(e, "invoke")

    async def ainvoke(self, *args, **kwargs) -> Any:
        if self.call_count >= self.max_calls:
            raise RuntimeError(f"MAX_CALLS_REACHED: Reached hard cap of {self.max_calls} API calls.")
        self.call_count += 1
        await asyncio.sleep(self.pace_seconds)
        try:
            return await self.base_llm.ainvoke(*args, **kwargs)
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


def run_deferred_smoke():
    print("=" * 65)
    print("PHASE 1c: DEFERRED RAGAS SMOKE TEST (5 ROWS OF CTI-ATE)")
    print("=" * 65)

    # 1. Offline guard check
    try:
        assert_offline_compliant("RAGAS Deferred Smoke Test")
    except RuntimeError as e:
        print(f"\n[OFFLINE GUARD ACTIVE] {e}")
        print("To run step 8, invoke with OFFLINE_ONLY=false:")
        print("  powershell -Command \"$env:OFFLINE_ONLY='false'; .\\venv\\Scripts\\python scripts/run_deferred_smoke.py\"")
        print("=" * 65)
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
    )
    from datasets import Dataset

    # 2. Setup monitored LLM with gemini-3.5-flash-lite, 0 retries, paced to 12 RPM max
    raw_llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        google_api_key=api_key,
        temperature=0.0,
        max_retries=0,
    )
    # Stop underlying client from retrying in loops on 429
    raw_llm.async_client._api_client._async_retry = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(1), reraise=True
    )
    raw_llm.client._api_client._async_retry = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(1), reraise=True
    )

    monitored_llm = MonitoredLLMWrapper(raw_llm, max_calls=40, pace_seconds=5.0)

    # 3. Best available retriever
    print("\nLoading STIX Knowledge Base & Initializing Retriever...")
    kb = load_stix_bundle()
    retriever = HybridSTIXRetriever(stix_kb=kb, enable_query_chunking=True)

    # 4. Load 5 rows of cti-ate
    ate = load_benchmark_dataset("cti-ate")
    num_samples = 5
    smoke_samples = []
    for i in range(num_samples):
        smoke_samples.append({
            "idx": i,
            "query": str(ate.df.iloc[i]["query"]),
            "ground_truth": str(ate.df.iloc[i]["ground_truth"]),
        })

    print(f"Loaded {len(smoke_samples)} samples from CTI-ATE.")

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    debug_log_path = logs_dir / "ragas_smoke_debug.log"

    eval_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }

    print("\n--- Generating Answers with gemini-3.5-flash-lite ---")
    generation_start_calls = monitored_llm.call_count

    try:
        with open(debug_log_path, "w", encoding="utf-8") as debug_file:
            for s in smoke_samples:
                idx = s["idx"]
                q = s["query"]
                gt = s["ground_truth"]
                docs = retriever.retrieve(q, top_k=3)
                contexts = [d.page_content for d in docs]
                ctx_text = "\n\n---\n\n".join(contexts)

                prompt = (
                    f"You are a cybersecurity expert analyzing cyber threat intelligence.\n"
                    f"Context from MITRE ATT&CK:\n{ctx_text}\n\n"
                    f"Threat Report / Query: {q}\n\n"
                    f"Identify and list all MITRE ATT&CK techniques, tactics, and procedures used in this threat report."
                )

                resp = monitored_llm.invoke(prompt)
                # Parse text content
                if isinstance(resp.content, list):
                    ans = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in resp.content])
                else:
                    ans = str(resp.content)

                eval_data["question"].append(q)
                eval_data["answer"].append(ans)
                eval_data["contexts"].append(contexts)
                eval_data["ground_truth"].append(gt)

                debug_file.write(f"=== Query {idx} ===\nQuery: {q[:100]}...\nAnswer:\n{ans}\n\n")
                print(f"  Row {idx + 1}/5: Generated {len(ans)} chars (Total API calls so far: {monitored_llm.call_count})")

        gen_calls = monitored_llm.call_count - generation_start_calls
        monitored_llm.generation_calls = gen_calls
        print(f"Generation phase complete. Calls made: {gen_calls}")

        # 5. Run RAGAS evaluate with max_workers=1 and max_retries=0
        print("\n--- Running RAGAS Evaluation (4 metrics, sequential max_workers=1) ---")
        judge_start_calls = monitored_llm.call_count
        hf_dataset = Dataset.from_dict(eval_data)
        metrics = [faithfulness, answer_relevancy, context_recall, context_precision]

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
        results_path = Path("results/phase_1/ragas_deferred_smoke_results.csv")
        results_path.parent.mkdir(parents=True, exist_ok=True)
        df_res.to_csv(results_path, index=False)

        print("\n" + "=" * 65)
        print("RAGAS SMOKE TEST RESULTS (5 ROWS)")
        print("=" * 65)
        metric_cols = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
        failing_info = {}
        for m in metric_cols:
            mean_val = df_res[m].mean()
            nan_cnt = int(df_res[m].isna().sum())
            print(f"  {m:20s}: Mean = {mean_val:.4f} | NaNs/Parse Failures = {nan_cnt}/5")
            if nan_cnt > 0:
                failing_rows = df_res[df_res[m].isna()]
                failing_idx = int(failing_rows.index[0])
                q_col = "user_input" if "user_input" in df_res.columns else "question"
                a_col = "response" if "response" in df_res.columns else "answer"
                sample_fail = {
                    "row_index": failing_idx,
                    "question": str(df_res.iloc[failing_idx][q_col])[:150],
                    "answer": str(df_res.iloc[failing_idx][a_col])[:150],
                }
                failing_info[m] = sample_fail
                print(f"    Sample failing row for {m}: row {failing_idx}")
                print(f"    Question snippet: {sample_fail['question']}...")

        calls_per_row = total_calls / num_samples
        print(f"\nAPI Call Accounting:")
        print(f"  Generation calls : {gen_calls}")
        print(f"  Judge calls      : {judge_calls}")
        print(f"  Total API calls  : {total_calls} (Cap: 40)")
        print(f"  Measured calls/row: {calls_per_row:.2f} calls per evaluated query")

        # Save summary JSON
        summary = {
            "status": "COMPLETED",
            "model": "gemini-3.5-flash-lite",
            "samples": num_samples,
            "total_calls": total_calls,
            "generation_calls": gen_calls,
            "judge_calls": judge_calls,
            "calls_per_row": calls_per_row,
            "metrics": {
                m: {
                    "mean": round(float(df_res[m].mean()), 4) if not df_res[m].isna().all() else None,
                    "nan_count": int(df_res[m].isna().sum()),
                }
                for m in metric_cols
            },
        }
        with open("results/phase_1/ragas_smoke_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print(f"\nSummary saved to results/phase_1/ragas_smoke_summary.json")

    except Exception as e:
        err_msg = str(e)
        print(f"\n[SMOKE TEST HALTED]: {err_msg}")
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            # Write to DEFERRED_API_TASKS.md as requested
            def_path = Path("reviews/DEFERRED_API_TASKS.md")
            def_content = (
                f"# DEFERRED API TASKS\n\n"
                f"### Task: Phase 1c Deferred Smoke Test (scripts/run_deferred_smoke.py)\n"
                f"- **Status**: SKIPPED (Quota Exhausted / HTTP 429)\n"
                f"- **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
                f"- **Model**: `gemini-3.5-flash-lite`\n"
                f"- **Exact Error**: `{err_msg}`\n"
                f"- **Response Headers Captured**: `{monitored_llm.last_429_headers}`\n"
                f"- **Exact Command to Resume**:\n"
                f"  ```powershell\n"
                f"  $env:OFFLINE_ONLY='false'; .\\venv\\Scripts\\python scripts/run_deferred_smoke.py\n"
                f"  ```\n"
            )
            def_path.write_text(def_content, encoding="utf-8")
            print(f"Recorded failure and resume command in {def_path}")
        raise e


if __name__ == "__main__":
    run_deferred_smoke()
