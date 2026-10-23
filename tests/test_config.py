"""Unit tests for configuration loading and ablation arm synchronization."""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.config import ExperimentConfig, load_config, set_seed


def test_ablation_arm_e0_flags():
    """E0 baseline: all enhancement flags must be disabled."""
    cfg = ExperimentConfig(ablation_arm="E0", dataset="cti-ate")
    assert cfg.use_entity_resolution is False
    assert cfg.use_security_chunking is False
    assert cfg.sibling_expansion is False


def test_ablation_arm_e1_flags():
    """E1: +O2 (Security-aware chunking + Sibling expansion)."""
    cfg = ExperimentConfig(ablation_arm="E1", dataset="cti-ate")
    assert cfg.use_entity_resolution is False
    assert cfg.use_security_chunking is True
    assert cfg.sibling_expansion is True


def test_ablation_arm_e2_flags():
    """E2: +O1 (Entity resolution)."""
    cfg = ExperimentConfig(ablation_arm="E2", dataset="cti-taa")
    assert cfg.use_entity_resolution is True
    assert cfg.use_security_chunking is False
    assert cfg.sibling_expansion is False


def test_ablation_arm_e3_flags():
    """E3: O1 + O2 (Entity resolution + Security-aware chunking + Sibling expansion)."""
    cfg = ExperimentConfig(ablation_arm="E3", dataset="cti-taa")
    assert cfg.use_entity_resolution is True
    assert cfg.use_security_chunking is True
    assert cfg.sibling_expansion is True


def test_invalid_ablation_arm():
    with pytest.raises(ValueError, match="Unknown ablation arm"):
        ExperimentConfig(ablation_arm="E99")


def test_invalid_dataset():
    with pytest.raises(ValueError, match="Invalid dataset"):
        ExperimentConfig(dataset="unknown-dataset")


def test_load_config_yaml():
    """Verify loading from actual config.yaml."""
    cfg = load_config("config.yaml")
    assert cfg.seed == 42
    assert cfg.ablation_arm in ["E0", "E1", "E2", "E3", "custom"]
    assert cfg.context_budget > 0
    assert cfg.dataset in ["cti-ate", "cti-taa", "CTI-ATTACK"]


def test_set_seed_deterministic():
    """Verify deterministic RNG behavior."""
    import random
    import numpy as np

    set_seed(1234)
    r1 = random.random()
    n1 = np.random.rand()

    set_seed(1234)
    r2 = random.random()
    n2 = np.random.rand()

    assert r1 == r2
    assert n1 == n2
