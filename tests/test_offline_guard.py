"""Unit tests proving that OFFLINE_ONLY=true strictly prevents any LLM/Judge API call
by raising RuntimeError immediately without network access.
"""

import os
import pytest
from src.offline_guard import is_offline_only, assert_offline_compliant, enforce_offline_guard


def test_offline_guard_is_active():
    """Verify that is_offline_only returns True under OFFLINE_ONLY=true."""
    os.environ["OFFLINE_ONLY"] = "true"
    assert is_offline_only() is True


def test_assert_offline_compliant_raises_runtime_error():
    """Verify that assert_offline_compliant raises RuntimeError when offline."""
    os.environ["OFFLINE_ONLY"] = "true"
    with pytest.raises(RuntimeError, match="OFFLINE_ONLY is enabled"):
        assert_offline_compliant("Test LLM Call")


def test_decorator_blocks_remote_call():
    """Verify that decorated remote functions are blocked before execution."""
    os.environ["OFFLINE_ONLY"] = "true"

    @enforce_offline_guard
    def dummy_remote_api():
        return "should never be reached"

    with pytest.raises(RuntimeError, match="OFFLINE_ONLY is enabled"):
        dummy_remote_api()


def test_offline_guard_disabled_behavior():
    """Verify that when explicitly set to false, guard does not raise."""
    os.environ["OFFLINE_ONLY"] = "false"
    assert is_offline_only() is False
    # Should not raise
    assert_offline_compliant("Allowed Call")
    # Reset back to true to ensure offline constraint remains active
    os.environ["OFFLINE_ONLY"] = "true"
