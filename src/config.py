"""Configuration loader and schema validator for RAGIntel thesis experiments."""

import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import yaml
from dotenv import load_dotenv

# Automatically load environment variables from .env
load_dotenv()


def set_seed(seed: int = 42) -> None:
    """Fix random seeds across all libraries for deterministic execution."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


@dataclass
class ExperimentConfig:
    seed: int = 42
    ablation_arm: str = "E0"
    use_entity_resolution: bool = False
    use_security_chunking: bool = False
    sibling_expansion: bool = False
    context_budget: int = 10
    max_context_tokens: int = 3000
    dataset: str = "cti-ate"
    llm: str = "gpt-4o-mini"
    retrieval: Dict[str, Any] = field(default_factory=dict)
    paths: Dict[str, Any] = field(default_factory=dict)
    raw_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate dataset choice
        valid_datasets = ["cti-ate", "cti-taa", "CTI-ATTACK"]
        if self.dataset not in valid_datasets:
            raise ValueError(f"Invalid dataset '{self.dataset}'. Must be one of {valid_datasets}")

        # Sync flags based on arm if an ablation arm was specified
        if self.ablation_arm == "E0":
            self.use_entity_resolution = False
            self.use_security_chunking = False
            self.sibling_expansion = False
        elif self.ablation_arm == "E1":
            self.use_entity_resolution = False
            self.use_security_chunking = True
            self.sibling_expansion = True
        elif self.ablation_arm == "E2":
            self.use_entity_resolution = True
            self.use_security_chunking = False
            self.sibling_expansion = False
        elif self.ablation_arm == "E3":
            self.use_entity_resolution = True
            self.use_security_chunking = True
            self.sibling_expansion = True
        elif self.ablation_arm == "custom":
            pass  # use explicit boolean flags
        else:
            raise ValueError(f"Unknown ablation arm: {self.ablation_arm}. Must be E0, E1, E2, E3, or custom.")

        # Entity resolution applies only to CTI-TAA (attribution) dataset
        # If enabled on another dataset, warn or enforce specification
        if self.use_entity_resolution and self.dataset != "cti-taa":
            # Note: per project spec: "Applies to CTI-TAA (attribution) only."
            pass


def load_config(config_path: str = "config.yaml") -> ExperimentConfig:
    """Load configuration from a YAML file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config = ExperimentConfig(
        seed=data.get("seed", 42),
        ablation_arm=data.get("ablation_arm", "E0"),
        use_entity_resolution=data.get("use_entity_resolution", False),
        use_security_chunking=data.get("use_security_chunking", False),
        sibling_expansion=data.get("sibling_expansion", False),
        context_budget=data.get("context_budget", 10),
        max_context_tokens=data.get("max_context_tokens", 3000),
        dataset=data.get("dataset", "cti-ate"),
        llm=data.get("llm", "gpt-4o-mini"),
        retrieval=data.get("retrieval", {}),
        paths=data.get("paths", {}),
        raw_config=data,
    )

    # Automatically set random seed
    set_seed(config.seed)
    return config
