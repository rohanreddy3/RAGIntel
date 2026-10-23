"""Unit tests for threat actor attribution scorers (S_exact vs S_alias) under strict spec.

Tests:
1. S_exact object-level hit: requires retrieved item's STIX metadata to match canonical ID/name.
2. S_alias object-level hit: credits retrieved item whose STIX metadata matches any STIX alias.
3. S_exact text-inclusive hit: checks whether retrieved text contains canonical name.
4. S_alias text-inclusive hit: checks whether retrieved text contains any known alias.
5. Verifies unreachable query behavior (e.g. unknown entity not in STIX).
"""

import pytest
from typing import Any, Dict, List
from langchain_core.documents import Document

from src.retrieval_eval import normalize_group_name


def score_attribution_toy(
    retrieved_docs: List[Document],
    ground_truth_str: str,
    group_alias_map: Dict[str, Dict[str, Any]],
    text_inclusive: bool = False,
) -> Dict[str, int]:
    """Score retrieval under S_exact and S_alias specifications."""
    raw_gt_norm = normalize_group_name(ground_truth_str)
    
    gt_canonical_norm = None
    gt_canonical_id = None
    all_gt_aliases = {raw_gt_norm}
    is_reachable = False
    
    for gid, gdata in group_alias_map.items():
        c_norm = normalize_group_name(gdata.get("canonical_name", ""))
        a_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
        if raw_gt_norm == c_norm or raw_gt_norm in a_norms or any(a in raw_gt_norm for a in a_norms if len(a) > 3) or gid.lower() in raw_gt_norm:
            gt_canonical_norm = c_norm
            gt_canonical_id = gid.lower()
            all_gt_aliases.add(gid.lower())
            all_gt_aliases.add(c_norm)
            all_gt_aliases.update(a_norms)
            is_reachable = True
            break
            
    hit_exact = 0
    hit_alias = 0
    
    for doc in retrieved_docs:
        mid = doc.metadata.get("mitre_id", "").lower()
        name_norm = normalize_group_name(doc.metadata.get("name", ""))
        aliases = [normalize_group_name(a) for a in doc.metadata.get("aliases", [])]
        text_norm = normalize_group_name(doc.page_content)
        
        if not is_reachable:
            continue

        # Object match
        oe = 1 if (gt_canonical_id and mid == gt_canonical_id) or (gt_canonical_norm and name_norm == gt_canonical_norm) else 0
        oa = 1 if oe == 1 or (mid and mid in all_gt_aliases) or any(a in all_gt_aliases for a in aliases if a) else 0
        
        if text_inclusive:
            te = oe
            if te == 0 and gt_canonical_norm and len(gt_canonical_norm) > 3 and gt_canonical_norm in text_norm:
                te = 1
            ta = oa
            if ta == 0:
                if te == 1:
                    ta = 1
                else:
                    for a in all_gt_aliases:
                        if len(a) >= 4 and a in text_norm:
                            ta = 1
                            break
            if te == 1:
                hit_exact = 1
            if ta == 1:
                hit_alias = 1
        else:
            if oe == 1:
                hit_exact = 1
            if oa == 1:
                hit_alias = 1
                
    return {
        "reachable": int(is_reachable),
        "hit_exact": hit_exact,
        "hit_alias": hit_alias,
    }


@pytest.fixture
def toy_group_map():
    return {
        "G0007": {
            "canonical_name": "APT28",
            "aliases": ["Fancy Bear", "Sednit", "Sofacy", "Pawn Storm"],
        },
        "G0034": {
            "canonical_name": "OilRig",
            "aliases": ["APT34", "Helix Kitten", "EUROPIUM"],
        },
    }


def test_s_exact_vs_s_alias_object_level(toy_group_map):
    # Case 1: Retrieved document is APT28 intrusion-set object
    doc_canonical = Document(
        page_content="APT28 is a threat group.",
        metadata={"mitre_id": "G0007", "name": "APT28", "aliases": ["Fancy Bear", "Sednit"]}
    )
    res1 = score_attribution_toy([doc_canonical], "Fancy Bear", toy_group_map, text_inclusive=False)
    # Ground truth is "Fancy Bear". Canonical is "APT28" (G0007).
    # Since doc has canonical ID G0007, S_exact=1, S_alias=1
    assert res1["hit_exact"] == 1
    assert res1["hit_alias"] == 1

    # Case 2: Retrieved document has an alias in metadata or text, but non-canonical ID
    doc_other = Document(
        page_content="Attributed to Fancy Bear.",
        metadata={"mitre_id": "T1059", "name": "Command Line", "aliases": []}
    )
    # Under object-level scoring:
    res2_obj = score_attribution_toy([doc_other], "APT28", toy_group_map, text_inclusive=False)
    assert res2_obj["hit_exact"] == 0
    assert res2_obj["hit_alias"] == 0

    # Under text-inclusive scoring:
    res2_txt = score_attribution_toy([doc_other], "APT28", toy_group_map, text_inclusive=True)
    assert res2_txt["hit_exact"] == 0  # "APT28" canonical not in text ("Fancy Bear" is)
    assert res2_txt["hit_alias"] == 1  # "Fancy Bear" alias is in text!


def test_oilrig_apt34_toy(toy_group_map):
    # Query mentions APT34, retrieved doc has canonical OilRig
    doc_oilrig = Document(
        page_content="OilRig operations targeting energy sector.",
        metadata={"mitre_id": "G0034", "name": "OilRig", "aliases": ["APT34"]}
    )
    res = score_attribution_toy([doc_oilrig], "APT34", toy_group_map, text_inclusive=False)
    assert res["reachable"] == 1
    assert res["hit_exact"] == 1
    assert res["hit_alias"] == 1


def test_unreachable_entity(toy_group_map):
    # Entity not in STIX
    doc = Document(
        page_content="Sharp Panda threat report.",
        metadata={"mitre_id": "T1071", "name": "Web Protocols"}
    )
    res = score_attribution_toy([doc], "Sharp Panda", toy_group_map, text_inclusive=True)
    assert res["reachable"] == 0
    assert res["hit_exact"] == 0
    assert res["hit_alias"] == 0
