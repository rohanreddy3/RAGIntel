"""Offline Guard Module.
Guarantees that when OFFLINE_ONLY is true (default), ZERO calls can be made
to any remote LLM API (Google Gemini, OpenAI, etc.) or remote judge service.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def is_offline_only() -> bool:
    """Return True if OFFLINE_ONLY is enabled in environment or defaults to True."""
    val = os.getenv("OFFLINE_ONLY", "true").strip().lower()
    return val in ("true", "1", "yes", "t")


def assert_offline_compliant(action: str = "LLM/Judge API call") -> None:
    """Raises RuntimeError immediately if OFFLINE_ONLY is enabled."""
    if is_offline_only():
        raise RuntimeError(
            f"OFFLINE_ONLY is enabled (default=True): {action} is strictly forbidden. "
            "Only local embeddings, local retrieval, and offline analysis are permitted."
        )


def enforce_offline_guard(func):
    """Decorator to enforce that a function making remote API calls cannot execute in offline mode."""
    def wrapper(*args, **kwargs):
        assert_offline_compliant(f"Calling function '{func.__name__}'")
        return func(*args, **kwargs)
    return wrapper
