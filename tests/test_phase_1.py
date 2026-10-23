"""Unit tests for Phase 1 components:
- STIX corpus builder and parent-child splitting (E0/E0' control arms)
- PersistentDiskCache determinism and on-disk storage
- FreeTierRateLimiter timing guarantees
- Offline retrieval metrics (MRR, Precision@k, Recall@k, nDCG@k)
- Alias-aware attribution matching for CTI-TAA
- MITRE ID cleaner regex
"""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
import pytest

from langchain_core.documents import Document
from src.corpus import (
    build_stix_raw_documents,
    split_documents_baseline,
    split_documents_control_e0_prime,
)
from src.data_loader import STIXKnowledgeBase
from src.cache import PersistentDiskCache, FreeTierRateLimiter
from src.retrieval_eval import (
    compute_retrieval_metrics_technique,
    compute_retrieval_metrics_taa_alias_aware,
    extract_technique_ids_from_text,
    normalize_group_name,
)
from scripts.smoke_test_generation import clean_mitre_ids


def test_build_stix_raw_documents():
    dummy_kb = STIXKnowledgeBase(
        attack_patterns=[{
            "id": "attack-pattern--123",
            "type": "attack-pattern",
            "name": "PowerShell",
            "description": "Adversaries may abuse PowerShell commands.",
            "external_references": [
                {"source_name": "mitre-attack", "external_id": "T1059.001"}
            ],
            "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "execution"}],
        }],
        intrusion_sets=[],
        malware=[],
        tools=[],
        relationships=[],
        total_objects=1,
        filepath="dummy.json",
        bundle_type="bundle",
    )
    docs = build_stix_raw_documents(dummy_kb)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["mitre_id"] == "T1059.001"
    assert doc.metadata["name"] == "PowerShell"
    assert "PowerShell" in doc.page_content
    assert "T1059.001" in doc.page_content


def test_split_documents_baseline():
    dummy_doc = Document(
        page_content="Paragraph content for testing splitter. " * 150,  # ~6000 chars
        metadata={"mitre_id": "T9999", "name": "Test"},
    )
    parents, children = split_documents_baseline([dummy_doc])
    assert len(parents) >= 2
    assert len(children) >= len(parents)
    for c in children:
        assert "parent_id" in c.metadata


def test_split_documents_control_e0_prime():
    dummy_doc = Document(
        page_content="Sentence text for testing single level chunking. " * 150,  # ~7000 chars
        metadata={"mitre_id": "T9999", "name": "Test"},
    )
    chunks = split_documents_control_e0_prime([dummy_doc])
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c.page_content) <= 2200


def test_persistent_disk_cache():
    temp_dir = tempfile.mkdtemp()
    try:
        cache = PersistentDiskCache(cache_dir=temp_dir)
        ns = "test_ns"
        payload = {"query": "Find T1059", "temp": 0.1}

        # Cache miss
        assert cache.get(ns, payload) is None
        assert cache.stats()["misses"] == 1

        # Cache set
        cache.set(ns, payload, "Response text T1059")

        # Cache hit
        hit = cache.get(ns, payload)
        assert hit == "Response text T1059"
        assert cache.stats()["hits"] == 1

        # Reopen cache from disk
        cache2 = PersistentDiskCache(cache_dir=temp_dir)
        hit2 = cache2.get(ns, payload)
        assert hit2 == "Response text T1059"
    finally:
        shutil.rmtree(temp_dir)


def test_free_tier_rate_limiter():
    limiter = FreeTierRateLimiter(requests_per_minute=60, min_delay_seconds=0.05)
    t0 = time.time()
    limiter.wait_if_needed()
    limiter.wait_if_needed()
    elapsed = time.time() - t0
    assert elapsed >= 0.045
    assert limiter.total_requests == 2


def test_compute_retrieval_metrics():
    # Ground truth: T1059, T1078
    gt_str = "T1059, T1078"
    retrieved_docs = [
        {"mitre_id": "T1059", "text": "PowerShell command execution T1059"},
        {"mitre_id": "T1003", "text": "OS Credential Dumping T1003"},
        {"mitre_id": "T1078", "text": "Valid Accounts T1078"},
    ]
    metrics = compute_retrieval_metrics_technique(retrieved_docs, gt_str, k_values=[1, 3])
    # Rank 1 has T1059 -> Precision@1 = 1.0, Recall@1 = 0.5, MRR = 1.0
    assert metrics["Precision@1"] == 1.0
    assert metrics["Recall@1"] == 0.5
    assert metrics["MRR"] == 1.0
    # Top 3 has T1059 and T1078 -> Precision@3 = 2/3 = 0.6667, Recall@3 = 1.0
    assert metrics["Recall@3"] == 1.0
    assert metrics["Precision@3"] == 0.6667


def test_compute_retrieval_metrics_taa_alias_aware():
    gt_str = "Bronze President"
    alias_map = {
        "G0060": {
            "canonical_name": "Mustang Panda",
            "aliases": ["Bronze President", "RedDelta", "Earth Preta"],
        }
    }
    retrieved_docs = [
        {"mitre_id": "G0060", "text": "Mustang Panda threat actor group", "aliases": ["Bronze President"]},
        {"mitre_id": "G0010", "text": "Turla group", "aliases": []},
    ]
    metrics = compute_retrieval_metrics_taa_alias_aware(retrieved_docs, gt_str, alias_map, k_values=[1, 3])
    assert metrics["MRR"] == 1.0
    assert metrics["Precision@1"] == 1.0
    assert metrics["Recall@1"] == 1.0


def test_clean_mitre_ids():
    text1 = "The attack uses T1059.001 for PowerShell and T1078 for accounts."
    assert clean_mitre_ids(text1) == "T1059.001, T1078"

    text2 = "No techniques were identified."
    assert clean_mitre_ids(text2) == "N/A"

    text3 = "Duplicate T1059 and T1059 should be deduped."
    assert clean_mitre_ids(text3) == "T1059"
