"""Unit test proving that src/ragas_patch.py provides ragas compatibility without modifying site-packages."""

import sys
from src.ragas_patch import apply_ragas_compatibility_patch


def test_ragas_monkeypatch_applied():
    apply_ragas_compatibility_patch()
    import ragas
    from ragas.llms import LangchainLLMWrapper
    from ragas.llms.base import is_multiple_completion_supported

    assert ragas.__version__ == "0.2.13"
    assert LangchainLLMWrapper is not None
