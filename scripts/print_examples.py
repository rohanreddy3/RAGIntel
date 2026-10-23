"""Part A2: Ground-Truth Match Extraction, Span Verification, and Boilerplate Analysis.

Writes JSON with:
- query_id
- row_idx
- query[:200]
- ground_truth
- detected_entities: list of {canonical_name, mitre_id, entity_type, matched_alias, span: [start, end], text_at_span}

Asserts query[start:end].lower() == matched_alias.lower() for every match in all 339 queries.
Reports violations if any.
For cti-taa:
- Prints most frequently detected entities across the 50 queries.
- Reports number of queries with identical detected entity sets (boilerplate false positives).
"""

import collections
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles, compute_query_id
from src.entity_resolver import CyberEntityResolver


def main():
    print("=" * 80)
    print("PART A2: SCRIPT-DRIVEN EXAMPLE EXTRACTION & SPAN AUDIT")
    print("=" * 80)

    stix_kb = load_stix_all_bundles()
    resolver = CyberEntityResolver(stix_kb=stix_kb, min_alias_len=3, random_seed=42)

    datasets = ["cti-ate", "cti-taa", "CTI-ATTACK"]
    all_examples: Dict[str, List[Dict[str, Any]]] = {}
    total_matches = 0
    violations = []

    # Dataset inspection records
    for ds_name in datasets:
        ds = load_benchmark_dataset(ds_name)
        df = ds.df
        all_examples[ds_name] = []

        for idx, row in df.iterrows():
            q = str(row["query"])
            gt = str(row.get("ground_truth", ""))
            qid = row.get("query_id") or compute_query_id(q)

            detected_raw = resolver.detect_entities(q)
            detected_serialized = []

            for d in detected_raw:
                total_matches += 1
                span = (d.start_char, d.end_char)
                text_at_span = q[d.start_char : d.end_char]
                matched_alias = d.matched_text

                # Assertion: query[span].lower() == matched_alias.lower()
                if text_at_span.lower() != matched_alias.lower():
                    violations.append({
                        "dataset": ds_name,
                        "row_idx": int(idx),
                        "query_id": qid,
                        "span": span,
                        "text_at_span": text_at_span,
                        "matched_alias": matched_alias,
                    })

                detected_serialized.append({
                    "canonical_name": d.entity.canonical_name,
                    "mitre_id": d.entity.mitre_id,
                    "entity_type": d.entity.entity_type,
                    "matched_alias": matched_alias,
                    "span": [d.start_char, d.end_char],
                    "text_at_span": text_at_span,
                    "is_canonical": d.is_canonical,
                })

            all_examples[ds_name].append({
                "query_id": qid,
                "row_idx": int(idx),
                "query_preview": q[:200],
                "ground_truth": gt,
                "num_detected": len(detected_serialized),
                "detected_entities": detected_serialized,
            })

    # Assertions across all 339 queries
    total_queries = sum(len(v) for v in all_examples.values())
    print(f"Total queries processed: {total_queries} (expected 339)")
    print(f"Total entity matches checked: {total_matches}")
    print(f"Total span violations: {len(violations)}")
    assert len(violations) == 0, f"Span violations encountered: {violations}"
    print("[PASS] Assertion query[span].lower() == matched_alias.lower() held for 100% of matches!")

    # CTI-TAA Boilerplate False-Positive Analysis
    print("\n" + "-" * 60)
    print("CTI-TAA BOILERPLATE FALSE-POSITIVE ANALYSIS (N=50)")
    print("-" * 60)

    taa_examples = all_examples["cti-taa"]
    entity_counts = collections.Counter()
    set_counts = collections.Counter()

    for item in taa_examples:
        detected = item["detected_entities"]
        names = tuple(sorted(set(d["canonical_name"] for d in detected)))
        set_counts[names] += 1
        for d in detected:
            entity_counts[d["canonical_name"]] += 1

    print("Top 10 Most Frequently Detected Entities in cti-taa:")
    for ent, count in entity_counts.most_common(10):
        print(f"  - {ent:25s}: {count:2d} queries ({count/50*100:.1f}%)")

    print("\nQueries Sharing Identical Detected Entity Sets:")
    identical_groups = {k: v for k, v in set_counts.items() if v > 1}
    for ent_set, cnt in sorted(identical_groups.items(), key=lambda x: x[1], reverse=True):
        set_str = ", ".join(ent_set) if ent_set else "(Empty set)"
        print(f"  - [{cnt} queries]: {set_str}")

    out_file = REPO_ROOT / "results" / "phase_4" / "detected_examples_audit.json"
    payload = {
        "metadata": {
            "total_queries": total_queries,
            "total_matches": total_matches,
            "total_violations": len(violations),
        },
        "cti_taa_boilerplate": {
            "top_entities": dict(entity_counts.most_common(15)),
            "identical_sets": {", ".join(k) if k else "EMPTY": v for k, v in set_counts.items() if v > 1},
        },
        "examples": all_examples,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved detected examples audit to {out_file}")


if __name__ == "__main__":
    main()
