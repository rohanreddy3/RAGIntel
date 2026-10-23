"""Unit tests for CyberEntityResolver (Step C2).

Tests:
1. Toy entity detection (intrusion sets and software)
2. Known collision handling and disambiguation
3. Query expansion variants (V0, V1, V2, V3)
4. Contamination guard: Verifies resolver never references or reads benchmark dataset files.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.entity_resolver import CyberEntityResolver, STIXEntity
from src.data_loader import load_stix_bundle


@pytest.fixture(scope="module")
def resolver():
    kb = load_stix_bundle()
    return CyberEntityResolver(stix_kb=kb, min_alias_len=3, random_seed=42)


def test_entity_detection_toy_example(resolver):
    """Verify entity detection on a toy query with actor and tool."""
    query = (
        "Adversary activity associated with APT28 (also known as Fancy Bear) "
        "utilized Cobalt Strike and Mimikatz for lateral movement."
    )
    detected = resolver.detect_entities(query)
    detected_ids = {d.entity.mitre_id for d in detected}
    detected_names = {d.entity.canonical_name for d in detected}

    # APT28 is G0007
    assert "G0007" in detected_ids or "APT28" in detected_names
    # Cobalt Strike is S0154
    assert "S0154" in detected_ids or "Cobalt Strike" in detected_names
    # Mimikatz is S0002
    assert "S0002" in detected_ids or "Mimikatz" in detected_names


def test_min_length_filter_no_short_words(resolver):
    """Verify that 1-2 letter English words are never indexed as aliases."""
    for norm_alias in resolver.alias_to_entities:
        assert len(norm_alias) >= 3, f"Spurious short alias found: '{norm_alias}'"


def test_query_expansion_variants(resolver):
    """Test all 4 query expansion variants: V0, V1, V2, V3."""
    raw_query = "The threat group Lazarus Group used WannaCry to encrypt files."

    # V0: Baseline unmodified
    q_v0, _ = resolver.expand_query(raw_query, variant="V0")
    assert q_v0 == raw_query

    # V1: Prepend detected aliases (budget-capped)
    q_v1, det_v1 = resolver.expand_query(raw_query, variant="V1", max_expansion_tokens=64)
    assert len(det_v1) > 0
    assert q_v1 != raw_query
    assert raw_query in q_v1
    assert "Lazarus Group" in q_v1

    # V2: Canonical name + MITRE ID only
    q_v2, det_v2 = resolver.expand_query(raw_query, variant="V2")
    assert "G0032" in q_v2 or "Lazarus Group" in q_v2
    assert raw_query in q_v2

    # V3: Random entity ablation control
    q_v3, _ = resolver.expand_query(raw_query, variant="V3", max_expansion_tokens=64)
    assert q_v3 != raw_query
    assert raw_query in q_v3


def test_collision_logging(resolver):
    """Verify that alias collisions across multiple STIX entities are detected and logged."""
    assert isinstance(resolver.collision_log, dict)
    # The collision log documents any alias shared by >= 2 entities
    for alias, cands in resolver.collision_log.items():
        assert len(cands) >= 2


def test_contamination_guard_no_benchmark_access():
    """Verify resolver code and module never imports, opens, or accesses benchmark datasets."""
    resolver_file = Path(__file__).resolve().parent.parent / "src" / "entity_resolver.py"
    with open(resolver_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    forbidden_patterns = [
        "cti-ate",
        "cti-taa",
        "CTI-ATTACK",
        "data/datasets",
        "read_excel",
        "Sheet1",
        "ground_truth",
    ]

    for pat in forbidden_patterns:
        assert pat not in code_content, (
            f"Contamination Guard Violation: Forbidden benchmark pattern '{pat}' "
            f"found in src/entity_resolver.py!"
        )
