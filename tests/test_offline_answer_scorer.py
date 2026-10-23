"""Unit tests for Offline Answer Scorer (Step D2).

Tests:
1. Toy CTI-TAA cases testing S_exact vs S_alias ("OilRig" vs "APT34", "Fancy Bear" vs "APT28")
2. Canonical hit cases where both S_exact and S_alias are 1.0
3. Technique extraction scoring on the 5 cached smoke test outputs from Phase 1c.
"""

import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.offline_answer_scorer import (
    OfflineTAAScorer,
    extract_technique_ids,
    score_technique_extraction_response,
)
from src.entity_resolver import CyberEntityResolver
from src.data_loader import load_stix_bundle


@pytest.fixture(scope="module")
def taa_scorer():
    kb = load_stix_bundle()
    resolver = CyberEntityResolver(stix_kb=kb, min_alias_len=3, random_seed=42)
    return OfflineTAAScorer(resolver=resolver)


def test_toy_oilrig_vs_apt34(taa_scorer):
    """Test S_exact vs S_alias on OilRig (canonical G0049) vs APT34 (alias).
    
    In MITRE ATT&CK, 'OilRig' is the canonical name and 'APT34' is the alias.
    If the response says 'APT34' and ground truth is 'OilRig', S_exact is 0.0,
    while S_alias is 1.0.
    """
    response = "The activity is consistent with APT34, an Iranian cyber espionage group."
    gt = "OilRig"

    res = taa_scorer.score_response(response, gt)
    # Under S_exact: 0.0 because canonical name 'OilRig' is not literally in response
    assert res["S_exact_hit"] == 0.0
    # Under S_alias: 1.0 because 'APT34' is a recognized STIX alias of OilRig
    assert res["S_alias_hit"] == 1.0
    assert "apt34" in res["matched_alias"].lower()


def test_toy_fancy_bear_vs_apt28(taa_scorer):
    """Test S_exact vs S_alias on Fancy Bear vs APT28 (G0007)."""
    response = "We attribute this campaign to Fancy Bear, targeting governmental institutions."
    gt = "APT28"

    res = taa_scorer.score_response(response, gt)
    assert res["S_exact_hit"] == 0.0
    assert res["S_alias_hit"] == 1.0
    assert "fancy bear" in res["matched_alias"].lower()


def test_canonical_and_alias_hit(taa_scorer):
    """Test response containing canonical name satisfies both S_exact and S_alias."""
    response = "Attributed to APT28 (Fancy Bear) based on infrastructure and tooling."
    gt = "APT28"

    res = taa_scorer.score_response(response, gt)
    assert res["S_exact_hit"] == 1.0
    assert res["S_alias_hit"] == 1.0


def test_five_cached_smoke_test_outputs():
    """Verify offline scoring on the 5 cached Phase 1c smoke test outputs."""
    checkpoints_dir = Path("results/phase_1/smoke_checkpoints")
    assert checkpoints_dir.is_dir(), f"Checkpoints dir missing: {checkpoints_dir}"

    for i in range(5):
        cp_file = checkpoints_dir / f"generation_row_0{i}.json" if (checkpoints_dir / f"generation_row_0{i}.json").exists() else checkpoints_dir / f"generation_row_{i}.json"
        assert cp_file.is_file(), f"Missing checkpoint: {cp_file}"

        with open(cp_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_resp = data["raw_response"]
        gt = data["ground_truth"]

        scores = score_technique_extraction_response(raw_resp, gt)

        assert "hit" in scores
        assert "precision" in scores
        assert "recall" in scores
        assert "f1" in scores
        assert 0.0 <= scores["precision"] <= 1.0
        assert 0.0 <= scores["recall"] <= 1.0
        assert 0.0 <= scores["f1"] <= 1.0
        assert scores["num_gt"] > 0
        assert scores["num_pred"] > 0
