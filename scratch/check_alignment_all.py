import glob
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from src.data_loader import load_benchmark_dataset, compute_query_id

def main():
    print("=" * 80)
    print("STEP A1: COMPREHENSIVE ROW ALIGNMENT & QUERY_ID AUDIT")
    print("=" * 80)

    # 1. Canonical query_ids from dataset loader
    canonical = {}
    for ds_name in ["cti-ate", "cti-taa", "CTI-ATTACK"]:
        ds = load_benchmark_dataset(ds_name)
        canonical[ds_name] = {}
        for idx, row in ds.df.iterrows():
            canonical[ds_name][int(idx)] = {
                "query": str(row["query"]),
                "query_id": row["query_id"],
                "ground_truth": str(row.get("ground_truth", "")),
            }
        print(f"Dataset {ds_name:12s}: {len(canonical[ds_name])} canonical rows loaded.")

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
                            print(f"[MISMATCH 3B] ds={ds} b={b} arm={arm} idx={idx}: {qid} vs {can_qid}")
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
                            print(f"[MISMATCH 3C] ds={ds} b={b} arm={arm} idx={idx}: {qid} vs {can_qid}")
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
                    print(f"[MISMATCH P2] key={k} idx={idx}: {qid} vs {can_qid}")
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
            can_qid = canonical[ds][idx]["query_id"]
            # prompt_text contains query text
            ptxt = gdata.get("prompt_text", "")
            can_q = canonical[ds][idx]["query"]
            checked_gen += 1
            if can_q not in ptxt:
                # check if query without whitespace is in prompt
                if "".join(can_q.split()) not in "".join(ptxt.split()):
                    mismatches_gen += 1
                    print(f"[MISMATCH GEN] file={Path(gf).name} ds={ds} idx={idx}")
    print(f"Generation cache files: checked={checked_gen}, mismatches={mismatches_gen}")

    # 6. Check D1 CSVs
    p_f1 = REPO_ROOT / "results" / "phase_4" / "per_query_technique_f1.csv"
    mismatches_f1 = 0
    checked_f1 = 0
    if p_f1.is_file():
        df_f1 = pd.read_csv(p_f1)
        for _, row in df_f1.iterrows():
            ds = row["dataset"]
            idx = int(row["row_idx"])
            checked_f1 += 1
            if ds not in canonical or idx not in canonical[ds]:
                mismatches_f1 += 1
    print(f"D1 Technique F1 CSV: checked={checked_f1}, mismatches={mismatches_f1}")

    p_taa = REPO_ROOT / "results" / "phase_4" / "per_query_cti_taa_attribution.csv"
    mismatches_taa = 0
    checked_taa = 0
    if p_taa.is_file():
        df_taa = pd.read_csv(p_taa)
        for _, row in df_taa.iterrows():
            ds = row["dataset"]
            idx = int(row["row_idx"])
            checked_taa += 1
            if ds not in canonical or idx not in canonical[ds]:
                mismatches_taa += 1
            else:
                gt = str(row["ground_truth"]).strip()
                can_gt = canonical[ds][idx]["ground_truth"].strip()
                if gt != can_gt:
                    mismatches_taa += 1
                    print(f"[MISMATCH TAA GT] idx={idx}: {gt!r} vs {can_gt!r}")
    print(f"D1 TAA Attribution CSV: checked={checked_taa}, mismatches={mismatches_taa}")

if __name__ == "__main__":
    main()
