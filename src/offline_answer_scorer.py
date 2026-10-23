"""Offline Answer Scorer for Threat Intelligence LLM Outputs (Step D2).

Evaluates generated threat analysis responses completely offline (zero API calls):
1. For CTI-TAA (Threat Actor Attribution):
   - Extracts candidate entity names and aliases from response text.
   - Computes S_exact (requires canonical name or ID) vs S_alias (credits any valid STIX alias).
   - Computes Hit, Precision, Recall, and F1.
2. For CTI-ATE & CTI-ATTACK (Technique Pattern Extraction):
   - Regex-extracts MITRE Technique IDs (T\d{4}(?:\.\d{3})?) from response text.
   - Computes set-based Hit, Precision, Recall, and F1 against ground-truth ID set.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.data_loader import STIXKnowledgeBase, load_stix_all_bundles
from src.entity_resolver import CyberEntityResolver


def extract_technique_ids(text: str) -> List[str]:
    """Extract all MITRE technique and sub-technique IDs from text."""
    if not isinstance(text, str):
        return []
    matches = re.findall(r"\bT\d{4}(?:\.\d{3})?\b", text)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def score_technique_extraction_response(
    response_text: str,
    ground_truth: str,
) -> Dict[str, float]:
    """Score a technique extraction response (CTI-ATE / CTI-ATTACK) against ground truth."""
    pred_ids = set(extract_technique_ids(response_text))
    gt_ids = set(extract_technique_ids(ground_truth))

    if not gt_ids:
        # Fallback split on commas
        gt_ids = {t.strip() for t in ground_truth.split(",") if t.strip().startswith("T")}

    num_gt = len(gt_ids)
    num_pred = len(pred_ids)

    if num_gt == 0:
        return {
            "hit": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "num_pred": num_pred,
            "num_gt": 0,
            "matched_ids": [],
        }

    intersection = pred_ids.intersection(gt_ids)
    num_match = len(intersection)

    hit = 1.0 if num_match > 0 else 0.0
    precision = num_match / num_pred if num_pred > 0 else 0.0
    recall = num_match / num_gt
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "hit": round(hit, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "num_pred": num_pred,
        "num_gt": num_gt,
        "num_matched": num_match,
        "matched_ids": sorted(list(intersection)),
        "predicted_ids": sorted(list(pred_ids)),
    }


class OfflineTAAScorer:
    """Offline scorer for threat actor attribution responses."""

    def __init__(self, resolver: Optional[CyberEntityResolver] = None):
        self.resolver = resolver or CyberEntityResolver()

    def score_response(
        self,
        response_text: str,
        ground_truth_raw: str,
    ) -> Dict[str, Any]:
        """Score CTI-TAA attribution response under S_exact and S_alias."""
        detected = self.resolver.detect_entities(response_text)
        pred_mitre_ids = {d.entity.mitre_id for d in detected}
        pred_canonical_names = {d.entity.canonical_name.lower() for d in detected}
        pred_matched_texts = {d.matched_text.lower() for d in detected}

        # Resolve ground truth entity from STIX
        gt_clean = ground_truth_raw.strip()
        gt_detected = self.resolver.detect_entities(gt_clean)

        gt_canonical_name = ""
        gt_mitre_id = ""
        gt_all_aliases: Set[str] = set()

        if gt_detected:
            gt_entity = gt_detected[0].entity
            gt_canonical_name = gt_entity.canonical_name
            gt_mitre_id = gt_entity.mitre_id
            gt_all_aliases = {a.lower() for a in gt_entity.aliases}
        else:
            # Fallback direct lookup
            for mid, ent in self.resolver.entities_by_id.items():
                if (
                    mid.lower() == gt_clean.lower()
                    or ent.canonical_name.lower() in gt_clean.lower()
                    or any(a.lower() in gt_clean.lower() for a in ent.aliases if len(a) >= 4)
                ):
                    gt_canonical_name = ent.canonical_name
                    gt_mitre_id = ent.mitre_id
                    gt_all_aliases = {a.lower() for a in ent.aliases}
                    break

        if not gt_canonical_name:
            gt_canonical_name = gt_clean
            gt_all_aliases = {gt_clean.lower()}

        # S_exact: requires literal occurrence of the canonical name or literal MITRE ID in response text
        exact_hit = 0.0
        if gt_mitre_id and re.search(r"\b" + re.escape(gt_mitre_id) + r"\b", response_text, re.IGNORECASE):
            exact_hit = 1.0
        elif gt_canonical_name and re.search(r"\b" + re.escape(gt_canonical_name) + r"\b", response_text, re.IGNORECASE):
            exact_hit = 1.0

        # S_alias: credits any valid STIX alias or canonical name (literal or resolver-detected)
        alias_hit = 0.0
        matched_alias = None
        if exact_hit == 1.0:
            alias_hit = 1.0
            matched_alias = gt_canonical_name
        elif gt_mitre_id in pred_mitre_ids:
            alias_hit = 1.0
            # Find which detected entity produced this
            matched_alias = next((d.matched_text for d in detected if d.entity.mitre_id == gt_mitre_id), None)
        else:
            for alias in gt_all_aliases:
                if len(alias) < 3:
                    continue
                if (
                    alias in pred_matched_texts
                    or re.search(r"\b" + re.escape(alias) + r"\b", response_text, re.IGNORECASE)
                ):
                    alias_hit = 1.0
                    matched_alias = alias
                    break

        num_pred_entities = len(detected)
        precision_alias = (1.0 / num_pred_entities) if (alias_hit and num_pred_entities > 0) else 0.0
        recall_alias = alias_hit
        f1_alias = (
            (2 * precision_alias * recall_alias / (precision_alias + recall_alias))
            if (precision_alias + recall_alias) > 0
            else 0.0
        )

        return {
            "S_exact_hit": exact_hit,
            "S_alias_hit": alias_hit,
            "matched_alias": matched_alias,
            "gt_canonical_name": gt_canonical_name,
            "gt_mitre_id": gt_mitre_id,
            "num_detected_entities": num_pred_entities,
            "detected_entities": [
                f"{d.entity.canonical_name} ({d.entity.mitre_id})" for d in detected
            ],
            "precision_alias": round(precision_alias, 4),
            "recall_alias": round(recall_alias, 4),
            "f1_alias": round(f1_alias, 4),
        }
