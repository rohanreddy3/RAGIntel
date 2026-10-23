"""RAGIntel Thesis Enhancements Package"""
__version__ = "0.1.0"

# Apply monkeypatches on package initialization
from src.ragas_patch import apply_ragas_compatibility_patch

apply_ragas_compatibility_patch()
