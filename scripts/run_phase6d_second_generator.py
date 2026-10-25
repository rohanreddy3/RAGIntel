"""Phase 6D Part F: Second Generator Model Replication on cti-taa.

Pre-declared selection rule:
Newest Gemma or Flash-Lite model returned by API model listing != gemini-3.5-flash-lite.
Pre-declared model: models/gemini-3.1-flash-lite.

Runs on cti-taa (50 queries):
1. LLM-only (50 calls)
2. V0 (50 calls)
3. V0h (50 calls)
4. Vrel (50 calls)
Total: 200 calls.
Bare prompt, temperature=0.0, max_output_tokens=512, pacing=5.0s.
Evaluates whether the ranking of arms matches primary generator.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)
API_KEY = os.getenv("GOOGLE_API_KEY")

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from scripts.compute_phase6c_metrics import score_group_match

CACHE_DIR = REPO_ROOT / ".cache" / "api_runner_second_gen"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR = REPO_ROOT / "results" / "phase_6d"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LEDGER_CSV = OUT_DIR / "second_generator_ledger.csv"

SECOND_MODEL_ID = "models/gemini-3.1-flash-lite"
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = 512
PACING_SECONDS = 5.0


def log_ledger_entry(
    arm: str,
    row_idx: int,
    status: str,
    http_code: int,
    prompt_tokens: int,
    completion_tokens: int,
    latency_s: float,
    error_msg: str = "",
):
    header = not LEDGER_CSV.exists()
    entry = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": SECOND_MODEL_ID,
        "dataset": "cti-taa",
        "arm": arm,
        "row_idx": row_idx,
        "status": status,
        "http_code": http_code,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_s": round(latency_s, 3),
        "error_msg": error_msg,
    }
    df_entry = pd.DataFrame([entry])
    df_entry.to_csv(LEDGER_CSV, mode="a", header=header, index=False)


def call_second_gen(
    client: Any,
    prompt_text: str,
    arm: str,
    row_idx: int,
    contexts_used: List[str],
    dry_run: bool = False,
) -> Tuple[str, bool]:
    """Generate response with pacing, rate limiting, and caching."""
    cache_file = CACHE_DIR / f"{arm}_cti-taa_row_{row_idx}.json"
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            return cdata.get("raw_answer", ""), True
        except Exception:
            pass

    if dry_run:
        time.sleep(0.01)
        return f"[DRY_RUN_ANSWER for {SECOND_MODEL_ID} {arm} row {row_idx}]", False

    prompt_tokens_est = len(prompt_text) // 4
    time.sleep(PACING_SECONDS)

    t0 = time.time()
    try:
        resp = client.models.generate_content(
            model=SECOND_MODEL_ID,
            contents=prompt_text,
        )
        latency = time.time() - t0
        raw_ans = resp.text if hasattr(resp, "text") and resp.text else ""
        completion_tokens_est = len(raw_ans) // 4

        finish_reason = "UNKNOWN"
        if hasattr(resp, "candidates") and resp.candidates:
            finish_reason = str(resp.candidates[0].finish_reason)

        usage_dict = {}
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage_dict = {
                "prompt_token_count": getattr(resp.usage_metadata, "prompt_token_count", prompt_tokens_est),
                "candidates_token_count": getattr(resp.usage_metadata, "candidates_token_count", completion_tokens_est),
                "total_token_count": getattr(resp.usage_metadata, "total_token_count", prompt_tokens_est + completion_tokens_est),
            }
            p_tok = usage_dict["prompt_token_count"]
            c_tok = usage_dict["candidates_token_count"]
        else:
            p_tok = prompt_tokens_est
            c_tok = completion_tokens_est

        log_ledger_entry(
            arm=arm,
            row_idx=row_idx,
            status="SUCCESS",
            http_code=200,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            latency_s=latency,
            error_msg=f"finish_reason={finish_reason}",
        )
        print(f"[{SECOND_MODEL_ID} | {arm}] row {row_idx} completed ({latency:.2f}s)", flush=True)

        payload = {
            "model": SECOND_MODEL_ID,
            "arm": arm,
            "dataset": "cti-taa",
            "row_idx": row_idx,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "prompt_text": prompt_text,
            "contexts_used": contexts_used,
            "raw_answer": raw_ans,
            "finish_reason": finish_reason,
            "usage": usage_dict,
            "latency_s": round(latency, 3),
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return raw_ans, False

    except Exception as e:
        latency = time.time() - t0
        err_str = str(e)
        log_ledger_entry(
            arm=arm,
            row_idx=row_idx,
            status="ERROR",
            http_code=500,
            prompt_tokens=prompt_tokens_est,
            completion_tokens=0,
            latency_s=latency,
            error_msg=err_str[:200],
        )
        print(f"[{SECOND_MODEL_ID} | {arm}] row {row_idx} ERROR: {err_str[:100]}", flush=True)
        return "", False


def run_evaluation(dry_run: bool = False):
    print("=" * 80)
    print(f"PHASE 6D PART F: SECOND GENERATOR REPLICATION ({SECOND_MODEL_ID})")
    print("=" * 80)

    from google import genai
    client = genai.Client(api_key=API_KEY)

    # 1. Load cti-taa
    df_taa = load_benchmark_dataset("cti-taa").df
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()

    # 2. Load context sources
    # V0 context from Phase 3 api_runner cache
    v0_cache_dir = REPO_ROOT / ".cache" / "api_runner"
    # V0h and Vrel contexts from Phase 5 o1_top10_cache.json
    o1_cache_file = REPO_ROOT / "results" / "phase_5" / "o1_top10_cache.json"
    with open(o1_cache_file, "r", encoding="utf-8") as f:
        o1_cache = json.load(f)

    v0h_dict = o1_cache["B2"]["V0h"]
    vrel_dict = o1_cache["B2"]["Vrel"]

    arms_order = ["LLM_only", "V0", "V0h", "Vrel"]
    results_by_arm: Dict[str, List[str]] = {a: [] for a in arms_order}

    # Interleave rows across arms
    for row_idx, row in df_taa.iterrows():
        raw_query = str(row["query"])

        for arm in arms_order:
            contexts = []
            if arm == "LLM_only":
                prompt = f"Question: {raw_query}\nAnswer:"
            elif arm == "V0":
                # Load V0 contexts used in primary runner
                v0_file = v0_cache_dir / f"cti-taa_B2_V0_cti-taa_row_{row_idx}.json"
                if v0_file.is_file():
                    with open(v0_file, "r", encoding="utf-8") as f:
                        contexts = json.load(f).get("contexts_used", [])
                ctx_str = "\n".join(contexts)
                prompt = f"Context:\n{ctx_str}\n\nQuestion: {raw_query}\nAnswer:"
            elif arm == "V0h":
                contexts = [c["page_content"] for c in v0h_dict[str(row_idx)]]
                ctx_str = "\n".join(contexts)
                prompt = f"Context:\n{ctx_str}\n\nQuestion: {raw_query}\nAnswer:"
            elif arm == "Vrel":
                contexts = [c["page_content"] for c in vrel_dict[str(row_idx)]]
                ctx_str = "\n".join(contexts)
                prompt = f"Context:\n{ctx_str}\n\nQuestion: {raw_query}\nAnswer:"

            ans, _ = call_second_gen(
                client=client,
                prompt_text=prompt,
                arm=arm,
                row_idx=row_idx,
                contexts_used=contexts,
                dry_run=dry_run,
            )
            results_by_arm[arm].append(ans)

    # 3. Offline Scoring across all 4 scorers
    print("\n" + "=" * 80)
    print(f"OFFLINE SCORING FOR SECOND GENERATOR ({SECOND_MODEL_ID})")
    print("=" * 80)

    scores_summary = {}
    for arm in arms_order:
        v1_exact_scores, v1_alias_scores = [], []
        v2_exact_scores, v2_alias_scores = [], []

        for row_idx, row in df_taa.iterrows():
            gt = str(row.get("ground_truth", ""))
            ans = results_by_arm[arm][row_idx]

            sc = score_group_match(ans, gt, group_alias_map)
            v1_exact_scores.append(float(sc["v1_exact"]))
            v1_alias_scores.append(float(sc["v1_alias"]))
            v2_exact_scores.append(float(sc["v2_exact"]))
            v2_alias_scores.append(float(sc["v2_alias"]))

        scores_summary[arm] = {
            "v2_alias": round(float(np.mean(v2_alias_scores)), 4),
            "v2_exact": round(float(np.mean(v2_exact_scores)), 4),
            "v1_alias": round(float(np.mean(v1_alias_scores)), 4),
            "v1_exact": round(float(np.mean(v1_exact_scores)), 4),
        }
        print(
            f"Arm {arm:<10}: Primary v2_alias={scores_summary[arm]['v2_alias']:.4f}, "
            f"v2_exact={scores_summary[arm]['v2_exact']:.4f}, "
            f"v1_alias={scores_summary[arm]['v1_alias']:.4f}, "
            f"v1_exact={scores_summary[arm]['v1_exact']:.4f}"
        )

    # 4. Compare ranking to primary generator
    # Primary generator scores (gemini-3.5-flash-lite):
    # Vrel: 0.7600, V0h: 0.7400, LLM_only: 0.7200, V0: 0.6400
    primary_scores = {
        "Vrel": 0.7600,
        "V0h": 0.7400,
        "LLM_only": 0.7200,
        "V0": 0.6400,
    }
    primary_ranking = sorted(primary_scores.keys(), key=lambda k: primary_scores[k], reverse=True)
    second_ranking = sorted(arms_order, key=lambda k: scores_summary[k]["v2_alias"], reverse=True)

    ranking_match = (primary_ranking == second_ranking)
    print(f"\nPrimary Generator Ranking (gemini-3.5-flash-lite): {' > '.join(primary_ranking)}")
    print(f"Second Generator Ranking  ({SECOND_MODEL_ID}) : {' > '.join(second_ranking)}")
    print(f"Ranking exact match: {ranking_match}")

    comparison_record = {
        "primary_model": "models/gemini-3.5-flash-lite",
        "second_model": SECOND_MODEL_ID,
        "primary_ranking_v2_alias": primary_ranking,
        "second_ranking_v2_alias": second_ranking,
        "ranking_matches": ranking_match,
        "primary_scores_v2_alias": primary_scores,
        "second_scores_v2_alias": {k: scores_summary[k]["v2_alias"] for k in arms_order},
        "second_full_scores": scores_summary,
    }

    out_file = OUT_DIR / "second_generator_ranking_comparison.json"
    scores_file = OUT_DIR / "second_generator_scores.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(comparison_record, f, indent=2)
    with open(scores_file, "w", encoding="utf-8") as f:
        json.dump(scores_summary, f, indent=2)

    print(f"\nSaved ranking comparison to {out_file} and scores to {scores_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulate second generator")
    parser.add_argument("--test-live-1", action="store_true", help="Execute 1 live API call to test quota")
    parser.add_argument("--run", action="store_true", help="Run live calls")
    args = parser.parse_args()

    if args.dry_run:
        run_evaluation(dry_run=True)
    elif args.test_live_1:
        print(f"[SECOND GEN] Testing 1 live call with {SECOND_MODEL_ID}...")
        from google import genai
        client = genai.Client(api_key=API_KEY)
        ans, _ = call_second_gen(
            client=client,
            prompt_text="Question: Name a common threat actor.\nAnswer:",
            arm="PROBE_TEST",
            row_idx=0,
            contexts_used=[],
            dry_run=False,
        )
        print(f"[SECOND GEN] Probe answer: {ans}")
    elif args.run:
        run_evaluation(dry_run=False)
    else:
        print("Usage: python scripts/run_phase6d_second_generator.py [--dry-run | --test-live-1 | --run]")
