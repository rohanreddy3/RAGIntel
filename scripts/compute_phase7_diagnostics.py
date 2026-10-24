"""Phase 7: Optimization 2 Redesign Diagnostics (Part A).

Descriptive diagnostic evaluation across Phase 5 baseline arms:
- E0'-k200
- E0'-TECH-k200
- E1a
- E1-MIXED
Across datasets (cti-ate, CTI-ATTACK) at budgets B in {500, 1000} tokens.

Metrics (descriptive only, no causal language):
1. Mean tokens per chunk entering packed context
2. Share of chunks containing technique ID string (matching T\\d{4}(?:\\.\\d{3})?)
3. Mean distinct technique IDs per context
4. Mean chunks per context from the same technique
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd
from langchain_core.documents import Document

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.chunking import count_tokens, truncate_to_token_budget, extract_parent_technique_id
from src.retrieval_eval import extract_technique_ids_from_text

PAT_TECH_ID = re.compile(r"T\d{4}(?:\.\d{3})?")


def deserialize_docs(doc_list: List[Dict[str, Any]]) -> List[Document]:
    """Deserialize dict representations into LangChain Document objects."""
    return [
        Document(
            page_content=d.get("page_content", d.get("content", "")),
            metadata=d.get("metadata", {}),
        )
        for d in doc_list
    ]


def compute_diagnostics_for_cell(
    records: List[Dict[str, Any]],
    budget_tokens: int,
) -> Dict[str, Any]:
    """Compute the 4 required diagnostics for a set of query records at budget B."""
    all_chunk_tokens: List[int] = []
    has_id_count = 0
    total_chunks = 0
    distinct_techs_per_q: List[int] = []
    chunks_per_tech_per_q: List[float] = []

    for q in records:
        raw_docs = deserialize_docs(q.get("top200", q.get("top50", [])))
        final_docs = truncate_to_token_budget(raw_docs, budget_tokens=budget_tokens)

        q_distinct_techs: Set[str] = set()
        tech_counts: Dict[str, int] = defaultdict(int)

        for d in final_docs:
            tok = count_tokens(d.page_content)
            all_chunk_tokens.append(tok)
            total_chunks += 1
            if PAT_TECH_ID.search(d.page_content):
                has_id_count += 1

            # Extract technique IDs for distinct technique count
            t_ids = extract_technique_ids_from_text(d.page_content)
            m_id = str(d.metadata.get("mitre_id", "")).strip()
            if m_id.startswith("T"):
                t_ids.add(m_id)
            parent_ids = {extract_parent_technique_id(t) for t in t_ids if t and t.startswith("T")}
            q_distinct_techs.update(parent_ids)

            # Primary technique from metadata for chunks-per-technique
            prim_tech = d.metadata.get("technique_id") or extract_parent_technique_id(d.metadata.get("mitre_id", ""))
            if prim_tech and prim_tech.startswith("T"):
                tech_counts[prim_tech] += 1

        distinct_techs_per_q.append(len(q_distinct_techs))

        if tech_counts:
            avg_c_per_t = sum(tech_counts.values()) / len(tech_counts)
            chunks_per_tech_per_q.append(avg_c_per_t)
        elif len(q_distinct_techs) > 0:
            chunks_per_tech_per_q.append(len(final_docs) / len(q_distinct_techs))
        else:
            chunks_per_tech_per_q.append(0.0)

    mean_tok = sum(all_chunk_tokens) / len(all_chunk_tokens) if all_chunk_tokens else 0.0
    share_id = (has_id_count / total_chunks) if total_chunks else 0.0
    mean_dist = sum(distinct_techs_per_q) / len(distinct_techs_per_q) if distinct_techs_per_q else 0.0
    mean_c_per_t = sum(chunks_per_tech_per_q) / len(chunks_per_tech_per_q) if chunks_per_tech_per_q else 0.0

    return {
        "mean_tokens_per_chunk": round(mean_tok, 2),
        "share_chunks_with_id_pct": round(share_id * 100, 2),
        "mean_distinct_tech_ids": round(mean_dist, 2),
        "mean_chunks_per_tech": round(mean_c_per_t, 2),
        "total_chunks_evaluated": total_chunks,
    }


def run_diagnostics():
    print("=" * 80)
    print("PHASE 7 PART A: OPTIMIZATION 2 REDESIGN DIAGNOSTICS")
    print("=" * 80)

    top200_path = REPO_ROOT / "results" / "phase_5" / "top200_hd_chunks.json"
    top50_path = REPO_ROOT / "results" / "phase_5" / "top50_hd_chunks.json"

    with open(top200_path, "r", encoding="utf-8") as f:
        d200 = json.load(f)
    with open(top50_path, "r", encoding="utf-8") as f:
        d50 = json.load(f)

    datasets = ["cti-ate", "CTI-ATTACK"]
    arms = [
        ("E0_prime_k200", "E0'-k200", d200),
        ("E0_prime_tech_k200", "E0'-TECH-k200", d200),
        ("E1a", "E1a", d50),
        ("E1_mixed", "E1-MIXED", d50),
    ]
    budgets = [500, 1000]

    rows = []
    detailed_results = {}

    for ds in datasets:
        detailed_results[ds] = {}
        for b in budgets:
            detailed_results[ds][str(b)] = {}
            for arm_key, arm_label, source_dict in arms:
                records = source_dict[ds]["B2"][arm_key]
                diag = compute_diagnostics_for_cell(records, budget_tokens=b)
                detailed_results[ds][str(b)][arm_label] = diag

                rows.append({
                    "dataset": ds,
                    "arm": arm_label,
                    "budget_tokens": b,
                    "mean_tokens_per_chunk": diag["mean_tokens_per_chunk"],
                    "share_chunks_with_technique_id_pct": diag["share_chunks_with_id_pct"],
                    "mean_distinct_technique_ids": diag["mean_distinct_tech_ids"],
                    "mean_chunks_per_technique": diag["mean_chunks_per_tech"],
                    "total_chunks_in_context": diag["total_chunks_evaluated"],
                })

    df_diag = pd.DataFrame(rows)

    assets_dir = REPO_ROOT / "results" / "phase_7" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    csv_path = assets_dir / "table_diagnostics_o2.csv"
    df_diag.to_csv(csv_path, index=False)
    print(f"Saved diagnostics table to {csv_path}")

    json_path = REPO_ROOT / "results" / "phase_7" / "diagnostics_o2.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(detailed_results, f, indent=2)
    print(f"Saved detailed diagnostics JSON to {json_path}")

    print("\n" + "=" * 80)
    print("O2 DIAGNOSTICS SUMMARY TABLE")
    print("=" * 80)
    print(df_diag.to_string(index=False))


if __name__ == "__main__":
    run_diagnostics()
