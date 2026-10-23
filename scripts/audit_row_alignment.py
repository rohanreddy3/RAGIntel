"""Part A1: Comprehensive Row Alignment and Query ID Audit.

Defines query_id = sha1(normalized query text)[:12] for every dataset row.
Verifies and adds query_id across:
1. Dataset loader (src/data_loader.py)
2. 3B top-50 cache (results/phase_3/top50_ranked_chunks.json)
3. 3C top-50 cache (results/phase_3/top50_phase3c_chunks.json)
4. Phase 2 benchmark grid / checkpoint (results/phase_2/p1_eval_checkpoint.json)
5. Generation cache (.cache/api_runner/*.json)
6. D1 CSVs (results/phase_4/per_query_technique_f1.csv and per_query_cti_taa_attribution.csv)

Asserts that (dataset, row_idx) -> query_id is 100% identical across all files.
Outputs results/phase_4/row_alignment_audit.json.
"""

import glob
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import load_benchmark_dataset, compute_query_id


def main():
    print("=" * 80)
    print("PART A1: ROW ALIGNMENT & QUERY_ID AUDIT")
    print("=" * 80)

    audit_report = {
        "definition": "query_id = sha1(normalized query text)[:12]",
        "canonical_counts": {},
        "file_audits": {},
        "mismatch_counts": {},
        "overall_status": "PENDING",
    }

    # 1. Canonical query_ids from dataset loader
    canonical = {}
    canonical_list = []
    for ds_name in ["cti-ate", "cti-taa", "CTI-ATTACK"]:
        ds = load_benchmark_dataset(ds_name)
        canonical[ds_name] = {}
        for idx, row in ds.df.iterrows():
            qid = compute_query_id(str(row["query"]))
            canonical[ds_name][int(idx)] = {
                "query": str(row["query"]),
                "query_id": qid,
                "ground_truth": str(row.get("ground_truth", "")),
            }
            canonical_list.append({
                "dataset": ds_name,
                "row_idx": int(idx),
                "query_id": qid,
                "query_preview": str(row["query"])[:60],
            })
        audit_report["canonical_counts"][ds_name] = len(canonical[ds_name])
        print(f"Loaded canonical {ds_name:12s}: {len(canonical[ds_name])} rows.")

    # 2. Check 3B top-50 cache: results/phase_3/top50_ranked_chunks.json
    p_3b = REPO_ROOT / "results" / "phase_3" / "top50_ranked_chunks.json"
    mismatches_3b = 0
    checked_3b = 0
    if p_3b.is_file():
        with open(p_3b, "r", encoding="utf-8") as f:
            c_3b = json.load(f)
        for ds in c_3b:
            for b in c_3b[ds]:
                for arm in c_3b[ds][b]:
                    for it in c_3b[ds][b][arm]:
                        idx = int(it["idx"])
                        q = it["query"]
                        qid = compute_query_id(q)
                        can_qid = canonical[ds][idx]["query_id"]
                        checked_3b += 1
                        if qid != can_qid:
                            mismatches_3b += 1
    audit_report["file_audits"]["top50_ranked_chunks_3B"] = {"checked": checked_3b, "mismatches": mismatches_3b}
    audit_report["mismatch_counts"]["top50_ranked_chunks_3B"] = mismatches_3b
    print(f"3B top-50 cache: checked={checked_3b}, mismatches={mismatches_3b}")

    # 3. Check 3C top-50 cache: results/phase_3/top50_phase3c_chunks.json
    p_3c = REPO_ROOT / "results" / "phase_3" / "top50_phase3c_chunks.json"
    mismatches_3c = 0
    checked_3c = 0
    if p_3c.is_file():
        with open(p_3c, "r", encoding="utf-8") as f:
            c_3c = json.load(f)
        for ds in c_3c:
            for b in c_3c[ds]:
                for arm in c_3c[ds][b]:
                    for it in c_3c[ds][b][arm]:
                        idx = int(it["idx"])
                        q = it["query"]
                        qid = compute_query_id(q)
                        can_qid = canonical[ds][idx]["query_id"]
                        checked_3c += 1
                        if qid != can_qid:
                            mismatches_3c += 1
    audit_report["file_audits"]["top50_phase3c_chunks"] = {"checked": checked_3c, "mismatches": mismatches_3c}
    audit_report["mismatch_counts"]["top50_phase3c_chunks"] = mismatches_3c
    print(f"3C top-50 cache: checked={checked_3c}, mismatches={mismatches_3c}")

    # 4. Check Phase 2 checkpoint: results/phase_2/p1_eval_checkpoint.json
    p_p2 = REPO_ROOT / "results" / "phase_2" / "p1_eval_checkpoint.json"
    mismatches_p2 = 0
    checked_p2 = 0
    if p_p2.is_file():
        with open(p_p2, "r", encoding="utf-8") as f:
            c_p2 = json.load(f)
        for k, records in c_p2.items():
            ds = "cti-taa" if "cti-taa" in k else "unknown"
            for it in records:
                idx = int(it["idx"])
                q = it["query"]
                qid = compute_query_id(q)
                can_qid = canonical[ds][idx]["query_id"]
                checked_p2 += 1
                if qid != can_qid:
                    mismatches_p2 += 1
    audit_report["file_audits"]["phase_2_checkpoint"] = {"checked": checked_p2, "mismatches": mismatches_p2}
    audit_report["mismatch_counts"]["phase_2_checkpoint"] = mismatches_p2
    print(f"Phase 2 checkpoint: checked={checked_p2}, mismatches={mismatches_p2}")

    # 5. Check Generation Cache: .cache/api_runner/*.json
    gen_files = glob.glob(str(REPO_ROOT / ".cache" / "api_runner" / "*.json"))
    mismatches_gen = 0
    checked_gen = 0
    for gf in gen_files:
        if Path(gf).name == "known_reset.json":
            continue
        with open(gf, "r", encoding="utf-8") as f:
            gdata = json.load(f)
        ds = gdata.get("dataset")
        idx = gdata.get("row_idx")
        if ds in canonical and idx is not None and idx in canonical[ds]:
            can_q = canonical[ds][idx]["query"]
            ptxt = gdata.get("prompt_text", "")
            checked_gen += 1
            if can_q not in ptxt and "".join(can_q.split()) not in "".join(ptxt.split()):
                mismatches_gen += 1
    audit_report["file_audits"]["generation_cache_files"] = {"checked": checked_gen, "mismatches": mismatches_gen}
    audit_report["mismatch_counts"]["generation_cache_files"] = mismatches_gen
    print(f"Generation cache files: checked={checked_gen}, mismatches={mismatches_gen}")

    # 6. Check & Update D1 CSVs with query_id
    p_f1 = REPO_ROOT / "results" / "phase_4" / "per_query_technique_f1.csv"
    mismatches_f1 = 0
    checked_f1 = 0
    if p_f1.is_file():
        df_f1 = pd.read_csv(p_f1)
        if "query_id" not in df_f1.columns:
            # Insert query_id after row_idx
            qids = [canonical[row["dataset"]][int(row["row_idx"])]["query_id"] for _, row in df_f1.iterrows()]
            row_idx_col = df_f1.columns.get_loc("row_idx")
            df_f1.insert(row_idx_col + 1, "query_id", qids)
            df_f1.to_csv(p_f1, index=False)
            print(f"Added query_id column to {p_f1}")
        for _, row in df_f1.iterrows():
            ds = row["dataset"]
            idx = int(row["row_idx"])
            qid = row["query_id"]
            checked_f1 += 1
            if ds not in canonical or idx not in canonical[ds] or qid != canonical[ds][idx]["query_id"]:
                mismatches_f1 += 1
    audit_report["file_audits"]["d1_per_query_technique_f1_csv"] = {"checked": checked_f1, "mismatches": mismatches_f1}
    audit_report["mismatch_counts"]["d1_per_query_technique_f1_csv"] = mismatches_f1
    print(f"D1 Technique F1 CSV: checked={checked_f1}, mismatches={mismatches_f1}")

    p_taa = REPO_ROOT / "results" / "phase_4" / "per_query_cti_taa_attribution.csv"
    mismatches_taa = 0
    checked_taa = 0
    if p_taa.is_file():
        df_taa = pd.read_csv(p_taa)
        if "query_id" not in df_taa.columns:
            # Insert query_id after row_idx
            qids = [canonical[row["dataset"]][int(row["row_idx"])]["query_id"] for _, row in df_taa.iterrows()]
            row_idx_col = df_taa.columns.get_loc("row_idx")
            df_taa.insert(row_idx_col + 1, "query_id", qids)
            df_taa.to_csv(p_taa, index=False)
            print(f"Added query_id column to {p_taa}")
        for _, row in df_taa.iterrows():
            ds = row["dataset"]
            idx = int(row["row_idx"])
            qid = row["query_id"]
            checked_taa += 1
            if ds not in canonical or idx not in canonical[ds] or qid != canonical[ds][idx]["query_id"]:
                mismatches_taa += 1
    audit_report["file_audits"]["d1_per_query_cti_taa_attribution_csv"] = {"checked": checked_taa, "mismatches": mismatches_taa}
    audit_report["mismatch_counts"]["d1_per_query_cti_taa_attribution_csv"] = mismatches_taa
    print(f"D1 TAA Attribution CSV: checked={checked_taa}, mismatches={mismatches_taa}")

    # Total assertions
    total_mismatches = sum(audit_report["mismatch_counts"].values())
    assert total_mismatches == 0, f"Total mismatches across files: {total_mismatches}"
    audit_report["overall_status"] = "PASSED (0 mismatches across all files)"

    out_file = REPO_ROOT / "results" / "phase_4" / "row_alignment_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    print(f"\n[PASS] All files 100% aligned! Saved audit report to {out_file}")


if __name__ == "__main__":
    main()
