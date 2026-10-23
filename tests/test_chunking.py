"""Unit tests for Optimization 2: Structure-Aware Chunking (C5 Requirements).

Validates:
1. Field uniqueness: distinct field tags and non-identical content per object.
2. Technique ID metadata: proper technique_id linking sub-techniques to parent.
3. Budget truncation: strictly enforced token cap B with last-chunk truncation.
4. Sibling ID match: E1b sibling expansion strictly matches technique_id, while E1c does not.
"""

import pytest
from langchain_core.documents import Document

from src.chunking import (
    count_tokens,
    extract_parent_technique_id,
    truncate_to_token_budget,
    build_field_chunks_e1a,
    StructureAwareIndex,
)
from src.data_loader import load_stix_bundle


@pytest.fixture(scope="module")
def sample_field_chunks():
    kb = load_stix_bundle("data/mitre/enterprise-attack.json")
    return build_field_chunks_e1a(kb)


def test_technique_id_extraction():
    """Verify root technique ID extraction logic."""
    assert extract_parent_technique_id("T1059.001") == "T1059"
    assert extract_parent_technique_id("T1059") == "T1059"
    assert extract_parent_technique_id("T1071.004") == "T1071"
    assert extract_parent_technique_id("G0032") == "G0032"
    assert extract_parent_technique_id("") == ""


def test_field_uniqueness(sample_field_chunks):
    """C5 Requirement 1: Verify field uniqueness per object."""
    # Group chunks by stix_id
    by_stix_id = {}
    for doc in sample_field_chunks:
        s_id = doc.metadata.get("stix_id")
        if s_id:
            by_stix_id.setdefault(s_id, []).append(doc)

    # Check attack patterns (which have up to 4 fields)
    checked_ap = 0
    for s_id, docs in by_stix_id.items():
        if docs[0].metadata.get("type") == "attack-pattern":
            fields = [d.metadata.get("field") for d in docs]
            assert len(fields) == len(set(fields)), f"Duplicate fields in STIX object {s_id}: {fields}"
            # Ensure contents are distinct
            contents = [d.page_content for d in docs]
            assert len(contents) == len(set(contents)), f"Duplicate content across fields for {s_id}"
            checked_ap += 1
            if checked_ap >= 20:
                break

    assert checked_ap >= 20, "Should have verified at least 20 attack-pattern objects"


def test_technique_id_metadata(sample_field_chunks):
    """C5 Requirement 2: Verify technique_id metadata links sub-techniques to parent."""
    tech_chunks = [d for d in sample_field_chunks if d.metadata.get("type") == "attack-pattern"]
    assert len(tech_chunks) > 0

    subtech_checked = 0
    root_checked = 0

    for doc in tech_chunks:
        m_id = doc.metadata.get("mitre_id", "")
        t_id = doc.metadata.get("technique_id", "")
        assert t_id != "", f"Missing technique_id metadata in chunk {m_id}"

        if "." in m_id:
            expected_parent = m_id.split(".")[0]
            assert t_id == expected_parent, f"Expected {expected_parent} for {m_id}, got {t_id}"
            subtech_checked += 1
        elif m_id.startswith("T"):
            assert t_id == m_id, f"Expected {m_id} for {m_id}, got {t_id}"
            root_checked += 1

    assert subtech_checked > 0, "Must verify sub-technique parent links"
    assert root_checked > 0, "Must verify root technique self links"


def test_budget_truncation():
    """C5 Requirement 3: Strictly enforced token cap B with last-chunk truncation."""
    doc1 = Document(page_content="word " * 30, metadata={"id": 1})
    doc2 = Document(page_content="word " * 40, metadata={"id": 2})
    doc3 = Document(page_content="word " * 50, metadata={"id": 3})

    # Test exact fit
    res_exact = truncate_to_token_budget([doc1, doc2], budget_tokens=70)
    total_tokens_exact = sum(count_tokens(d.page_content) for d in res_exact)
    assert total_tokens_exact == 70
    assert len(res_exact) == 2

    # Test truncation of last chunk
    res_trunc = truncate_to_token_budget([doc1, doc2, doc3], budget_tokens=50)
    total_tokens_trunc = sum(count_tokens(d.page_content) for d in res_trunc)
    assert total_tokens_trunc == 50
    assert len(res_trunc) == 2  # doc1 (30) + truncated doc2 (20)
    assert res_trunc[1].metadata.get("truncated") is True
    assert res_trunc[1].metadata.get("budget_tokens_kept") == 20

    # Test budget smaller than first chunk
    res_small = truncate_to_token_budget([doc1], budget_tokens=15)
    assert sum(count_tokens(d.page_content) for d in res_small) == 15
    assert len(res_small) == 1
    assert res_small[0].metadata.get("truncated") is True

    # Test zero budget
    res_zero = truncate_to_token_budget([doc1], budget_tokens=0)
    assert len(res_zero) == 0


def test_sibling_id_match(sample_field_chunks):
    """C5 Requirement 4: Sibling ID match in E1b vs random in E1c."""
    index = StructureAwareIndex(sample_field_chunks)

    # Find a sub-technique with known siblings (e.g. under T1059 or T1071)
    seed_candidate = None
    for doc in sample_field_chunks:
        m_id = doc.metadata.get("mitre_id", "")
        if "." in m_id and m_id.startswith("T"):
            siblings = index.get_siblings(doc)
            if len(siblings) >= 3:
                seed_candidate = doc
                break

    assert seed_candidate is not None, "Failed to find seed candidate with siblings"
    seed_parent_id = seed_candidate.metadata["technique_id"]

    # E1b: Sibling expansion
    expanded_e1b = index.expand_siblings_e1b([seed_candidate], budget_tokens=1000)
    assert len(expanded_e1b) > 1

    # Verify every added chunk shares the SAME parent technique_id
    for doc in expanded_e1b:
        doc_tech_id = doc.metadata.get("technique_id")
        assert doc_tech_id == seed_parent_id, (
            f"E1b added non-sibling: expected technique_id {seed_parent_id}, got {doc_tech_id} ({doc.metadata.get('mitre_id')})"
        )

    # E1c: Random sibling control
    expanded_e1c = index.expand_random_siblings_e1c([seed_candidate], budget_tokens=1000, random_seed=42)
    assert len(expanded_e1c) > 1

    # Verify added chunks do NOT share the same parent technique_id
    added_random = expanded_e1c[1:]
    different_count = sum(1 for d in added_random if d.metadata.get("technique_id") != seed_parent_id)
    assert different_count > 0, "E1c random control must contain non-matching technique IDs"
