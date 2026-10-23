"""Ragas Compatibility Monkeypatch.
Fixes modern langchain-community 0.4+ compatibility with ragas 0.2 without editing site-packages.
"""

import sys
import types


def apply_ragas_compatibility_patch() -> None:
    """Injects lightweight shims for deprecated vertexai modules in sys.modules
    so ragas can import cleanly without touching any site-packages files.
    """
    if "langchain_community.chat_models.vertexai" not in sys.modules:
        try:
            import langchain_community.chat_models.vertexai
        except (ImportError, ModuleNotFoundError):
            class DummyChatVertexAI:
                pass

            mod = types.ModuleType("langchain_community.chat_models.vertexai")
            mod.ChatVertexAI = DummyChatVertexAI
            sys.modules["langchain_community.chat_models.vertexai"] = mod

            try:
                import langchain_community.chat_models
                langchain_community.chat_models.vertexai = mod
            except Exception:
                pass

    if "langchain_community.llms" in sys.modules or True:
        try:
            from langchain_community.llms import VertexAI
        except (ImportError, ModuleNotFoundError):
            class DummyVertexAI:
                pass

            try:
                import langchain_community.llms
                langchain_community.llms.VertexAI = DummyVertexAI
            except Exception:
                pass


# Apply patch automatically when module is imported
apply_ragas_compatibility_patch()
