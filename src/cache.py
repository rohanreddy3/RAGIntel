"""Persistent on-disk cache and rate limiter for LLM and Embedding calls.
Guarantees free-tier quota adherence and prevents redundant API/compute invocations.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple


class PersistentDiskCache:
    """Hash-based JSON cache stored on disk for deterministic repeat lookups."""

    def __init__(self, cache_dir: str = ".cache/llm"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _get_key(self, namespace: str, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        hasher = hashlib.sha256()
        hasher.update(namespace.encode("utf-8"))
        hasher.update(b"::")
        hasher.update(serialized.encode("utf-8"))
        return hasher.hexdigest()

    def get(self, namespace: str, payload: Any) -> Optional[Any]:
        key = self._get_key(namespace, payload)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.is_file():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.hits += 1
                return data.get("response")
            except Exception:
                pass
        self.misses += 1
        return None

    def set(self, namespace: str, payload: Any, response: Any) -> None:
        key = self._get_key(namespace, payload)
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "namespace": namespace,
                    "payload": payload,
                    "response": response,
                    "timestamp": time.time(),
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Failed to write to cache {cache_file}: {e}")

    def stats(self) -> Dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_cached_files": len(list(self.cache_dir.glob("*.json"))),
        }


class FreeTierRateLimiter:
    """Enforces Google Gemini free-tier rate limits (15 requests/minute)."""

    def __init__(self, requests_per_minute: int = 14, min_delay_seconds: float = 4.3):
        self.rpm = requests_per_minute
        self.min_delay = min_delay_seconds
        self.last_request_time = 0.0
        self.total_requests = 0

    def wait_if_needed(self) -> float:
        now = time.time()
        elapsed = now - self.last_request_time
        sleep_time = 0.0
        if elapsed < self.min_delay:
            sleep_time = self.min_delay - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        self.total_requests += 1
        return sleep_time
