"""Inspect Part 2 items missing from 3B report:

2.2: Active techniques per domain vs 1,514 in index.
2.3: Detected-entity strings with match spans for 5 cti-ate rows (check SideCopy prefix on rows 0 and 5).
2.4: Case studies Row 21 and Row 24 exact V1 prefix strings, V0 vs V1 top-10 IDs.
2.5: Count of cti-taa rows with ground truth 'Lazarus' (2 vs 5), and cti-ate rows 0-3 ground truth printed straight from xlsx.
"""

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.entity_resolver import CyberEntityResolver


def main():
    print("=" * 80)
    print("INSPECTING PART 2 LOOSE ENDS")
    print("=" * 80)

    kb = load_stix_all_bundles()
    resolver = CyberEntityResolver(stix_kb=kb, min_alias_len=3, random_seed=42)

    # -------------------------------------------------------------------------
    # Item 2.2: Active techniques per domain
    # -------------------------------------------------------------------------
    print("\n--- 2.2: Active Technique Count per Domain vs 1,514 ---")
    valid_sources = ["mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"]
    enterprise_techs = set()
    mobile_techs = set()
    ics_techs = set()

    for obj in kb.attack_patterns:
        ext_refs = obj.get("external_references", [])
        for r in ext_refs:
            s_name = r.get("source_name")
            m_id = r.get("external_id")
            if s_name == "mitre-attack" and m_id:
                enterprise_techs.add(m_id)
            elif s_name == "mitre-mobile-attack" and m_id:
                mobile_techs.add(m_id)
            elif s_name == "mitre-ics-attack" and m_id:
                ics_techs.add(m_id)

    total_active_techs = enterprise_techs | mobile_techs | ics_techs
    print(f"Enterprise techniques: {len(enterprise_techs)}")
    print(f"Mobile techniques:     {len(mobile_techs)}")
    print(f"ICS techniques:        {len(ics_techs)}")
    print(f"Total Unique Active Techniques in STIX: {len(total_active_techs)}")

    # -------------------------------------------------------------------------
    # Item 2.3: Entity spans for 5 cti-ate rows (check SideCopy on rows 0 and 5)
    # -------------------------------------------------------------------------
    print("\n--- 2.3: Detected Entity Strings & Match Spans for cti-ate Rows 0-5 ---")
    ds_ate = load_benchmark_dataset("cti-ate")
    df_ate = ds_ate.df

    for idx in range(6):
        row = df_ate.iloc[idx]
        q_text = str(row["query"])
        # Detect entities with resolver
        expanded_q, detected = resolver.expand_query(q_text, variant="V1", max_expansion_tokens=64)
        print(f"\n[cti-ate Row {idx}] Query length: {len(q_text)} chars")
        print(f"  Prefix injected: {repr(expanded_q[:120])}")
        print(f"  Detected entities count: {len(detected)}")
        for d in detected:
            print(f"    - Entity: {d.entity.canonical_name} ({d.entity.mitre_id}) | Matched string: '{d.matched_text}' | Span: ({d.start_char}, {d.end_char})")

    # -------------------------------------------------------------------------
    # Item 2.4: Row 21 & 24 Case Studies
    # -------------------------------------------------------------------------
    print("\n--- 2.4: Row 21 & Row 24 Case Studies ---")
    ds_taa = load_benchmark_dataset("cti-taa")
    df_taa = ds_taa.df

    for target_idx in [21, 24]:
        row = df_taa.iloc[target_idx]
        q_text = str(row["query"])
        gt = str(row.get("ground_truth", ""))
        exp_v1, det_v1 = resolver.expand_query(q_text, variant="V1", max_expansion_tokens=64)
        print(f"\n[cti-taa Row {target_idx}] GT: {gt}")
        print(f"  V1 Prefix: {repr(exp_v1[:140])}")
        print(f"  Detected Entities: {[(d.entity.canonical_name, d.entity.mitre_id, d.matched_text, (d.start_char, d.end_char)) for d in det_v1]}")

    # -------------------------------------------------------------------------
    # Item 2.5: Lazarus Count in cti-taa & cti-ate Rows 0-3 from xlsx
    # -------------------------------------------------------------------------
    print("\n--- 2.5: Count of Lazarus in cti-taa & cti-ate 0-3 GT from xlsx ---")
    lazarus_exact_rows = []
    lazarus_substr_rows = []
    for idx, row in df_taa.iterrows():
        gt = str(row.get("ground_truth", ""))
        if gt.strip().lower() == "lazarus":
            lazarus_exact_rows.append((idx, gt))
        if "lazarus" in gt.lower():
            lazarus_substr_rows.append((idx, gt))

    print(f"cti-taa rows with exact GT == 'Lazarus': {len(lazarus_exact_rows)} (Rows: {[r[0] for r in lazarus_exact_rows]})")
    print(f"cti-taa rows containing 'lazarus' substring: {len(lazarus_substr_rows)}")
    for r in lazarus_substr_rows:
        print(f"  Row {r[0]}: {r[1]}")

    print("\ncti-ate Rows 0-3 Ground Truth directly from xlsx:")
    for idx in range(4):
        print(f"  Row {idx}: {df_ate.iloc[idx].get('ground_truth')}")


if __name__ == "__main__":
    main()
