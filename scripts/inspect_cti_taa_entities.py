"""Inspection script for Part C1: Group and Software Entities in CTI-TAA.

Performs:
1. Inspection of what text group and software documents contain in corpus.py.
2. Across all 50 CTI-TAA queries:
   (a) How many mention a ground-truth alias anywhere in the text.
   (b) How many mention other entities (intrusion sets or software).
   (c) How many ground truths are intrusion sets (groups) vs software (malware/tools).
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_stix_all_bundles
from src.corpus import build_stix_raw_documents


def inspect_c1():
    print("=" * 70)
    print("PART C1: ENTITY INSPECTION IN CTI-TAA AND STIX CORPUS")
    print("=" * 70)

    # 1. Load STIX ALL
    stix_all = load_stix_all_bundles()
    raw_docs = build_stix_raw_documents(stix_all)

    group_docs = [d for d in raw_docs if d.metadata.get("type") == "intrusion-set"]
    software_docs = [d for d in raw_docs if d.metadata.get("type") in ["malware", "tool", "software"]]

    print(f"\n1. STIX ALL Document Counts in corpus.py:")
    print(f"   Total raw documents: {len(raw_docs)}")
    print(f"   Intrusion-set (group) documents: {len(group_docs)}")
    print(f"   Software (malware/tool) documents: {len(software_docs)}")

    # Show sample text of group document and software document
    print("\n--- Sample Group Document (First 300 chars) ---")
    if group_docs:
        print(group_docs[0].page_content[:300])
        print("Metadata:", group_docs[0].metadata)

    print("\n--- Sample Software Document (First 300 chars) ---")
    if software_docs:
        print(software_docs[0].page_content[:300])
        print("Metadata:", software_docs[0].metadata)

    # Build entity registry from STIX ALL
    # Groups: canonical_name, mitre_id, aliases
    # Software: canonical_name, mitre_id, aliases
    entities_by_type = {"intrusion-set": {}, "software": {}}
    alias_to_entity = {}  # lower alias -> (canonical_name, mitre_id, type)

    valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]

    for obj in stix_all.intrusion_sets:
        name = obj.get("name")
        ext_refs = obj.get("external_references", [])
        mitre_id = next((r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources), None)
        aliases = set(obj.get("aliases", []))
        if name:
            aliases.add(name)
        if obj.get("x_mitre_aliases"):
            aliases.update(obj.get("x_mitre_aliases", []))
        if mitre_id and name:
            entities_by_type["intrusion-set"][mitre_id] = {
                "name": name,
                "mitre_id": mitre_id,
                "aliases": list(aliases),
            }
            for a in aliases:
                a_clean = a.strip().lower()
                if len(a_clean) >= 3:
                    alias_to_entity[a_clean] = (name, mitre_id, "intrusion-set")

    for obj in stix_all.malware + stix_all.tools:
        name = obj.get("name")
        ext_refs = obj.get("external_references", [])
        mitre_id = next((r.get("external_id") for r in ext_refs if r.get("source_name") in valid_sources), None)
        aliases = set(obj.get("x_mitre_aliases", []))
        if name:
            aliases.add(name)
        if obj.get("aliases"):
            aliases.update(obj.get("aliases", []))
        if mitre_id and name:
            entities_by_type["software"][mitre_id] = {
                "name": name,
                "mitre_id": mitre_id,
                "aliases": list(aliases),
            }
            for a in aliases:
                a_clean = a.strip().lower()
                if len(a_clean) >= 3:
                    alias_to_entity[a_clean] = (name, mitre_id, "software")

    print(f"\n2. STIX ALL Entities Extracted:")
    print(f"   Intrusion sets: {len(entities_by_type['intrusion-set'])}")
    print(f"   Software: {len(entities_by_type['software'])}")
    print(f"   Indexed unique aliases (len >= 3): {len(alias_to_entity)}")

    # 2. Inspect CTI-TAA
    df_taa = pd.read_excel("data/datasets/cti-taa.xlsx")
    print(f"\n3. Inspecting CTI-TAA ({len(df_taa)} queries):")

    gt_types = {"intrusion-set": 0, "software": 0, "unknown": 0}
    queries_mention_gt_alias = 0
    queries_mention_other_entities = 0

    per_query_details = []

    for idx, row in df_taa.iterrows():
        query_text = str(row["query"])
        gt_raw = str(row["ground_truth"]).strip()

        # Identify GT entity
        gt_entity_match = None
        for a_lower, (cname, mid, etype) in alias_to_entity.items():
            if a_lower == gt_raw.lower():
                gt_entity_match = (cname, mid, etype)
                break
        
        if not gt_entity_match:
            # Check by mitre_id directly
            for mid, info in entities_by_type["intrusion-set"].items():
                if mid.lower() == gt_raw.lower() or info["name"].lower() == gt_raw.lower():
                    gt_entity_match = (info["name"], mid, "intrusion-set")
                    break
            if not gt_entity_match:
                for mid, info in entities_by_type["software"].items():
                    if mid.lower() == gt_raw.lower() or info["name"].lower() == gt_raw.lower():
                        gt_entity_match = (info["name"], mid, "software")
                        break

        if gt_entity_match:
            gt_types[gt_entity_match[2]] += 1
            gt_cname, gt_mid, gt_type = gt_entity_match
            # All aliases of GT entity
            gt_aliases = set(a.lower() for a in entities_by_type[gt_type][gt_mid]["aliases"])
        else:
            gt_types["unknown"] += 1
            gt_cname, gt_mid, gt_type = gt_raw, "Unknown", "unknown"
            gt_aliases = {gt_raw.lower()}

        # Check: does query mention GT alias anywhere?
        # Use word boundary regex
        gt_mentioned = False
        for a in gt_aliases:
            if len(a) < 3:
                continue
            pattern = r"\b" + re.escape(a) + r"\b"
            if re.search(pattern, query_text, re.IGNORECASE):
                gt_mentioned = True
                break

        if gt_mentioned:
            queries_mention_gt_alias += 1

        # Check other entities mentioned in query
        other_entities_found = set()
        for a_lower, (cname, mid, etype) in alias_to_entity.items():
            if len(a_lower) < 3:
                continue
            # Skip if this is the GT entity
            if gt_entity_match and mid == gt_mid:
                continue
            pattern = r"\b" + re.escape(a_lower) + r"\b"
            if re.search(pattern, query_text, re.IGNORECASE):
                other_entities_found.add(f"{cname} ({mid}, {etype})")

        if len(other_entities_found) > 0:
            queries_mention_other_entities += 1

        per_query_details.append({
            "idx": idx,
            "gt_raw": gt_raw,
            "gt_canonical": gt_cname,
            "gt_mid": gt_mid,
            "gt_type": gt_type,
            "gt_mentioned_in_query": gt_mentioned,
            "num_other_entities": len(other_entities_found),
            "other_entities_sample": list(other_entities_found)[:3],
        })

    print(f"\n--- CTI-TAA Findings Summary (N={len(df_taa)}) ---")
    print(f"(a) Queries mentioning ground-truth alias anywhere in text: {queries_mention_gt_alias} / {len(df_taa)} ({queries_mention_gt_alias/len(df_taa)*100:.1f}%)")
    print(f"(b) Queries mentioning OTHER entities in text: {queries_mention_other_entities} / {len(df_taa)} ({queries_mention_other_entities/len(df_taa)*100:.1f}%)")
    print(f"(c) Ground-truth entity types breakdown:")
    print(f"    - Intrusion Sets (Groups): {gt_types['intrusion-set']} ({gt_types['intrusion-set']/len(df_taa)*100:.1f}%)")
    print(f"    - Software (Malware/Tools): {gt_types['software']} ({gt_types['software']/len(df_taa)*100:.1f}%)")
    print(f"    - Unknown / Unmapped: {gt_types['unknown']} ({gt_types['unknown']/len(df_taa)*100:.1f}%)")

    # Save summary
    out_path = Path("results/phase_2/cti_taa_entity_inspection.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "dataset": "cti-taa",
            "num_queries": len(df_taa),
            "queries_mention_gt_alias": queries_mention_gt_alias,
            "queries_mention_other_entities": queries_mention_other_entities,
            "ground_truth_types": gt_types,
            "per_query_details": per_query_details,
        }, f, indent=2)
    print(f"\nSaved detailed inspection to {out_path}")


if __name__ == "__main__":
    inspect_c1()
