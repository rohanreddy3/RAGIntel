"""Unit tests for dataset and STIX knowledge base loaders."""

import pytest
from pathlib import Path
from src.data_loader import (
    load_benchmark_dataset,
    load_all_benchmark_datasets,
    load_stix_bundle,
    DATASET_CONFIGS,
)


def test_load_cti_ate():
    info = load_benchmark_dataset("cti-ate")
    assert info.name == "cti-ate"
    assert info.num_samples == 60
    assert "query" in info.columns
    assert "ground_truth" in info.columns
    assert not info.df["query"].isna().any()


def test_load_cti_taa():
    info = load_benchmark_dataset("cti-taa")
    assert info.name == "cti-taa"
    assert info.num_samples == 50
    assert "query" in info.columns
    assert "ground_truth" in info.columns
    assert not info.df["query"].isna().any()


def test_load_cti_attack():
    info = load_benchmark_dataset("CTI-ATTACK")
    assert info.name == "CTI-ATTACK"
    assert info.num_samples == 229
    assert "query" in info.columns
    assert "ground_truth" in info.columns
    assert not info.df["query"].isna().any()


def test_load_all_datasets():
    datasets = load_all_benchmark_datasets()
    assert len(datasets) == 3
    assert set(datasets.keys()) == {"cti-ate", "cti-taa", "CTI-ATTACK"}


def test_load_stix_bundle():
    bundle_path = "data/mitre/enterprise-attack.json"
    assert Path(bundle_path).is_file(), "STIX bundle must exist"
    kb = load_stix_bundle(bundle_path)
    assert kb.bundle_type == "bundle"
    assert kb.total_objects > 20000

    tech_map = kb.get_techniques_map()
    assert len(tech_map) > 500
    # Check well-known technique T1071 (Application Layer Protocol)
    assert "T1071" in tech_map
    assert "name" in tech_map["T1071"]
    assert "description" in tech_map["T1071"]

    group_map = kb.get_group_alias_map()
    assert len(group_map) > 100
    # Check well-known threat group G0007 (APT28)
    assert "G0007" in group_map
    assert "canonical_name" in group_map["G0007"]
    assert len(group_map["G0007"]["aliases"]) > 1


def test_is_active_stix_object():
    from src.data_loader import is_active_stix_object

    # Normal object
    assert is_active_stix_object({"type": "attack-pattern", "id": "1"}) is True
    # Revoked object
    assert is_active_stix_object({"type": "attack-pattern", "id": "2", "revoked": True}) is False
    # Deprecated object
    assert is_active_stix_object({"type": "attack-pattern", "id": "3", "x_mitre_deprecated": True}) is False
    # Both
    assert is_active_stix_object({"type": "attack-pattern", "id": "4", "revoked": True, "x_mitre_deprecated": True}) is False


def test_stix_active_vs_all_counts():
    bundle_path = "data/mitre/enterprise-attack.json"
    kb_active = load_stix_bundle(bundle_path, filter_active_only=True)
    kb_all = load_stix_bundle(bundle_path, filter_active_only=False)

    assert kb_all.total_objects == 26085
    assert kb_active.total_objects < kb_all.total_objects
    assert kb_active.total_objects == 25639
    # Difference is exactly 446 inactive objects
    assert kb_all.total_objects - kb_active.total_objects == 446


def test_stix_audit_mathematical_reconciliation():
    """Mathematically reconciles 1,877 unfiltered objects vs 1,698 active objects in raw corpus."""
    from src.corpus import build_stix_raw_documents

    bundle_path = "data/mitre/enterprise-attack.json"
    kb_all = load_stix_bundle(bundle_path, filter_active_only=False)
    kb_active = load_stix_bundle(bundle_path, filter_active_only=True)

    # 1. Unfiltered counts sum to 1,877
    assert len(kb_all.attack_patterns) == 858
    assert len(kb_all.intrusion_sets) == 191
    assert len(kb_all.malware) == 733
    assert len(kb_all.tools) == 95
    total_unfiltered = (
        len(kb_all.attack_patterns)
        + len(kb_all.intrusion_sets)
        + len(kb_all.malware)
        + len(kb_all.tools)
    )
    assert total_unfiltered == 1877

    # 2. Inactive (revoked or deprecated) breakdown
    inactive_patterns = len(kb_all.attack_patterns) - len(kb_active.attack_patterns)
    inactive_groups = len(kb_all.intrusion_sets) - len(kb_active.intrusion_sets)
    inactive_malware = len(kb_all.malware) - len(kb_active.malware)
    inactive_tools = len(kb_all.tools) - len(kb_active.tools)

    assert inactive_patterns == 161
    assert inactive_groups == 15
    assert inactive_malware == 3
    assert inactive_tools == 0
    total_inactive = inactive_patterns + inactive_groups + inactive_malware + inactive_tools
    assert total_inactive == 179

    # 3. Active counts sum to exactly 1,698
    assert len(kb_active.attack_patterns) == 697
    assert len(kb_active.intrusion_sets) == 176
    assert len(kb_active.malware) == 730
    assert len(kb_active.tools) == 95
    total_active = (
        len(kb_active.attack_patterns)
        + len(kb_active.intrusion_sets)
        + len(kb_active.malware)
        + len(kb_active.tools)
    )
    assert total_active == 1698
    assert total_unfiltered - total_inactive == total_active

    # 4. Raw corpus builder produces exactly 1,698 documents
    raw_docs = build_stix_raw_documents(kb_active)
    assert len(raw_docs) == 1698


