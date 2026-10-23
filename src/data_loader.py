"""Data loading and schema validation module for RAG CTI Thesis experiments.

Supports:
- CTI-ATE (Adversary Technique Extraction)
- CTI-TAA (Threat Actor Attribution)
- CTI-ATTACK (Technique Pattern Extraction)
- MITRE ATT&CK Enterprise STIX 2.1 Bundle
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def compute_query_id(query_text: str) -> str:
    """Compute sha1(normalized query text)[:12] for row alignment across all pipelines."""
    norm = str(query_text).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


@dataclass
class DatasetInfo:
    name: str
    filepath: str
    sheet_name: str
    df: pd.DataFrame
    num_samples: int
    columns: List[str]

    def summary(self) -> str:
        return (
            f"Dataset '{self.name}': {self.num_samples} samples, "
            f"columns: {self.columns}, sheet: '{self.sheet_name}'"
        )


DATASET_CONFIGS = {
    "cti-ate": {
        "file_key": "cti_ate",
        "default_path": "data/datasets/cti-ate.xlsx",
        "sheet_name": "Sheet1",
        "expected_columns": ["query", "ground_truth"],
        "expected_count": 60,
    },
    "cti-taa": {
        "file_key": "cti_taa",
        "default_path": "data/datasets/cti-taa.xlsx",
        "sheet_name": "Sheet1",
        "expected_columns": ["query", "ground_truth"],
        "expected_count": 50,
    },
    "CTI-ATTACK": {
        "file_key": "cti_attack",
        "default_path": "data/datasets/CTI-ATTACK.xlsx",
        "sheet_name": "CTI-ATTACK",
        "expected_columns": ["query", "ground_truth"],
        "expected_count": 229,
    },
}


def load_benchmark_dataset(
    dataset_name: str,
    filepath: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> DatasetInfo:
    """Load and validate one of the three CTI benchmark datasets."""
    # Normalize name lookup
    cfg_key = None
    for k in DATASET_CONFIGS:
        if k.lower() == dataset_name.lower():
            cfg_key = k
            break

    if not cfg_key:
        valid_options = list(DATASET_CONFIGS.keys())
        raise ValueError(f"Unknown dataset '{dataset_name}'. Must be one of {valid_options}")

    cfg = DATASET_CONFIGS[cfg_key]
    path = Path(filepath or cfg["default_path"])
    sheet = sheet_name or cfg["sheet_name"]

    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    # Load from Excel
    df = pd.read_excel(path, sheet_name=sheet)

    # Validate required columns
    missing_cols = [c for c in cfg["expected_columns"] if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Dataset '{cfg_key}' is missing required columns: {missing_cols}. "
            f"Present columns: {list(df.columns)}"
        )

    # Ensure query column is non-empty string
    df = df.dropna(subset=["query"]).copy()
    df["query"] = df["query"].astype(str).str.strip()
    df = df[df["query"] != ""]

    # Ensure ground_truth column exists and is string
    if "ground_truth" in df.columns:
        df["ground_truth"] = df["ground_truth"].fillna("").astype(str).str.strip()

    # Assign query_id = sha1(normalized query text)[:12]
    df["query_id"] = df["query"].apply(compute_query_id)

    return DatasetInfo(
        name=cfg_key,
        filepath=str(path),
        sheet_name=sheet,
        df=df,
        num_samples=len(df),
        columns=list(df.columns),
    )


def load_all_benchmark_datasets(base_dir: str = "data/datasets") -> Dict[str, DatasetInfo]:
    """Load all three benchmark datasets."""
    results = {}
    for name in DATASET_CONFIGS:
        results[name] = load_benchmark_dataset(name)
    return results


@dataclass
class STIXKnowledgeBase:
    filepath: str
    bundle_type: str
    total_objects: int
    attack_patterns: List[Dict[str, Any]]
    intrusion_sets: List[Dict[str, Any]]
    malware: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]

    def get_techniques_map(self) -> Dict[str, Dict[str, Any]]:
        """Map technique MITRE ID (e.g., T1071, T1071.001) to technique metadata."""
        tech_map = {}
        valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]
        for obj in self.attack_patterns:
            ext_refs = obj.get("external_references", [])
            mitre_id = next(
                (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
                None,
            )
            if mitre_id:
                tech_map[mitre_id] = {
                    "stix_id": obj.get("id"),
                    "mitre_id": mitre_id,
                    "name": obj.get("name"),
                    "description": obj.get("description", ""),
                    "is_subtechnique": obj.get("x_mitre_is_subtechnique", False),
                    "tactics": [
                        p.get("phase_name")
                        for p in obj.get("kill_chain_phases", [])
                        if p.get("kill_chain_name") in valid_sources
                    ],
                }
        return tech_map

    def get_group_alias_map(self) -> Dict[str, Dict[str, Any]]:
        """Extract intrusion-set canonical IDs and aliases for entity resolution (O1)."""
        group_map = {}
        valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]
        for obj in self.intrusion_sets:
            ext_refs = obj.get("external_references", [])
            mitre_id = next(
                (r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources),
                None,
            )
            canonical_name = obj.get("name")
            aliases = list(obj.get("aliases", []))
            if canonical_name and canonical_name not in aliases:
                aliases.insert(0, canonical_name)

            if mitre_id and canonical_name:
                group_map[mitre_id] = {
                    "stix_id": obj.get("id"),
                    "mitre_id": mitre_id,
                    "canonical_name": canonical_name,
                    "aliases": aliases,
                    "description": obj.get("description", ""),
                }
        return group_map


def is_active_stix_object(obj: Dict[str, Any]) -> bool:
    """Return True if the STIX object is active (neither revoked nor deprecated)."""
    if obj.get("revoked", False):
        return False
    if obj.get("x_mitre_deprecated", False):
        return False
    return True


def load_stix_bundle(
    filepath: str = "data/mitre/enterprise-attack.json",
    filter_active_only: bool = True,
) -> STIXKnowledgeBase:
    """Load MITRE ATT&CK Enterprise STIX bundle (E0-STIX-ENT)."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"STIX bundle file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_objects = data.get("objects", [])
    if filter_active_only:
        objects = [o for o in all_objects if is_active_stix_object(o)]
    else:
        objects = all_objects

    attack_patterns = [o for o in objects if o.get("type") == "attack-pattern"]
    intrusion_sets = [o for o in objects if o.get("type") == "intrusion-set"]
    malware = [o for o in objects if o.get("type") == "malware"]
    tools = [o for o in objects if o.get("type") == "tool"]
    relationships = [o for o in objects if o.get("type") == "relationship"]

    return STIXKnowledgeBase(
        filepath=str(path),
        bundle_type=data.get("type", "bundle"),
        total_objects=len(objects),
        attack_patterns=attack_patterns,
        intrusion_sets=intrusion_sets,
        malware=malware,
        tools=tools,
        relationships=relationships,
    )


def load_stix_all_bundles(
    base_dir: str = "data/mitre",
    filter_active_only: bool = True,
) -> STIXKnowledgeBase:
    """Load combined MITRE ATT&CK STIX bundle across Enterprise, Mobile, and ICS (E0-STIX-ALL)."""
    dir_p = Path(base_dir)
    bundle_files = [
        dir_p / "enterprise-attack.json",
        dir_p / "mobile-attack.json",
        dir_p / "ics-attack.json",
    ]

    dedup_objects: Dict[str, Dict[str, Any]] = {}

    for bf in bundle_files:
        if not bf.is_file():
            continue
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
        for obj in data.get("objects", []):
            if filter_active_only and not is_active_stix_object(obj):
                continue
            oid = obj.get("id")
            if oid and oid not in dedup_objects:
                dedup_objects[oid] = obj

    objects = list(dedup_objects.values())
    attack_patterns = [o for o in objects if o.get("type") == "attack-pattern"]
    intrusion_sets = [o for o in objects if o.get("type") == "intrusion-set"]
    malware = [o for o in objects if o.get("type") == "malware"]
    tools = [o for o in objects if o.get("type") == "tool"]
    relationships = [o for o in objects if o.get("type") == "relationship"]

    return STIXKnowledgeBase(
        filepath=str(dir_p),
        bundle_type="bundle_all",
        total_objects=len(objects),
        attack_patterns=attack_patterns,
        intrusion_sets=intrusion_sets,
        malware=malware,
        tools=tools,
        relationships=relationships,
    )

