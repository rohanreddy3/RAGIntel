"""Generate Phase 6D Part G Deterministic Case Studies.

Protocol:
- For cti-taa choose 5 queries where Vrel wins and 3 where it loses (rule: first rows by row_idx in each category).
- For each print:
  - query_id
  - ground truth
  - detected software
  - top-3 voted groups
  - whether the ground-truth group profile is in the retrieved context
  - model answer
- Assert that every printed span exists verbatim in the query text.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, load_stix_all_bundles
from src.retrieval_eval import normalize_group_name
from scripts.run_o1_phase5_benchmark import (
    FIXED_STOPLIST,
    build_stix_indices,
    build_alias_matchers,
    split_query,
)
from scripts.compute_phase6c_metrics import score_group_match


def main():
    print("=" * 80)
    print("PHASE 6D PART G: DETERMINISTIC CASE STUDIES")
    print("=" * 80)

    out_dir = REPO_ROOT / "results" / "phase_6d"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = REPO_ROOT / ".cache" / "api_runner"

    # 1. Load cti-taa benchmark dataset
    df_taa = load_benchmark_dataset("cti-taa").df

    # 2. Load STIX KB and build graph
    stix_kb = load_stix_all_bundles()
    group_alias_map = stix_kb.get_group_alias_map()
    intrusion_sets, software, software_to_groups, software_weights = build_stix_indices(stix_kb)
    matchers = build_alias_matchers(intrusion_sets, software)

    # 3. Load cached answers for Vrel and V0h
    vrel_records = [json.load(open(cache_dir / f"Vrel_cti-taa_row_{i}.json", encoding="utf-8")) for i in range(50)]
    v0h_records = [json.load(open(cache_dir / f"V0h_cti-taa_row_{i}.json", encoding="utf-8")) for i in range(50)]
    v1_records = [json.load(open(cache_dir / f"cti-taa_B2_V1_cti-taa_row_{i}.json", encoding="utf-8")) for i in range(50)]

    # 4. Score all rows under Vrel, V0h, and V1
    row_stats = []
    for idx, row in df_taa.iterrows():
        gt_str = str(row["ground_truth"])
        ans_vrel = vrel_records[idx].get("raw_answer", "")
        ans_v0h = v0h_records[idx].get("raw_answer", "")
        ans_v1 = v1_records[idx].get("raw_answer", "")

        m_vrel = score_group_match(ans_vrel, gt_str, group_alias_map)
        m_v0h = score_group_match(ans_v0h, gt_str, group_alias_map)
        m_v1 = score_group_match(ans_v1, gt_str, group_alias_map)

        row_stats.append({
            "idx": idx,
            "query_id": str(row.get("query_id", f"cti-taa-{idx}")),
            "query": str(row["query"]),
            "ground_truth": gt_str,
            "vrel": m_vrel,
            "v0h": m_v0h,
            "v1": m_v1,
            "ans_vrel": ans_vrel,
            "ans_v0h": ans_v0h,
            "contexts_vrel": vrel_records[idx].get("contexts_used", []),
        })

    # Rule: First 5 rows where Vrel wins over V0h on exact attribution (or alias if tied)
    # Wins: m_vrel > m_v0h on v1_exact (rows 0, 8, 22, 24, 41)
    # Losses: m_vrel < m_v0h on v1_exact (rows 20, 26, 36, 38)
    win_indices = [r["idx"] for r in row_stats if r["vrel"]["v1_exact"] > r["v0h"]["v1_exact"]][:5]
    loss_indices = [r["idx"] for r in row_stats if r["vrel"]["v1_exact"] < r["v0h"]["v1_exact"]][:3]

    print(f"Selected Win rows (Vrel > V0h): {win_indices}")
    print(f"Selected Loss rows (Vrel < V0h): {loss_indices}")

    case_studies = []

    for category, indices in [("WIN (Vrel > V0h)", win_indices), ("LOSS (Vrel < V0h)", loss_indices)]:
        for idx in indices:
            r = row_stats[idx]
            q_text = r["query"]
            _, body_text, _ = split_query(q_text)
            gt_raw = r["ground_truth"]

            # Entity resolution detection
            detected_sw = []
            seen_spans = []
            for pat, can_name, alias, etype, sid in matchers:
                if etype not in ["malware", "tool"]:
                    continue
                for m in pat.finditer(body_text):
                    s, e = m.span()
                    if any(s < oe and e > os_ for os_, oe in seen_spans):
                        continue
                    if body_text[s:e] == alias:
                        seen_spans.append((s, e))
                        detected_sw.append({
                            "software_id": sid,
                            "canonical_name": can_name,
                            "matched_alias": alias,
                            "span_start": s,
                            "span_end": e,
                        })

            # ASSERTION: Every printed span exists verbatim in the query text!
            for d in detected_sw:
                span_text = d["matched_alias"]
                assert span_text in q_text, f"ASSERTION FAILED: Span '{span_text}' does not exist in query text for row {idx}!"

            # Group voting
            group_scores = defaultdict(float)
            for d in detected_sw:
                sw_id = d["software_id"]
                w = software_weights.get(sw_id, 0.0)
                for g_id in software_to_groups.get(sw_id, []):
                    group_scores[g_id] += w

            sorted_groups = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            top_3_voted = []
            for g_id, sc in sorted_groups:
                g_info = intrusion_sets.get(g_id, {})
                top_3_voted.append({
                    "intrusion_set_id": g_id,
                    "canonical_name": g_info.get("canonical_name", ""),
                    "mitre_id": g_info.get("mitre_id", ""),
                    "score": round(sc, 4),
                })

            # Check if ground-truth group profile is in retrieved context
            all_gt_aliases = {normalize_group_name(gt_raw)}
            for gid, gdata in group_alias_map.items():
                c_norm = normalize_group_name(gdata.get("canonical_name", ""))
                a_norms = {normalize_group_name(a) for a in gdata.get("aliases", [])}
                if normalize_group_name(gt_raw) in ({c_norm} | a_norms):
                    all_gt_aliases.add(gid.lower())
                    all_gt_aliases.add(c_norm)
                    all_gt_aliases.update(a_norms)

            ctx_text = " ".join(r["contexts_vrel"]).lower()
            gt_in_context = any(len(a) >= 3 and a in ctx_text for a in all_gt_aliases)

            study = {
                "category": category,
                "row_idx": idx,
                "query_id": r["query_id"],
                "ground_truth": gt_raw,
                "detected_software": [f"{d['matched_alias']} (canonical: {d['canonical_name']})" for d in detected_sw],
                "top_3_voted_groups": [f"{g['canonical_name']} ({g['mitre_id']}, score: {g['score']})" for g in top_3_voted],
                "ground_truth_in_context": bool(gt_in_context),
                "model_answer_vrel": r["ans_vrel"].strip(),
                "model_answer_v0h": r["ans_v0h"].strip(),
                "vrel_score": r["vrel"],
                "v0h_score": r["v0h"],
            }
            case_studies.append(study)

    # Save to JSON
    with open(out_dir / "case_studies_cti_taa.json", "w", encoding="utf-8") as f:
        json.dump(case_studies, f, indent=2)

    # Save to Markdown
    md_content = "# Phase 6D: Deterministic Case Studies on Threat Actor Attribution (`cti-taa`)\n\n"
    md_content += "Selection rule: First 5 rows where Vrel wins over V0h, and first 3 rows where Vrel loses.\n"
    md_content += "All detected entity spans asserted to exist verbatim within query text.\n\n"

    for cs in case_studies:
        ans_vrel = cs['model_answer_vrel']
        ans_v0h = cs['model_answer_v0h']
        md_content += f"### {cs['category']}: Row {cs['row_idx']} ({cs['query_id']})\n"
        md_content += f"- **Ground Truth Threat Group**: `{cs['ground_truth']}`\n"
        md_content += f"- **Detected Software in Query**: {', '.join(cs['detected_software']) if cs['detected_software'] else 'None detected'}\n"
        md_content += f"- **Top-3 Voted Groups (via STIX uses relationships)**: {', '.join(cs['top_3_voted_groups']) if cs['top_3_voted_groups'] else 'None'}\n"
        md_content += f"- **Ground-Truth Group Profile in Context**: `{cs['ground_truth_in_context']}`\n"
        md_content += f"- **Vrel Output**: {ans_vrel}\n"
        md_content += f"- **V0h Output**: {ans_v0h}\n"
        md_content += f"- **Scorer Match**: Vrel exact={cs['vrel_score']['v1_exact']}, alias={cs['vrel_score']['v2_alias']} vs V0h exact={cs['v0h_score']['v1_exact']}, alias={cs['v0h_score']['v2_alias']}\n\n"

    with open(out_dir / "case_studies_cti_taa.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Successfully generated {len(case_studies)} case studies with verbatim span assertions!")
    print(f"Saved to {out_dir / 'case_studies_cti_taa.json'} and {out_dir / 'case_studies_cti_taa.md'}")


if __name__ == "__main__":
    main()
