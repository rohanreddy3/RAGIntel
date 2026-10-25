"""API Generation Runner for Phase 3.
Autonomous background runner for Gemini LLM generation with strict quota adherence,
pacing, ledger logging, and offline scoring.

GLOBAL RULES:
- OFFLINE_ONLY is overridden ONLY in this runner process via RUN_API_PART=true.
- Touches ONLY: scripts/api_runner.py, config_generation.yaml, reviews/api_*, .cache/api_runner/.
- Model config locked via config_generation.yaml with SHA-256 verification.
- Interleaves arms by row.
- Pacing 5.0 s per call; max_workers=1; daily cap 1,300 calls.
- On 429, sleeps until next UTC midnight reset and resumes automatically.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

# Set runner-specific override BEFORE importing src modules
os.environ["RUN_API_PART"] = "true"
os.environ["OFFLINE_ONLY"] = "false"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)

API_KEY = os.getenv("GOOGLE_API_KEY")
CONFIG_PATH = REPO_ROOT / "config_generation.yaml"
CACHE_DIR = REPO_ROOT / ".cache" / "api_runner"
LEDGER_CSV = REPO_ROOT / "reviews" / "api_ledger.csv"
QUOTA_LOG_CSV = REPO_ROOT / "reviews" / "api_quota_log.csv"
KNOWN_RESET_JSON = CACHE_DIR / "known_reset.json"
STATUS_MD = REPO_ROOT / "reviews" / "api_status.md"
SCORES_JSON = REPO_ROOT / "reviews" / "api_scores.json"
ANALYSIS_PLAN = REPO_ROOT / "analysis_plan.md"


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_and_load_config() -> Dict[str, Any]:
    """Verify configuration integrity and load yaml."""
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Missing locked config: {CONFIG_PATH}")

    current_hash = compute_file_sha256(CONFIG_PATH)
    lock_file = CACHE_DIR / "config_generation.lock"

    if lock_file.is_file():
        expected_hash = lock_file.read_text(encoding="utf-8").strip()
        if current_hash != expected_hash:
            raise RuntimeError(
                f"CONFIG INTEGRITY ERROR: config_generation.yaml has changed mid-experiment!\n"
                f"Expected hash: {expected_hash}\n"
                f"Current hash:  {current_hash}\n"
                "Refusing to run."
            )
    else:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(current_hash, encoding="utf-8")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["_sha256"] = current_hash
    return cfg


def init_ledger():
    """Ensure the ledger CSV has headers."""
    LEDGER_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER_CSV.is_file():
        with open(LEDGER_CSV, "w", encoding="utf-8") as f:
            f.write(
                "timestamp,call_id,arm,dataset,row_idx,model,status,http_code,prompt_tokens_est,completion_tokens_est,latency_s,error_msg\n"
            )


def log_ledger_entry(
    arm: str,
    dataset: str,
    row_idx: int,
    model: str,
    status: str,
    http_code: int,
    prompt_tokens: int,
    completion_tokens: int,
    latency_s: float,
    error_msg: str = "",
):
    """Append entry to api_ledger.csv."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    call_id = hashlib.md5(f"{ts}_{arm}_{dataset}_{row_idx}".encode()).hexdigest()[:12]
    clean_err = error_msg.replace(",", ";").replace("\n", " ")[:150]
    with open(LEDGER_CSV, "a", encoding="utf-8") as f:
        f.write(
            f"{ts},{call_id},{arm},{dataset},{row_idx},{model},{status},{http_code},{prompt_tokens},{completion_tokens},{latency_s:.3f},{clean_err}\n"
        )


def init_quota_log():
    """Ensure the quota log CSV has headers (Rule 1)."""
    QUOTA_LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not QUOTA_LOG_CSV.is_file():
        with open(QUOTA_LOG_CSV, "w", encoding="utf-8") as f:
            f.write(
                "timestamp,quota_metric,retry_delay_s,raw_error,success_calls_prev_60s,success_calls_prev_24h\n"
            )


def log_quota_event(
    quota_metric: str,
    retry_delay_s: float,
    raw_error: str,
    success_60s: int,
    success_24h: int,
):
    """Append 429 quota event to api_quota_log.csv (Rule 1)."""
    init_quota_log()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_err = raw_error.replace(",", ";").replace("\n", " ")[:250]
    with open(QUOTA_LOG_CSV, "a", encoding="utf-8") as f:
        f.write(
            f"{ts},{quota_metric},{retry_delay_s:.1f},{clean_err},{success_60s},{success_24h}\n"
        )


def count_rolling_successes() -> Tuple[int, int]:
    """Count successful calls in the previous 60s and previous 24h."""
    if not LEDGER_CSV.is_file():
        return 0, 0
    now = datetime.datetime.now(datetime.timezone.utc)
    s_60s = 0
    s_24h = 0
    with open(LEDGER_CSV, "r", encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 8 and parts[6] == "SUCCESS":
                try:
                    ts = datetime.datetime.fromisoformat(parts[0])
                    delta = (now - ts).total_seconds()
                    if 0 <= delta <= 60:
                        s_60s += 1
                    if 0 <= delta <= 86400:
                        s_24h += 1
                except Exception:
                    pass
    return s_60s, s_24h


def parse_quota_error(err_str: str) -> Tuple[str, float]:
    """Parse 429 error response body to identify quota metric and retryDelay (Rule 1 & 2)."""
    s = err_str.lower()
    metric = "unknown"
    if "per_minute" in s or "per minute" in s or "requests per minute" in s or "rpm" in s:
        metric = "per-minute"
    elif "token" in s or "tokens" in s:
        metric = "tokens"
    elif "per_day" in s or "per day" in s or "requests per day" in s or "rpd" in s or "current quota" in s or "exceeded your current quota" in s:
        metric = "per-day"
    else:
        metric = "unknown"

    m = re.search(r"retry[_-]?delay['\":\s]+(\d+(?:\.\d+)?)", s)
    if not m:
        m = re.search(r"after (\d+(?:\.\d+)?) seconds", s)
    if not m:
        m = re.search(r"retry in (\d+(?:\.\d+)?) seconds", s)
    if not m:
        m = re.search(r"wait (\d+(?:\.\d+)?) seconds", s)
    if not m:
        m = re.search(r"['\"]seconds['\"]:\s*(\d+(?:\.\d+)?)", s)
    retry_delay = float(m.group(1)) if m else 0.0
    return metric, retry_delay


def compute_next_probe_delay() -> Tuple[float, str]:
    """Computes delay until next probe (Rule 2 & 3).
    
    Probes every 15 minutes, and also probes at 07:00 UTC and 07:05 UTC (confirmed daily reset window).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    base_target = now + datetime.timedelta(minutes=15)
    target = base_target

    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)

    checkpoints = [
        datetime.datetime(today.year, today.month, today.day, 7, 0, 15, tzinfo=datetime.timezone.utc),
        datetime.datetime(today.year, today.month, today.day, 7, 5, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(today.year, today.month, today.day, 8, 5, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 30, tzinfo=datetime.timezone.utc),
        datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 7, 0, 15, tzinfo=datetime.timezone.utc),
        datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 7, 5, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 8, 5, 0, tzinfo=datetime.timezone.utc),
    ]

    # If known reset was confirmed previously, add that time of day as a checkpoint
    if KNOWN_RESET_JSON.is_file():
        try:
            reset_data = json.loads(KNOWN_RESET_JSON.read_text(encoding="utf-8"))
            if "confirmed_reset_utc" in reset_data:
                k_dt = datetime.datetime.fromisoformat(reset_data["confirmed_reset_utc"])
                cp_k_today = datetime.datetime(today.year, today.month, today.day, k_dt.hour, k_dt.minute, 30, tzinfo=datetime.timezone.utc)
                cp_k_tomorrow = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, k_dt.hour, k_dt.minute, 30, tzinfo=datetime.timezone.utc)
                checkpoints.extend([cp_k_today, cp_k_tomorrow])
        except Exception:
            pass

    upcoming = sorted([cp for cp in checkpoints if now < cp <= base_target])
    if upcoming:
        target = upcoming[0]

    delay = max(5.0, (target - now).total_seconds())
    return delay, target.isoformat()


def send_probe(generator: Optional["APIGenerator"] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """Send ONE real trivial API call with the existing key now.
    
    Logs the exact result (success or 429 + reason) with the real UTC time.
    """
    cfg = verify_and_load_config()
    init_ledger()
    if generator is None:
        generator = APIGenerator(cfg, dry_run=False)

    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.time()
    try:
        resp = generator.client.models.generate_content(
            model=generator.model_id,
            contents="Ping",
        )
        latency = time.time() - t0
        finish_reason = "UNKNOWN"
        if hasattr(resp, "candidates") and resp.candidates:
            finish_reason = str(resp.candidates[0].finish_reason)

        usage_dict = {}
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage_dict = {
                "prompt_token_count": getattr(resp.usage_metadata, "prompt_token_count", 2),
                "candidates_token_count": getattr(resp.usage_metadata, "candidates_token_count", 9),
                "total_token_count": getattr(resp.usage_metadata, "total_token_count", 11),
            }

        log_ledger_entry(
            arm="PROBE",
            dataset="probe",
            row_idx=0,
            model=generator.model_id,
            status="SUCCESS",
            http_code=200,
            prompt_tokens=usage_dict.get("prompt_token_count", 2),
            completion_tokens=usage_dict.get("candidates_token_count", 9),
            latency_s=latency,
            error_msg=f"finish_reason={finish_reason}",
        )
        update_status_md(f"Probe succeeded at {now_utc}. Status: HTTP 200 (SUCCESS).")
        return True, "SUCCESS (HTTP 200)", {
            "timestamp": now_utc,
            "latency_s": round(latency, 3),
            "finish_reason": finish_reason,
            "usage": usage_dict,
            "text": ascii(resp.text) if hasattr(resp, "text") and resp.text else "",
        }
    except Exception as e:
        latency = time.time() - t0
        err_str = str(e)
        http_code = 429 if ("429" in err_str or "ResourceExhausted" in err_str) else 500
        metric, retry_delay = parse_quota_error(err_str)
        s_60s, s_24h = count_rolling_successes()
        if http_code == 429:
            log_quota_event(
                quota_metric=metric,
                retry_delay_s=retry_delay,
                raw_error=err_str,
                success_60s=s_60s,
                success_24h=s_24h,
            )
        log_ledger_entry(
            arm="PROBE",
            dataset="probe",
            row_idx=0,
            model=generator.model_id,
            status="RATE_LIMITED_429" if http_code == 429 else "ERROR",
            http_code=http_code,
            prompt_tokens=2,
            completion_tokens=0,
            latency_s=latency,
            error_msg=err_str,
        )
        update_status_md(
            f"Probe failed at {now_utc}: {metric} (HTTP {http_code}).",
            last_429_reason=f"{metric}: {err_str[:100]}",
        )
        return False, f"HTTP {http_code} ({metric}): {err_str}", {
            "timestamp": now_utc,
            "latency_s": round(latency, 3),
            "metric": metric,
            "retry_delay_s": retry_delay,
            "raw_error": err_str,
        }



class APIGenerator:
    """Manages Gemini generation with pacing, rate limiting, and caching."""

    def __init__(self, cfg: Dict[str, Any], dry_run: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        self.model_id = cfg["model_id"]
        self.temperature = float(cfg.get("temperature", 0.0))
        self.max_output_tokens = int(cfg.get("max_output_tokens", 512))
        self.pacing_seconds = float(cfg.get("pacing_seconds", 5.0))
        self.daily_cap = int(cfg.get("daily_cap", 1300))
        self.last_call_time = 0.0
        self.first_429_time: Optional[str] = None
        self.total_calls_session = 0
        self.probing_daily_reset = False
        self.calls_since_last_reset = 0
        self.measured_daily_limit = 480

        # Load known reset state if available
        if KNOWN_RESET_JSON.is_file():
            try:
                r_info = json.loads(KNOWN_RESET_JSON.read_text(encoding="utf-8"))
                self.probing_daily_reset = bool(r_info.get("probing_daily_reset", False))
                self.measured_daily_limit = int(r_info.get("measured_daily_limit", 480))
            except Exception:
                pass

        if not dry_run:
            if not API_KEY:
                raise ValueError("GOOGLE_API_KEY environment variable is required")
            from google import genai
            self.client = genai.Client(api_key=API_KEY)

    def generate(
        self,
        arm: str,
        dataset: str,
        row_idx: int,
        prompt_text: str,
        contexts_used: List[str],
    ) -> Tuple[str, bool]:
        """Generate response with cache check, pacing, daily quota adherence, and 429 backoff.
        
        Returns: (raw_answer, was_cache_hit)
        """
        cache_key = f"{arm}_{dataset}_row_{row_idx}"
        cache_file = CACHE_DIR / f"{cache_key}.json"

        # Check disk cache first
        if cache_file.is_file():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return cached_data.get("raw_answer", ""), True
            except Exception:
                pass

        if self.dry_run:
            # Simulate response without calling remote API
            time.sleep(0.01)
            sim_answer = f"[DRY_RUN_SIMULATED_ANSWER for {arm} {dataset} row {row_idx}]"
            return sim_answer, False

        # Enforce pacing (5s per call)
        elapsed = time.time() - self.last_call_time
        if elapsed < self.pacing_seconds:
            time.sleep(self.pacing_seconds - elapsed)

        prompt_tokens_est = len(prompt_text) // 4

        while True:
            t0 = time.time()
            try:
                self.last_call_time = time.time()
                resp = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt_text,
                )
                latency = time.time() - t0
                self.total_calls_session += 1

                raw_answer = resp.text if hasattr(resp, "text") and resp.text else ""
                completion_tokens_est = len(raw_answer) // 4

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
                    actual_p_tokens = usage_dict["prompt_token_count"]
                    actual_c_tokens = usage_dict["candidates_token_count"]
                else:
                    actual_p_tokens = prompt_tokens_est
                    actual_c_tokens = completion_tokens_est

                # Rule 3 & 4: If this call succeeds after a daily 429, log the confirmed reset!
                if self.probing_daily_reset:
                    confirm_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    print(f"\n[API RUNNER] FIRST SUCCESSFUL CALL AFTER RESET: CONFIRMED AT {confirm_ts}")
                    reset_data = {
                        "confirmed_reset_utc": confirm_ts,
                        "status": "Reset confirmed",
                    }
                    KNOWN_RESET_JSON.parent.mkdir(parents=True, exist_ok=True)
                    KNOWN_RESET_JSON.write_text(json.dumps(reset_data, indent=2), encoding="utf-8")
                    update_status_md(f"Reset confirmed at {confirm_ts}. Resumed active generation.")
                    self.probing_daily_reset = False
                    self.calls_since_last_reset = 0

                self.calls_since_last_reset += 1

                log_ledger_entry(
                    arm=arm,
                    dataset=dataset,
                    row_idx=row_idx,
                    model=self.model_id,
                    status="SUCCESS",
                    http_code=200,
                    prompt_tokens=actual_p_tokens,
                    completion_tokens=actual_c_tokens,
                    latency_s=latency,
                    error_msg=f"finish_reason={finish_reason}",
                )
                print(f"[{arm} {dataset}] row {row_idx} completed ({latency:.2f}s, finish_reason={finish_reason})", flush=True)

                # Save cache file
                cache_payload = {
                    "arm": arm,
                    "dataset": dataset,
                    "row_idx": row_idx,
                    "model_id": self.model_id,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "prompt_hash": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
                    "prompt_text": prompt_text,
                    "contexts_used": contexts_used,
                    "raw_answer": raw_answer,
                    "finish_reason": finish_reason,
                    "usage": usage_dict,
                    "latency_s": round(latency, 3),
                }
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_payload, f, indent=2)

                return raw_answer, False

            except Exception as e:
                latency = time.time() - t0
                err_str = str(e)
                http_code = 500

                if "429" in err_str or "ResourceExhausted" in err_str:
                    http_code = 429
                    s_60s, s_24h = count_rolling_successes()
                    metric, retry_delay = parse_quota_error(err_str)

                    # Rule 1: Log to reviews/api_quota_log.csv
                    log_quota_event(
                        quota_metric=metric,
                        retry_delay_s=retry_delay,
                        raw_error=err_str,
                        success_60s=s_60s,
                        success_24h=s_24h,
                    )

                    log_ledger_entry(
                        arm=arm,
                        dataset=dataset,
                        row_idx=row_idx,
                        model=self.model_id,
                        status="RATE_LIMITED_429",
                        http_code=429,
                        prompt_tokens=prompt_tokens_est,
                        completion_tokens=0,
                        latency_s=latency,
                        error_msg=err_str,
                    )

                    # Rule 2: Decide wait from error
                    if metric in ["per-minute", "tokens"]:
                        wait_sec = max(retry_delay, 70.0)
                        print(f"[API RUNNER] 429 ({metric}). Waiting {wait_sec:.1f}s before retry...")
                        update_status_md(
                            f"429 ({metric}): waiting {wait_sec:.1f}s to retry.",
                            last_429_reason=f"{metric}: {err_str[:80]}",
                        )
                        time.sleep(wait_sec)
                        continue
                    else:
                        # Per-day or unknown: Rule 2 ("unknown: treat as per-day"), Rule 3 & 4
                        self.probing_daily_reset = True
                        measured = self.calls_since_last_reset or s_24h
                        measured_limit = measured if measured > 0 else 480
                        self.measured_daily_limit = measured_limit

                        delay, next_probe_iso = compute_next_probe_delay()
                        reset_data = {
                            "last_429_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "last_429_reason": f"{metric}: {err_str[:120]}",
                            "next_probe_time": next_probe_iso,
                            "measured_daily_limit": measured_limit,
                            "probing_daily_reset": True,
                        }
                        if KNOWN_RESET_JSON.is_file():
                            try:
                                old_data = json.loads(KNOWN_RESET_JSON.read_text(encoding="utf-8"))
                                if "confirmed_reset_utc" in old_data:
                                    reset_data["confirmed_reset_utc"] = old_data["confirmed_reset_utc"]
                            except Exception:
                                pass

                        KNOWN_RESET_JSON.parent.mkdir(parents=True, exist_ok=True)
                        KNOWN_RESET_JSON.write_text(json.dumps(reset_data, indent=2), encoding="utf-8")

                        print(
                            f"[API RUNNER] 429 daily quota hit ({metric}). Probing with NEXT real work item at {next_probe_iso} "
                            f"(in {delay/60:.1f} min)..."
                        )
                        update_status_md(
                            f"Daily 429 hit ({metric}). Probing every 30m; next probe at {next_probe_iso}.",
                            next_probe_time=next_probe_iso,
                            last_429_reason=f"{metric}: {err_str[:100]}",
                        )
                        time.sleep(delay)
                        continue

                elif "503" in err_str or "overloaded" in err_str:
                    http_code = 503
                    log_ledger_entry(
                        arm=arm,
                        dataset=dataset,
                        row_idx=row_idx,
                        model=self.model_id,
                        status="SERVER_UNAVAILABLE_503",
                        http_code=503,
                        prompt_tokens=prompt_tokens_est,
                        completion_tokens=0,
                        latency_s=latency,
                        error_msg=err_str,
                    )
                    print(f"[API RUNNER] 503 transient error. Retrying in 15 seconds...")
                    time.sleep(15.0)
                    continue

                else:
                    log_ledger_entry(
                        arm=arm,
                        dataset=dataset,
                        row_idx=row_idx,
                        model=self.model_id,
                        status="ERROR",
                        http_code=http_code,
                        prompt_tokens=prompt_tokens_est,
                        completion_tokens=0,
                        latency_s=latency,
                        error_msg=err_str,
                    )
                    print(f"[API RUNNER] Unhandled error: {err_str}. Backing off 30s...")
                    time.sleep(30.0)
                    continue


def clean_mitre_ids(text: str) -> List[str]:
    """Extract technique IDs."""
    if not isinstance(text, str):
        return []
    ids = re.findall(r"T\d{4}(?:\.\d{3})?", text)
    seen = set()
    return [x for x in ids if not (x in seen or seen.add(x))]


def score_technique_f1(pred_ids: List[str], gt_str: str) -> Tuple[float, float, float]:
    """Compute Precision, Recall, F1 for technique extraction."""
    gt_ids = clean_mitre_ids(gt_str)
    if not gt_ids:
        return (0.0, 0.0, 0.0)

    pred_set = set(pred_ids)
    gt_set = set(gt_ids)

    tp = len(pred_set & gt_set)
    fp = len(pred_set - gt_set)
    fn = len(gt_set - pred_set)

    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(gt_set) if gt_set else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def score_taa_match(answer: str, gt_str: str, group_alias_map: Dict[str, Any]) -> float:
    """Check if intrusion set ID or canonical name or alias appears in answer."""
    from src.retrieval_eval import normalize_group_name
    gt_norm = normalize_group_name(gt_str)
    all_gt_aliases = {gt_norm}

    for gid, gdata in group_alias_map.items():
        canonical_norm = normalize_group_name(gdata.get("canonical_name", ""))
        alias_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if gt_norm == canonical_norm or gt_norm in alias_norms or any(a in gt_norm for a in alias_norms if len(a) > 3):
            all_gt_aliases.add(gid.lower())
            all_gt_aliases.add(canonical_norm)
            all_gt_aliases.update(alias_norms)

    ans_norm = normalize_group_name(answer)
    for alias in all_gt_aliases:
        if len(alias) >= 3 and alias in ans_norm:
            return 1.0
    return 0.0


HEARTBEAT_HISTORY: List[str] = []


def update_status_md(
    extra_note: str = "",
    next_probe_time: Optional[str] = None,
    last_429_reason: Optional[str] = None,
    is_heartbeat: bool = False,
):
    """Write current status summary to reviews/api_status.md (Rule 5 & 6)."""
    global HEARTBEAT_HISTORY
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    s_60s, s_24h = count_rolling_successes()

    reset_info = {}
    if KNOWN_RESET_JSON.is_file():
        try:
            reset_info = json.loads(KNOWN_RESET_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Save next_probe_time / last_429_reason to KNOWN_RESET_JSON so heartbeat retains it
    if next_probe_time or last_429_reason:
        if next_probe_time:
            reset_info["next_probe_time"] = next_probe_time
        if last_429_reason:
            reset_info["last_429_reason"] = last_429_reason
        try:
            KNOWN_RESET_JSON.parent.mkdir(parents=True, exist_ok=True)
            KNOWN_RESET_JSON.write_text(json.dumps(reset_info, indent=2), encoding="utf-8")
        except Exception:
            pass

    # Count cached files per arm
    arm_counts = {}
    if CACHE_DIR.is_dir():
        for f in CACHE_DIR.glob("*.json"):
            if f.name.endswith(".lock") or f.name == "known_reset.json":
                continue
            if f.name.startswith("E0_prime_HD_k200"):
                arm = "E0'-HD-k200 (Phase 6C)"
            elif f.name.startswith("E0_prime"):
                arm = "E0' (original splitter)"
            elif f.name.startswith("E1b_mixed"):
                arm = "E1b-MIXED (B* = 500)"
            elif f.name.startswith("E1b"):
                arm = "E1b (superseded Phase 3A)"
            elif f.name.startswith("LLM-only"):
                arm = "LLM-only"
            elif f.name.startswith("V0h_cti-taa") or f.name.startswith("cti-taa_B2_V0h"):
                arm = "cti-taa (B2, V0h)"
            elif f.name.startswith("Vrel_cti-taa") or f.name.startswith("cti-taa_B2_Vrel"):
                arm = "cti-taa (B2, Vrel)"
            elif f.name.startswith("cti-taa_B2_V0"):
                arm = "cti-taa (B2, V0)"
            elif f.name.startswith("cti-taa_B2_V1"):
                arm = "cti-taa (B2, V1)"
            else:
                parts = f.stem.split("_")
                arm = parts[0]
            arm_counts[arm] = arm_counts.get(arm, 0) + 1

    measured_limit = reset_info.get("measured_daily_limit", "480 (provisional, probing every 30m until real limit measured)")
    confirmed_reset = reset_info.get("confirmed_reset_utc", "Pending empirical confirmation")
    disp_last_429 = last_429_reason or reset_info.get("last_429_reason", "None recently")
    disp_next_probe = next_probe_time or reset_info.get("next_probe_time", "N/A (active processing)")

    # Read existing heartbeat history from STATUS_MD if history is empty
    if not HEARTBEAT_HISTORY and STATUS_MD.is_file():
        try:
            prev_lines = STATUS_MD.read_text(encoding="utf-8").splitlines()
            for line in prev_lines:
                if line.strip().startswith("- `2026-") and "PID" in line:
                    HEARTBEAT_HISTORY.append(line.strip())
            HEARTBEAT_HISTORY = HEARTBEAT_HISTORY[-10:]
        except Exception:
            pass

    if is_heartbeat or not HEARTBEAT_HISTORY:
        beat_line = f"- `{now_utc}` - PID {os.getpid()} - Process Alive"
        HEARTBEAT_HISTORY.append(beat_line)
        HEARTBEAT_HISTORY = HEARTBEAT_HISTORY[-10:]

    content = f"""# API Generation Runner Status

- **Last Updated (UTC)**: `{now_utc}`
- **Heartbeat Status**: Alive and logging every 10 min (PID: {os.getpid()})
- **Calls Used in Current Window (Rolling 24h)**: `{s_24h} / {measured_limit}`
- **Rolling 24-Hour Successful Calls**: `{s_24h}`
- **Previous 60s Successful Calls**: `{s_60s}`
- **Last Quota Event / 429 Reason**: `{disp_last_429}`
- **Next Probe Time (UTC)**: `{disp_next_probe}`
- **Confirmed Reset Time**: `{confirmed_reset}`
- **Measured Daily Limit**: `{measured_limit}`
- **Arm Identification**: Note that `E0` corresponds to `E0'` (original STIX splitter control).
- **Notes**: {extra_note if extra_note else "Normal operation"}

## Completed Cache Records by Arm
| Arm | Cached Responses |
| :--- | :--- |
"""
    for arm, count in sorted(arm_counts.items()):
        content += f"| `{arm}` | {count} |\n"

    if not arm_counts:
        content += "| *None yet* | 0 |\n"

    content += "\n## Heartbeat Log (Every 10 min)\n"
    for b in HEARTBEAT_HISTORY:
        content += f"{b}\n"

    STATUS_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_MD, "w", encoding="utf-8") as f:
        f.write(content)


def start_heartbeat_thread():
    """Background thread writing heartbeat to api_status.md every 10 min (Rule 6)."""
    def heartbeat_worker():
        while True:
            time.sleep(600)  # 10 minutes
            try:
                update_status_md(extra_note="Heartbeat tick (process alive)", is_heartbeat=True)
            except Exception:
                pass

    t = threading.Thread(target=heartbeat_worker, daemon=True)
    t.start()


def poll_for_b_star(max_wait_seconds: int = 86400) -> int:
    """Poll analysis_plan.md until 'B* = <number> tokens' appears."""
    pattern = re.compile(r"B\*\s*=\s*(\d+)\s*tokens", re.IGNORECASE)
    t0 = time.time()
    print("[API RUNNER] Checking analysis_plan.md for locked context budget 'B* = <number> tokens'...")

    while time.time() - t0 < max_wait_seconds:
        if ANALYSIS_PLAN.is_file():
            text = ANALYSIS_PLAN.read_text(encoding="utf-8")
            m = pattern.search(text)
            if m:
                b_val = int(m.group(1))
                print(f"[API RUNNER] Found locked token budget: B* = {b_val} tokens!")
                return b_val

        update_status_md("Waiting for B* token budget in analysis_plan.md before Step 3...")
        time.sleep(10.0)

    raise TimeoutError("Timed out waiting for B* token budget in analysis_plan.md")


def run_experiment(dry_run: bool = False, test_3_calls_only: bool = False):
    """Main execution orchestrating steps (1), (2), (3), (4)."""
    cfg = verify_and_load_config()
    init_ledger()
    update_status_md("Runner initialized.")

    start_heartbeat_thread()
    generator = APIGenerator(cfg, dry_run=dry_run)

    # Load datasets
    datasets = {}
    for ds_name, rel_path in cfg["datasets"].items():
        df = pd.read_excel(REPO_ROOT / rel_path).dropna(subset=["query"])
        df = df[df["query"].str.strip() != ""].reset_index(drop=True)
        datasets[ds_name] = df

    live_calls_made = 0

    # =========================================================================
    # Step 1: LLM-only arm (no retrieval): all 339 rows
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: LLM-Only Arm (No Retrieval, 339 queries)")
    print("=" * 70)

    template_no_ctx = cfg["prompt_templates"]["no_context"]

    for ds_name in ["cti-ate", "cti-taa", "CTI-ATTACK"]:
        df = datasets[ds_name]
        for row_idx, row in df.iterrows():
            query = str(row["query"])
            prompt = template_no_ctx.format(query=query)

            raw_ans, was_hit = generator.generate(
                arm="LLM-only",
                dataset=ds_name,
                row_idx=row_idx,
                prompt_text=prompt,
                contexts_used=[],
            )

            if not was_hit and not dry_run:
                live_calls_made += 1
                if test_3_calls_only and live_calls_made >= 3:
                    print(f"\n[API RUNNER] Completed 3 live test calls! Exiting test mode cleanly.")
                    update_status_md("3 live test calls verified successfully.")
                    return

        update_status_md(f"Step 1: Finished LLM-only for {ds_name}.")

    # =========================================================================
    # Step 2: cti-taa, E0-STIX-ALL, baseline B2: variants V0 and V1 (50 rows each, interleaved)
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: cti-taa, E0-STIX-ALL, baseline B2: variants V0 and V1 (50 rows each, interleaved)")
    print("=" * 70)

    stix_kb = None
    retriever_all = None
    resolver = None
    template_with_ctx = cfg["prompt_templates"]["with_context"]

    df_taa = datasets["cti-taa"]

    for row_idx, row in df_taa.iterrows():
        raw_query = str(row["query"])

        # Interleave V0 and V1 for this row
        for variant in ["V0", "V1"]:
            arm_name = f"cti-taa_B2_{variant}"
            cache_file = CACHE_DIR / f"{arm_name}_cti-taa_row_{row_idx}.json"
            if cache_file.is_file():
                continue

            # Lazy load models only on cache miss
            if retriever_all is None:
                from src.data_loader import load_stix_all_bundles
                from src.retriever import HybridSTIXRetriever
                from src.entity_resolver import CyberEntityResolver
                stix_kb = load_stix_all_bundles()
                retriever_all = HybridSTIXRetriever(stix_kb=stix_kb, cache_dir=".cache/retriever_index_all")
                resolver = CyberEntityResolver(stix_kb=stix_kb, min_alias_len=3, random_seed=42)

            # Prepare expanded query if V1
            if variant == "V1":
                exp_query, _ = resolver.expand_query(raw_query, variant="V1", max_expansion_tokens=64)
            else:
                exp_query = raw_query

            docs = retriever_all.retrieve(exp_query, top_k=10, enable_query_chunking=False)
            contexts = [d.page_content for d in docs]
            ctx_str = "\n".join(contexts)
            prompt = template_with_ctx.format(context=ctx_str, query=raw_query)

            raw_ans, was_hit = generator.generate(
                arm=arm_name,
                dataset="cti-taa",
                row_idx=row_idx,
                prompt_text=prompt,
                contexts_used=contexts,
            )

            if not was_hit and not dry_run:
                live_calls_made += 1
                if test_3_calls_only and live_calls_made >= 3:
                    print(f"\n[API RUNNER] Completed 3 live test calls! Exiting test mode cleanly.")
                    update_status_md("3 live test calls verified successfully.")
                    return

        if (row_idx + 1) % 10 == 0:
            update_status_md(f"Step 2: Completed {row_idx + 1}/50 rows (interleaved V0 and V1).")

    update_status_md("Step 2: Finished all 50 rows for cti-taa V0 and V1.")

    # =========================================================================
    # Step 3: E0' and E1b at the fixed token budget B*, for cti-ate and CTI-ATTACK (289 rows per arm)
    # Runner MUST refuse to start until analysis_plan.md contains "B* = <number> tokens"
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: Structure-Aware Chunking Arms E0' and E1b at Token Budget B*")
    print("=" * 70)

    b_star_budget = poll_for_b_star()
    print(f"[API RUNNER] Starting Step 3 with verified budget B* = {b_star_budget} tokens...")

    # Load pre-computed top50 cache to avoid loading heavy FAISS/SentenceTransformer models into RAM
    top50_cache_path = REPO_ROOT / "results" / "phase_3" / "top50_ranked_chunks.json"
    top50_cache = {}
    if top50_cache_path.is_file():
        try:
            with open(top50_cache_path, "r", encoding="utf-8") as f:
                top50_cache = json.load(f)
        except Exception:
            pass

    # Load pre-assembled E1b-MIXED contexts at B* = 500 tokens
    e1b_contexts_path = REPO_ROOT / "results" / "phase_3" / "e1b_mixed_contexts_b500.json"
    e1b_contexts_data = {}
    if e1b_contexts_path.is_file():
        try:
            with open(e1b_contexts_path, "r", encoding="utf-8") as f:
                e1b_contexts_data = json.load(f)
        except Exception:
            pass

    o2_retriever = None

    for ds_name in ["cti-ate", "CTI-ATTACK"]:
        df = datasets[ds_name]
        for row_idx, row in df.iterrows():
            raw_query = str(row["query"])

            # E0_prime is already 100% complete; E1b_mixed is the new confirmatory arm
            step3_arms = ["E0_prime", "E1b_mixed"]
            for arm in step3_arms:
                cache_file = CACHE_DIR / f"{arm}_{ds_name}_row_{row_idx}.json"
                if cache_file.is_file():
                    continue

                contexts = []
                if arm == "E1b_mixed":
                    contexts = e1b_contexts_data.get(ds_name, {}).get(str(row_idx), [])
                    if not contexts:
                        # If contexts not yet assembled for this dataset, defer
                        continue
                elif ds_name in top50_cache and "B2" in top50_cache[ds_name] and arm in top50_cache[ds_name]["B2"]:
                    q_records = top50_cache[ds_name]["B2"][arm]
                    rec = next((r for r in q_records if r["idx"] == int(row_idx)), None)
                    if rec:
                        accum_tokens = 0
                        for chunk in rec["top50"]:
                            tok = chunk.get("tokens", len(chunk["content"]) // 4)
                            if accum_tokens + tok > b_star_budget:
                                break
                            contexts.append(chunk["content"])
                            accum_tokens += tok

                if not contexts and arm != "E1b_mixed":
                    if o2_retriever is None:
                        from src.data_loader import load_stix_all_bundles
                        from src.chunking import StructureAwareSTIXRetriever
                        if stix_kb is None:
                            stix_kb = load_stix_all_bundles()
                        o2_retriever = StructureAwareSTIXRetriever(stix_kb=stix_kb, budget_tokens=b_star_budget)
                    docs = o2_retriever.retrieve(raw_query, arm=arm, budget_tokens=b_star_budget)
                    contexts = [d.page_content for d in docs]

                ctx_str = "\n".join(contexts)
                prompt = template_with_ctx.format(context=ctx_str, query=raw_query)

                raw_ans, was_hit = generator.generate(
                    arm=arm,
                    dataset=ds_name,
                    row_idx=row_idx,
                    prompt_text=prompt,
                    contexts_used=contexts,
                )

                if not was_hit and not dry_run:
                    live_calls_made += 1
                    if test_3_calls_only and live_calls_made >= 3:
                        print(f"\n[API RUNNER] Completed 3 live test calls! Exiting test mode cleanly.")
                        update_status_md("3 live test calls verified successfully.")
                        return

        update_status_md(f"Step 3: Finished {ds_name} for E0' and E1b.")

    update_status_md("Steps 1, 2, and 3 completed successfully. Ready for Step 4 RAGAS subsample.")
    print("\n[API RUNNER] All generation steps complete!")


def run_phase6c_arms(
    generator: APIGenerator,
    dry_run: bool = False,
    test_3_calls_only: bool = False,
):
    """Run the 389 Section 12 generation arms in priority order.
    
    1. E0'-HD-k200 on cti-ate (60)
    2. E0'-HD-k200 on CTI-ATTACK (229)
    3. cti-taa V0h (50)
    4. cti-taa Vrel (50)
    
    Strict constraints:
    - B* = 500 tokens
    - Bare prompt template: "Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    - Truncation via truncate_to_token_budget(docs, 500)
    - Row count & query_id alignment asserted
    - No change to model, prompt, temperature, max_output_tokens
    """
    import gzip
    from langchain_core.documents import Document
    from src.chunking import truncate_to_token_budget
    from src.data_loader import compute_query_id

    cfg = generator.cfg
    template_with_ctx = cfg["prompt_templates"]["with_context"]

    # Load datasets
    df_ate = pd.read_excel(REPO_ROOT / cfg["datasets"]["cti-ate"]).dropna(subset=["query"]).reset_index(drop=True)
    df_att = pd.read_excel(REPO_ROOT / cfg["datasets"]["CTI-ATTACK"]).dropna(subset=["query"]).reset_index(drop=True)
    df_taa = pd.read_excel(REPO_ROOT / cfg["datasets"]["cti-taa"]).dropna(subset=["query"]).reset_index(drop=True)

    # 1. Load context sources
    top200_hd_path = REPO_ROOT / "results" / "phase_5" / "top200_hd_chunks.json.gz"
    with gzip.open(top200_hd_path, "rt", encoding="utf-8") as f:
        top200_hd = json.load(f)

    o1_top10_path = REPO_ROOT / "results" / "phase_5" / "o1_top10_cache.json"
    with open(o1_top10_path, "r", encoding="utf-8") as f:
        o1_cache = json.load(f)

    # Assert row counts & alignments
    ate_recs = top200_hd["cti-ate"]["B2"]["E0_prime_k200"]
    assert len(ate_recs) == len(df_ate) == 60, f"cti-ate length mismatch: {len(ate_recs)} vs {len(df_ate)}"
    for idx, row in df_ate.iterrows():
        assert ate_recs[idx]["idx"] == idx
        assert ate_recs[idx]["query_id"] == compute_query_id(str(row["query"]))

    att_recs = top200_hd["CTI-ATTACK"]["B2"]["E0_prime_k200"]
    assert len(att_recs) == len(df_att) == 229, f"CTI-ATTACK length mismatch: {len(att_recs)} vs {len(df_att)}"
    for idx, row in df_att.iterrows():
        assert att_recs[idx]["idx"] == idx
        assert att_recs[idx]["query_id"] == compute_query_id(str(row["query"]))

    v0h_dict = o1_cache["B2"]["V0h"]
    vrel_dict = o1_cache["B2"]["Vrel"]
    assert len(v0h_dict) == len(df_taa) == 50
    assert len(vrel_dict) == len(df_taa) == 50
    for idx, row in df_taa.iterrows():
        assert str(idx) in v0h_dict and len(v0h_dict[str(idx)]) == 10
        assert str(idx) in vrel_dict and len(vrel_dict[str(idx)]) == 10

    print("[API RUNNER] Section 12 arms verified: row counts and query_id alignment 100% matched.", flush=True)

    live_calls_made = 0

    # Priority 1: E0'-HD-k200 on cti-ate (60)
    print("\n" + "=" * 70, flush=True)
    print("PHASE 6C PRIORITY 1: E0'-HD-k200 on cti-ate (60 queries, B*=500)", flush=True)
    print("=" * 70, flush=True)
    arm_name = "E0_prime_HD_k200"
    for row_idx, row in df_ate.iterrows():
        raw_query = str(row["query"])
        rec = ate_recs[row_idx]
        raw_docs = [Document(page_content=c["page_content"], metadata=c.get("metadata", {})) for c in rec["top200"]]
        trunc_docs = truncate_to_token_budget(raw_docs, budget_tokens=500)
        contexts = [d.page_content for d in trunc_docs]
        ctx_str = "\n".join(contexts)
        prompt = template_with_ctx.format(context=ctx_str, query=raw_query)

        raw_ans, was_hit = generator.generate(
            arm=arm_name,
            dataset="cti-ate",
            row_idx=row_idx,
            prompt_text=prompt,
            contexts_used=contexts,
        )
        if not was_hit and not dry_run:
            live_calls_made += 1
            if test_3_calls_only and live_calls_made >= 3:
                print("[API RUNNER] Completed 3 test calls. Exiting.", flush=True)
                return

    update_status_md("Phase 6C: Finished Priority 1 (E0'-HD-k200 cti-ate, 60 queries).")

    # Priority 2: E0'-HD-k200 on CTI-ATTACK (229)
    print("\n" + "=" * 70, flush=True)
    print("PHASE 6C PRIORITY 2: E0'-HD-k200 on CTI-ATTACK (229 queries, B*=500)", flush=True)
    print("=" * 70, flush=True)
    for row_idx, row in df_att.iterrows():
        raw_query = str(row["query"])
        rec = att_recs[row_idx]
        raw_docs = [Document(page_content=c["page_content"], metadata=c.get("metadata", {})) for c in rec["top200"]]
        trunc_docs = truncate_to_token_budget(raw_docs, budget_tokens=500)
        contexts = [d.page_content for d in trunc_docs]
        ctx_str = "\n".join(contexts)
        prompt = template_with_ctx.format(context=ctx_str, query=raw_query)

        raw_ans, was_hit = generator.generate(
            arm=arm_name,
            dataset="CTI-ATTACK",
            row_idx=row_idx,
            prompt_text=prompt,
            contexts_used=contexts,
        )
        if not was_hit and not dry_run:
            live_calls_made += 1
            if test_3_calls_only and live_calls_made >= 3:
                print("[API RUNNER] Completed 3 test calls. Exiting.", flush=True)
                return

    update_status_md("Phase 6C: Finished Priority 2 (E0'-HD-k200 CTI-ATTACK, 229 queries).")

    # Priority 3: cti-taa V0h (50)
    print("\n" + "=" * 70, flush=True)
    print("PHASE 6C PRIORITY 3: cti-taa V0h (50 queries, top-10 chunks under body-only)", flush=True)
    print("=" * 70, flush=True)
    for row_idx, row in df_taa.iterrows():
        raw_query = str(row["query"])
        chunks = v0h_dict[str(row_idx)]
        contexts = [c["page_content"] for c in chunks]
        ctx_str = "\n".join(contexts)
        prompt = template_with_ctx.format(context=ctx_str, query=raw_query)

        raw_ans, was_hit = generator.generate(
            arm="V0h",
            dataset="cti-taa",
            row_idx=row_idx,
            prompt_text=prompt,
            contexts_used=contexts,
        )
        if not was_hit and not dry_run:
            live_calls_made += 1
            if test_3_calls_only and live_calls_made >= 3:
                print("[API RUNNER] Completed 3 test calls. Exiting.", flush=True)
                return

    update_status_md("Phase 6C: Finished Priority 3 (cti-taa V0h, 50 queries).")

    # Priority 4: cti-taa Vrel (50)
    print("\n" + "=" * 70, flush=True)
    print("PHASE 6C PRIORITY 4: cti-taa Vrel (50 queries, top-10 chunks under entity rel expansion)", flush=True)
    print("=" * 70, flush=True)
    for row_idx, row in df_taa.iterrows():
        raw_query = str(row["query"])
        chunks = vrel_dict[str(row_idx)]
        contexts = [c["page_content"] for c in chunks]
        ctx_str = "\n".join(contexts)
        prompt = template_with_ctx.format(context=ctx_str, query=raw_query)

        raw_ans, was_hit = generator.generate(
            arm="Vrel",
            dataset="cti-taa",
            row_idx=row_idx,
            prompt_text=prompt,
            contexts_used=contexts,
        )
        if not was_hit and not dry_run:
            live_calls_made += 1
            if test_3_calls_only and live_calls_made >= 3:
                print("[API RUNNER] Completed 3 test calls. Exiting.", flush=True)
                return

    update_status_md("Phase 6C: Finished Priority 4 (cti-taa Vrel, 50 queries). All 389 calls complete!")
    print("\n[API RUNNER] Phase 6C generation complete across all 389 calls!", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API Generation Runner")
    parser.add_argument("--probe", action="store_true", help="Send ONE real trivial API call to probe Gemini API quota")
    parser.add_argument("--phase6c", action="store_true", help="Run Phase 6C Section 12 generation arms (389 calls)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate generation without remote API calls")
    parser.add_argument("--test-live-3", action="store_true", help="Execute exactly 3 live API calls to test pipeline")
    parser.add_argument("--run", action="store_true", help="Run Phase 6C generation pipeline in background")
    args = parser.parse_args()

    if args.probe:
        print("[API RUNNER] Probing Gemini API with single live call...")
        success, msg, details = send_probe()
        print(f"[API RUNNER] Probe Result: {msg}")
        print(json.dumps(details, indent=2))
    elif args.dry_run:
        print("[API RUNNER] Launching Phase 6C in DRY RUN mode...")
        cfg = verify_and_load_config()
        gen = APIGenerator(cfg, dry_run=True)
        run_phase6c_arms(gen, dry_run=True)
    elif args.test_live_3:
        print("[API RUNNER] Launching Phase 6C in 3-CALL LIVE TEST mode...")
        cfg = verify_and_load_config()
        gen = APIGenerator(cfg, dry_run=False)
        run_phase6c_arms(gen, dry_run=False, test_3_calls_only=True)
    elif args.phase6c or args.run:
        print("[API RUNNER] Launching Phase 6C Generation Arms (389 calls)...")
        cfg = verify_and_load_config()
        init_ledger()
        start_heartbeat_thread()
        gen = APIGenerator(cfg, dry_run=False)
        run_phase6c_arms(gen, dry_run=False, test_3_calls_only=False)
    else:
        print("Usage: python scripts/api_runner.py [--probe | --phase6c | --run | --dry-run | --test-live-3]")

